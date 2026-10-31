# Integration validation — 2026-10-31

## Executed

GitHub Actions also verified Windows and Linux with Python 3.11: [successful cross-platform run](https://github.com/TakbirZaman/Customer-Churn-Predictor/actions/runs/41182733479). Both platforms passed the tests and live startup/sample-report checks; the dashboard build passed.

The Windows run invoked `start-retention-windows.bat --check-startup` in a fresh environment. It caught and led to a fix for Streamlit's first-run email prompt; the launcher now starts Streamlit headlessly and waits for both services to be ready. It also checks both ports before starting.

- Python 3.12, scikit-learn 1.8.0: **36 tests passed** across backend, connector, agent, persistence and Streamlit.
- Real committed model used by backend tests, including independent checks of individual feature replacement score differences.
- Invalid categories, negative/non-finite charges, fractional integer fields, missing columns, duplicate IDs/headers, empty and oversized uploads rejected.
- Connector tests verify generated reports, CSVs, PNG and JSON; unrelated email fields are not forwarded; returned LLM evidence contains aggregates rather than individual records.
- Agent tool loop exercised with a mocked language provider and real prediction/report tool.
- Streamlit retention button exercised against the real API via TestClient; new-session isolation verified. Existing sales demo and general analyst tests also pass.
- Live launcher started FastAPI and Streamlit; real HTTP CLI analysis generated all five outputs from 19 sample customers. Seven scored at or above 0.50; four exceeded 0.60. Average score 0.4299. These are synthetic sample results.
- Existing Next.js dashboard: `npm run lint`, `npx tsc --noEmit`, and `npm run build` passed.
- `git diff --check` passed.

## Limits

- The batch launcher was verified on the GitHub-hosted Windows runner with Python 3.11. A physical Windows 10 desktop and Python 3.12 on Windows were not separately tested.
- No real provider credentials were used. Free-form cloud/Ollama responses require configuration; provider behavior was tested with mocked responses.
- No real customer dataset or retention intervention was evaluated. Synthetic model performance does not establish business performance.
- Harmless upstream Starlette/AnyIO and joblib/NumPy deprecation warnings occur in this runtime.
- Local service only. No hosted deployment or public authentication has been added.
