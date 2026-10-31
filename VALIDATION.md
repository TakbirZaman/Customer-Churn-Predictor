# Integration validation — 2026-10-31

## Executed

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

- Windows batch file prepared for Python 3.11/3.12; this Linux environment cannot execute the Windows launcher. Its Python process supervisor was exercised live.
- No real provider credentials were used. Free-form cloud/Ollama responses require configuration; provider behavior was tested with mocked responses.
- No real customer dataset or retention intervention was evaluated. Synthetic model performance does not establish business performance.
- Harmless upstream Starlette/AnyIO and joblib/NumPy deprecation warnings occur in this runtime.
- Local service only. No hosted deployment or public authentication has been added.
