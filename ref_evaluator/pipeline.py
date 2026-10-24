"""End-to-end evaluation of one paper, independent of the notebook UI."""
from __future__ import annotations

import csv
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Callable, Iterable

from .cache import ResultCache
from .calibration import assess_impact, calibrate_scores, compute_ref_score
from .config import Config
from .extraction import count_words, extract_text, segment_text, strip_references
from .scoring import evaluate_segment


@dataclass
class EvaluationResult:
    file_name: str
    word_count: int
    references_stripped: bool
    segment_count: int
    segments_evaluated: int
    truncated: bool
    failed_segments: int
    impact_level: str
    impact_factor: float
    impact_keywords_found: int
    calibrated_score: float
    ref_score: float
    ref_band: str
    segment_scores: list = field(default_factory=list)

    @property
    def final_ref(self) -> str:
        return f"{self.ref_band}, {self.ref_score:.2f}"


def run_evaluation(
    client,
    file_name: str,
    file_bytes: bytes,
    config: Config,
    log: Callable[[str], None] = print,
) -> EvaluationResult:
    """Run extraction → scoring → calibration → banding for one file."""
    text = extract_text(file_name, file_bytes)
    if not text.strip():
        raise ValueError(
            "No extractable text found. The PDF may be a scanned image without OCR, "
            "or the file may be corrupted."
        )

    body = strip_references(text) if config.strip_references else text
    references_stripped = len(body) < len(text)
    if references_stripped:
        log(f"✂️ Removed reference list ({count_words(text) - count_words(body)} words).")

    word_count = count_words(body)
    log(f"🧮 Word Count: {word_count}")

    impact_level, impact_factor, keywords_found = assess_impact(body, config)
    log(f"🌍 Impact Assessment: {impact_level} (x{impact_factor}, {keywords_found} distinct keywords)")

    all_segments = segment_text(body, config.segment_words)
    segments_to_run = all_segments if config.max_segments is None else all_segments[: config.max_segments]
    truncated = len(segments_to_run) < len(all_segments)

    if truncated:
        skipped = len(all_segments) - len(segments_to_run)
        skipped_words = sum(count_words(s) for s in all_segments[len(segments_to_run):])
        log(
            f"⚠️ This paper has {len(all_segments)} segments; only the first "
            f"{len(segments_to_run)} are being scored ({skipped} segment(s) / {skipped_words} "
            "words skipped). Raise max_segments in the Config cell to score the whole paper."
        )

    results = []
    failed = 0
    for i, seg in enumerate(segments_to_run):
        log(f"\n➡️ Evaluating segment {i + 1}/{len(segments_to_run)}...")
        res = evaluate_segment(client, seg, config, log=log)
        if res is None:
            failed += 1
            continue
        log(f"   Segment {i + 1}: {res}")
        results.append(res)

    if not results:
        raise RuntimeError(
            "All segments failed to score — check your network connection and Cohere account status."
        )
    if failed:
        log(f"⚠️ {failed} segment(s) failed to score and were excluded from the average.")

    calibrated_score = calibrate_scores(results)
    band = compute_ref_score(calibrated_score, impact_factor)
    log(f"\n✅ Final REF Rating: {band}")

    return EvaluationResult(
        file_name=file_name,
        word_count=word_count,
        references_stripped=references_stripped,
        segment_count=len(all_segments),
        segments_evaluated=len(results),
        truncated=truncated,
        failed_segments=failed,
        impact_level=impact_level,
        impact_factor=impact_factor,
        impact_keywords_found=keywords_found,
        calibrated_score=round(calibrated_score, 4),
        ref_score=band.score,
        ref_band=band.label,
        segment_scores=results,
    )


def evaluate_with_cache(
    client,
    file_name: str,
    file_bytes: bytes,
    config: Config,
    cache: ResultCache,
    log: Callable[[str], None] = print,
) -> tuple[EvaluationResult, bool]:
    """Evaluate a file, reusing a cached result when the file and config match.

    Returns (result, from_cache). Results with failed segments are not cached, so the
    paper is re-scored in full next time.
    """
    key = cache.key(file_bytes, config)
    cached = cache.load(key)
    if cached is not None:
        try:
            result = EvaluationResult(**cached)
        except TypeError:  # written by an incompatible version
            result = None
        if result is not None:
            result.file_name = file_name
            return result, True

    result = run_evaluation(client, file_name, file_bytes, config, log=log)
    if result.failed_segments:
        log("⚠️ Result not cached because some segments failed; re-run to score them.")
    else:
        cache.save(key, asdict(result))
    return result, False


CSV_COLUMNS = [f.name for f in fields(EvaluationResult) if f.name != "segment_scores"]


def write_results_csv(results: Iterable[EvaluationResult], path: Path | str, append: bool = True) -> Path:
    """Write one row per result (without per-segment scores) for comparison with expert ratings."""
    path = Path(path)
    write_header = not (append and path.exists())
    with open(path, "a" if append else "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        if write_header:
            writer.writeheader()
        for result in results:
            writer.writerow(asdict(result))
    return path
