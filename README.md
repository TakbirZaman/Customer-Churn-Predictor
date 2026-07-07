# Churn Radar — Customer Churn Prediction System

A full-stack machine learning application that predicts customer churn risk in real time —
one customer at a time, or in bulk from a CSV upload.

**Stack:** FastAPI + scikit-learn (model API) · Next.js 15 + TypeScript + Tailwind (dashboard)

---

## What's included

```
churn-predictor/
├── ml/
│   ├── generate_data.py       # synthetic demo dataset generator
│   ├── train_model.py         # trains the model, exports all artifacts
│   └── customer_churn.csv     # generated training data (5,000 rows)
├── backend/
│   ├── app.py                 # FastAPI server (predict, predict-batch, metadata)
│   ├── requirements.txt
│   ├── churn_model.pkl        # trained Random Forest classifier
│   ├── preprocessor.pkl       # fitted scaler + one-hot encoder
│   ├── metrics.json           # accuracy / precision / recall / ROC-AUC
│   ├── feature_importance.json
│   └── schema.json            # drives the frontend form automatically
├── frontend/                  # Next.js dashboard
└── sample_customers.csv       # sample file to test bulk upload
```

## Model performance

Trained on 5,000 synthetic customer records (37% churn rate) with a Random Forest classifier:

| Metric | Score |
|---|---|
| ROC-AUC | 0.80 |
| Accuracy | 0.72 |
| Precision | 0.61 |
| Recall | 0.70 |
| F1 | 0.65 |

Top churn drivers: tenure, monthly charges, total charges, support call volume, and
month-to-month contract type — all consistent with real-world telecom churn research.

## Running it locally

**1. Backend**
```bash
cd backend
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```
API docs auto-generated at `http://localhost:8000/docs`.

> The model was trained and pickled with the exact `scikit-learn==1.5.2` pinned in
> `requirements.txt`. If you ever see an `InconsistentVersionWarning` on startup, it means
> your installed scikit-learn drifted from that pin — re-run `python ml/train_model.py`
> with the pinned version installed to regenerate matching artifacts.

**2. Frontend**
```bash
cd frontend
npm install
cp .env.local.example .env.local   # points to the backend URL
npm run dev
```
Open `http://localhost:3000`.

## Using it with a real client dataset

This ships with realistic **synthetic** data so it works out of the box with no setup.
To go live with a client's actual customers:

1. Replace `ml/customer_churn.csv` with their export — same column names, or update
   `train_model.py`'s `numeric_features` / `categorical_features` lists to match theirs.
2. Re-run `python train_model.py`. It regenerates `churn_model.pkl`, `schema.json`, etc.
3. Restart the backend. The frontend form and validation update automatically because
   it reads `schema.json` through the `/metadata` endpoint — no frontend code changes needed.
4. For bulk scoring, customers upload a CSV with the same columns to the dashboard directly.

## API reference

| Endpoint | Method | Purpose |
|---|---|---|
| `/health` | GET | Liveness check |
| `/metadata` | GET | Model metrics, feature importance, input schema |
| `/predict` | POST | Score a single customer (JSON body) |
| `/predict-batch` | POST | Score a CSV of customers (multipart file upload) |

## Deployment notes

- **Backend:** any Python host that runs Uvicorn/ASGI — Render, Railway, Fly.io, or a VPS.
- **Frontend:** Vercel (zero-config for Next.js) — set `NEXT_PUBLIC_API_URL` to the deployed
  backend URL in project environment variables.
- Tighten `allow_origins` in `backend/app.py`'s CORS config to the production frontend domain
  before going live.

## Customization ideas for clients

- Swap the Random Forest for XGBoost/LightGBM if the client wants marginal accuracy gains
  on larger datasets (the preprocessing pipeline is model-agnostic).
- Add a retention-offer recommendation layer that maps risk tier → suggested action.
- Persist predictions to a database (Postgres/MongoDB) to track risk trends over time.
- Add authentication if this will be exposed outside an internal team.
