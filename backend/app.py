"""
FastAPI backend for the Customer Churn Prediction model.

Endpoints:
  GET  /health              - liveness check
  GET  /metadata             - schema, metrics, feature importance (drives the frontend form + charts)
  POST /predict               - single customer prediction
  POST /predict-batch         - CSV upload -> predictions for every row

Run:
  pip install -r requirements.txt
  uvicorn app:app --reload --port 8000
"""
import io
import json
from pathlib import Path
from typing import Literal, Optional

import joblib
import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ConfigDict
from retention import validate_frame, explain, analyze, model_id, MAX_ROWS, MAX_BYTES, NOTE

BASE_DIR = Path(__file__).parent

app = FastAPI(title="Churn Prediction API", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # tighten to your frontend's domain in production
    allow_methods=["*"],
    allow_headers=["*"],
)

model = joblib.load(BASE_DIR / "churn_model.pkl")
preprocessor = joblib.load(BASE_DIR / "preprocessor.pkl")
metrics = json.loads((BASE_DIR / "metrics.json").read_text())
feature_importance = json.loads((BASE_DIR / "feature_importance.json").read_text())
schema = json.loads((BASE_DIR / "schema.json").read_text())

FEATURE_COLUMNS = (
    schema["numeric_features"]
    + list(schema["categorical_features"].keys())
    + schema["binary_features"]
)


reference = json.loads((BASE_DIR / "explanation_reference.json").read_text())
MODEL_VERSION = model_id(BASE_DIR)


class Customer(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    tenure_months: int = Field(..., ge=0, le=100)
    monthly_charges: float = Field(..., ge=0)
    total_charges: float = Field(..., ge=0)
    num_support_calls: int = Field(..., ge=0, le=20)
    contract_type: Literal["Month-to-month", "One year", "Two year"]
    internet_service: Literal["Fiber optic", "DSL", "No"]
    payment_method: Literal["Electronic check", "Mailed check", "Bank transfer", "Credit card"]
    partner: Literal["Yes", "No"]
    dependents: Literal["Yes", "No"]
    tech_support: Literal["Yes", "No", "No internet"]
    online_security: Literal["Yes", "No", "No internet"]
    paperless_billing: Literal["Yes", "No"]
    senior_citizen: int = Field(..., ge=0, le=1)


def score_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    validate_frame(df, Customer, FEATURE_COLUMNS)
    X = df[FEATURE_COLUMNS]
    X_t = preprocessor.transform(X)
    proba = model.predict_proba(X_t)[:, 1]
    df_out = df.copy()
    df_out["churn_probability"] = proba.round(4)
    df_out["risk_level"] = pd.cut(
        proba, bins=[-0.01, 0.3, 0.6, 1.0], labels=["Low", "Medium", "High"]
    )
    return df_out


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/metadata")
def metadata():
    return {"metrics": metrics, "feature_importance": feature_importance, "schema": schema, "model_version": MODEL_VERSION, "limitations": NOTE}


@app.post("/predict")
def predict(customer: Customer):
    df = pd.DataFrame([customer.model_dump()])
    result = score_dataframe(df).iloc[0]
    return {
        "churn_probability": float(result["churn_probability"]),
        "risk_level": str(result["risk_level"]),
        "prediction": "Churn" if result["churn_probability"] >= 0.5 else "Stay",
        "explanation": explain(df, model, preprocessor, FEATURE_COLUMNS, reference)[0],
        "explanation_method": "One feature replaced at a time by training median/mode; not causal.",
        "limitations": NOTE,
    }


async def read_csv(file):
    if not (file.filename or '').lower().endswith('.csv'):
        raise HTTPException(400, 'Please upload a .csv file.')
    raw = await file.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise HTTPException(413, 'CSV exceeds 5 MB.')
    try:
        import csv
        text = raw.decode('utf-8-sig')
        headers = next(csv.reader(io.StringIO(text)))
        if len(headers) != len(set(headers)):
            raise HTTPException(400, 'Duplicate CSV headers are not supported.')
        return pd.read_csv(io.StringIO(text), nrows=MAX_ROWS + 1, dtype={'customer_id': str})
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(400, 'Could not parse CSV. Use UTF-8 with a header row.')


@app.post('/predict-batch')
async def predict_batch(file: UploadFile = File(...)):
    result = score_dataframe(await read_csv(file))
    summary = {
        'total_customers': len(result),
        'predicted_churn_count': int((result.churn_probability >= .5).sum()),
        'avg_churn_probability': round(float(result.churn_probability.mean()), 4),
        'high_risk_count': int((result.risk_level == 'High').sum()),
    }
    return {'summary': summary, 'rows': json.loads(result.to_json(orient='records'))}


@app.post('/retention-analysis')
async def retention_analysis(file: UploadFile = File(...),
                             currency: str = Query('unspecified', pattern=r'^(unspecified|[A-Z]{3})$'),
                             explain_top: int = Query(20, ge=0, le=50)):
    scored = score_dataframe(await read_csv(file))
    return analyze(scored, lambda frame: explain(frame, model, preprocessor, FEATURE_COLUMNS, reference),
                   MODEL_VERSION, currency, explain_top)
