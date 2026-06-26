"""Summarization logic for EasyTravel call transcripts.

Produces a single comprehensive paragraph (`call_summary`) describing the call.
"""
from __future__ import annotations
import re
from fastapi import HTTPException

from flaw_injector import get_flaw_prompt
from llm_provider import chat as llm_chat

MAX_TOKENS = 600

SYSTEM_PROMPT_BASE = (
    "You are a call-centre summarization assistant for EasyTravel, a travel booking company. "
    "Given a transcript of a customer-service call (agent and customer turns), produce a SINGLE "
    "comprehensive paragraph that captures the entire call. The paragraph must read like a "
    "professional case note and include, woven naturally into the prose:\n"
    "- the customer's name and the agent's name\n"
    "- the customer's issue or request\n"
    "- relevant booking references, flight numbers, routes, dates, amounts, and IDs\n"
    "- what the agent did, any commitments made (callbacks, emails, refunds, escalations) with timeframes\n"
    "- the final resolution status (Resolved / Resolved with workaround / Pending / Escalated / Unresolved)\n\n"
    "Match the style and level of detail of these examples:\n"
    "Example: \"Customer Rohan Mehta requested cancellation of flight ET-4521 (BLR-DEL, 15 Jul) due to a "
    "medical reason. Agent Priya waived the cancellation fee on medical grounds and confirmed a full refund "
    "of Rs. 4,500 within 7 business days. Customer agreed to email the medical certificate within 7 days. Resolved.\"\n"
    "Example: \"Customer Vikram Iyer reported missing checked-in baggage from flight ET-2104 (DXB-MAA), PIR "
    "MAA-9981. Bag contains important medicines. Agent Ananya initiated Rs. 5,000 interim allowance and "
    "escalated to Senior Supervisor Manish Khanna (ESC-44217) with a 4-hour callback SLA. Escalated.\"\n\n"
    "Return ONLY the paragraph text. No JSON, no headings, no bullet points, no markdown."
)


def _build_system_prompt(flawed: bool, flaw_type: str | None) -> str:
    if not flawed:
        return SYSTEM_PROMPT_BASE
    flaw_instruction = get_flaw_prompt(flaw_type or "")
    return SYSTEM_PROMPT_BASE + "\n\n" + flaw_instruction


def _clean_summary(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:\w+)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
    text = re.sub(r"\s+", " ", text).strip()
    return text


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
    api_version: str | None = None,
) -> dict:
    system_prompt = _build_system_prompt(flawed, flaw_type)
    messages = [{
        "role": "user",
        "content": f"Transcript:\n\n{transcript.strip()}\n\nWrite the single-paragraph summary now.",
    }]
    raw = llm_chat(
        provider=provider,
        api_key=api_key,
        system_prompt=system_prompt,
        messages=messages,
        max_tokens=MAX_TOKENS,
        model=model,
        base_url=base_url,
        api_version=api_version,
    )
    summary = _clean_summary(raw)
    if not summary:
        raise HTTPException(status_code=502, detail="Model returned an empty summary.")
    return {
        "call_summary": summary,
        "context": _derive_context(transcript),
    }
