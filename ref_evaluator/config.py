"""Tunable settings for the evaluator, passed explicitly to each stage of the pipeline."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Optional


@dataclass(frozen=True)
class Config:
    model_name: str = "command-a-03-2025"
    # Bump when you change scoring logic that isn't captured by the fields below
    # (e.g. the penalty rules in calibration.py). Prompt text is hashed automatically.
    scoring_version: str = "v5"
    temperature: float = 0.0
    seed: Optional[int] = 42

    # ~1300 words matches the ~1500 NLTK tokens per segment in the dissertation (§3.3 / §3.5),
    # since NLTK counts punctuation as tokens.
    segment_words: int = 1300
    max_segments: Optional[int] = 5     # None scores the whole paper
    max_retries: int = 2                # retries per segment on malformed replies or transient API errors
    backoff_seconds: float = 2.0        # base delay for exponential backoff on 429 / 5xx / network errors
    strip_references: bool = True       # drop the reference list before scoring and impact assessment

    impact_keywords: tuple[str, ...] = (
        "policy", "public health", "clinical", "societal", "industry", "application",
        "impact", "real-world", "translation", "implementation", "sustainability",
        "biotech", "education", "environment",
    )
    # (minimum distinct keywords, label, multiplier), checked in order
    impact_bands: tuple[tuple[int, str, float], ...] = (
        (12, "High Impact", 1.15),
        (9, "Medium Impact", 1.10),
        (4, "Low Impact", 1.05),
    )

    def fingerprint(self, system_prompt: str) -> str:
        """Hash of every setting that affects scores, used to invalidate cached results."""
        data = asdict(self)
        data.pop("max_retries")
        data.pop("backoff_seconds")
        data["system_prompt"] = system_prompt
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()[:16]
