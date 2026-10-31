# Customer Churn Predictor + Analyst Studio

Predict customer churn, compare business segments, and produce retention reports from one local workspace. The existing Next.js dashboard remains available; **Analyst Studio now connects directly to the FastAPI model service**.

## Start on Windows

1. Install **Python 3.11 or 3.12** with the Python launcher (`py`).
2. Download this repository using **Code → Download ZIP**, then extract it.
3. Double-click **`start-retention-windows.bat`**. First launch installs dependencies and needs internet access.
4. Open **http://localhost:8501** → **Customer retention**.
5. Upload `sample_customers.csv`, keep currency **unspecified** for the synthetic sample, and click **Run retention analysis**.
6. Download the report, prioritized customer CSV, segment CSV, risk chart and individual explanations.

Keep the terminal open while using the application. Press Ctrl+C to stop both services. The batch launcher checks for Python 3.11, then 3.12. It does not require Node.js, Docker or an AI API key for retention analysis.

**The bundled model uses synthetic telecom data.** It demonstrates the workflow, not real-world business accuracy. Validate or retrain it using appropriate real data and a defined prediction horizon before making operational decisions.

## What is connected

| Component | Responsibility |
|---|---|
| FastAPI model service | Validated single/batch predictions, segment analysis, individual feature sensitivity |
| Analyst Studio | CSV/XLSX input, charts, downloadable evidence and reports, saved analysis sessions |
| Agent tool `analyze_retention` | Calls the local API when asked a churn or retention question |
| Next.js dashboard | Existing interactive scoring and bulk upload, now with individual sensitivity and a Studio link |

The connector sends only model-required fields and an optional customer ID to a **loopback-only** API. Aggregate results and artifact filenames go to the configured language model; individual customer records and explanations stay in local output files for this tool. Other existing agent tools can return row-level data; use local Ollama if all model processing must stay on your machine.

## Ask the business analyst

For free-form chat, configure a supported provider or local Ollama in `analyst-studio/.env` using `.env.example`, then restart. No paid API is required for the Customer retention tab or CLI command.

Example prompt after upload:

> Analyze retention for my customer file. Compare contract, tenure, spending and support-call groups. Save a report and identify which groups deserve investigation. The source currency is BDT.

The agent uses the trained model for scores and deterministic calculations for totals. Recommendations are hypotheses to test, not claims of proven churn causes or guaranteed savings.

## Manual startup

From the repository root:

```bash
python -m venv .venv-retention
# Windows: .venv-retention\Scripts\activate
# macOS/Linux: source .venv-retention/bin/activate
pip install -r requirements-retention.txt
python run_retention.py
```

Or start each separately:

```bash
cd backend
python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

```bash
cd analyst-studio
python -m streamlit run app.py --server.address 127.0.0.1
```

The separate Analyst Studio connector defaults to `http://127.0.0.1:8000`. Set `CHURN_API_URL` in its `.env` only if you use another loopback port. External hosts, credentials in URLs, redirects and environment proxies are rejected.

Optional original dashboard (with the backend running):

```bash
cd frontend
npm ci
npm run dev
```

Open http://localhost:3000. `NEXT_PUBLIC_API_URL` selects the API; `NEXT_PUBLIC_ANALYST_URL` selects the Studio link. CORS permits the two localhost dashboard origins by default.

## Command-line analysis

With the API running:

```bash
cd analyst-studio
python cli.py --retention --file ../sample_customers.csv
# Use --currency BDT only when the source data actually uses BDT.
```

Outputs and sessions are stored in `analyst-studio/.analyst/`, unless `ANALYST_HOME` is configured. The existing sales demo, general analyst chat, SQL and optional Docker tools remain available.

## Data contract and calculations

- Retention input: 1–5,000 rows, maximum 5 MB for the API CSV; use `sample_customers.csv` as the template.
- All 13 model features are required. Missing/invalid categories, negative charges, non-finite numbers, fractional integer fields, duplicate CSV headers, and duplicate or empty customer IDs are rejected.
- `customer_id` is optional. If absent, source row numbers identify customers. Unrelated columns are excluded by the agent connector.
- Risk bands: **Low ≤ 0.30**, **Medium > 0.30 and ≤ 0.60**, **High > 0.60**. Binary churn prediction separately uses **≥ 0.50**.
- The priority list sorts by **monthly charges × model score**. This is a monthly charge exposure proxy, **not expected lost revenue**, a calibrated forecast, lifetime value or ROI. Currency is never inferred.
- Segments cover contract, tenure, monthly charges and support-call count. Counts include all scored customers.
- Individual explanations replace one feature at a time with its **training-split median/mode**. The difference between the original score and replacement score indicates sensitivity to that reference. Differences are not additive; correlated features can create unrealistic combinations. These are not SHAP values or causal effects.
- Batch explanations cover the first 20 priority accounts by default (API maximum 50). All customer predictions are exported. Single prediction includes five leading sensitivity factors.
- CSV outputs escape formula-like text for spreadsheet safety. Row-level files remain local; only aggregate evidence is returned by the retention tool to chat.

## API

| Route | Result |
|---|---|
| `GET /health` | Liveness |
| `GET /metadata` | Schema, metrics, model fingerprint, global importance and limitations |
| `POST /predict` | JSON customer → score, risk band, prediction, individual sensitivity |
| `POST /predict-batch` | Multipart CSV `file` → summary and scored rows |
| `POST /retention-analysis?currency=BDT&explain_top=20` | Multipart CSV → summary, segments, priority rows, explanations and suggested actions |

Interactive API docs: http://127.0.0.1:8000/docs. This is a local single-user application, with no public authentication or hosted service configured.

## Model maintenance and tests

The committed model was serialized with scikit-learn **1.8.0**; backend dependencies now match it. To retrain on the current dataset and regenerate the training reference:

```bash
python ml/train_model.py
```

Changing data alone does not validate the model for production. Define the target/horizon, avoid leakage, evaluate calibration and held-out performance, and review subgroup outcomes.

```bash
pip install pytest httpx
python -m pytest -q
```

See [VALIDATION.md](VALIDATION.md) for checks performed and remaining environment limitations.
