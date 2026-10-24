import csv

import pytest

from ref_evaluator import Config, ResultCache, evaluate_with_cache, run_evaluation, write_results_csv

GOOD = '{"originality": 3, "significance": 3, "rigour": 3}'
PAPER = (" ".join(f"word{i}" for i in range(250)) + " policy clinical").encode()


def quiet(_):
    pass


def test_run_evaluation_truncates_and_reports(fake_client):
    client = fake_client([GOOD, GOOD])
    result = run_evaluation(client, "paper.txt", PAPER, Config(segment_words=100, max_segments=2), log=quiet)
    assert result.segment_count == 3
    assert result.segments_evaluated == 2
    assert result.truncated
    assert result.ref_score == 3.0
    assert result.final_ref == "High 3* (Internationally Excellent), 3.00"


def test_run_evaluation_excludes_failed_segments(fake_client):
    client = fake_client(["bad", "bad", GOOD])
    result = run_evaluation(client, "paper.txt", PAPER, Config(segment_words=200, max_retries=1), log=quiet)
    assert result.failed_segments == 1
    assert result.segments_evaluated == 1
    assert result.ref_score == 3.0


def test_run_evaluation_empty_file(fake_client):
    with pytest.raises(ValueError):
        run_evaluation(fake_client([]), "empty.txt", b"   ", Config(), log=quiet)


def test_cache_round_trip(fake_client, tmp_path):
    cache = ResultCache(tmp_path)
    config = Config(segment_words=1000)
    first, from_cache = evaluate_with_cache(fake_client([GOOD]), "a.txt", PAPER, config, cache, log=quiet)
    assert not from_cache
    second, from_cache = evaluate_with_cache(fake_client([]), "b.txt", PAPER, config, cache, log=quiet)
    assert from_cache
    assert second.file_name == "b.txt"
    assert second.ref_score == first.ref_score
    assert second.segment_scores == first.segment_scores


def test_cache_invalidated_by_config_change(fake_client, tmp_path):
    cache = ResultCache(tmp_path)
    evaluate_with_cache(fake_client([GOOD]), "a.txt", PAPER, Config(max_segments=5), cache, log=quiet)
    _, from_cache = evaluate_with_cache(fake_client([GOOD]), "a.txt", PAPER, Config(max_segments=10), cache, log=quiet)
    assert not from_cache


def test_partial_results_not_cached(fake_client, tmp_path):
    cache = ResultCache(tmp_path)
    config = Config(segment_words=200, max_retries=0)
    evaluate_with_cache(fake_client(["bad", GOOD]), "a.txt", PAPER, config, cache, log=quiet)
    assert list(tmp_path.iterdir()) == []


def test_write_results_csv(fake_client, tmp_path):
    result = run_evaluation(fake_client([GOOD]), "paper.txt", PAPER, Config(), log=quiet)
    path = write_results_csv([result], tmp_path / "out.csv")
    write_results_csv([result], path)
    rows = list(csv.DictReader(open(path)))
    assert len(rows) == 2
    assert rows[0]["ref_band"] == "High 3* (Internationally Excellent)"
    assert "segment_scores" not in rows[0]
