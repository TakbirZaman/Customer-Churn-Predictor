# Validation record

Build date: 30 October 2026 (Asia/Dhaka).

## Executed successfully in the Linux build environment

- Python syntax compilation for the package.
- `python cli.py --demo`: real pandas calculations, independent sum, two CSV exports, PNG chart, Markdown report.
- `python -m pytest -q`: **20 tests passed**.
- Streamlit AppTest: initial render, sample analysis, report generation and creation of a separate new session.
- Provider tests use a deterministic fake transport; the agent itself calls the real analysis tools in integration tests.
- Demo reference: six rows, zero duplicates, total 63,000 BDT, category totals 48,000 and 15,000, monthly totals 16,000 / 30,000 / 17,000.

## Not verified live here

- Groq, Gemini, OpenRouter or Ollama inference: no user provider credentials/local model were configured.
- Live DDGS market research: external search availability is service-dependent.
- Docker runner: Docker is unavailable in this build environment. Runner implementation is included, but an actual container execution still needs validation on a Docker host.
- Windows/macOS launchers: supplied for those systems, but executed tests were on Linux.
- Visual browser screenshot review: Streamlit behavior tested using AppTest, not a full browser screenshot.
- Hosted deployment: not performed. There is no public endpoint or background 24/7 service.

## Tested package versions

pandas 2.2.3; numpy 2.3.5; matplotlib 3.10.8; openpyxl 3.1.5;
streamlit 1.66.1; python-dotenv 1.2.4; ddgs 9.16.1; pytest 9.2.0.

`requirements.txt` uses bounded compatible version ranges. The optional Docker image pins its own Python 3.11-compatible analysis libraries; it has not been built here.
