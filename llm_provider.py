"""Provider-agnostic chat-completion call for EasyTravel.

Supports two providers, selected via the `provider` argument:
  - "anthropic"  -> Claude (claude-sonnet-4-6 default)
  - "openai"     -> GPT (gpt-4.1-nano default)
"""
from __future__ import annotations
from fastapi import HTTPException

ANTHROPIC_DEFAULT_MODEL = "claude-sonnet-4-6"
OPENAI_DEFAULT_MODEL = "gpt-4.1-nano"
SUPPORTED_PROVIDERS = ("anthropic", "openai")


def chat(
    provider: str,
    api_key: str,
    system_prompt: str,
    messages: list[dict],
    max_tokens: int = 1024,
    model: str | None = None,
    base_url: str | None = None,
    api_version: str | None = None,
) -> str:
    p = (provider or "anthropic").lower().strip()
    if p not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported provider '{provider}'. Use one of: {', '.join(SUPPORTED_PROVIDERS)}",
        )
    if p == "anthropic":
        return _call_anthropic(api_key, system_prompt, messages, max_tokens, model or ANTHROPIC_DEFAULT_MODEL)
    return _call_openai(api_key, system_prompt, messages, max_tokens, model or OPENAI_DEFAULT_MODEL, base_url, api_version)


def _call_anthropic(api_key: str, system_prompt: str, messages: list[dict], max_tokens: int, model: str) -> str:
    import anthropic
    try:
        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=messages,
        )
        parts = [b.text for b in resp.content if getattr(b, "type", None) == "text"]
        return ("\n".join(parts)).strip() or "(empty response from model)"
    except anthropic.AuthenticationError:
        raise HTTPException(status_code=401, detail="Invalid Anthropic API key.")
    except anthropic.APIConnectionError as e:
        raise HTTPException(status_code=502, detail=f"Could not reach Anthropic API: {e}")
    except anthropic.APIStatusError as e:
        raise HTTPException(status_code=502, detail=f"Anthropic API error: {getattr(e, 'message', str(e))}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Anthropic call failed: {e}")


def _is_azure_endpoint(base_url: str | None, api_version: str | None) -> bool:
    if api_version and api_version.strip():
        return True
    if base_url and "azure.com" in base_url.lower():
        return True
    return False


def _call_openai(api_key: str, system_prompt: str, messages: list[dict], max_tokens: int, model: str, base_url: str | None = None, api_version: str | None = None) -> str:
    try:
        from openai import AuthenticationError, APIConnectionError, APIStatusError, RateLimitError
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"openai package not installed: {e}")
    try:
        if _is_azure_endpoint(base_url, api_version):
            from openai import AzureOpenAI
            if not base_url or not base_url.strip():
                raise HTTPException(status_code=400, detail="Azure OpenAI requires a Base URL (azure_endpoint).")
            if not api_version or not api_version.strip():
                raise HTTPException(status_code=400, detail="Azure OpenAI requires an API Version (e.g. 2024-10-21).")
            client = AzureOpenAI(
                api_key=api_key,
                azure_endpoint=base_url.strip(),
                api_version=api_version.strip(),
            )
        else:
            from openai import OpenAI
            client_kwargs = {"api_key": api_key}
            if base_url and base_url.strip():
                client_kwargs["base_url"] = base_url.strip()
            client = OpenAI(**client_kwargs)
        oai_messages = [{"role": "system", "content": system_prompt}]
        oai_messages.extend(messages)
        resp = client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            messages=oai_messages,
        )
        text = resp.choices[0].message.content if resp.choices else ""
        return (text or "").strip() or "(empty response from model)"
    except AuthenticationError:
        raise HTTPException(status_code=401, detail="Invalid OpenAI API key.")
    except APIConnectionError as e:
        raise HTTPException(status_code=502, detail=f"Could not reach OpenAI API: {e}")
    except RateLimitError as e:
        raise HTTPException(status_code=429, detail=f"OpenAI rate limit: {e}")
    except APIStatusError as e:
        raise HTTPException(status_code=502, detail=f"OpenAI API error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI call failed: {e}")
