"""Offline stand-ins for the OpenAI client, so tests need no network and no API key."""

import hashlib
import json
import math
import re
from types import SimpleNamespace
from typing import Any

DIMENSIONS = 1536
_WORD = re.compile(r"[a-z0-9]+")


def fake_embedding(text: str) -> list[float]:
    """Hash each word into one of 1536 buckets and normalize.

    Texts that share words end up close together, so retrieval ordering stays meaningful.
    """
    vector = [0.0] * DIMENSIONS
    for word in _WORD.findall(text.lower()):
        bucket = int(hashlib.sha256(word.encode()).hexdigest(), 16) % DIMENSIONS
        vector[bucket] += 1.0
    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [v / norm for v in vector]


def _usage() -> SimpleNamespace:
    return SimpleNamespace(prompt_tokens=10, completion_tokens=5, total_tokens=15)


def text_reply(content: str, finish_reason: str = "stop") -> SimpleNamespace:
    """A chat completion that answers with plain text."""
    message = SimpleNamespace(role="assistant", content=content, tool_calls=None)
    choice = SimpleNamespace(finish_reason=finish_reason, message=message)
    return SimpleNamespace(choices=[choice], usage=_usage())


def tool_reply(*calls: tuple[str, dict[str, Any]]) -> SimpleNamespace:
    """A chat completion that asks for one or more tool calls, given as (name, arguments)."""
    tool_calls = [
        SimpleNamespace(
            id=f"call_{i}",
            type="function",
            function=SimpleNamespace(name=name, arguments=json.dumps(args)),
        )
        for i, (name, args) in enumerate(calls)
    ]
    message = SimpleNamespace(role="assistant", content=None, tool_calls=tool_calls)
    choice = SimpleNamespace(finish_reason="tool_calls", message=message)
    return SimpleNamespace(choices=[choice], usage=_usage())


class _Embeddings:
    def __init__(self, calls: list[dict[str, Any]]) -> None:
        self._calls = calls

    async def create(self, *, model: str, input: str | list[str]) -> SimpleNamespace:
        self._calls.append({"model": model, "input": input})
        texts = [input] if isinstance(input, str) else list(input)
        data = [SimpleNamespace(index=i, embedding=fake_embedding(t)) for i, t in enumerate(texts)]
        return SimpleNamespace(data=data, usage=SimpleNamespace(prompt_tokens=0, total_tokens=0))


class _Completions:
    def __init__(self, replies: list[SimpleNamespace], calls: list[dict[str, Any]]) -> None:
        self.replies = replies
        self._calls = calls

    async def create(self, **kwargs: Any) -> SimpleNamespace:
        # Copy the message list: the agent keeps appending to the same list after each call.
        self._calls.append({**kwargs, "messages": list(kwargs.get("messages", []))})
        if not self.replies:
            raise AssertionError("FakeOpenAI ran out of scripted chat replies")
        return self.replies.pop(0)


class FakeOpenAI:
    """Mimics the parts of AsyncOpenAI the app uses. Chat replies are scripted per test."""

    def __init__(self, chat_replies: list[SimpleNamespace] | None = None) -> None:
        self.embedding_calls: list[dict[str, Any]] = []
        self.chat_calls: list[dict[str, Any]] = []
        self.embeddings = _Embeddings(self.embedding_calls)
        self.chat = SimpleNamespace(
            completions=_Completions(list(chat_replies or []), self.chat_calls)
        )

    def queue(self, *replies: SimpleNamespace) -> None:
        self.chat.completions.replies.extend(replies)

    async def close(self) -> None:
        return None
