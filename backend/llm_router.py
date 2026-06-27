"""HandwritingEval LLM router — Gemini Flash vision only.

Supports a single image OR multiple images (e.g. multi-page PDFs).
Retries with exponential backoff on transient 503 overloads.
Surfaces a clear QuotaExceeded error on 429.
"""
from __future__ import annotations

import json
import os
import re
import time
from typing import Any

from google import genai
from google.genai import types as gtypes
from groq import Groq


_client: genai.Client | None = None
_groq_client: Groq | None = None
_gemini_quota_blocked_until: float = 0.0  # epoch sec; skip Gemini until past this


def _groq() -> Groq:
    global _groq_client
    if _groq_client is None:
        key = os.getenv("GROQ_API_KEY", "").strip()
        if not key:
            raise RuntimeError("GROQ_API_KEY not set — needed for Groq vision fallback")
        _groq_client = Groq(api_key=key)
    return _groq_client


def _gemini() -> genai.Client:
    global _client
    if _client is None:
        key = os.getenv("GEMINI_API_KEY", "").strip()
        if not key: raise RuntimeError("GEMINI_API_KEY not set")
        _client = genai.Client(api_key=key)
    return _client


def _extract_json(raw: str) -> dict[str, Any]:
    if not raw: raise ValueError("empty model output")
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if fenced: return json.loads(fenced.group(1))
    brace = re.search(r"\{.*\}", raw, re.DOTALL)
    if brace: return json.loads(brace.group(0))
    return json.loads(raw)


class QuotaExceeded(Exception):
    """Raised when daily Gemini quota is exhausted (429)."""


def _is_overloaded(err_msg: str) -> bool:
    return ("503" in err_msg or "UNAVAILABLE" in err_msg
            or "overloaded" in err_msg.lower() or "high demand" in err_msg.lower())


def _is_quota(err_msg: str) -> bool:
    return ("429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg
            or "exceeded your current quota" in err_msg.lower())


# Fallback chain — when the primary is overloaded, walk down this list.
# Each model is tried with one retry (2s backoff) before falling through.
_FALLBACK_CHAIN = [
    "gemini-2.5-flash",      # best quality, primary
    "gemini-2.0-flash",      # ~2× faster, slightly less smart
    "gemini-2.0-flash-lite", # fastest fallback when others overloaded
    "gemini-flash-latest",   # last-resort alias
]


def _model_chain() -> list[str]:
    """Primary model from env first, then fallbacks (de-duplicated, preserve order)."""
    primary = os.getenv("GEMINI_MODEL", "").strip() or _FALLBACK_CHAIN[0]
    chain = [primary] + [m for m in _FALLBACK_CHAIN if m != primary]
    seen, out = set(), []
    for m in chain:
        if m and m not in seen:
            seen.add(m); out.append(m)
    return out


def _try_model(model: str, parts, retries: int = 1, base_wait: float = 1.0):
    """Call one model with at most 1 quick retry (1s backoff). On overload,
    fall through to the NEXT model immediately rather than waiting longer."""
    last_err = None
    for attempt in range(retries + 1):
        if attempt > 0:
            time.sleep(base_wait)
        try:
            rsp = _gemini().models.generate_content(
                model=model,
                contents=parts,
                config=gtypes.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.2,
                    max_output_tokens=8192,
                ),
            )
            return True, _extract_json(rsp.text or "")
        except Exception as e:
            msg = str(e)
            last_err = e
            if _is_quota(msg):
                # Quota errors are terminal — surface immediately, don't fall back
                raise QuotaExceeded(
                    "Gemini daily quota exhausted for this API key. "
                    "Either wait until quota resets (~24h, UTC midnight) or "
                    "use a fresh key from https://aistudio.google.com/app/apikey"
                )
            if not _is_overloaded(msg):
                # Non-overload errors are also terminal for this attempt
                return False, e
            print(f"[gemini {model}] overloaded (attempt {attempt + 1}/{retries + 1}), backing off…")
    return False, last_err


