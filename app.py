"""EasyTravel Streamlit frontend — paste a transcript, get a comprehensive call summary."""
from __future__ import annotations
from pathlib import Path
import random
import requests
import pandas as pd
import streamlit as st

from config_store import load_config, save_config

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

COGNIZANT_NAVY = "#000048"
COGNIZANT_DARK_BLUE = "#173793"
COGNIZANT_BLUE = "#3C66CE"
COGNIZANT_TEAL = "#1E728C"
COGNIZANT_CYAN = "#36C0CF"
COGNIZANT_SOFT_BLUE = "#639BD5"
COGNIZANT_BG = "#F4F6FA"
COGNIZANT_TEXT = "#1A1A1A"

st.set_page_config(page_title="EasyTravel Call Intelligence", layout="wide", initial_sidebar_state="expanded")

CUSTOM_CSS = f"""
<style>
    [data-testid="stToolbar"],
    [data-testid="stDeployButton"],
    [data-testid="stMainMenu"],
    header [data-testid="stHeaderActionElements"],
    header button[kind="header"],
    .stAppDeployButton,
    #MainMenu {{
        display: none !important;
        visibility: hidden !important;
    }}
    header[data-testid="stHeader"] {{
        background: transparent !important;
        height: 0 !important;
    }}
    html, body, [class*="css"] {{
        font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
        color: {COGNIZANT_TEXT};
    }}
    .stApp {{
        background-color: {COGNIZANT_BG};
    }}
    section[data-testid="stSidebar"] {{
        background-color: {COGNIZANT_NAVY};
        min-width: 320px !important;
        max-width: 320px !important;
        width: 320px !important;
        transform: none !important;
        visibility: visible !important;
    }}
    [data-testid="stSidebarCollapseButton"],
    [data-testid="stSidebarCollapsedControl"],
    button[kind="headerNoPadding"][aria-label*="sidebar" i],
    button[aria-label="Close sidebar"],
    button[aria-label="Open sidebar"] {{
        display: none !important;
        visibility: hidden !important;
    }}
    section[data-testid="stSidebar"] * {{
        color: #FFFFFF !important;
    }}
    section[data-testid="stSidebar"] input,
    section[data-testid="stSidebar"] textarea {{
        background-color: #FFFFFF !important;
        color: {COGNIZANT_TEXT} !important;
    }}
    section[data-testid="stSidebar"] [data-baseweb="input"],
    section[data-testid="stSidebar"] [data-baseweb="textarea"] {{
        background-color: #FFFFFF !important;
        border: 1px solid {COGNIZANT_SOFT_BLUE} !important;
        border-radius: 4px !important;
    }}
    section[data-testid="stSidebar"] [data-baseweb="input"] *,
    section[data-testid="stSidebar"] [data-baseweb="textarea"] * {{
        border: none !important;
        box-shadow: none !important;
        background-color: transparent !important;
    }}
    section[data-testid="stSidebar"] [data-baseweb="input"] input,
    section[data-testid="stSidebar"] [data-baseweb="textarea"] textarea {{
        background-color: #FFFFFF !important;
        color: {COGNIZANT_TEXT} !important;
        -webkit-text-fill-color: {COGNIZANT_TEXT} !important;
        outline: none !important;
    }}
    section[data-testid="stSidebar"] [data-baseweb="input"]:focus-within,
    section[data-testid="stSidebar"] [data-baseweb="textarea"]:focus-within {{
        border-color: {COGNIZANT_CYAN} !important;
        box-shadow: none !important;
        outline: none !important;
    }}
    [data-baseweb="base-input"] {{
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }}
    input:focus, textarea:focus, button:focus,
    input:focus-visible, textarea:focus-visible, button:focus-visible {{
        outline: none !important;
        box-shadow: none !important;
    }}
    div[data-testid="stAppViewContainer"] :not(section[data-testid="stSidebar"]) [data-baseweb="input"] > div > div {{
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }}
    div[data-testid="stAppViewContainer"] label,
    div[data-testid="stAppViewContainer"] [data-testid="stWidgetLabel"] p {{
        color: {COGNIZANT_NAVY} !important;
        font-weight: 600 !important;
    }}
    div[data-testid="stAppViewContainer"] :not(section[data-testid="stSidebar"]) [data-baseweb="textarea"] {{
        background-color: #FFFFFF !important;
        border: 1px solid {COGNIZANT_SOFT_BLUE} !important;
        border-radius: 6px !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.04);
    }}
    div[data-testid="stAppViewContainer"] :not(section[data-testid="stSidebar"]) [data-baseweb="textarea"]:focus-within {{
        border-color: {COGNIZANT_BLUE} !important;
        box-shadow: 0 0 0 2px rgba(60,102,206,0.15) !important;
    }}
    div[data-testid="stAppViewContainer"] :not(section[data-testid="stSidebar"]) [data-baseweb="textarea"] textarea,
    div[data-testid="stAppViewContainer"] :not(section[data-testid="stSidebar"]) textarea {{
        background-color: #FFFFFF !important;
        color: {COGNIZANT_TEXT} !important;
        -webkit-text-fill-color: {COGNIZANT_TEXT} !important;
        caret-color: {COGNIZANT_NAVY} !important;
        font-family: 'Consolas', 'Menlo', 'Courier New', monospace !important;
        font-size: 0.92rem !important;
        line-height: 1.55 !important;
        padding: 0.9rem 1rem !important;
    }}
    div[data-testid="stAppViewContainer"] :not(section[data-testid="stSidebar"]) textarea::placeholder {{
        color: #8A93A6 !important;
        opacity: 1 !important;
    }}
    div[data-testid="stAppViewContainer"] :not(section[data-testid="stSidebar"]) [data-baseweb="input"] > div {{
        background-color: #FFFFFF !important;
        border: 1px solid {COGNIZANT_SOFT_BLUE} !important;
        border-radius: 4px !important;
    }}
    div[data-testid="stAppViewContainer"] :not(section[data-testid="stSidebar"]) [data-baseweb="input"] input {{
        background-color: #FFFFFF !important;
        color: {COGNIZANT_TEXT} !important;
        -webkit-text-fill-color: {COGNIZANT_TEXT} !important;
    }}
    details[data-testid="stExpander"] {{
        background-color: #FFFFFF !important;
        border: 1px solid #E1E6F0 !important;
        border-radius: 4px !important;
        margin-top: 0.8rem;
    }}
    details[data-testid="stExpander"] summary {{
        color: {COGNIZANT_DARK_BLUE} !important;
        font-weight: 600;
    }}
    h1, h2, h3, h4 {{
        color: {COGNIZANT_NAVY};
        font-weight: 600;
    }}
    a, a:visited {{
        color: {COGNIZANT_BLUE};
    }}
    .stButton > button {{
        background-color: {COGNIZANT_DARK_BLUE};
        color: #FFFFFF;
        border: none;
        border-radius: 4px;
        font-weight: 500;
        padding: 0.5rem 1.2rem;
    }}
    .stButton > button:hover {{
        background-color: {COGNIZANT_BLUE};
        color: #FFFFFF;
    }}
    .stButton > button:active {{
        background-color: {COGNIZANT_TEAL};
        color: #FFFFFF;
    }}
    .stButton > button:disabled {{
        background-color: #B0B7C3;
        color: #FFFFFF;
    }}
    div[data-testid="stAlert"] {{
        border-radius: 4px;
    }}
    .et-header {{
        background: linear-gradient(90deg, {COGNIZANT_NAVY} 0%, {COGNIZANT_DARK_BLUE} 60%, {COGNIZANT_TEAL} 100%);
        color: #FFFFFF;
        padding: 1.4rem 1.8rem;
        border-radius: 6px;
        margin-bottom: 1.2rem;
        border-bottom: 3px solid {COGNIZANT_CYAN};
    }}
    .et-header h1 {{
        color: #FFFFFF;
        margin: 0;
        font-size: 1.7rem;
        font-weight: 600;
    }}
    .et-header p {{
        color: {COGNIZANT_SOFT_BLUE};
        margin: 0.3rem 0 0 0;
        font-size: 0.95rem;
    }}
    .et-summary-card {{
        background-color: #FFFFFF;
        border-left: 4px solid {COGNIZANT_CYAN};
        padding: 1.2rem 1.4rem;
        border-radius: 4px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
        line-height: 1.65;
        font-size: 1.0rem;
        color: {COGNIZANT_TEXT};
    }}
    .et-summary-card .et-label {{
        font-size: 0.8rem;
        font-weight: 600;
        letter-spacing: 0.08em;
        color: {COGNIZANT_DARK_BLUE};
        text-transform: uppercase;
        margin-bottom: 0.6rem;
    }}
</style>
"""


