"""REF academic paper evaluator: LLM-assisted REF-style scoring of research outputs."""
from .cache import ResultCache
from .calibration import RefBand, assess_impact, calibrate_scores, compute_ref_score
from .config import Config
from .pipeline import EvaluationResult, evaluate_with_cache, run_evaluation, write_results_csv
from .scoring import SYSTEM_PROMPT, ScoringError, evaluate_segment, parse_scores

__all__ = [
    "Config",
    "EvaluationResult",
    "RefBand",
    "ResultCache",
    "SYSTEM_PROMPT",
    "ScoringError",
    "assess_impact",
    "calibrate_scores",
    "compute_ref_score",
    "evaluate_segment",
    "evaluate_with_cache",
    "parse_scores",
    "run_evaluation",
    "write_results_csv",
]
