"""EasyTravel Streamlit frontend — paste a transcript, get a structured summary, evaluate it."""
from __future__ import annotations
from pathlib import Path
import random
import requests
import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
SAMPLE_XLSX = BASE_DIR / "sample_data" / "EasyTravel_Sample_Transcripts.xlsx"
BACKEND_URL = "http://localhost:8002"
REQUEST_TIMEOUT = 90

PROVIDER_OPTIONS = ["anthropic", "openai"]
PROVIDER_DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-4-6",
    "openai": "gpt-4.1-nano",
}
PROVIDER_KEY_HINTS = {
    "anthropic": "sk-ant-...",
    "openai": "sk-...",
}

SAMPLE_PLACEHOLDER = (
    "Agent: Thank you for calling EasyTravel, this is Priya. How may I help you?\n"
    "Customer: Hi, I need to cancel my flight ET-4521 to Delhi.\n"
    "Agent: I am sorry to hear that. May I know the reason for cancellation?"
)

st.set_page_config(page_title="EasyTravel Call Intelligence", page_icon="✈️", layout="wide")


def _init_state():
    if "transcript_input" not in st.session_state:
        st.session_state.transcript_input = ""
    if "last_summary" not in st.session_state:
        st.session_state.last_summary = None
    if "evaluations" not in st.session_state:
        st.session_state.evaluations = []
    if "transcript_counter" not in st.session_state:
        st.session_state.transcript_counter = 0
    if "provider" not in st.session_state:
        st.session_state.provider = "anthropic"


def _load_sample_transcripts() -> list[dict]:
    if not SAMPLE_XLSX.exists():
        return []
    try:
        df = pd.read_excel(SAMPLE_XLSX, sheet_name="Sample Transcripts")
        return df.to_dict(orient="records")
    except Exception:
        return []


def _backend_health() -> tuple[bool, str]:
    try:
        r = requests.get(f"{BACKEND_URL}/health", timeout=4)
        if r.ok:
            return True, "ok"
        return False, f"HTTP {r.status_code}"
    except Exception as e:
        return False, str(e)


def _call_summarize(transcript: str, api_key: str, provider: str, model: str, base_url: str | None = None) -> dict | None:
    payload = {
        "transcript": transcript,
        "api_key": api_key,
        "provider": provider,
        "model": model or None,
        "base_url": base_url or None,
    }
    try:
        r = requests.post(f"{BACKEND_URL}/summarize", json=payload, timeout=REQUEST_TIMEOUT)
        if r.status_code == 401:
            st.error(f"Invalid {provider.title()} API key. Please check the sidebar.")
            return None
        if not r.ok:
            try:
                detail = r.json().get("detail", r.text)
            except Exception:
                detail = r.text
            st.error(f"Backend error: {detail}")
            return None
        return r.json()
    except requests.exceptions.ConnectionError:
        st.error("Cannot reach backend at " + BACKEND_URL + ". Is run.py still running?")
        return None
    except Exception as e:
        st.error(f"Request failed: {e}")
        return None


def _sidebar() -> tuple[str, str, str, str]:
    with st.sidebar:
        st.markdown("## ✈️ EasyTravel")
        st.caption("Call Intelligence Hub")
        st.divider()

        st.markdown("### LLM Settings")
        provider = st.radio(
            "Provider",
            PROVIDER_OPTIONS,
            index=PROVIDER_OPTIONS.index(st.session_state.get("provider", "anthropic")),
            horizontal=True,
            key="provider",
            format_func=lambda x: x.title(),
        )
        model = st.text_input(
            "Model",
            value=PROVIDER_DEFAULT_MODELS.get(provider, ""),
            help="Override only if you know the model id; defaults are sensible.",
            key=f"model_{provider}",
        )
        api_key = st.text_input(
            f"{provider.title()} API Key",
            type="password",
            placeholder=PROVIDER_KEY_HINTS.get(provider, ""),
            help="Your key is sent only to the local backend.",
            key=f"api_key_{provider}",
        )
        base_url = ""
        if provider == "openai":
            base_url = st.text_input(
                "Base URL (optional)",
                value="",
                placeholder="https://api.openai.com/v1",
                help="Leave blank for public OpenAI. Set this for Azure OpenAI, an internal gateway, or any OpenAI-compatible endpoint (vLLM, LiteLLM, etc.).",
                key="base_url_openai",
            )

        st.divider()
        st.warning("⚠️ Some summaries may contain subtle flaws — that is the workshop exercise.")

        with st.expander("ℹ️ About this app", expanded=False):
            st.markdown(
                "**EasyTravel Call Intelligence** turns customer-service transcripts into "
                "structured summaries: customer issue, resolution, action items, sentiment, "
                "and key details.\n\nA configured fraction of summaries will contain a "
                "subtle, plausible flaw. Your job is to spot them.\n\n"
                "Choose between Anthropic Claude and OpenAI GPT as the backing LLM."
            )

        st.divider()

        with st.expander("📊 My Evaluations", expanded=False):
            if not st.session_state.evaluations:
                st.caption("No evaluations submitted yet.")
            else:
                df = pd.DataFrame(st.session_state.evaluations)
                st.dataframe(df, use_container_width=True, hide_index=True)

        st.divider()
        ok, info = _backend_health()
        if ok:
            st.success("Backend OK")
        else:
            st.error(f"Backend unreachable: {info}")

    return api_key, provider, model, base_url