def _grade_with_groq_vision(system_prompt: str,
                             images: list[tuple[bytes, str]]) -> dict[str, Any]:
    """Fallback grading via Groq Llama-4-Scout vision when all Gemini models fail.
    Up to 5 images per call. Returns the same JSON schema as Gemini path."""
    import base64

    model = os.getenv("GROQ_VISION_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")
    content: list[dict[str, Any]] = [{"type": "text", "text": system_prompt}]
    for img_bytes, mime in images[:5]:  # Groq caps at ~5 images per call
        b64 = base64.b64encode(img_bytes).decode("ascii")
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:{mime or 'image/png'};base64,{b64}"},
        })

    # Estimate tokens needed based on question count in prompt (~100 tokens per question)
    q_count = len(re.findall(r"Q\d+", system_prompt))
    groq_max_tokens = max(3000, q_count * 100 + 1500)
    rsp = _groq().chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": content}],
        temperature=0.2,
        max_tokens=groq_max_tokens,
        response_format={"type": "json_object"},
    )
    return _extract_json(rsp.choices[0].message.content or "")


def grade_handwriting(system_prompt: str,
                      images: list[tuple[bytes, str]]) -> dict[str, Any]:
    """Evaluate a handwritten answer with retries + fallback model chain.

    Tries primary model with 2 retries (2s, 4s). If still overloaded, falls
    through to the next model in the chain. Quota errors (429) surface immediately.
    """
    if not images:
        raise ValueError("No images provided")

    parts = [gtypes.Part.from_bytes(data=b, mime_type=m) for b, m in images]
    if len(images) > 1:
        parts.append(f"NOTE: The image(s) above are {len(images)} pages of one answer sheet, in order. Treat them as a single submission.")
    parts.append(system_prompt)

    global _gemini_quota_blocked_until
    last_err = None
    quota_hit = False
    skip_gemini = time.time() < _gemini_quota_blocked_until
    if skip_gemini:
        print(f"[gemini] quota block active for {int(_gemini_quota_blocked_until - time.time())}s more — skipping straight to Groq")
    for model in (() if skip_gemini else _model_chain()):
        try:
            ok, result = _try_model(model, parts)
        except QuotaExceeded as e:
            quota_hit = True
            last_err = e
            _gemini_quota_blocked_until = time.time() + 600  # 10-min circuit-break
            print(f"[gemini {model}] quota exhausted — blocking Gemini for 10min, going straight to Groq")
            break
        if ok:
            if model != _model_chain()[0]:
                if isinstance(result, dict):
                    result["_fallback_model_used"] = model
            return result
        last_err = result
        print(f"[gemini] falling through from {model} -> next in chain")

    print(f"[gemini] {'skipped (quota block active)' if skip_gemini else ('quota exhausted' if quota_hit else 'all Gemini models failed')} — using Groq Llama-4-Scout vision")
    groq_err = None
    try:
        result = _grade_with_groq_vision(system_prompt, images)
        if isinstance(result, dict):
            result["_fallback_model_used"] = os.getenv(
                "GROQ_VISION_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")
        return result
    except Exception as e:
        groq_err = e
        print(f"[groq vision] failed ({e}) — trying Gemini one more time as final fallback")

    # Final fallback: Gemini again (in case its quota cleared or earlier failure was transient).
    # We retry the LAST Gemini model in the chain with a fresh attempt.
    try:
        last_model = _model_chain()[-1]
        ok, result = _try_model(last_model, parts, retries=0)
        if ok:
            if isinstance(result, dict):
                result["_fallback_model_used"] = f"{last_model} (retry after Groq failure)"
            _gemini_quota_blocked_until = 0  # clear circuit-breaker since it worked
            return result
        raise result if isinstance(result, Exception) else RuntimeError(str(result))
    except Exception as ge:
        raise RuntimeError(
            f"All providers failed. Gemini: {last_err}. Groq vision: {groq_err}. Gemini retry: {ge}"
        )