def _init_state():
    if "config_loaded" not in st.session_state:
        cfg = load_config()
        prov = cfg.get("provider") or "openai"
        if prov not in PROVIDER_OPTIONS:
            prov = "openai"
        st.session_state.provider = prov
        for p in PROVIDER_OPTIONS:
            mkey = f"model_{p}"
            akey = f"api_key_{p}"
            if mkey not in st.session_state:
                st.session_state[mkey] = (cfg.get("model") if p == prov else "") or PROVIDER_DEFAULT_MODELS.get(p, "")
            if akey not in st.session_state:
                st.session_state[akey] = (cfg.get("api_key") if p == prov else "") or ""
        if "base_url_openai" not in st.session_state:
            st.session_state["base_url_openai"] = (cfg.get("base_url") if prov == "openai" else "") or ""
        if "api_version_openai" not in st.session_state:
            st.session_state["api_version_openai"] = (cfg.get("api_version") if prov == "openai" else "") or ""
        st.session_state.config_loaded = True
    if "transcript_input" not in st.session_state:
        st.session_state.transcript_input = ""
    if "last_summary" not in st.session_state:
        st.session_state.last_summary = None
    if "provider" not in st.session_state:
        st.session_state.provider = "openai"


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


def _call_summarize(transcript: str, api_key: str, provider: str, model: str, base_url: str | None = None, api_version: str | None = None) -> dict | None:
    payload = {
        "transcript": transcript,
        "api_key": api_key,
        "provider": provider,
        "model": model or None,
        "base_url": base_url or None,
        "api_version": api_version or None,
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


def _sidebar() -> tuple[str, str, str, str, str]:
    with st.sidebar:
        st.markdown("## EasyTravel")
        st.caption("Call Intelligence Hub")
        st.divider()

        st.markdown("### LLM Settings")
        provider = st.radio(
            "Provider",
            PROVIDER_OPTIONS,
            horizontal=True,
            key="provider",
            format_func=lambda x: x.title(),
        )
        model = st.text_input(
            "Model",
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
        api_version = ""
        if provider == "openai":
            base_url = st.text_input(
                "Base URL / Azure Endpoint (optional)",
                placeholder="https://api.openai.com/v1  or  https://<resource>.openai.azure.com",
                help="Leave blank for public OpenAI. For Azure OpenAI, paste your resource endpoint.",
                key="base_url_openai",
            )
            api_version = st.text_input(
                "Azure API Version (Azure only)",
                placeholder="2024-10-21",
                help="Required only for Azure OpenAI.",
                key="api_version_openai",
            )

        if st.button("Save Configuration", use_container_width=True):
            save_config({
                "provider": provider,
                "api_key": api_key,
                "model": model,
                "base_url": base_url,
                "api_version": api_version,
            })
            st.success("Saved to config.yaml")

        st.divider()
        st.info("Some generated summaries may contain a subtle flaw — that is the workshop exercise.")

        with st.expander("About this application", expanded=False):
            st.markdown(
                "**EasyTravel Call Intelligence** converts customer-service transcripts into "
                "a single comprehensive call summary covering the customer's issue, the agent's "
                "actions, commitments, key references, and the final resolution status.\n\n"
                "A configured fraction of summaries will contain a subtle, plausible flaw. "
                "Your job is to spot them.\n\n"
                "Supports both Anthropic Claude and OpenAI GPT as the backing LLM."
            )

        st.divider()
        ok, info = _backend_health()
        if ok:
            st.success("Backend connected")
        else:
            st.error(f"Backend unreachable: {info}")

    return api_key, provider, model, base_url, api_version


def _render_summary_card(s: dict):
    summary_text = s.get("call_summary", "")
    ctx = s.get("context") or {}

    st.markdown(
        f"""
        <div class="et-summary-card">
            <div class="et-label">Call Summary</div>
            <div>{summary_text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("Transcript metadata", expanded=False):
        st.json(ctx)


def main():
    _init_state()
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    api_key, provider, model, base_url, api_version = _sidebar()

    st.markdown(
        """
        <div class="et-header">
            <h1>EasyTravel — Call Intelligence Hub</h1>
            <p>Paste a customer-service call transcript to generate a comprehensive call summary.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if "pending_transcript" in st.session_state:
        st.session_state.transcript_input = st.session_state.pop("pending_transcript")

    transcript = st.text_area(
        "Call Transcript",
        height=300,
        placeholder=SAMPLE_PLACEHOLDER,
        key="transcript_input",
    )

    c1, c2 = st.columns(2)
    with c1:
        summarize_clicked = st.button(
            "Generate Summary",
            type="primary",
            use_container_width=True,
            disabled=not transcript.strip(),
        )
    with c2:
        load_sample_clicked = st.button(
            "Load Sample Transcript",
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
                result = _call_summarize(transcript, api_key, provider, model, base_url, api_version)
            if result:
                st.session_state.last_summary = result

    if st.session_state.last_summary:
        _render_summary_card(st.session_state.last_summary)


if __name__ == "__main__":
    main()
