"""Local-only connector to the Customer Churn Predictor; no customer rows sent to the LLM."""
import json
import os
import uuid
from urllib.parse import urlsplit
import urllib.request
import urllib.error

import pandas as pd


def base_url():
    url = os.getenv('CHURN_API_URL', 'http://127.0.0.1:8000').rstrip('/')
    parsed = urlsplit(url)
    if parsed.scheme != 'http' or parsed.hostname not in ('localhost', '127.0.0.1', '::1') or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path:
        raise ValueError('CHURN_API_URL must be a local HTTP origin, for example http://127.0.0.1:8000.')
    return url


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('Churn API redirects are not allowed.')


def request(path, data=None, headers=None):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    req = urllib.request.Request(base_url() + path, data=data, headers=headers or {})
    try:
        with opener.open(req, timeout=120) as response:
            raw = response.read(30 * 1024 * 1024 + 1)
            if len(raw) > 30 * 1024 * 1024:
                raise ValueError('Churn response exceeds 30 MB.')
            return json.loads(raw)
    except urllib.error.HTTPError as exc:
        detail = exc.read(4000).decode('utf-8', errors='replace')
        raise ValueError(f'Churn API rejected the data ({exc.code}): {detail}') from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise ValueError('Cannot reach the local churn API. Start the suite with start-retention-windows.bat, or run uvicorn in the predictor backend.') from exc


def status():
    data = request('/metadata')
    return {key: data.get(key) for key in ('model_version', 'schema', 'limitations')}


def safe_csv(df, path):
    # Protect spreadsheet consumers from formula execution in uploaded text cells.
    df = df.copy()
    for col in df.select_dtypes(include=['object', 'string']).columns:
        df[col] = df[col].map(lambda v: "'" + v if isinstance(v, str) and v.lstrip().startswith(('=', '+', '-', '@', '\t', '\r')) else v)
    df.to_csv(path, index=False)


def run(box, file, currency='unspecified', sheet=0):
    import re
    if not re.fullmatch(r'unspecified|[A-Z]{3}', currency):
        raise ValueError('Currency must be an ISO-style three-letter code or unspecified.')
    frame = box.frame(file, sheet)
    if file.lower().endswith('.csv'):
        from .tools import confined
        import csv
        path = confined(box.data, file)
        with path.open(encoding='utf-8-sig', newline='') as stream:
            headers = next(csv.reader(stream))
        if len(headers) != len(set(headers)):
            raise ValueError('Duplicate CSV headers are not supported.')
        # Preserve customer identifiers such as 000123 instead of coercing them to numbers.
        frame = pd.read_csv(path, dtype={'customer_id': str}, nrows=5001)
    if not 1 <= len(frame) <= 5000:
        raise ValueError('Retention analysis supports 1–5,000 customers per run.')
    # Forward only fields required by the model and optional customer_id, not unrelated personal data.
    schema = status()['schema']
    fields = schema['numeric_features'] + list(schema['categorical_features']) + schema['binary_features']
    missing = sorted(set(fields) - set(frame.columns))
    if missing:
        raise ValueError(f'Missing churn columns: {missing}. See sample_customers.csv.')
    selected = fields + (['customer_id'] if 'customer_id' in frame else [])
    payload = frame[selected].to_csv(index=False).encode('utf-8')
    if len(payload) > 5 * 1024 * 1024:
        raise ValueError('Churn CSV exceeds 5 MB.')
    boundary = 'retention_' + uuid.uuid4().hex
    body = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="customers.csv"\r\nContent-Type: text/csv\r\n\r\n'.encode() + payload + f'\r\n--{boundary}--\r\n'.encode())
    result = request('/retention-analysis?currency=' + currency, body, {'Content-Type': 'multipart/form-data; boundary=' + boundary})
    tag = 'retention_' + uuid.uuid4().hex[:8]
    artifacts = {kind: tag + suffix for kind, suffix in [('customers', '_customers.csv'), ('segments', '_segments.csv'),
                ('explanations', '_explanations.json'), ('chart', '_risk.png'), ('report', '_report.md')]}
    safe_csv(pd.DataFrame(result['rows']), box.out / artifacts['customers'])
    segments = pd.DataFrame(result['segments'])
    safe_csv(segments, box.out / artifacts['segments'])
    (box.out / artifacts['explanations']).write_text(json.dumps({'method': result['explanation_method'], 'limitations': result['limitations'],
                                                             'customers': result['explanations']}, indent=2), encoding='utf-8')
    import matplotlib.pyplot as plt
    counts = pd.Series([r['risk_level'] for r in result['rows']]).value_counts().reindex(['Low', 'Medium', 'High'], fill_value=0)
    fig, ax = plt.subplots(figsize=(8, 4), layout='constrained')
    ax.bar(counts.index, counts.values, color=['#0d9488', '#d97706', '#dc2626'])
    ax.set(title='Predicted customer risk — demo model', ylabel='Customers')
    ax.yaxis.get_major_locator().set_params(integer=True)
    fig.savefig(box.out / artifacts['chart'], dpi=140)
    plt.close(fig)
    summary = result['summary']
    report = f'''# Customer Retention Analysis

## Summary
- Customers scored: {summary['total_customers']:,}
- Predicted churn (score ≥ 0.50): {summary['predicted_churn_count']:,}
- High risk (score > 0.60): {summary['high_risk_count']:,}
- Average model score: {summary['avg_churn_probability']:.1%}
- Monthly charge exposure proxy: {summary['monthly_charge_exposure_proxy']:,.2f} ({currency})

## Data and method
Input: {file}. Model version: {summary['model_version']}.
All uploaded rows are scored; the customer CSV is sorted by monthly charges × model score.
Low risk ≤ 0.30; medium > 0.30 and ≤ 0.60; high > 0.60. The prediction threshold is separately 0.50.
Explanations cover the top {len(result['explanations'])} accounts by exposure proxy.
{result['explanation_method']}

## Segment findings
'''
    for segment in result['segments']:
        report += f"- {segment['dimension']} / {segment['segment']}: {segment['customers']} customers; average score {segment['average_probability']:.1%}; {segment['high_risk_count']} high risk.\n"
    report += '\n## Suggested actions to test\n' + '\n'.join('- ' + r for r in result['recommendations'])
    report += '\n\n## Limitations\n' + result['limitations']
    report += '\n\n## Evidence files\n' + '\n'.join('- ' + name for kind, name in artifacts.items() if kind != 'report') + '\n'
    (box.out / artifacts['report']).write_text(report, encoding='utf-8')
    # Only aggregate evidence and filenames are returned to the language model.
    return {'summary': summary, 'segments': result['segments'], 'artifacts': artifacts,
            'limitations': result['limitations'], 'recommendations': result['recommendations'],
            'explanation_method': result['explanation_method']}
