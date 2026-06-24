"""Programmatic Python client for the EasyTravel FastAPI backend.

Usage:
    from api_client import EasyTravelClient

    # Default — Anthropic Claude
    et = EasyTravelClient(api_key="sk-ant-...")
    result = et.summarize(transcript_text)

    # OpenAI GPT
    et = EasyTravelClient(api_key="sk-...", provider="openai", model="gpt-4.1-nano")
    result = et.summarize(transcript_text)

    # Batch summarize all 10 sample transcripts
    import pandas as pd
    df = pd.read_excel("sample_data/EasyTravel_Sample_Transcripts.xlsx", sheet_name="Sample Transcripts")
    results = et.summarize_batch(df["Full_Transcript"].tolist())
"""
from __future__ import annotations
import requests

EASYTRAVEL_URL = "http://localhost:8002"
DEFAULT_TIMEOUT = 90


class EasyTravelClient:
    def __init__(
        self,
        api_key: str,
        provider: str = "anthropic",
        model: str | None = None,
        base_url: str = EASYTRAVEL_URL,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        if not api_key:
            raise ValueError("api_key is required")
        self.api_key = api_key
        self.provider = provider
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def summarize(self, transcript: str) -> dict:
        payload = {
            "transcript": transcript,
            "api_key": self.api_key,
            "provider": self.provider,
            "model": self.model,
        }
        r = requests.post(f"{self.base_url}/summarize", json=payload, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def summarize_batch(self, transcripts: list[str]) -> dict:
        payload = {
            "api_key": self.api_key,
            "transcripts": transcripts,
            "provider": self.provider,
            "model": self.model,
        }
        r = requests.post(f"{self.base_url}/batch", json=payload, timeout=self.timeout * 3)
        r.raise_for_status()
        return r.json()

    def health(self) -> dict:
        r = requests.get(f"{self.base_url}/health", timeout=10)
        r.raise_for_status()
        return r.json()
