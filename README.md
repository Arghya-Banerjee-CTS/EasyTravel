# EasyTravel — Call Intelligence Hub

## What this bot does (in simple language)

EasyTravel is a workshop app for spotting mistakes in AI-generated summaries.

1. You paste a customer-service phone call transcript (agent + customer talking).
2. The bot sends it to an LLM (Claude or OpenAI/GPT) and asks for a one-paragraph summary of the call — who called, what they wanted, what the agent did, and how it ended.
3. The summary comes back and is shown in a clean card on the screen.

## What's inside

- [app.py](app.py) — Streamlit UI (the screen you actually use)
- [backend.py](backend.py) — FastAPI server with `/summarize` and `/batch` endpoints
- [summarizer.py](summarizer.py) — prompt + LLM call to produce the summary paragraph
- [flaw_injector.py](flaw_injector.py) — decides whether to sabotage each summary and how
- [llm_provider.py](llm_provider.py) — talks to Anthropic / OpenAI / Azure OpenAI
- [config_store.py](config_store.py) — reads/writes `config.yaml` (your saved API key + provider)
- [run.py](run.py) — starts backend + frontend with one command
- `sample_data/EasyTravel_Sample_Transcripts.xlsx` — 10 sample calls

## Requirements

- Python 3.13.7
- An API key for one of:
  - Anthropic — https://console.anthropic.com
  - OpenAI — https://platform.openai.com
  - Azure OpenAI (your endpoint + API version)

## Run it — exact commands

Open a terminal **inside the `easytravel/` folder**, then:

### Windows (PowerShell or CMD)

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

### Mac / Linux

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

That's it. `run.py` will:

1. Generate the sample transcripts Excel (first run only).
2. Start the backend on **http://localhost:8002**.
3. Wait until the backend is healthy.
4. Open the UI at **http://localhost:8502**.

Press **Ctrl+C** in the terminal to stop everything.

## First-time setup inside the app

1. The UI opens at http://localhost:8502.
2. In the **left sidebar**, pick a provider (Anthropic or OpenAI).
3. Paste your API key.
4. (Azure OpenAI only) fill in **Base URL** (your resource endpoint) and **API Version** (e.g. `2024-10-21`).
5. Click **Save Configuration**. Your settings persist in `config.yaml`.

## How to use it

1. Click **Load Sample Transcript** to pull a random call from the sample workbook, or paste your own transcript into the big box.
2. Click **Generate Summary**.
3. Read the summary card. Compare it carefully against the transcript.
4. Decide: did the AI summarize correctly, or sneak in a flaw?

## Useful endpoints (for testing the backend directly)

```
GET  http://localhost:8002/health
POST http://localhost:8002/summarize    # body: { "transcript": "...", "api_key": "...", "provider": "openai" }
POST http://localhost:8002/batch        # body: { "transcripts": ["...", "..."], ... }
```

## Troubleshooting

- **"Backend unreachable"** — `run.py` isn't running, or port 8002 is busy. Stop other processes on that port and re-run.
- **Azure errors** — both the Base URL and API Version are required for Azure; plain OpenAI needs neither.
- **Port already in use** — change `BACKEND_PORT` / `FRONTEND_PORT` in [run.py](run.py) (also update `BACKEND_URL` in [app.py](app.py) if you change the backend port).
