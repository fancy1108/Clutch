"""Token usage calculation and logging helpers for design canvas sessions."""

from __future__ import annotations


def empty_token_usage() -> dict[str, int]:
    return {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}


def merge_token_usage(*usages: dict[str, int] | None) -> dict[str, int]:
    merged = empty_token_usage()
    for usage in usages:
        if not usage:
            continue
        merged["input_tokens"] += int(usage.get("input_tokens") or 0)
        merged["output_tokens"] += int(usage.get("output_tokens") or 0)
    merged["total_tokens"] = merged["input_tokens"] + merged["output_tokens"]
    return merged


def estimate_token_usage(
    *,
    prompt: str = "",
    response_text: str = "",
    reasoning: str | None = None,
) -> dict[str, int]:
    def _count(text: str) -> int:
        return len((text or "").split())

    input_tokens = _count(prompt)
    output_tokens = _count(response_text) + _count(reasoning or "")
    if input_tokens == 0 and output_tokens == 0:
        return empty_token_usage()
    if output_tokens == 0:
        output_tokens = max(1, input_tokens // 4)
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
    }


def normalize_usage_dict(raw: object) -> dict[str, int] | None:
    if not isinstance(raw, dict):
        return None
    if "prompt_tokens" in raw or "completion_tokens" in raw:
        inp = int(raw.get("prompt_tokens") or 0)
        out = int(raw.get("completion_tokens") or 0)
        total = int(raw.get("total_tokens") or (inp + out))
        return {"input_tokens": inp, "output_tokens": out, "total_tokens": total}
    if "input_tokens" in raw or "output_tokens" in raw:
        inp = int(raw.get("input_tokens") or 0)
        out = int(raw.get("output_tokens") or 0)
        return {"input_tokens": inp, "output_tokens": out, "total_tokens": inp + out}
    return None


def usage_from_llm_result(
    result: object,
    *,
    prompt: str = "",
    response_text: str = "",
    reasoning: str | None = None,
) -> tuple[dict[str, int], bool]:
    if isinstance(result, dict):
        normalized = normalize_usage_dict(result.get("usage"))
        if normalized and normalized["total_tokens"] > 0:
            return normalized, False
    estimated = estimate_token_usage(
        prompt=prompt,
        response_text=response_text,
        reasoning=reasoning,
    )
    return estimated, estimated["total_tokens"] > 0


def format_token_usage_text(label: str, usage: dict[str, int], *, estimated: bool = False) -> str:
    input_tokens = int(usage.get("input_tokens") or 0)
    output_tokens = int(usage.get("output_tokens") or 0)
    total_tokens = int(usage.get("total_tokens") or (input_tokens + output_tokens))
    suffix = " (estimated)" if estimated else ""
    return (
        f"Tokens · {label}: {total_tokens:,} total "
        f"({input_tokens:,} in / {output_tokens:,} out){suffix}"
    )
