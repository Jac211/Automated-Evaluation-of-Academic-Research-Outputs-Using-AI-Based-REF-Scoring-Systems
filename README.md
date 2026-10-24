# Automated Evaluation of Academic Research Outputs Using AI-Based REF Scoring

A notebook tool that gives an indicative [Research Excellence Framework](https://www.ref.ac.uk/) (REF) rating
for an academic paper. A large language model (Cohere `command-a-03-2025`) scores the paper on
**originality**, **significance** and **rigour**. The scores are then calibrated, weighted for impact and
mapped to a REF band (1*–4*, with High/Middle/Low sub-bands).

It accompanies the dissertation in [`dissertation/`](dissertation/), which documents the design rationale
(§3.3–3.6), validation and limitations.

> **Decision support, not a replacement for expert review.** See §5.3 of the dissertation for the ethical
> and institutional implications.

## Setup

Requires Python 3.10+ and a [Cohere API key](https://dashboard.cohere.com/api-keys).

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # then put your key in .env; it is git-ignored
jupyter lab REF_Evaluator_v4.ipynb
```

Run the cells top to bottom, choose one or more `.pdf` or `.txt` files and click **Evaluate**.
Each paper's result is printed, cached in `ref_cache/` and appended to `ref_results.csv`.

## Using it from Python

```python
import cohere
from ref_evaluator import Config, ResultCache, evaluate_with_cache

client = cohere.ClientV2(api_key="...")
result, from_cache = evaluate_with_cache(
    client, "paper.pdf", open("paper.pdf", "rb").read(), Config(max_segments=None), ResultCache()
)
print(result.final_ref, result.segment_scores)
```

## Method

1. **Extraction**: text is taken from the PDF (`pypdf`) or TXT file, and the reference list is removed.
2. **Segmentation**: the body is split into ~1300-word segments (≈1500 NLTK tokens, as in the dissertation).
   By default only the first 5 are scored (`Config.max_segments`). You are warned when a paper is truncated.
3. **Scoring**: each segment is sent in full to the LLM with a strict REF-reviewer prompt. Structured JSON
   output, temperature 0 and a fixed seed are used. Replies must contain whole-number scores from 1 to 4.
   Invalid replies are retried, and rate limits and server errors are retried with exponential backoff. A
   segment that still fails is left out of the average rather than counted as zero.
4. **Calibration** (§3.5): each segment's mean score is penalised for inconsistency (−0.5 when one dimension is
   ≤2 and another is 4), over-generosity (−0.3 when the mean is above 3.5) and weak rigour (−0.2 when rigour
   is below 3), with a floor of 1.0.
5. **Impact weighting**: a multiplier of 1.00–1.15 based on how many *distinct* impact keywords appear
   (policy, clinical, societal, …). Distinct keywords are counted, not occurrences, so keyword-dense text
   can't inflate the score.
6. **Banding** (§3.3): the weighted score (capped at 4.0 and rounded to 2 decimals) is mapped to a band:

   | Score | Band |
   |---|---|
   | ≥ 3.8 | High 4* |
   | ≥ 3.5 | Middle 4* |
   | ≥ 3.2 | Low 4* |
   | ≥ 2.8 | High 3* |
   | ≥ 2.5 | Middle 3* |
   | ≥ 2.2 | Low 3* |
   | ≥ 1.8 | High 2* |
   | ≥ 1.5 | Middle 2* |
   | ≥ 1.2 | Low 2* |
   | < 1.2 | 1* |

Cached results are keyed by the file's hash plus every setting that affects scores, including the prompt
text. Changing the model, prompt, segment size or segment cap re-scores papers instead of serving stale
results. Results where some segments failed are not cached. If you change the calibration code, bump
`Config.scoring_version`.

## Limitations

- Textual proxies for originality and rigour may miss contribution types such as datasets and software.
- Validated on life-sciences papers; results may not generalise to other fields without adaptation.
- Scanned PDFs without OCR have no extractable text.
- Upstream model updates can shift scores even with deterministic settings.

## Development

```bash
pip install -r requirements-dev.txt
pre-commit install   # strips notebook outputs on commit
pytest
```

The scoring logic lives in [`ref_evaluator/`](ref_evaluator/), and the notebook is only the interface.
Tests use a fake client and make no API calls. CI runs them on every push.

## Licence

[MIT](LICENSE) © 2025 Jac Ison