def _render_summary_card(s: dict):
    with st.container(border=True):
        st.markdown("### Structured Summary")
        st.markdown("**📋 CUSTOMER ISSUE**")
        st.write(s.get("customer_issue", "—"))
        st.divider()

        status = s.get("resolution_status", "—")
        status_color = {
            "Resolved": "🟢",
            "Resolved with workaround": "🟢",
            "Pending": "🟡",
            "Escalated": "🟠",
            "Unresolved": "🔴",
        }.get(status, "⚪")
        st.markdown("**✅ RESOLUTION STATUS**")
        st.write(f"{status_color} {status}")
        st.divider()

        st.markdown("**📞 ACTION ITEMS**")
        items = s.get("action_items", []) or []
        if items:
            for it in items:
                st.markdown(f"- {it}")
        else:
            st.caption("(none)")
        st.divider()

        sentiment = s.get("sentiment", "—")
        sentiment_icon = {
            "Satisfied": "😊",
            "Neutral": "😐",
            "Frustrated": "😟",
            "Distressed": "😢",
        }.get(sentiment, "😐")
        st.markdown("**😊 CUSTOMER SENTIMENT**")
        st.write(f"{sentiment_icon} {sentiment}")
        st.divider()

        st.markdown("**📝 KEY DETAILS**")
        st.write(s.get("key_details", "—"))

        ctx = s.get("context") or {}
        with st.expander("🔎 Transcript metadata (what the model received)"):
            st.json(ctx)


def _evaluation_section(s: dict):
    st.divider()
    st.markdown("### Your evaluation")
    eval_choice = st.radio(
        "How does this summary look?",
        ["✅ Accurate", "❌ Contains a flaw"],
        horizontal=True,
        key=f"eval_radio_{st.session_state.transcript_counter}",
    )
    notes = st.text_area(
        "Notes (what did you notice?)",
        height=80,
        key=f"eval_notes_{st.session_state.transcript_counter}",
    )
    if st.button("Submit Evaluation", type="primary"):
        st.session_state.evaluations.append({
            "transcript_no": st.session_state.transcript_counter,
            "rating": eval_choice,
            "notes": notes,
        })
        st.success("Evaluation submitted. See the sidebar for the full list.")


def main():
    _init_state()
    api_key, provider, model, base_url = _sidebar()

    st.title("✈️ EasyTravel — Call Intelligence Hub")
    st.caption("Paste a customer-service call transcript. Get a structured summary.")

    if "pending_transcript" in st.session_state:
        st.session_state.transcript_input = st.session_state.pop("pending_transcript")

    transcript = st.text_area(
        "Paste Call Transcript Here",
        height=300,
        placeholder=SAMPLE_PLACEHOLDER,
        key="transcript_input",
    )

    c1, c2 = st.columns(2)
    with c1:
        summarize_clicked = st.button(
            "🎯 Summarize Call",
            type="primary",
            use_container_width=True,
            disabled=not transcript.strip(),
        )
    with c2:
        load_sample_clicked = st.button(
            "📂 Load Sample Transcript",
            use_container_width=True,
        )

    if load_sample_clicked:
        samples = _load_sample_transcripts()
        if samples:
            chosen = random.choice(samples)
            st.session_state.pending_transcript = chosen.get("Full_Transcript", "")
            st.session_state.last_summary = None
            st.rerun()
        else:
            st.warning("Sample transcripts file not found.")

    if summarize_clicked:
        if not api_key:
            st.error(f"Please enter your {provider.title()} API key in the sidebar.")
        else:
            with st.spinner("Generating summary..."):
                result = _call_summarize(transcript, api_key, provider, model, base_url)
            if result:
                st.session_state.last_summary = result
                st.session_state.transcript_counter += 1

    if st.session_state.last_summary:
        _render_summary_card(st.session_state.last_summary)
        _evaluation_section(st.session_state.last_summary)


if __name__ == "__main__":
    main()
