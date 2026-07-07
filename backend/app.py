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
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).parent

app = FastAPI(title="Churn Prediction API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to your frontend's domain in production
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


class Customer(BaseModel):
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
    missing = [c for c in FEATURE_COLUMNS if c not in df.columns]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing required columns: {missing}")
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
    return {"metrics": metrics, "feature_importance": feature_importance, "schema": schema}


@app.post("/predict")
def predict(customer: Customer):
    df = pd.DataFrame([customer.model_dump()])
    result = score_dataframe(df).iloc[0]
    return {
        "churn_probability": float(result["churn_probability"]),
        "risk_level": str(result["risk_level"]),
        "prediction": "Churn" if result["churn_probability"] >= 0.5 else "Stay",
    }


@app.post("/predict-batch")
async def predict_batch(file: UploadFile = File(...)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a .csv file")
    raw = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(raw))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse CSV: {e}")

    result = score_dataframe(df)
    summary = {
        "total_customers": len(result),
        "predicted_churn_count": int((result["churn_probability"] >= 0.5).sum()),
        "avg_churn_probability": round(float(result["churn_probability"].mean()), 4),
        "high_risk_count": int((result["risk_level"] == "High").sum()),
    }
    return {"summary": summary, "rows": result.to_dict(orient="records")}
