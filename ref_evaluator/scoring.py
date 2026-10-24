"""LLM scoring of individual segments via the Cohere chat API."""
from __future__ import annotations

import json
import time
from typing import Callable, Optional

import httpx
from cohere.core.api_error import ApiError

from .calibration import DIMENSIONS
from .config import Config

SYSTEM_PROMPT = (
    "You are a REF (Research Excellence Framework) reviewer. Be very critical. "
    "Rate the following text realistically from 1–4 on: Originality, Significance, Rigour.\n"
    "- 4 = Truly world-leading and transformative.\n"
    "- 3 = Strong and internationally excellent but not ground-breaking.\n"
    "- 2 = Competent, sound, but limited originality or rigour.\n"
    "- 1 = Weak, flawed, or of national interest only.\n"
    "Avoid inflating scores. Respond with JSON only, no other text: "
    '{"originality": X, "significance": Y, "rigour": Z}'
)

RESPONSE_FORMAT = {
    "type": "json_object",
    "json_schema": {
        "type": "object",
        "properties": {d: {"type": "integer", "minimum": 1, "maximum": 4} for d in DIMENSIONS},
        "required": list(DIMENSIONS),
    },
}

_TRANSIENT_STATUS = {429, 500, 502, 503, 504}


class ScoringError(Exception):
    """A non-retryable failure, such as an invalid API key, that should stop the whole run."""


def parse_scores(reply: str) -> dict:
    """Parse a reply into {dimension: int 1-4}, raising ValueError if anything is missing or invalid."""
    start, end = reply.find("{"), reply.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"No JSON object found in reply: {reply!r}")
    data = json.loads(reply[start:end])

    scores = {}
    for dim in DIMENSIONS:
        value = data.get(dim)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value != int(value):
            raise ValueError(f"{dim} is not a whole number: {value!r}")
        if not 1 <= value <= 4:
            raise ValueError(f"{dim} is outside 1-4: {value!r}")
        scores[dim] = int(value)
    return scores


def evaluate_segment(
    client,
    segment: str,
    config: Config,
    log: Callable[[str], None] = print,
    sleep: Callable[[float], None] = time.sleep,
) -> Optional[dict]:
    """Score one segment on originality/significance/rigour.

    Malformed replies are retried straight away; rate limits, server errors and network
    errors are retried with exponential backoff. Returns None if the segment still fails,
    so the caller can exclude it rather than count it as a 0. Auth and other client errors
    raise ScoringError, since retrying them can't help.
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": segment},
    ]
    last_error: Optional[Exception] = None

    for attempt in range(config.max_retries + 1):
        try:
            response = client.chat(
                model=config.model_name,
                messages=messages,
                temperature=config.temperature,
                seed=config.seed,
                response_format=RESPONSE_FORMAT,
            )
            return parse_scores(response.message.content[0].text)
        except ApiError as e:
            if e.status_code not in _TRANSIENT_STATUS:
                raise ScoringError(f"Cohere API error {e.status_code}: {e.body}") from e
            last_error = e
        except (httpx.TransportError, httpx.TimeoutException) as e:
            last_error = e
        except (ValueError, IndexError, AttributeError) as e:  # malformed or empty reply
            last_error = e
            continue

        if attempt < config.max_retries:
            sleep(config.backoff_seconds * 2 ** attempt)

    log(f"⚠️ Segment evaluation failed after {config.max_retries + 1} attempt(s): {last_error}")
    return None
