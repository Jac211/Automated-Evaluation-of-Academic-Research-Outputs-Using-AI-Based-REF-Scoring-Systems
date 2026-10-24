from types import SimpleNamespace

import pytest


class FakeClient:
    """Stands in for cohere.ClientV2: returns queued replies, or raises queued exceptions."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def chat(self, **kwargs):
        self.calls.append(kwargs)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return SimpleNamespace(message=SimpleNamespace(content=[SimpleNamespace(text=reply)]))


@pytest.fixture
def fake_client():
    return FakeClient
