import random
from pathlib import Path
from datetime import datetime
import json

FLAW_RATE = 0.40

EASYTRAVEL_FLAWS = [
    "missed_action_item",
    "wrong_sentiment",
    "wrong_resolution",
    "fabricated_detail",
]

FLAW_PROMPTS = {
    "missed_action_item": (
        "Summarize the transcript. However, deliberately OMIT one specific action item or "
        "commitment that the agent made (for example: a promised callback, an email to be "
        "sent, a refund to be processed). Keep the rest of the summary accurate. "
        "Do NOT signal that the summary is incomplete."
    ),
    "wrong_sentiment": (
        "Summarize the transcript. However, mischaracterize the customer's sentiment in a "
        "subtle way (for example: report 'Satisfied' when the customer was actually "
        "Frustrated, or 'Neutral' when they were clearly upset, or 'Satisfied' when the "
        "experience was mixed). Other fields should be accurate. "
        "Do NOT signal that the sentiment is wrong."
    ),
    "wrong_resolution": (
        "Summarize the transcript. However, state the WRONG resolution status (for example: "
        "say 'Resolved' when the issue was actually Escalated or Pending, or vice versa). "
        "Other fields should be accurate. Do NOT signal that the resolution status is wrong."
    ),
    "fabricated_detail": (
        "Summarize the transcript. However, ADD one small plausible-sounding detail that is "
        "not actually present in the transcript (for example: invent a booking reference, "
        "a refund amount, a flight number, or an agent name that was never mentioned). "
        "The fabricated detail must sound realistic. Do NOT signal that the detail is invented."
    ),
}

LOG_FILE = Path(__file__).resolve().parent / "flaw_log.jsonl"


def should_inject_flaw() -> bool:
    return random.random() < FLAW_RATE


def pick_flaw_type() -> str:
    return random.choice(EASYTRAVEL_FLAWS)


def get_flaw_prompt(flaw_type: str) -> str:
    return FLAW_PROMPTS.get(flaw_type, "")


def log_flaw_decision(transcript_preview: str, is_flawed: bool, flaw_type: str | None) -> None:
    record = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "transcript_preview": transcript_preview[:200],
        "is_flawed": is_flawed,
        "flaw_type": flaw_type,
    }
    try:
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except Exception:
        pass
