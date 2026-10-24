import pytest

from ref_evaluator import Config, assess_impact, calibrate_scores, compute_ref_score


def s(o, sig, r):
    return {"originality": o, "significance": sig, "rigour": r}


def test_calibrate_no_penalty():
    assert calibrate_scores([s(3, 3, 3)]) == 3.0


def test_calibrate_rigour_penalty():
    assert calibrate_scores([s(3, 3, 2)]) == pytest.approx(8 / 3 - 0.2)


def test_calibrate_inconsistency_and_rigour_penalty():
    assert calibrate_scores([s(4, 4, 2)]) == pytest.approx(10 / 3 - 0.5 - 0.2)


def test_calibrate_overgenerosity_clamp():
    assert calibrate_scores([s(4, 4, 4)]) == pytest.approx(3.7)


def test_calibrate_floor_and_average():
    assert calibrate_scores([s(1, 1, 1), s(3, 3, 3)]) == 2.0


def test_calibrate_ignores_extra_keys():
    assert calibrate_scores([{**s(3, 3, 3), "note": 0}]) == 3.0


def test_calibrate_empty():
    with pytest.raises(ValueError):
        calibrate_scores([])


@pytest.mark.parametrize(
    "score, label",
    [
        (4.0, "High 4* (World Leading)"),
        (3.8, "High 4* (World Leading)"),
        (3.5, "Middle 4* (World Leading)"),
        (3.2, "Low 4* (Borderline World Leading)"),
        (2.8, "High 3* (Internationally Excellent)"),
        (2.5, "Middle 3* (Internationally Excellent)"),
        (2.2, "Low 3* (Borderline Excellent)"),
        (1.8, "High 2* (Recognised Internationally)"),
        (1.5, "Middle 2* (Recognised Internationally)"),
        (1.2, "Low 2* (Nationally Recognised)"),
        (1.19, "1* (Below National Standard)"),
    ],
)
def test_band_thresholds(score, label):
    assert compute_ref_score(score, 1.0).label == label


def test_band_uses_rounded_score():
    band = compute_ref_score(3.1999, 1.0)
    assert band.score == 3.2
    assert band.label.startswith("Low 4*")
    assert str(band) == "Low 4* (Borderline World Leading), 3.20"


def test_band_caps_at_four():
    assert compute_ref_score(3.9, 1.15).score == 4.0


def test_impact_counts_distinct_keywords():
    config = Config()
    assert assess_impact("policy " * 50, config) == ("Minimal Impact", 1.0, 1)
    assert assess_impact("policy clinical societal industry", config)[:2] == ("Low Impact", 1.05)


def test_impact_high_is_reachable():
    config = Config()
    text = " ".join(config.impact_keywords)
    label, factor, found = assess_impact(text, config)
    assert (label, factor, found) == ("High Impact", 1.15, len(config.impact_keywords))


def test_impact_word_boundaries():
    assert assess_impact("policymakers impactful", Config())[2] == 0
