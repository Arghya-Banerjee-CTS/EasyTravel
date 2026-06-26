"""FastAPI backend for EasyTravel call summarizer.

Endpoints:
    GET  /health     -> { status }
    POST /summarize  -> single-paragraph call summary
    POST /batch      -> summarize multiple transcripts
"""
from __future__ import annotations
from pathlib import Path
from typing import Optional
import os

from fastapi import FastAPI
from pydantic import BaseModel, Field

from summarizer import summarize
from flaw_injector import should_inject_flaw, pick_flaw_type, log_flaw_decision
from config_store import load_config

BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)

app = FastAPI(title="EasyTravel Backend", version="2.0.0")


class SummarizeRequest(BaseModel):
    transcript: str = Field(..., min_length=10)
    api_key: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    base_url: Optional[str] = None
    api_version: Optional[str] = None


class ContextBlock(BaseModel):
    transcript_excerpt: str
    turn_count: int
    agent_name: str
    customer_name: str


class SummarizeResponse(BaseModel):
    call_summary: str
    context: ContextBlock
    is_flawed: bool


class BatchRequest(BaseModel):
    transcripts: list[str] = Field(..., min_length=1)
    api_key: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    base_url: Optional[str] = None
    api_version: Optional[str] = None


class BatchResultItem(BaseModel):
    index: int
    call_summary: str
    context: ContextBlock
    is_flawed: bool


class BatchResponse(BaseModel):
    results: list[BatchResultItem]
    total: int
    flawed_count: int


@app.get("/health")
def health():
    return {"status": "ok"}


def _summarize_one(transcript: str, api_key: str, provider: str, model: str | None, base_url: str | None = None, api_version: str | None = None) -> dict:
    flawed = should_inject_flaw()
    flaw_type = pick_flaw_type() if flawed else None
    log_flaw_decision(transcript, flawed, flaw_type)
    result = summarize(transcript, api_key, flawed, flaw_type, provider=provider, model=model, base_url=base_url, api_version=api_version)
    result["is_flawed"] = flawed
    return result


def _resolve_creds(req) -> dict:
    cfg = load_config()
    return {
        "api_key": req.api_key or cfg.get("api_key", ""),
        "provider": req.provider or cfg.get("provider", "openai"),
        "model": req.model or cfg.get("model") or None,
        "base_url": req.base_url or cfg.get("base_url") or None,
        "api_version": req.api_version or cfg.get("api_version") or None,
    }


@app.post("/summarize", response_model=SummarizeResponse)
def summarize_endpoint(req: SummarizeRequest):
    c = _resolve_creds(req)
    return _summarize_one(req.transcript, c["api_key"], c["provider"], c["model"], c["base_url"], c["api_version"])


@app.post("/batch", response_model=BatchResponse)
def batch_endpoint(req: BatchRequest):
    c = _resolve_creds(req)
    results = []
    flawed_count = 0
    for i, t in enumerate(req.transcripts):
        r = _summarize_one(t, c["api_key"], c["provider"], c["model"], c["base_url"], c["api_version"])
        if r["is_flawed"]:
            flawed_count += 1
        results.append({"index": i, **r})
    return {"results": results, "total": len(results), "flawed_count": flawed_count}
