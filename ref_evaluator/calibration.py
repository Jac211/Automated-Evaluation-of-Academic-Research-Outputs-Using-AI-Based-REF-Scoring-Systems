"""Calibration, impact weighting and REF banding (dissertation §3.3, §3.5)."""
from __future__ import annotations

import re
from dataclasses import dataclass

from .config import Config

DIMENSIONS = ("originality", "significance", "rigour")


def calibrate_scores(results: list[dict]) -> float:
    """Compress over-generous or internally inconsistent LLM scores into a single 1-4 figure.

    `results` should already have any failed segments filtered out by the caller.
    """
    if not results:
        raise ValueError("calibrate_scores called with no valid results")

    calibrated = []
    for r in results:
        scores = [r[d] for d in DIMENSIONS]
        avg = sum(scores) / len(scores)
        penalty = 0.0

        # Penalise inconsistency or inflated combinations
        if min(scores) <= 2 and max(scores) >= 4:
            penalty += 0.5
        if avg > 3.5:
            penalty += 0.3  # overgenerosity clamp
        if r["rigour"] < 3:
            penalty += 0.2  # rigour is most predictive of expert assessment (dissertation §3.5)

        calibrated.append(max(1.0, avg - penalty))

    return sum(calibrated) / len(calibrated)


def assess_impact(text: str, config: Config) -> tuple[str, float, int]:
    """Impact weighting from how many *distinct* impact keywords appear in the text.

    Counting distinct keywords rather than occurrences stops keyword-dense text from
    inflating the multiplier. Returns (label, multiplier, distinct keywords found).
    """
    matches = sum(
        bool(re.search(rf"\b{re.escape(kw)}\b", text, flags=re.IGNORECASE))
        for kw in config.impact_keywords
    )
    for minimum, label, multiplier in config.impact_bands:
        if matches >= minimum:
            return label, multiplier, matches
    return "Minimal Impact", 1.00, matches


_BANDS = [
    (3.8, "High 4* (World Leading)"),
    (3.5, "Middle 4* (World Leading)"),
    (3.2, "Low 4* (Borderline World Leading)"),
    (2.8, "High 3* (Internationally Excellent)"),
    (2.5, "Middle 3* (Internationally Excellent)"),
    (2.2, "Low 3* (Borderline Excellent)"),
    (1.8, "High 2* (Recognised Internationally)"),
    (1.5, "Middle 2* (Recognised Internationally)"),
    (1.2, "Low 2* (Nationally Recognised)"),
]


@dataclass(frozen=True)
class RefBand:
    label: str
    score: float

    def __str__(self) -> str:
        return f"{self.label}, {self.score:.2f}"


def compute_ref_score(calibrated_score: float, impact_factor: float) -> RefBand:
    """Map a calibrated score + impact factor to a REF band, per dissertation §3.3.

    The score is rounded before comparison so the band always matches the displayed value.
    """
    weighted_score = round(min(calibrated_score * impact_factor, 4.0), 2)
    for threshold, label in _BANDS:
        if weighted_score >= threshold:
            return RefBand(label, weighted_score)
    return RefBand("1* (Below National Standard)", weighted_score)
