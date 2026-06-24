"""Summarization logic for EasyTravel call transcripts.

Builds a structured JSON-shaped prompt and dispatches to the selected LLM
provider via llm_provider.chat. Parses the JSON response into the 5 fields
required by the API: customer_issue, resolution_status, action_items,
sentiment, key_details.
"""
from __future__ import annotations
import json
import re
from fastapi import HTTPException

from flaw_injector import get_flaw_prompt
from llm_provider import chat as llm_chat

MAX_TOKENS = 1024

SYSTEM_PROMPT_BASE = (
    "You are a call-centre summarization assistant for EasyTravel, a travel booking company. "
    "Given a transcript of a customer-service call (agent and customer turns), produce a "
    "concise, structured summary as STRICT JSON with the following keys:\n"
    "  customer_issue: string (one or two sentences describing what the customer needed)\n"
    "  resolution_status: one of 'Resolved', 'Resolved with workaround', 'Pending', 'Escalated', 'Unresolved'\n"
    "  action_items: array of strings (each a concrete commitment by either party; empty array if none)\n"
    "  sentiment: one of 'Satisfied', 'Neutral', 'Frustrated', 'Distressed'\n"
    "  key_details: string (booking refs, names, amounts, dates, escalation IDs)\n\n"
    "Return ONLY the JSON object, no prose, no markdown fences."
)


def _build_system_prompt(flawed: bool, flaw_type: str | None) -> str:
    if not flawed:
        return SYSTEM_PROMPT_BASE
    flaw_instruction = get_flaw_prompt(flaw_type or "")
    return SYSTEM_PROMPT_BASE + "\n\n" + flaw_instruction


def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
        text = re.sub(r"```$", "", text).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"No JSON object found in model output: {text[:200]}")
    snippet = text[start : end + 1]
    return json.loads(snippet)


def _coerce_fields(data: dict) -> dict:
    out = {
        "customer_issue": str(data.get("customer_issue", "")).strip() or "Not stated.",
        "resolution_status": str(data.get("resolution_status", "")).strip() or "Pending",
        "action_items": [],
        "sentiment": str(data.get("sentiment", "")).strip() or "Neutral",
        "key_details": str(data.get("key_details", "")).strip() or "",
    }
    raw_items = data.get("action_items", [])
    if isinstance(raw_items, list):
        out["action_items"] = [str(x).strip() for x in raw_items if str(x).strip()]
    elif isinstance(raw_items, str) and raw_items.strip():
        out["action_items"] = [raw_items.strip()]
    return out


def _derive_context(transcript: str) -> dict:
    lines = [ln.rstrip() for ln in transcript.splitlines() if ln.strip()]
    turn_count = sum(1 for ln in lines if re.match(r"^\s*[A-Za-z][A-Za-z ]{0,20}:", ln))

    agent_name = ""
    customer_name = ""

    try:
        m_agent = re.search(r"this is\s+([A-Z][a-zA-Z]+)", transcript)
        if m_agent:
            agent_name = m_agent.group(1)
    except Exception:
        pass

    try:
        m_cust = re.search(r"\bI am\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)", transcript)
        if m_cust:
            customer_name = m_cust.group(1)
        else:
            cust_idx = transcript.find("Customer")
            if cust_idx >= 0:
                m_cust2 = re.search(
                    r"this is\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)",
                    transcript[cust_idx:],
                )
                if m_cust2:
                    customer_name = m_cust2.group(1)
    except Exception:
        pass

    excerpt_lines = lines[:6]
    excerpt = "\n".join(excerpt_lines)
    if len(transcript) > len(excerpt) + 20:
        excerpt += "\n..."
    return {
        "transcript_excerpt": excerpt,
        "turn_count": turn_count,
        "agent_name": agent_name,
        "customer_name": customer_name,
    }


def summarize(
    transcript: str,
    api_key: str,
    flawed: bool,
    flaw_type: str | None,
    provider: str = "anthropic",
    model: str | None = None,
    base_url: str | None = None,
) -> dict:
    system_prompt = _build_system_prompt(flawed, flaw_type)
    messages = [{
        "role": "user",
        "content": f"Transcript:\n\n{transcript.strip()}\n\nProduce the JSON summary now.",
    }]
    raw = llm_chat(
        provider=provider,
        api_key=api_key,
        system_prompt=system_prompt,
        messages=messages,
        max_tokens=MAX_TOKENS,
        model=model,
        base_url=base_url,
    )
    try:
        data = _extract_json(raw)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Model did not return valid JSON: {e}")

    fields = _coerce_fields(data)
    fields["context"] = _derive_context(transcript)
    return fields
