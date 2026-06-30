# REF Academic Paper Evaluator v4

Cleaned-up, security-fixed version of `3.0 Evaluator.ipynb`, built from your dissertation's
Appendix A reference script and design rationale (§3.3–3.6).

## Setup

1. Copy `.env.example` to `.env` in this folder.
2. Replace the placeholder with your actual Cohere API key.
3. Add `.env` to your `.gitignore` if this folder is ever version-controlled — never commit it.
4. Open `REF_Evaluator_v4.ipynb` and run the cells top to bottom.

**If you've used this tool before with a key hardcoded in a notebook or `.env` file that you've
since uploaded, emailed, zipped, or shared anywhere, rotate that key in your Cohere dashboard.**
A key that has ever existed in plain text outside your local machine should be treated as
compromised, regardless of whether you've since "fixed" the code.

## What changed from v3

- **API key**: now loaded from `.env` via `python-dotenv` instead of hardcoded as a string.
  The notebook raises a clear error on startup if the key is missing, rather than failing
  confusingly later.
- **JSON parsing robustness**: a malformed LLM response now retries once before giving up,
  instead of immediately scoring the segment as `{0, 0, 0}`. A segment that still fails after
  retrying is excluded from the average entirely, rather than dragging the calibrated score
  down with a fake zero.
- **Truncation transparency**: if a paper has more segments than `MAX_SEGMENTS` (default 5,
  matching your dissertation's documented rationale of balancing context coverage against API
  cost), the tool now explicitly tells you how many segments and roughly how many tokens were
  skipped. `MAX_SEGMENTS` is a config variable you can raise or set to `None` to score the
  whole paper.
- **Cache invalidation**: cache keys now combine the file hash with the model name and a
  `PROMPT_VERSION` string. Previously, changing the model or editing the system prompt would
  silently keep serving old cached scores for a file you'd already evaluated. Bump
  `PROMPT_VERSION` whenever you meaningfully change the scoring logic.
- **Multi-file upload**: the widget now accepts multiple files in one go (v3 supported only
  one file per run).
- **Code structure**: split into clearly separated cells (extraction, scoring, calibration,
  caching, pipeline, UI) with type hints and docstrings, so individual pieces can be tested
  or reused outside the notebook.

## What was deliberately *not* changed

Your dissertation's Design Rationale (§3.5) explicitly justifies several things that might look
like odd choices in isolation — these are preserved exactly as designed:

- The `rigour < 3` penalty in `calibrate_scores`, because your testing found rigour most
  predictive of expert REF assessment.
- The conservative penalty magnitudes, to avoid false 4* inflation.
- The modest impact multiplier (1.00–1.15), kept small so it doesn't overshadow the core
  quality dimensions.
- The REF banding thresholds, which match the table in your dissertation's §3.3 exactly
  (verified against a smoke test).

## Known carried-over limitation

The impact-keyword counter in `assess_impact` uses simple word-boundary regex matching per
keyword. Keywords that appear adjacent to each other in unnatural sequences (e.g. dense
keyword stuffing without sentence structure) can undercount relative to keywords spread across
natural prose. This was present in v3 and is unlikely to matter for real academic writing, but
is worth knowing about if you ever stress-test the tool with synthetic text.
