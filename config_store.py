"""Load/save user-facing LLM configuration from config.yaml."""
from __future__ import annotations
from pathlib import Path
import yaml

CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"

DEFAULTS: dict = {
    "provider": "openai",
    "api_key": "",
    "model": "",
    "base_url": "",
    "api_version": "",
}


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return dict(DEFAULTS)
    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception:
        return dict(DEFAULTS)
    merged = dict(DEFAULTS)
    for k in DEFAULTS:
        v = data.get(k)
        if v is not None:
            merged[k] = v
    return merged


def save_config(cfg: dict) -> None:
    out = {k: (cfg.get(k) or DEFAULTS[k]) for k in DEFAULTS}
    with CONFIG_PATH.open("w", encoding="utf-8") as f:
        yaml.safe_dump(out, f, sort_keys=False, default_flow_style=False)
