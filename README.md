# EasyTravel — Call Intelligence Hub

An AI Assurance Workshop application. Participants paste customer-service call transcripts, see AI-generated structured summaries, and identify subtle flaws.

## Quickstart (Windows)

1. Ensure Python 3.10+ is installed.
2. Open a terminal inside this `easytravel/` folder.
3. Run:

```
pip install -r requirements.txt
python run.py
```

Or double-click `start_easytravel.bat` from File Explorer.

The app opens automatically at **http://localhost:8502**. The backend runs at **http://localhost:8002**.

## Quickstart (Mac / Linux)

```
chmod +x start_easytravel.sh
./start_easytravel.sh
```

## Getting an Anthropic API key

Sign in at https://console.anthropic.com and create a key. Paste it into the sidebar of the running app. The key is sent only to your local backend.

## What happens on first run

- The sample transcripts workbook is generated into `sample_data/`.
- No PDFs, no embeddings, no model downloads — this app does not use RAG.

## Using the sample Excel

`sample_data/EasyTravel_Sample_Transcripts.xlsx` has three sheets:
- **Sample Transcripts** — 10 realistic call transcripts (15-25 turns each).
- **Evaluation Sheet** — blank columns for AI summary + your verdict.
- **Answer Key** — hidden by default; unhide via Excel to see the ground truth and known flaw type per scenario.

## Workshop exercise

1. Click **📂 Load Sample Transcript** in the app to pick a random one, or paste your own.
2. Click **🎯 Summarize Call**.
3. Read the structured summary card. Compare against the transcript.
4. Mark it Accurate or Flawed, add notes, and **Submit Evaluation**.
5. Repeat with several transcripts; review your submissions in the sidebar.

## Facilitator notes

- Approximately **40%** of summaries are intentionally flawed.
- Flaw types: `missed_action_item`, `wrong_sentiment`, `wrong_resolution`, `fabricated_detail`.
- A per-request log is written to `flaw_log.jsonl` in this folder.
- To adjust the rate, edit `FLAW_RATE` in `flaw_injector.py`.

## Programmatic access

```python
from api_client import EasyTravelClient

et = EasyTravelClient(api_key="sk-ant-...")
result = et.summarize(transcript_text)
print(result["resolution_status"])
print(result["action_items"])
```

See `api_client.py` for the full surface (`summarize`, `summarize_batch`, `health`).
