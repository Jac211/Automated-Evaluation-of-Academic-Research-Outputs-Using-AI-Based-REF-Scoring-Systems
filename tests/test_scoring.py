import httpx
import pytest
from cohere.core.api_error import ApiError

from ref_evaluator import Config, ScoringError, evaluate_segment, parse_scores

GOOD = '{"originality": 3, "significance": 2, "rigour": 4}'
EXPECTED = {"originality": 3, "significance": 2, "rigour": 4}


def run(client, **config):
    return evaluate_segment(client, "text", Config(**config), log=lambda _: None, sleep=lambda _: None)


def test_parse_scores_with_surrounding_text():
    assert parse_scores(f"Sure! {GOOD} Thanks.") == EXPECTED


def test_parse_scores_accepts_whole_floats():
    assert parse_scores('{"originality": 3.0, "significance": 2, "rigour": 4}') == EXPECTED


@pytest.mark.parametrize(
    "reply",
    [
        "no json here",
        '{"originality": 3, "significance": 2}',
        '{"originality": 5, "significance": 2, "rigour": 4}',
        '{"originality": 0, "significance": 2, "rigour": 4}',
        '{"originality": 3.5, "significance": 2, "rigour": 4}',
        '{"originality": "3", "significance": 2, "rigour": 4}',
        '{"originality": true, "significance": 2, "rigour": 4}',
    ],
)
def test_parse_scores_rejects_invalid(reply):
    with pytest.raises(ValueError):
        parse_scores(reply)


def test_sends_full_segment_and_reproducibility_settings(fake_client):
    client = fake_client([GOOD])
    long_segment = "word " * 2000
    evaluate_segment(client, long_segment, Config(), log=lambda _: None)
    call = client.calls[0]
    assert call["messages"][1]["content"] == long_segment
    assert call["temperature"] == 0.0
    assert call["seed"] == 42
    assert call["response_format"]["type"] == "json_object"


def test_retries_malformed_reply(fake_client):
    client = fake_client(["garbage", GOOD])
    assert run(client) == EXPECTED


def test_returns_none_after_retries(fake_client):
    client = fake_client(["bad"] * 3)
    assert run(client, max_retries=2) is None
    assert len(client.calls) == 3


def test_backs_off_on_rate_limit(fake_client):
    client = fake_client([ApiError(status_code=429, body="slow down"), GOOD])
    delays = []
    result = evaluate_segment(client, "text", Config(backoff_seconds=1.5), log=lambda _: None, sleep=delays.append)
    assert result == EXPECTED
    assert delays == [1.5]


def test_retries_network_error(fake_client):
    client = fake_client([httpx.ConnectError("down"), GOOD])
    assert run(client) == EXPECTED


def test_auth_error_fails_fast(fake_client):
    client = fake_client([ApiError(status_code=401, body="invalid api token"), GOOD])
    with pytest.raises(ScoringError):
        run(client)
    assert len(client.calls) == 1
