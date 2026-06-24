"""FastAPI backend for EasyTravel call summarizer.

Endpoints:
    GET  /health     -> { status }
    POST /summarize  -> structured summary + retrieved context echo
    POST /batch      -> summarize multiple transcripts

Both /summarize and /batch accept optional `provider` ("anthropic" | "openai")
and `model` fields to control which LLM is used.
"""
from __future__ import annotations
from pathlib import Path
from typing import Optional
import os

from fastapi import FastAPI
from pydantic import BaseModel, Field

from summarizer import summarize
from flaw_injector import should_inject_flaw, pick_flaw_type, log_flaw_decision

BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)

app = FastAPI(title="EasyTravel Backend", version="1.0.0")


class SummarizeRequest(BaseModel):
    transcript: str = Field(..., min_length=10)
    api_key: str = Field(..., min_length=8)
    provider: str = "anthropic"
    model: Optional[str] = None


class ContextBlock(BaseModel):
    transcript_excerpt: str
    turn_count: int
    agent_name: str
    customer_name: str


class SummarizeResponse(BaseModel):
    customer_issue: str
    resolution_status: str
    action_items: list[str]
    sentiment: str
    key_details: str
    context: ContextBlock
    is_flawed: bool


class BatchRequest(BaseModel):
    api_key: str = Field(..., min_length=8)
    transcripts: list[str] = Field(..., min_length=1)
    provider: str = "anthropic"
    model: Optional[str] = None


class BatchResultItem(BaseModel):
    index: int
    customer_issue: str
    resolution_status: str
    action_items: list[str]
    sentiment: str
    key_details: str
    context: ContextBlock
    is_flawed: bool


class BatchResponse(BaseModel):
    results: list[BatchResultItem]
    total: int
    flawed_count: int


@app.get("/health")
def health():
    return {"status": "ok"}


def _summarize_one(transcript: str, api_key: str, provider: str, model: str | None) -> dict:
    flawed = should_inject_flaw()
    flaw_type = pick_flaw_type() if flawed else None
    log_flaw_decision(transcript, flawed, flaw_type)
    result = summarize(transcript, api_key, flawed, flaw_type, provider=provider, model=model)
    result["is_flawed"] = flawed
    return result


@app.post("/summarize", response_model=SummarizeResponse)
def summarize_endpoint(req: SummarizeRequest):
    return _summarize_one(req.transcript, req.api_key, req.provider, req.model)


@app.post("/batch", response_model=BatchResponse)
def batch_endpoint(req: BatchRequest):
    results = []
    flawed_count = 0
    for i, t in enumerate(req.transcripts):
        r = _summarize_one(t, req.api_key, req.provider, req.model)
        if r["is_flawed"]:
            flawed_count += 1
        results.append({"index": i, **r})
    return {"results": results, "total": len(results), "flawed_count": flawed_count}
