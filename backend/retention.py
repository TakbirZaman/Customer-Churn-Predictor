"""Deterministic retention evidence; never treats model scores as causal effects."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from fastapi import HTTPException

MAX_ROWS = 5000
MAX_BYTES = 5 * 1024 * 1024
NOTE = ('Demo model trained on synthetic telecom data. Scores are not validated forecasts for a real business. '
        'Feature replacement measures model sensitivity, not causal reasons or guaranteed intervention effects. '
        'Monthly charge exposure is a prioritization proxy, not expected lost revenue; the model has no defined forecast horizon.')


def validate_frame(df, customer_type, features):
    if df.empty or len(df) > MAX_ROWS:
        raise HTTPException(400, f'Provide 1–{MAX_ROWS} customers per batch.')
    if len(df.columns) > 150 or df.columns.duplicated().any():
        raise HTTPException(400, 'Duplicate headers or more than 150 columns are not supported.')
    missing = sorted(set(features) - set(df.columns))
    if missing:
        raise HTTPException(400, f'Missing required columns: {missing}')
    errors = []
    from pydantic import ValidationError
    for i, row in enumerate(df[features].to_dict('records')):
        try:
            customer_type.model_validate(row)
        except ValidationError as exc:
            errors.append({'row': i + 2, 'fields': sorted({str(e['loc'][0]) for e in exc.errors()})})
            if len(errors) == 10:
                break
    if errors:
        raise HTTPException(422, {'message': 'Invalid CSV values. Row numbers include the header.', 'errors': errors})
    if 'customer_id' in df:
        ids = df.customer_id.astype('string')
        if ids.isna().any() or ids.str.strip().eq('').any() or ids.duplicated().any():
            raise HTTPException(400, 'customer_id must be non-empty and unique when supplied.')


def model_id(base):
    digest = hashlib.sha256()
    for name in ('churn_model.pkl', 'preprocessor.pkl', 'schema.json', 'explanation_reference.json'):
        digest.update((base / name).read_bytes())
    return digest.hexdigest()[:16]


def explain(df, model, preprocessor, features, reference):
    """One-at-a-time replacement against training-split median/mode reference."""
    original = model.predict_proba(preprocessor.transform(df[features]))[:, 1]
    candidates = []
    for feature in features:
        altered = df[features].copy()
        altered[feature] = reference[feature]
        candidates.append(altered)
    scores = model.predict_proba(preprocessor.transform(pd.concat(candidates, ignore_index=True)))[:, 1]
    scores = scores.reshape(len(features), len(df))
    results = []
    for row_i, (_, row) in enumerate(df.iterrows()):
        changes = []
        for col_i, feature in enumerate(features):
            delta = float(original[row_i] - scores[col_i, row_i])
            value = row[feature]
            if hasattr(value, 'item'): value = value.item()
            changes.append({'feature': feature, 'value': value, 'reference_value': reference[feature],
                            'probability_difference': round(delta, 6),
                            'direction': 'higher' if delta > 0 else 'lower' if delta < 0 else 'unchanged'})
        changes.sort(key=lambda x: abs(x['probability_difference']), reverse=True)
        results.append({'row_number': int(row.name) + 2, 'top_factors': changes[:5]})
    return results


def analyze(scored, explain_fn, version, currency, explain_top=20):
    df = scored.copy()
    df['source_row'] = np.arange(len(df)) + 2
    if 'customer_id' not in df:
        df['customer_id'] = ['row-' + str(i) for i in df.source_row]
    df['monthly_charge_exposure_proxy'] = df.monthly_charges * df.churn_probability
    priority = df.sort_values(['monthly_charge_exposure_proxy', 'churn_probability'], ascending=False, kind='stable')
    explanations = explain_fn(priority.head(explain_top)) if explain_top else []
    for item, (_, row) in zip(explanations, priority.head(explain_top).iterrows()):
        item['customer_id'] = str(row.customer_id)
    segments = []
    groups = {'contract_type': df.contract_type, 'tenure_band': pd.cut(df.tenure_months, [-1, 12, 36, 100], labels=['0–12 months', '13–36 months', '37–100 months']),
              'support_calls_band': pd.cut(df.num_support_calls, [-1, 0, 2, 20], labels=['0', '1–2', '3–20']),
              'monthly_charges_band': pd.cut(df.monthly_charges, [-1, 50, 100, float('inf')], labels=['0–50', '>50–100', '>100'])}
    for dimension, keys in groups.items():
        for label, part in df.groupby(keys, observed=True, dropna=False):
            segments.append({'dimension': dimension, 'segment': str(label), 'customers': len(part),
                             'average_probability': round(float(part.churn_probability.mean()), 4),
                             'high_risk_count': int((part.risk_level == 'High').sum()),
                             'monthly_charge_exposure_proxy': round(float(part.monthly_charge_exposure_proxy.sum()), 2)})
    summary = {'total_customers': len(df), 'predicted_churn_count': int((df.churn_probability >= .5).sum()),
               'high_risk_count': int((df.risk_level == 'High').sum()),
               'avg_churn_probability': round(float(df.churn_probability.mean()), 4),
               'monthly_charge_exposure_proxy': round(float(df.monthly_charge_exposure_proxy.sum()), 2),
               'currency': currency, 'model_version': version}
    return {'summary': summary, 'segments': segments,
            'rows': json.loads(priority.to_json(orient='records')), 'explanations': explanations,
            'explanation_method': 'One feature replaced at a time by training-split median/mode; differences do not sum to the score.',
            'limitations': NOTE,
            'recommendations': ['Review high-exposure accounts first; verify the customer record before outreach.',
                                'For customers with repeated support calls, investigate unresolved service issues.',
                                'Test voluntary plan reviews or onboarding help in a controlled retention experiment; measure outcomes before scaling.']}
