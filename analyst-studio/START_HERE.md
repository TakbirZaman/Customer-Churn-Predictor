# Start your Analyst Studio

Built for Takbir Zaman Bhuiyan from the attached Data + Business Analyst Agent plan.

## 1. Run it on Windows

1. Extract the ZIP into a normal folder (do not run inside the ZIP).
2. Install Python 3.11 or newer from https://www.python.org/downloads/ if needed.
3. Double-click **start-windows.bat**. The first run downloads dependencies.
4. Open **http://localhost:8501** if your browser does not open automatically.
5. Click **Try a complete sample analysis — no key needed**.

The demo uses real computations on synthetic sales, producing a chart, CSVs and a report. It is not an AI chatbot until a model is connected.

## 2. Connect a model

The launcher creates `.env` from `.env.example`. Open `.env` in a text editor.

For Groq, create your own key at https://console.groq.com/keys and set:

```dotenv
GROQ_API_KEY=your_actual_key_here
GROQ_MODEL=openai/gpt-oss-120b
```

Stop the app with Ctrl+C in its terminal, then run the launcher again. Never share your `.env` file or API key. Use a free-tier account and inspect your provider's quota/billing settings; this application cannot override them.

Optional backups:
- Gemini: add `GEMINI_API_KEY` and the exact current tool-capable `GEMINI_MODEL` shown in Google AI Studio. No potentially retired model is hard-coded.
- OpenRouter: add `OPENROUTER_API_KEY`. The default `openrouter/free` selects a free model; paid model IDs are rejected by this app.
- Offline AI: install Ollama, download a tool-capable local model suited to your computer, then put its exact name in `OLLAMA_MODEL`. Turn on **Local models only**. This disables cloud fallback. Downloading the model requires internet; running it requires adequate RAM and power.

You only need ONE working provider. A ChatGPT or Claude subscription is not used by this application.

## 3. Analyze your own data

Open **Data explorer**, upload a CSV, XLSX, or SQLite database, then ask:

> Inspect my uploaded file. Check missing values and duplicates. Calculate revenue by month, create a chart, and save a report. State any assumptions.

Other examples:
- “Which categories have the highest total revenue? Verify the total independently.”
- “List the tables in my SQLite database and summarize their structure using sqlite_master.”
- Enable **Allow web research**, then ask: “Assess a student-focused software service in Dhaka. Separate evidence from assumptions, cite your sources, and outline a low-cost validation plan.”

Download files in **Reports & charts**. Reload saved analyses from the sidebar. **Activity** shows the computations and model usage.

## 4. Optional custom Python

Built-in profiling, aggregation, charting and SQL work without Docker.
For model-written pandas/Python code, install and start Docker, open a terminal in this folder, then run:

```bash
docker build -f Dockerfile.runner -t analyst-python:local .
```

Turn on **Enable Docker Python**. Every execution gets a fresh container: no network, read-only inputs, no keys, limited CPU/memory, 30-second execution budget. Code reads `/data` and writes supported files to `/outputs`. Variables do not persist between executions.

## Linux / macOS

Install Python 3.11+ and venv support, then run:

```bash
bash start.sh
```

## What remains on your side

- Supply your own free API key or local Ollama model for AI chat.
- Install Docker only if you want arbitrary Python analysis.
- Keep the computer on while using the app. This package is not deployed and does not provide 24/7 hosting.

There is no guaranteed free always-on cloud computer bundled here. The application runs locally and has no subscription fee; provider quotas, internet, hardware and electricity are separate. The launchers and Windows Docker path need validation on your own Windows device.

## Customer retention integration

Use the repository's `start-retention-windows.bat` to launch the model API and this app together. If running this agent independently, first start the updated Customer-Churn-Predictor backend (`python -m uvicorn app:app --host 127.0.0.1 --port 8000`). Then open **Customer retention**, upload the provided `data/sample_customers.csv`, and run analysis. No AI key is needed for this tab.

The synthetic sample has no specified currency. Keep `unspecified`; set BDT or another code only for data whose currency you know. Download the report, customer priority list, segment breakdown, risk chart and individual model-sensitivity explanations. Chat can use `analyze_retention` with a configured provider. The model is a synthetic telecom demonstration and must be validated before business use.
