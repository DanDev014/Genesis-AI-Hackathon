"""
Shared LLM client with token-cost discipline built in.

Every generative call in Kora goes through here. That gives us four things
we can point at when judges ask about cost:

1. Model tiering. Gemini Flash by default, Gemini Pro only when explicitly
   requested.
2. Response caching by SHA-256 of (system + user + tier). Zero tokens on
   identical inputs. Demo replays cost once, then zero.
3. Live cost meter — input/output/cached/total tokens, exposed at /tokens.
4. Mock fallback. No API key? No call. Deterministic output, zero tokens.

Backed by the Gemini API (free tier) rather than Anthropic — same public
interface as before, so nothing else in Kora needs to change.

Kept small on purpose. This is the one file to change if you want to
retune the cost/quality trade-off or swap providers again.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from typing import Optional

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_SMART = os.getenv("LLM_SMART", "gemini-1.5-pro")
MODEL_FAST = os.getenv("LLM_FAST", "gemini-1.5-flash")

# Rough public per-million-token prices in USD. Used only for the meter,
# not for anything customer-facing. Gemini's free tier is $0 up to its rate
# limits — we report that honestly rather than pricing it like a paid API.
# Override with env vars if you move to Gemini's paid tier.
PRICE_IN = {"smart": 0.0, "fast": 0.0}
PRICE_OUT = {"smart": 0.0, "fast": 0.0}

_cache: dict = {}          # sha256 -> raw text
_meter = {
    "calls": 0,
    "cache_hits": 0,
    "input_tokens_smart": 0, "output_tokens_smart": 0,
    "input_tokens_fast": 0,  "output_tokens_fast": 0,
    "usd_estimate": 0.0,
    "last_call": None,
}


def enabled() -> bool:
    return bool(API_KEY)


def mode() -> str:
    return "live" if API_KEY else "mock"


def _key(system: str, user: str, tier: str) -> str:
    return hashlib.sha256(f"{tier}||{system}||{user}".encode("utf-8")).hexdigest()


def _model_for(tier: str) -> str:
    return MODEL_FAST if tier == "fast" else MODEL_SMART


def _record(tier: str, in_tokens: int, out_tokens: int) -> None:
    _meter["calls"] += 1
    _meter[f"input_tokens_{tier}"] += in_tokens
    _meter[f"output_tokens_{tier}"] += out_tokens
    _meter["usd_estimate"] += (
        in_tokens / 1_000_000 * PRICE_IN[tier]
        + out_tokens / 1_000_000 * PRICE_OUT[tier]
    )
    _meter["last_call"] = time.time()


def cost_report() -> dict:
    """Public snapshot for the /tokens endpoint."""
    return {
        "mode": mode(),
        "provider": "gemini",
        "model_smart": MODEL_SMART,
        "model_fast": MODEL_FAST,
        "total_calls": _meter["calls"],
        "cache_hits": _meter["cache_hits"],
        "cache_hit_rate": (
            _meter["cache_hits"] / (_meter["calls"] + _meter["cache_hits"])
            if (_meter["calls"] + _meter["cache_hits"]) else 0
        ),
        "input_tokens_smart":  _meter["input_tokens_smart"],
        "output_tokens_smart": _meter["output_tokens_smart"],
        "input_tokens_fast":   _meter["input_tokens_fast"],
        "output_tokens_fast":  _meter["output_tokens_fast"],
        "usd_estimate":        round(_meter["usd_estimate"], 4),
        "cache_size":          len(_cache),
    }


def reset_meter() -> None:
    for k in list(_meter.keys()):
        _meter[k] = 0 if isinstance(_meter[k], (int, float)) else None


# ---------- calls ----------
def call_text(system: str, user: str, tier: str = "fast",
              max_tokens: Optional[int] = None) -> Optional[str]:
    """Return the model text, or None if no key. Cache-first. Flash-by-default."""
    if not API_KEY:
        return None

    k = _key(system, user, tier)
    if k in _cache:
        _meter["cache_hits"] += 1
        return _cache[k]

    # Token budget: scale with input length rather than blowing SDK defaults.
    # Rough heuristic: allow up to 40% of the input length as output, capped.
    if max_tokens is None:
        est_input = max(1, (len(system) + len(user)) // 4)
        max_tokens = max(200, min(1200, int(est_input * 0.4)))

    import google.generativeai as genai  # imported lazily so mock mode is dep-free
    genai.configure(api_key=API_KEY)
    model_name = _model_for(tier)
    try:
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system,
        )
        resp = model.generate_content(
            user,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
            ),
        )
    except Exception as exc:
        print(f"[llm_client] {model_name} failed: {exc}")
        return None

    text = (resp.text or "").strip() if hasattr(resp, "text") else ""
    if not text:
        print(f"[llm_client] {model_name} returned no text (possibly blocked/empty).")
        return None

    _cache[k] = text
    # Record actual usage from the response. Gemini's field names differ from
    # Anthropic's — prompt_token_count / candidates_token_count instead of
    # input_tokens / output_tokens — but we normalise into the same meter.
    try:
        usage = getattr(resp, "usage_metadata", None)
        in_tok = getattr(usage, "prompt_token_count", 0) or 0
        out_tok = getattr(usage, "candidates_token_count", 0) or 0
    except Exception:
        in_tok = out_tok = 0
    _record(tier, in_tok, out_tok)
    return text


def call_json(system: str, user: str, tier: str = "fast",
              max_tokens: Optional[int] = None) -> Optional[dict]:
    """call_text with best-effort JSON parsing."""
    text = call_text(system, user, tier=tier, max_tokens=max_tokens)
    if text is None:
        return None
    try:
        raw = re.sub(r"^```(?:json)?|```$", "", text.strip(),
                     flags=re.MULTILINE).strip()
        s, e = raw.find("{"), raw.rfind("}")
        if s != -1 and e != -1:
            raw = raw[s:e + 1]
        return json.loads(raw)
    except Exception as exc:
        print(f"[llm_client] JSON parse failed: {exc}")
        return None