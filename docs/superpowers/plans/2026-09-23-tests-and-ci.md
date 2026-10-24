# Tests and CI Implementation Plan (Plan 1 of 2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the existing backend and frontend a real test suite, plus a GitHub Actions workflow that runs lint, build, and tests on every push and pull request.

**Architecture:** The backend uses pytest with a fake OpenAI client, so no test touches the network. Unit tests need no database. Integration tests run against a real pgvector Postgres in a separate `ragdemo_test` database. The frontend uses Vitest with React Testing Library and MSW, and each test renders into a fresh Redux store. Tests for three known frontend defects are written against the correct behavior and checked in as `it.fails`, so CI stays green while the defects stay visible.

**Tech Stack:** pytest 9, pytest-asyncio 1.4, pytest-cov 7, ruff 0.16, httpx; Vitest 5, jsdom 30, React Testing Library 16, user-event 14, jest-dom 7, MSW 2; GitHub Actions (checkout, setup-python, setup-node, all v7).

**Spec:** `docs/superpowers/specs/2026-09-23-tests-and-eval-harness-design.md` (Part 1). Plan 2 covers Parts 2 to 4, the eval data and harness.

## Global Constraints

- Work on branch `feature/tests-and-evals`.
- **No commits without review.** Every task ends by staging its files and stopping. Commit only after the repo owner approves the staged diff.
- **Never stage the owner's uncommitted Google Drive work:** `backend/.env.example`, `backend/app/config.py`, `backend/app/models/requests.py`, `backend/app/routers/ingest.py`, `backend/requirements.txt`, `backend/app/services/gdrive.py`. Never use `git add -A`, `git add .`, or `git commit -a`.
- Do not change application behavior. The only edits to existing app files are `frontend/src/app/store.ts` (already approved and made) and the lint fixes in Task 4 (made only after approval).
- The backend Dockerfiles use Python 3.12 and the local `backend/.venv` uses 3.11. Tests must pass on both (verified for this plan).
- The frontend uses Node 22.
- Prose in docs and the README: no em-dashes.
- Commit messages end with the line `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Local environment notes

- Port 5432 on this machine is taken by another project's Postgres (`rftw-pg`, which has no pgvector). Start this repo's Postgres on 5433: `POSTGRES_PORT=5433 docker compose up -d postgres` from the repo root, then `export TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5433/ragdemo_test`.
- Backend commands run from `backend/` with the virtual environment active: `source .venv/bin/activate`.

## File Structure

```
backend/
  requirements-dev.txt              NEW  test and lint tools
  pyproject.toml                    NEW  pytest and ruff settings
  tests/
    __init__.py                     NEW
    conftest.py                     NEW  environment setup; database fixtures (Task 3)
    fakes.py                        NEW  FakeOpenAI, fake_embedding, text_reply, tool_reply
    unit/
      __init__.py                   NEW
      test_fakes.py                 NEW
      test_chunker.py               NEW
      test_config.py                NEW
      test_retrieval_helpers.py     NEW
      test_agent.py                 NEW
    integration/
      __init__.py                   NEW
      test_retrieval_db.py          NEW
      test_api.py                   NEW
  app/routers/documents.py          EDIT (Task 4, after approval) import order
  app/routers/ingest.py             EDIT (Task 4, after approval) import order; not staged here
  =0.0.9                            DELETE (Task 4, after approval)
frontend/
  package.json, package-lock.json   EDIT test dependencies and scripts
  vite.config.ts                    EDIT test settings
  eslint.config.js                  EDIT ignore coverage/
  .gitignore                        EDIT ignore coverage/
  src/app/store.ts                  EDIT (done) makeStore() factory
  src/test/
    setup.ts                        NEW  jest-dom, MSW lifecycle, scrollIntoView stub
    server.ts                       NEW  MSW server and default handlers
    renderWithStore.tsx             NEW  render into a fresh store
  src/features/chat/
    chatSlice.test.ts               NEW
    ChatInput.test.tsx              NEW
    SourceCitations.test.tsx        NEW
    AgentSteps.test.tsx             NEW  includes it.fails for D6
    ChatPage.test.tsx               NEW  includes it.fails for D3 and D4
.github/workflows/ci.yml            NEW
README.md                           EDIT CI badge and "Running tests" section
```

---

### Task 1: Backend test tooling and the fake OpenAI client

**Files:**
- Create: `backend/requirements-dev.txt`, `backend/pyproject.toml`, `backend/tests/__init__.py`, `backend/tests/unit/__init__.py`, `backend/tests/conftest.py`, `backend/tests/fakes.py`
- Test: `backend/tests/unit/test_fakes.py`

**Interfaces:**
- Consumes: nothing.
- Produces (used by Tasks 2 and 3, and by Plan 2):
  - `tests.fakes.DIMENSIONS: int` (1536)
  - `tests.fakes.fake_embedding(text: str) -> list[float]`
  - `tests.fakes.text_reply(content: str, finish_reason: str = "stop") -> SimpleNamespace`
  - `tests.fakes.tool_reply(*calls: tuple[str, dict[str, Any]]) -> SimpleNamespace`, where tool call ids are `call_0`, `call_1`, and so on
  - `tests.fakes.FakeOpenAI(chat_replies: list[SimpleNamespace] | None = None)` with `.embeddings.create(*, model, input)`, `.chat.completions.create(**kwargs)`, `.queue(*replies)`, `.close()`, `.embedding_calls: list[dict]`, and `.chat_calls: list[dict]` (each chat call records a copy of its `messages` list)
  - `tests/conftest.py` module constant `TEST_DATABASE_URL: str`

- [ ] **Step 1: Create the dev requirements**

`backend/requirements-dev.txt`:

```
pytest>=9.1
pytest-asyncio>=1.4
pytest-cov>=7.1
ruff>=0.16
# httpx drives the FastAPI app in tests; none of the app's dependencies install it.
httpx>=0.28
```

- [ ] **Step 2: Install everything into the backend virtual environment**

Run (from `backend/`): `source .venv/bin/activate && pip install -r requirements.txt -r requirements-dev.txt`
Expected: finishes without errors. `requirements.txt` includes the Google Drive packages from the owner's uncommitted work, which the working-tree `ingest.py` imports.

- [ ] **Step 3: Create the pytest settings**

`backend/pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
markers = [
    "integration: needs Postgres with the pgvector extension (see README, Running tests)",
]
```

- [ ] **Step 4: Create the package markers and the environment-only conftest**

Create empty files `backend/tests/__init__.py` and `backend/tests/unit/__init__.py`.

`backend/tests/conftest.py`:

```python
"""Shared test setup.

The environment is set before anything imports `app`, because `app.config.get_settings()`
and `app.db.engine.get_engine()` are cached the first time they are called.
"""

import os
from urllib.parse import urlsplit

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/ragdemo_test"
)
_TEST_DB_NAME = urlsplit(TEST_DATABASE_URL).path.lstrip("/")
# Guard: the integration fixtures truncate tables, so never point them at a real database.
assert _TEST_DB_NAME.endswith("_test"), "TEST_DATABASE_URL must name a database ending in _test"

os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["OPENAI_API_KEY"] = "test-key-not-used"
```

- [ ] **Step 5: Write the failing tests for the fakes**

`backend/tests/unit/test_fakes.py`:

```python
import math

import pytest

from tests.fakes import DIMENSIONS, FakeOpenAI, fake_embedding, text_reply


def test_fake_embedding_is_deterministic_normalized_and_case_insensitive():
    vector = fake_embedding("Backups are retained")

    assert vector == fake_embedding("backups ARE retained")
    assert len(vector) == DIMENSIONS
    assert math.isclose(sum(v * v for v in vector), 1.0)


def test_texts_that_share_words_are_closer():
    query = fake_embedding("how long are backups retained")
    near = fake_embedding("backups are retained for 35 days")
    far = fake_embedding("multi factor authentication is required")

    assert math.dist(query, near) < math.dist(query, far)


def test_empty_text_gives_a_zero_vector():
    assert fake_embedding("") == [0.0] * DIMENSIONS


async def test_batch_embeddings_keep_their_input_order():
    client = FakeOpenAI()

    response = await client.embeddings.create(model="m", input=["alpha", "beta"])

    assert [item.index for item in response.data] == [0, 1]
    assert response.data[1].embedding == fake_embedding("beta")
    assert client.embedding_calls == [{"model": "m", "input": ["alpha", "beta"]}]


async def test_chat_replies_come_back_in_order_and_calls_are_recorded():
    client = FakeOpenAI([text_reply("first")])
    client.queue(text_reply("second"))
    messages = [{"role": "user", "content": "hi"}]

    first = await client.chat.completions.create(model="m", messages=messages)
    messages.append({"role": "assistant", "content": "later"})
    second = await client.chat.completions.create(model="m", messages=messages)

    assert first.choices[0].message.content == "first"
    assert second.choices[0].message.content == "second"
    assert client.chat_calls[0]["messages"] == [{"role": "user", "content": "hi"}]


async def test_running_out_of_replies_fails_loudly():
    client = FakeOpenAI()

    with pytest.raises(AssertionError, match="ran out of scripted chat replies"):
        await client.chat.completions.create(model="m", messages=[])
```

- [ ] **Step 6: Run the tests to verify they fail**

Run: `pytest tests/unit/test_fakes.py -q`
Expected: collection error, `ModuleNotFoundError: No module named 'tests.fakes'`.

- [ ] **Step 7: Write the fakes**

`backend/tests/fakes.py`:

```python
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
```

- [ ] **Step 8: Run the tests to verify they pass**

Run: `pytest tests/unit/test_fakes.py -q`
Expected: `6 passed`.

- [ ] **Step 9: Stage for review and stop**

```bash
git add backend/requirements-dev.txt backend/pyproject.toml backend/tests/__init__.py backend/tests/unit/__init__.py backend/tests/conftest.py backend/tests/fakes.py backend/tests/unit/test_fakes.py
git diff --cached --stat
```

Show the staged diff to the repo owner and wait for approval. After approval:

```bash
git commit -m "$(cat <<'EOF'
test: add backend test tooling and an offline fake OpenAI client

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Backend unit tests for existing code

These tests describe how the current code already behaves, so they are expected to pass on the first run. If any fails, stop and report it. Do not change application code to make it pass.

**Files:**
- Test: `backend/tests/unit/test_chunker.py`, `backend/tests/unit/test_config.py`, `backend/tests/unit/test_retrieval_helpers.py`, `backend/tests/unit/test_agent.py`

**Interfaces:**
- Consumes (Task 1): `FakeOpenAI`, `text_reply`, `tool_reply` from `tests.fakes`.
- Consumes (app): `app.services.chunker.chunk_text(content, chunk_size=1000, overlap=100) -> list[str]`, `normalize_patterns(patterns: list[str]) -> list[str]`, `read_files(directory: str, patterns: list[str]) -> list[tuple[str, str]]`; `app.config.Settings` with the computed property `async_database_url`; `app.services.retrieval._to_pgvector(embedding: list[float]) -> str`; `app.services.agent.run_agent(question, session, client, top_k=5, history=None) -> AgentResponse(answer, sources, tool_calls)`, which calls the module-level names `search_similar_chunks` and `list_documents`.
- Produces: nothing new.

- [ ] **Step 1: Write the chunker tests**

`backend/tests/unit/test_chunker.py`:

```python
import pytest

from app.services.chunker import chunk_text, normalize_patterns, read_files


def test_chunk_text_empty_input_gives_no_chunks():
    assert chunk_text("", chunk_size=10, overlap=2) == []


def test_chunk_text_short_input_is_one_chunk():
    assert chunk_text("abc", chunk_size=10, overlap=2) == ["abc"]


def test_chunk_text_input_exactly_one_chunk_long():
    assert chunk_text("a" * 10, chunk_size=10, overlap=2) == ["a" * 10]


def test_chunk_text_overlaps_consecutive_chunks():
    assert chunk_text("abcdefghij", chunk_size=4, overlap=1) == ["abcd", "defg", "ghij"]


@pytest.mark.parametrize(("chunk_size", "overlap"), [(5, 5), (5, 6)])
def test_chunk_text_rejects_overlap_not_smaller_than_chunk(chunk_size, overlap):
    with pytest.raises(ValueError, match="chunk_size must be larger than overlap"):
        chunk_text("abcdefghij", chunk_size=chunk_size, overlap=overlap)


@pytest.mark.parametrize(
    ("patterns", "expected"),
    [
        (["md"], ["*.md"]),
        ([".txt"], ["*.txt"]),
        (["*.pdf"], ["*.pdf"]),
        (["notes/readme"], ["notes/readme"]),
        ([" md ", ""], ["*.md"]),
        (["", "   "], ["*.txt", "*.md"]),
        ([], ["*.txt", "*.md"]),
    ],
)
def test_normalize_patterns(patterns, expected):
    assert normalize_patterns(patterns) == expected


def test_read_files_matches_patterns_recursively_and_skips_empty_files(tmp_path):
    (tmp_path / "a.md").write_text("  alpha  ")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.txt").write_text("beta")
    (tmp_path / "c.py").write_text("print('not matched')")
    (tmp_path / "empty.md").write_text("   ")

    files = dict(read_files(str(tmp_path), ["md", "txt"]))

    assert files == {
        str(tmp_path / "a.md"): "alpha",
        str(tmp_path / "sub" / "b.txt"): "beta",
    }


def test_read_files_returns_each_file_once_when_patterns_overlap(tmp_path):
    (tmp_path / "a.md").write_text("alpha")

    files = read_files(str(tmp_path), ["*.md", "a.md"])

    assert files == [(str(tmp_path / "a.md"), "alpha")]
```

- [ ] **Step 2: Write the config and helper tests**

`backend/tests/unit/test_config.py`:

```python
import pytest

from app.config import Settings


@pytest.mark.parametrize(
    ("database_url", "expected"),
    [
        ("postgresql://u:p@host/db", "postgresql+asyncpg://u:p@host/db"),
        ("postgres://u:p@host/db", "postgresql+asyncpg://u:p@host/db"),
        ("postgresql+asyncpg://u:p@host/db", "postgresql+asyncpg://u:p@host/db"),
        ("  postgresql://u:p@host/db  ", "postgresql+asyncpg://u:p@host/db"),
    ],
)
def test_async_database_url_uses_the_asyncpg_driver(database_url, expected):
    assert Settings(database_url=database_url).async_database_url == expected


def test_async_database_url_rejects_an_empty_url():
    with pytest.raises(ValueError, match="DATABASE_URL must not be empty"):
        _ = Settings(database_url="   ").async_database_url
```

`backend/tests/unit/test_retrieval_helpers.py`:

```python
from app.services.retrieval import _to_pgvector


def test_to_pgvector_formats_a_bracketed_comma_list():
    assert _to_pgvector([0.5, -1.0, 2]) == "[0.5,-1.0,2]"


def test_to_pgvector_empty_list():
    assert _to_pgvector([]) == "[]"
```

- [ ] **Step 3: Write the agent tests**

`backend/tests/unit/test_agent.py`:

```python
import pytest

from app.services import agent
from app.services.agent import run_agent
from tests.fakes import FakeOpenAI, text_reply, tool_reply


@pytest.fixture
def search_calls(monkeypatch):
    """Replace vector search with a stub that returns one chunk named after the query."""
    calls: list[dict] = []

    async def fake_search(query, session, client, top_k=5):
        calls.append({"query": query, "top_k": top_k})
        return [f"Source: {query}.md\nchunk about {query}"]

    monkeypatch.setattr(agent, "search_similar_chunks", fake_search)
    return calls


def _tool_messages(chat_call: dict) -> list[dict]:
    return [m for m in chat_call["messages"] if isinstance(m, dict) and m.get("role") == "tool"]


async def test_searches_then_answers(search_calls):
    client = FakeOpenAI(
        [tool_reply(("vector_search", {"query": "mfa"})), text_reply("MFA is required.")]
    )

    result = await run_agent("Is MFA required?", session=None, client=client)

    assert result.answer == "MFA is required."
    assert result.sources == ["Source: mfa.md\nchunk about mfa"]
    assert result.tool_calls == [{"name": "vector_search", "args": {"query": "mfa"}}]
    tool_messages = _tool_messages(client.chat_calls[1])
    assert tool_messages == [
        {"role": "tool", "tool_call_id": "call_0", "content": "Source: mfa.md\nchunk about mfa"}
    ]


async def test_duplicate_sources_are_collapsed(search_calls):
    client = FakeOpenAI(
        [
            tool_reply(("vector_search", {"query": "mfa"}), ("vector_search", {"query": "mfa"})),
            text_reply("done"),
        ]
    )

    result = await run_agent("Is MFA required?", session=None, client=client)

    assert result.sources == ["Source: mfa.md\nchunk about mfa"]
    assert len(result.tool_calls) == 2


async def test_top_k_comes_from_the_tool_call_or_the_default(search_calls):
    client = FakeOpenAI(
        [
            tool_reply(
                ("vector_search", {"query": "a"}),
                ("vector_search", {"query": "b", "top_k": 7}),
            ),
            text_reply("done"),
        ]
    )

    await run_agent("q", session=None, client=client, top_k=3)

    assert search_calls == [{"query": "a", "top_k": 3}, {"query": "b", "top_k": 7}]


async def test_empty_search_tells_the_model_nothing_was_found(monkeypatch):
    async def no_results(query, session, client, top_k=5):
        return []

    monkeypatch.setattr(agent, "search_similar_chunks", no_results)
    client = FakeOpenAI([tool_reply(("vector_search", {"query": "x"})), text_reply("done")])

    result = await run_agent("q", session=None, client=client)

    assert _tool_messages(client.chat_calls[1])[0]["content"] == "No results found."
    assert result.sources == []


@pytest.mark.parametrize(
    ("documents", "expected"),
    [(["a.md", "b.md"], "a.md\nb.md"), ([], "No documents indexed yet.")],
)
async def test_list_documents_tool(monkeypatch, documents, expected):
    async def fake_list(session):
        return documents

    monkeypatch.setattr(agent, "list_documents", fake_list)
    client = FakeOpenAI([tool_reply(("list_documents", {})), text_reply("done")])

    await run_agent("What documents are there?", session=None, client=client)

    assert _tool_messages(client.chat_calls[1])[0]["content"] == expected


async def test_unknown_tool_is_reported_back_to_the_model():
    client = FakeOpenAI([tool_reply(("delete_everything", {})), text_reply("done")])

    result = await run_agent("q", session=None, client=client)

    assert _tool_messages(client.chat_calls[1])[0]["content"] == "Unknown tool: delete_everything"
    assert result.tool_calls == [{"name": "delete_everything", "args": {}}]


async def test_history_sits_between_system_prompt_and_question():
    history = [
        {"role": "user", "content": "earlier question"},
        {"role": "assistant", "content": "earlier answer"},
    ]
    client = FakeOpenAI([text_reply("done")])

    await run_agent("new question", session=None, client=client, history=history)

    messages = client.chat_calls[0]["messages"]
    assert messages[0]["role"] == "system"
    assert messages[1:3] == history
    assert messages[3] == {"role": "user", "content": "new question"}


async def test_other_finish_reasons_return_whatever_text_there_is():
    client = FakeOpenAI([text_reply("partial answer", finish_reason="length")])

    result = await run_agent("q", session=None, client=client)

    assert result.answer == "partial answer"
    assert result.sources == []
```

- [ ] **Step 4: Run all unit tests**

Run: `pytest tests/unit -q`
Expected: `37 passed` (6 fakes, 15 chunker, 5 config, 2 helpers, 9 agent). If any test fails, stop and report. It means the code behaves differently from what this plan recorded.

- [ ] **Step 5: Stage for review and stop**

```bash
git add backend/tests/unit/test_chunker.py backend/tests/unit/test_config.py backend/tests/unit/test_retrieval_helpers.py backend/tests/unit/test_agent.py
git diff --cached --stat
```

After approval:

```bash
git commit -m "$(cat <<'EOF'
test: cover chunking, config, and the agent loop with unit tests

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Backend integration tests against pgvector

**Files:**
- Modify: `backend/tests/conftest.py` (replace with the full version below)
- Create: `backend/tests/integration/__init__.py`
- Test: `backend/tests/integration/test_retrieval_db.py`, `backend/tests/integration/test_api.py`

**Interfaces:**
- Consumes (Task 1): `FakeOpenAI`, `fake_embedding`, `text_reply`, `tool_reply`; `TEST_DATABASE_URL`.
- Consumes (app): `app.db.engine.get_engine()`, `AsyncSessionLocal()`; `app.db.migrations.ensure_schema()`; `app.services.retrieval.store_embedding(content, embedding, source_path, chunk_index, session)`, `search_similar_chunks(query, session, client, top_k=5) -> list[str]` (each item is `"Source: <path>\n<content>"`), `list_documents(session) -> list[str]`, `delete_document(source_path, session) -> int`; `app.main.app`, whose routers read the OpenAI client from `app.state.openai_client`.
- Produces (used by Plan 2):
  - `database` session fixture: creates `ragdemo_test` and the schema. It skips when Postgres is unreachable, or fails when `REQUIRE_DATABASE=1`.
  - `db_session` fixture: an empty `document_chunks` table and an `AsyncSession`, with the engine disposed after each test.

- [ ] **Step 1: Start Postgres with pgvector**

Run (from the repo root): `POSTGRES_PORT=5433 docker compose up -d postgres`
Then: `export TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5433/ragdemo_test`
Expected: `docker compose ps postgres` shows the service as healthy.

- [ ] **Step 2: Replace conftest with the version that adds database fixtures**

`backend/tests/conftest.py`:

```python
"""Shared test setup.

The environment is set before anything imports `app`, because `app.config.get_settings()`
and `app.db.engine.get_engine()` are cached the first time they are called.
"""

import asyncio
import os
from urllib.parse import urlsplit

import pytest

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/ragdemo_test"
)
_TEST_DB_NAME = urlsplit(TEST_DATABASE_URL).path.lstrip("/")
# Guard: the integration fixtures truncate tables, so never point them at a real database.
assert _TEST_DB_NAME.endswith("_test"), "TEST_DATABASE_URL must name a database ending in _test"

os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["OPENAI_API_KEY"] = "test-key-not-used"

import asyncpg  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.exc import DBAPIError  # noqa: E402

from app.db.engine import AsyncSessionLocal, get_engine  # noqa: E402
from app.db.migrations import ensure_schema  # noqa: E402


async def _prepare_database() -> None:
    admin_url = TEST_DATABASE_URL.rsplit("/", 1)[0] + "/postgres"
    conn = await asyncpg.connect(admin_url, ssl=False)
    try:
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", _TEST_DB_NAME)
        if not exists:
            await conn.execute(f'CREATE DATABASE "{_TEST_DB_NAME}"')
    finally:
        await conn.close()
    try:
        await ensure_schema()
    finally:
        await get_engine().dispose()


@pytest.fixture(scope="session")
def database() -> str:
    """Create the test database and schema once per run, or skip if Postgres is unavailable."""
    try:
        asyncio.run(_prepare_database())
    except (OSError, asyncpg.PostgresError, DBAPIError) as exc:
        message = f"Postgres with pgvector is not reachable at {TEST_DATABASE_URL}: {exc}"
        # CI sets REQUIRE_DATABASE=1 so a broken database fails the build instead of skipping.
        if os.environ.get("REQUIRE_DATABASE") == "1":
            pytest.fail(message)
        pytest.skip(message)
    return TEST_DATABASE_URL


@pytest.fixture
async def db_session(database):
    """An empty document_chunks table and a session on it.

    The engine is disposed afterwards because asyncpg connections belong to the event loop that
    opened them, and each test runs in its own loop.
    """
    async with get_engine().begin() as conn:
        await conn.execute(text("TRUNCATE document_chunks RESTART IDENTITY"))
    async with AsyncSessionLocal() as session:
        yield session
    await get_engine().dispose()
```

- [ ] **Step 3: Write the retrieval database tests**

Create empty `backend/tests/integration/__init__.py`.

`backend/tests/integration/test_retrieval_db.py`:

```python
import pytest
from sqlalchemy import text

from app.services.retrieval import (
    delete_document,
    list_documents,
    search_similar_chunks,
    store_embedding,
)
from tests.fakes import FakeOpenAI, fake_embedding

pytestmark = pytest.mark.integration


async def _store(session, source_path: str, chunk_index: int, content: str) -> None:
    await store_embedding(content, fake_embedding(content), source_path, chunk_index, session)


async def test_store_embedding_upserts_on_source_and_chunk_index(db_session):
    await _store(db_session, "policy.md", 0, "first version")
    await _store(db_session, "policy.md", 0, "second version")
    await db_session.commit()

    rows = (await db_session.execute(text("SELECT content FROM document_chunks"))).all()

    assert rows == [("second version",)]


async def test_search_returns_the_closest_chunks_first(db_session):
    await _store(db_session, "access.md", 0, "multi factor authentication is required")
    await _store(db_session, "backup.md", 0, "backups are retained for thirty five days")
    await _store(db_session, "logs.md", 0, "audit logs are retained for one year")
    await db_session.commit()

    results = await search_similar_chunks(
        "how long are backups retained", db_session, FakeOpenAI(), top_k=2
    )

    assert len(results) == 2
    assert results[0] == "Source: backup.md\nbackups are retained for thirty five days"


async def test_list_documents_is_distinct_and_sorted(db_session):
    await _store(db_session, "b.md", 0, "one")
    await _store(db_session, "b.md", 1, "two")
    await _store(db_session, "a.md", 0, "three")
    await db_session.commit()

    assert await list_documents(db_session) == ["a.md", "b.md"]


async def test_delete_document_removes_all_its_chunks(db_session):
    await _store(db_session, "a.md", 0, "one")
    await _store(db_session, "a.md", 1, "two")
    await _store(db_session, "b.md", 0, "three")
    await db_session.commit()

    deleted = await delete_document("a.md", db_session)

    assert deleted == 2
    assert await list_documents(db_session) == ["b.md"]
```

- [ ] **Step 4: Write the API tests**

`backend/tests/integration/test_api.py`:

```python
import asyncio

import httpx
import pytest

from app.main import app
from app.services.retrieval import store_embedding
from tests.fakes import FakeOpenAI, fake_embedding, text_reply, tool_reply

pytestmark = pytest.mark.integration


@pytest.fixture
def fake_openai() -> FakeOpenAI:
    client = FakeOpenAI()
    # The routers read the client from app.state, which the lifespan normally fills in.
    app.state.openai_client = client
    return client


@pytest.fixture
async def api(db_session, fake_openai):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


async def _store(session, source_path: str, chunk_index: int, content: str) -> None:
    await store_embedding(content, fake_embedding(content), source_path, chunk_index, session)


async def test_health(api):
    response = await api.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_chat_runs_the_agent_and_returns_sources(api, db_session, fake_openai):
    await _store(db_session, "access.md", 0, "user access reviews happen quarterly")
    await db_session.commit()
    fake_openai.queue(
        tool_reply(("vector_search", {"query": "access reviews"})),
        text_reply("Quarterly."),
    )

    response = await api.post("/chat", json={"question": "How often are access reviews?"})

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "Quarterly."
    assert body["sources"] == ["Source: access.md\nuser access reviews happen quarterly"]
    assert body["tool_calls"] == [{"name": "vector_search", "args": {"query": "access reviews"}}]


async def test_documents_can_be_listed_and_deleted(api, db_session):
    await _store(db_session, "a.md", 0, "one")
    await _store(db_session, "a.md", 1, "two")
    await _store(db_session, "b.md", 0, "three")
    await db_session.commit()

    assert (await api.get("/documents")).json() == {"documents": ["a.md", "b.md"], "total": 2}

    deleted = await api.delete("/documents/a.md")

    assert deleted.json() == {"deleted_chunks": 2, "source_path": "a.md"}
    assert (await api.get("/documents")).json() == {"documents": ["b.md"], "total": 1}


async def test_ingest_local_indexes_a_folder(api, tmp_path):
    (tmp_path / "one.md").write_text("encryption at rest uses AES-256")
    (tmp_path / "two.md").write_text("backups are retained for thirty five days")

    started = await api.post("/ingest/local", json={"directory": str(tmp_path), "patterns": ["md"]})

    assert started.status_code == 202
    job_id = started.json()["job_id"]
    for _ in range(50):
        job = (await api.get(f"/ingest/jobs/{job_id}")).json()
        if job["status"] in ("complete", "failed"):
            break
        await asyncio.sleep(0.05)
    assert job["status"] == "complete", job
    assert job["files_indexed"] == 2
    assert job["chunks_stored"] == 2
    assert (await api.get("/documents")).json()["total"] == 2


async def test_ingest_local_rejects_a_missing_folder(api, tmp_path):
    response = await api.post("/ingest/local", json={"directory": str(tmp_path / "nope")})

    assert response.status_code == 400


async def test_unknown_job_is_a_404(api):
    response = await api.get("/ingest/jobs/not-a-real-job")

    assert response.status_code == 404
```

- [ ] **Step 5: Run the full backend suite**

Run: `pytest -q`
Expected: `47 passed` (37 unit and 10 integration). As in Task 2, these describe current behavior. If one fails, stop and report.

- [ ] **Step 6: Check the skip and fail paths**

Run: `TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5999/ragdemo_test pytest -q`
Expected: `37 passed, 10 skipped`.

Run: `REQUIRE_DATABASE=1 TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5999/ragdemo_test pytest -q`
Expected: `37 passed, 10 errors`.

Run: `pytest -q -m "not integration"`
Expected: `37 passed, 10 deselected`.

- [ ] **Step 7: Stage for review and stop**

```bash
git add backend/tests/conftest.py backend/tests/integration/__init__.py backend/tests/integration/test_retrieval_db.py backend/tests/integration/test_api.py
git diff --cached --stat
```

After approval:

```bash
git commit -m "$(cat <<'EOF'
test: add pgvector integration tests for retrieval and the API routes

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Lint baseline (approval checkpoint)

On the current code, ruff with rule sets E, F, and I reports 21 findings. None are in the test code.

- 19 are E501 (line too long): 16 in `app/services/generation.py`, 14 of which are the commented-out prompt strings, plus 3 in `app/routers/ingest.py`.
- 2 are I001 (import order), in `app/routers/documents.py` and `app/routers/ingest.py`. Both exist in the committed versions too.

**Do not start this task until the repo owner picks an option.** The steps below implement Option A, the recommendation.

- **Option A (recommended):** Ignore E501 with a comment explaining why, and fix the two import blocks with `ruff --fix` (a pure reorder, no code changes). Also delete the stray `backend/=0.0.9` (D5).
- **Option B:** Keep E501 and exclude `generation.py` and `ingest.py` from it with `per-file-ignores`, and fix the import blocks as in A.

**Files:**
- Modify: `backend/pyproject.toml`, `backend/app/routers/documents.py:1-6`, `backend/app/routers/ingest.py:1-17`
- Delete: `backend/=0.0.9`

**Interfaces:**
- Consumes: `backend/pyproject.toml` from Task 1.
- Produces: `ruff check .` passes in `backend/`, which the CI job in Task 8 relies on.

- [ ] **Step 1: Add the ruff settings**

Append to `backend/pyproject.toml`:

```toml

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I"]
# Long lines are left alone: most are the commented-out prompt strings in generation.py.
ignore = ["E501"]
```

- [ ] **Step 2: Confirm the remaining findings**

Run (from `backend/`): `ruff check . --output-format concise`
Expected: exactly two findings, `app/routers/documents.py:1:1: I001` and `app/routers/ingest.py:1:1: I001`.

- [ ] **Step 3: Apply the import-order fixes**

Run: `ruff check app/routers/documents.py app/routers/ingest.py --select I --fix`

Expected change in `documents.py`: `from sqlalchemy.ext.asyncio import AsyncSession` moves up into the third-party block under `from fastapi import APIRouter, Depends`.

Expected change in `ingest.py`: the long `fastapi` and `app.services.chunker` imports wrap into parenthesized lists, and `from app.services.gdrive import read_drive_files` moves below `from app.services.embeddings import batch_embeddings`.

Run: `ruff check .`
Expected: `All checks passed!`

- [ ] **Step 4: Delete the stray file (D5)**

Run (from the repo root): `git rm "backend/=0.0.9"`

- [ ] **Step 5: Re-run the backend suite**

Run (from `backend/`): `pytest -q`
Expected: `47 passed`.

- [ ] **Step 6: Stage for review and stop**

```bash
git add backend/pyproject.toml backend/app/routers/documents.py
git diff --cached --stat
```

`backend/app/routers/ingest.py` is deliberately **not** staged. It also holds the owner's uncommitted Drive work, so its import fix goes out in the same commit as that work. **Push this branch only after `ingest.py` is committed.** Otherwise CI's ruff step fails on the committed `ingest.py`, which has the same import-order finding.

After approval:

```bash
git commit -m "$(cat <<'EOF'
chore: add ruff settings, sort router imports, remove stray pip artifact

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Frontend test tooling and the chat slice tests

**Files:**
- Modify: `frontend/package.json`, `frontend/package-lock.json`, `frontend/vite.config.ts`, `frontend/eslint.config.js`, `frontend/.gitignore`
- Already modified (approved): `frontend/src/app/store.ts`
- Create: `frontend/src/test/setup.ts`, `frontend/src/test/server.ts`, `frontend/src/test/renderWithStore.tsx`
- Test: `frontend/src/features/chat/chatSlice.test.ts`

**Interfaces:**
- Consumes (app): `makeStore()` from `@/app/store`; `chatReducer` and the actions `addMessage`, `appendToken`, `setMessageSources`, `setMessageToolCalls`, `finishStreaming`, `clearMessages` from `@/features/chat/chatSlice`; the `Message` type from `@/types`.
- Produces (used by Tasks 6 and 7):
  - `API = 'http://localhost/api'` and `server` (an MSW `setupServer`) from `@/test/server`. The default `POST ${API}/chat` handler returns the answer `'Access reviews happen quarterly.'`, one source `'Source: access-control-policy.md\nUser access is reviewed quarterly.'`, and one tool call `{ name: 'vector_search', args: { query: 'access review frequency' } }`.
  - `renderWithStore(ui: ReactElement)` from `@/test/renderWithStore`, which returns `{ store, ...renderResult }`.

- [ ] **Step 1: Confirm the store factory (already done)**

`frontend/src/app/store.ts` should read:

```ts
import { configureStore } from '@reduxjs/toolkit';
import { baseApi } from './api/baseApi';
import { chatReducer } from '@/features/chat/chatSlice';
import { ingestReducer } from '@/features/ingest/ingestSlice';

// A factory so tests can start each case from a clean store; the app uses the singleton below.
export function makeStore() {
  return configureStore({
    reducer: {
      [baseApi.reducerPath]: baseApi.reducer,
      chat: chatReducer,
      ingest: ingestReducer,
    },
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware().concat(baseApi.middleware),
  });
}

export const store = makeStore();

export type AppStore = ReturnType<typeof makeStore>;
export type RootState = ReturnType<AppStore['getState']>;
export type AppDispatch = AppStore['dispatch'];
```

- [ ] **Step 2: Install the test dependencies**

Run (from `frontend/`):

```bash
npm install -D vitest@^5.0.1 @vitest/coverage-v8@^5.0.1 jsdom@^30.1.1 @testing-library/react@^16.3.3 @testing-library/dom@^10.4.2 @testing-library/user-event@^14.6.7 @testing-library/jest-dom@^7.0.1 msw@^2.15.0
```

Then add these to `"scripts"` in `frontend/package.json`, after `"preview"`:

```json
    "test": "vitest run",
    "test:watch": "vitest",
    "coverage": "vitest run --coverage"
```

- [ ] **Step 3: Add the test settings to the Vite config**

Replace `frontend/vite.config.ts` with:

```ts
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import tsconfigPaths from 'vite-tsconfig-paths'

export default defineConfig({
  plugins: [react(), tsconfigPaths()],
  server: {
    host: true, // bind to 0.0.0.0 so Docker can expose the port
    proxy: {
      '/api': {
        // In docker-compose dev: VITE_BACKEND_URL=http://backend:8002
        // Locally without Docker: leave unset, falls back to localhost:8002
        target: process.env.VITE_BACKEND_URL ?? 'http://localhost:8002',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    // RTK Query needs an absolute base URL under Node's fetch.
    env: { VITE_API_URL: 'http://localhost/api' },
    coverage: {
      provider: 'v8',
      include: ['src/**/*.{ts,tsx}'],
      exclude: ['src/test/**', 'src/main.tsx'],
    },
  },
})
```

- [ ] **Step 4: Keep coverage output out of lint and git**

In `frontend/eslint.config.js`, change `globalIgnores(['dist'])` to `globalIgnores(['dist', 'coverage'])`.

Append to `frontend/.gitignore`:

```
coverage
```

- [ ] **Step 5: Create the test helpers**

`frontend/src/test/server.ts`:

```ts
import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';

export const API = 'http://localhost/api';

export const handlers = [
  http.post(`${API}/chat`, () =>
    HttpResponse.json({
      answer: 'Access reviews happen quarterly.',
      sources: ['Source: access-control-policy.md\nUser access is reviewed quarterly.'],
      tool_calls: [{ name: 'vector_search', args: { query: 'access review frequency' } }],
    }),
  ),
];

export const server = setupServer(...handlers);
```

`frontend/src/test/setup.ts`:

```ts
import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterAll, afterEach, beforeAll } from 'vitest';
import { server } from './server';

// jsdom does not implement scrollIntoView; MessageList calls it on every update.
Element.prototype.scrollIntoView = () => {};

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => {
  server.resetHandlers();
  cleanup();
});
afterAll(() => server.close());
```

`frontend/src/test/renderWithStore.tsx`:

```tsx
import type { ReactElement } from 'react';
import { render } from '@testing-library/react';
import { Provider } from 'react-redux';
import { makeStore } from '@/app/store';

export function renderWithStore(ui: ReactElement) {
  const store = makeStore();
  return { store, ...render(<Provider store={store}>{ui}</Provider>) };
}
```

- [ ] **Step 6: Write the chat slice tests**

`frontend/src/features/chat/chatSlice.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import type { Message } from '@/types';
import {
  addMessage,
  appendToken,
  chatReducer,
  clearMessages,
  finishStreaming,
  setMessageSources,
  setMessageToolCalls,
} from './chatSlice';

const streaming: Message = { id: 'a1', role: 'assistant', content: 'Hel', isStreaming: true };

function stateWith(...messages: Message[]) {
  return { messages };
}

describe('chatSlice', () => {
  it('adds a message', () => {
    const state = chatReducer(undefined, addMessage(streaming));
    expect(state.messages).toEqual([streaming]);
  });

  it('appends a streamed token to the matching message', () => {
    const state = chatReducer(stateWith(streaming), appendToken({ id: 'a1', token: 'lo' }));
    expect(state.messages[0].content).toBe('Hello');
  });

  it('sets sources and tool calls on the matching message', () => {
    let state = chatReducer(stateWith(streaming), setMessageSources({ id: 'a1', sources: ['s1'] }));
    state = chatReducer(
      state,
      setMessageToolCalls({ id: 'a1', toolCalls: [{ name: 'vector_search', args: { query: 'q' } }] }),
    );
    expect(state.messages[0].sources).toEqual(['s1']);
    expect(state.messages[0].toolCalls).toEqual([{ name: 'vector_search', args: { query: 'q' } }]);
  });

  it('marks a message as finished streaming', () => {
    const state = chatReducer(stateWith(streaming), finishStreaming('a1'));
    expect(state.messages[0].isStreaming).toBe(false);
  });

  it('ignores updates for an unknown id', () => {
    const before = stateWith(streaming);
    let state = chatReducer(before, appendToken({ id: 'nope', token: 'x' }));
    state = chatReducer(state, setMessageSources({ id: 'nope', sources: ['s'] }));
    state = chatReducer(state, setMessageToolCalls({ id: 'nope', toolCalls: [] }));
    state = chatReducer(state, finishStreaming('nope'));
    expect(state).toEqual(before);
  });

  it('clears all messages', () => {
    const state = chatReducer(stateWith(streaming), clearMessages());
    expect(state.messages).toEqual([]);
  });
});
```

- [ ] **Step 7: Run the tests, typecheck, and lint**

Run: `npm test`
Expected: `Test Files 1 passed (1)`, `Tests 6 passed (6)`.

Run: `npx tsc -b --noEmit && npm run lint`
Expected: tsc exits 0. Lint shows exactly one warning, the existing `react-hooks/exhaustive-deps` warning in `ChatPage.tsx` (that's D4), and no errors.

- [ ] **Step 8: Stage for review and stop**

```bash
git add frontend/package.json frontend/package-lock.json frontend/vite.config.ts frontend/eslint.config.js frontend/.gitignore frontend/src/app/store.ts frontend/src/test/setup.ts frontend/src/test/server.ts frontend/src/test/renderWithStore.tsx frontend/src/features/chat/chatSlice.test.ts
git diff --cached --stat
```

After approval:

```bash
git commit -m "$(cat <<'EOF'
test: add Vitest, Testing Library, and MSW with chat slice tests

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: Frontend component tests

**Files:**
- Test: `frontend/src/features/chat/ChatInput.test.tsx`, `frontend/src/features/chat/SourceCitations.test.tsx`, `frontend/src/features/chat/AgentSteps.test.tsx`

**Interfaces:**
- Consumes (app): `ChatInput({ onSubmit, disabled })`, `SourceCitations({ sources })`, `AgentSteps({ toolCalls })`.
- Produces: nothing new.

- [ ] **Step 1: Write the ChatInput tests**

`frontend/src/features/chat/ChatInput.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { ChatInput } from './ChatInput';

describe('ChatInput', () => {
  it('submits the trimmed question on Enter and clears the box', async () => {
    const onSubmit = vi.fn();
    render(<ChatInput onSubmit={onSubmit} />);
    const box = screen.getByRole('textbox');

    await userEvent.type(box, '  what is MFA?  {Enter}');

    expect(onSubmit).toHaveBeenCalledWith('what is MFA?');
    expect(box).toHaveValue('');
  });

  it('adds a newline on Shift+Enter instead of submitting', async () => {
    const onSubmit = vi.fn();
    render(<ChatInput onSubmit={onSubmit} />);

    await userEvent.type(screen.getByRole('textbox'), 'line one{Shift>}{Enter}{/Shift}line two');

    expect(onSubmit).not.toHaveBeenCalled();
    expect(screen.getByRole('textbox')).toHaveValue('line one\nline two');
  });

  it('ignores an empty question', async () => {
    const onSubmit = vi.fn();
    render(<ChatInput onSubmit={onSubmit} />);

    await userEvent.click(screen.getByRole('button', { name: 'Send' }));
    await userEvent.type(screen.getByRole('textbox'), '   {Enter}');

    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('shows "Thinking…" and blocks input while disabled', () => {
    render(<ChatInput onSubmit={vi.fn()} disabled />);

    expect(screen.getByRole('button', { name: 'Thinking…' })).toBeDisabled();
    expect(screen.getByRole('textbox')).toBeDisabled();
  });
});
```

- [ ] **Step 2: Write the SourceCitations tests**

`frontend/src/features/chat/SourceCitations.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { SourceCitations } from './SourceCitations';

describe('SourceCitations', () => {
  it('renders nothing when there are no sources', () => {
    const { container } = render(<SourceCitations sources={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('uses singular and plural labels', () => {
    const { rerender } = render(<SourceCitations sources={['Source: a.md\ntext']} />);
    expect(screen.getByRole('button', { name: /^1 source ▼$/ })).toBeInTheDocument();

    rerender(<SourceCitations sources={['Source: a.md\ntext', 'Source: b.md\ntext']} />);
    expect(screen.getByRole('button', { name: /^2 sources ▼$/ })).toBeInTheDocument();
  });

  it('expands to show each source header and excerpt', async () => {
    render(<SourceCitations sources={['Source: a.md\nfirst excerpt']} />);
    const toggle = screen.getByRole('button');
    expect(toggle).toHaveAttribute('aria-expanded', 'false');

    await userEvent.click(toggle);

    expect(toggle).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByText('Source: a.md')).toBeInTheDocument();
    expect(screen.getByText('first excerpt')).toBeInTheDocument();
  });

  it('cuts excerpts at 200 characters with an ellipsis', async () => {
    render(<SourceCitations sources={[`Source: a.md\n${'x'.repeat(250)}`]} />);

    await userEvent.click(screen.getByRole('button'));

    expect(screen.getByText(`${'x'.repeat(200)}…`)).toBeInTheDocument();
  });
});
```

- [ ] **Step 3: Write the AgentSteps tests, including the known defect D6**

`frontend/src/features/chat/AgentSteps.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { AgentSteps } from './AgentSteps';

describe('AgentSteps', () => {
  it('lists each tool call with its query', () => {
    render(<AgentSteps toolCalls={[{ name: 'vector_search', args: { query: 'mfa policy' } }]} />);

    expect(screen.getByText('vector_search')).toBeInTheDocument();
    expect(screen.getByText('“mfa policy”')).toBeInTheDocument();
  });

  // Known defect D6: String(undefined) is "undefined", so a call with no query shows “undefined”.
  it.fails('shows no query text for a tool call without a query', () => {
    render(<AgentSteps toolCalls={[{ name: 'list_documents', args: {} }]} />);

    expect(screen.getByText('list_documents')).toBeInTheDocument();
    expect(screen.queryByText(/undefined/)).not.toBeInTheDocument();
  });
});
```

- [ ] **Step 4: Run the tests**

Run: `npm test`
Expected: `Test Files 4 passed (4)`, `Tests 15 passed | 1 expected fail (16)`.

- [ ] **Step 5: Confirm D6 fails for the right reason**

Run: `sed 's/it\.fails(/it(/' src/features/chat/AgentSteps.test.tsx > src/features/chat/AgentSteps.strict.test.tsx && npx vitest run src/features/chat/AgentSteps.strict.test.tsx; rm src/features/chat/AgentSteps.strict.test.tsx`
Expected: the "without a query" test fails because the text `undefined` is found. Then the temporary file is deleted.

- [ ] **Step 6: Stage for review and stop**

```bash
git add frontend/src/features/chat/ChatInput.test.tsx frontend/src/features/chat/SourceCitations.test.tsx frontend/src/features/chat/AgentSteps.test.tsx
git diff --cached --stat
```

After approval:

```bash
git commit -m "$(cat <<'EOF'
test: cover chat input, citations, and agent steps components

Records known defect D6 (a tool call without a query shows "undefined") as it.fails.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: Chat page flow tests

**Files:**
- Test: `frontend/src/features/chat/ChatPage.test.tsx`

**Interfaces:**
- Consumes (Task 5): `API`, `server` from `@/test/server`; `renderWithStore` from `@/test/renderWithStore`.
- Consumes (app): `ChatPage`.
- Produces: nothing new.

- [ ] **Step 1: Write the page tests, including known defects D3 and D4**

`frontend/src/features/chat/ChatPage.test.tsx`:

```tsx
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';
import { API, server } from '@/test/server';
import { renderWithStore } from '@/test/renderWithStore';
import { ChatPage } from './ChatPage';

async function ask(question: string) {
  const user = userEvent.setup();
  await user.type(screen.getByRole('textbox'), `${question}{Enter}`);
}

describe('ChatPage', () => {
  it('shows the error message when the API fails', async () => {
    server.use(http.post(`${API}/chat`, () => new HttpResponse(null, { status: 500 })));
    renderWithStore(<ChatPage />);
    await ask('How often are access reviews?');
    expect(await screen.findByText('An error occurred. Please try again.')).toBeInTheDocument();
  });

  // Known defect D3: the placeholder assistant message is never replaced.
  it.fails('shows the answer exactly once, with its sources and agent steps', async () => {
    const { store } = renderWithStore(<ChatPage />);
    await ask('How often are access reviews?');
    expect(await screen.findByText('Access reviews happen quarterly.')).toBeInTheDocument();
    const assistant = store.getState().chat.messages.filter((m) => m.role === 'assistant');
    expect(assistant).toHaveLength(1);
    expect(screen.getByRole('button', { name: /1 source/ })).toBeInTheDocument();
    expect(screen.getByText('vector_search')).toBeInTheDocument();
  });

  // Known defect D4: history is captured from the first render and is always empty.
  it.fails('sends the previous turn as history on the next question', async () => {
    const bodies: unknown[] = [];
    server.use(
      http.post(`${API}/chat`, async ({ request }) => {
        bodies.push(await request.json());
        return HttpResponse.json({ answer: `answer ${bodies.length}`, sources: [], tool_calls: [] });
      }),
    );
    renderWithStore(<ChatPage />);
    await ask('first question');
    await screen.findByText('answer 1');
    await ask('second question');
    await screen.findByText('answer 2');
    expect(bodies[1]).toMatchObject({
      question: 'second question',
      messages: [
        { role: 'user', content: 'first question' },
        { role: 'assistant', content: 'answer 1' },
      ],
    });
  });

  it('clears the conversation', async () => {
    renderWithStore(<ChatPage />);
    await ask('How often are access reviews?');
    await screen.findByText('Access reviews happen quarterly.');
    await userEvent.setup().click(screen.getByRole('button', { name: 'Clear' }));
    await waitFor(() =>
      expect(screen.getByText('Ask anything about your indexed documents.')).toBeInTheDocument(),
    );
  });
});
```

- [ ] **Step 2: Run the whole frontend suite**

Run: `npm test`
Expected: `Test Files 5 passed (5)`, `Tests 17 passed | 3 expected fail (20)`. React prints "Encountered two children with the same key" warnings during the D3 test. That's D3 itself, and it's expected.

- [ ] **Step 3: Confirm D3 and D4 fail for the right reasons**

Run: `sed 's/it\.fails(/it(/' src/features/chat/ChatPage.test.tsx > src/features/chat/ChatPage.strict.test.tsx && npx vitest run src/features/chat/ChatPage.strict.test.tsx; rm src/features/chat/ChatPage.strict.test.tsx`
Expected:
- D3: `expected [ { …(6) }, { …(6) } ] to have a length of 1 but got 2`
- D4: the diff shows `"messages": []` was received.

The temporary file is then deleted.

- [ ] **Step 4: Run coverage, typecheck, and lint**

Run: `npm run coverage && npx tsc -b --noEmit && npm run lint`
Expected: a coverage table prints. tsc exits 0. Lint shows only the existing D4 warning in `ChatPage.tsx`, and nothing from `coverage/`.

- [ ] **Step 5: Stage for review and stop**

```bash
git add frontend/src/features/chat/ChatPage.test.tsx
git diff --cached --stat
```

After approval:

```bash
git commit -m "$(cat <<'EOF'
test: cover the chat page flow with MSW

Records known defects D3 (duplicate assistant message) and D4 (history always empty)
as it.fails, so CI stays green until each fix lands.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 8: CI workflow and README

**Files:**
- Create: `.github/workflows/ci.yml`
- Modify: `README.md` (badge under the title; a new "Running tests" section before "Environment variables")

**Interfaces:**
- Consumes: `backend/requirements-dev.txt`, `backend/pyproject.toml`, the `REQUIRE_DATABASE` and `TEST_DATABASE_URL` handling in `backend/tests/conftest.py`, and the `lint`, `build`, and `test` npm scripts.
- Produces: the `CI` workflow at `.github/workflows/ci.yml`, which the badge URL points to.

- [ ] **Step 1: Write the workflow**

`.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
  pull_request:

jobs:
  backend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend
    services:
      postgres:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: ragdemo
        ports:
          - 5432:5432
        options: >-
          --health-cmd "pg_isready -U postgres"
          --health-interval 5s
          --health-timeout 5s
          --health-retries 10
    env:
      TEST_DATABASE_URL: postgresql://postgres:postgres@localhost:5432/ragdemo_test
      REQUIRE_DATABASE: "1"
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-python@v7
        with:
          python-version: "3.12"
          cache: pip
          cache-dependency-path: |
            backend/requirements.txt
            backend/requirements-dev.txt
      - run: pip install -r requirements.txt -r requirements-dev.txt
      - run: ruff check .
      - run: pytest --cov=app --cov-report=term-missing

  frontend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-node@v7
        with:
          node-version: "22"
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - run: npm ci
      - run: npm run lint
      - run: npm run build
      - run: npm test
```

- [ ] **Step 2: Add the badge under the README title**

In `README.md`, replace:

```markdown
# Agentic RAG Pipeline

A production-ready
```

with:

```markdown
# Agentic RAG Pipeline

[![CI](https://github.com/seandjones/rag-pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/seandjones/rag-pipeline/actions/workflows/ci.yml)

A production-ready
```

- [ ] **Step 3: Add the "Running tests" section**

In `README.md`, insert this immediately before the line `## Environment variables`:

````markdown
## Running tests

CI runs everything below on every push and pull request.

### Backend

Unit tests need nothing running. Integration tests need Postgres with pgvector. They use their own `ragdemo_test` database, never your `ragdemo` data, and skip with a message if Postgres isn't reachable.

```bash
docker compose up -d postgres        # add POSTGRES_PORT=5433 if 5432 is taken
cd backend
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt

# Only needed if Postgres isn't on localhost:5432
export TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5433/ragdemo_test

pytest                        # everything
pytest -m "not integration"   # unit tests only
pytest --cov=app              # with coverage
ruff check .                  # lint
```

### Frontend

```bash
cd frontend
npm install
npm test              # run once
npm run test:watch    # re-run on save
npm run coverage      # with coverage
```

Tests marked `it.fails` document known bugs. They pass while the bug exists and fail once it's fixed, which is the signal to switch them to `it`.

---

````

- [ ] **Step 4: Validate the workflow file**

Run: `python3 -c "import yaml, sys; yaml.safe_load(open('.github/workflows/ci.yml')); print('ok')"`
Expected: `ok`. If PyYAML isn't available, use `ruby -ryaml -e "YAML.load_file('.github/workflows/ci.yml'); puts 'ok'"`.

Then run each CI command locally one last time:
- from `backend/`: `ruff check . && pytest -q` (expected `47 passed`)
- from `frontend/`: `npm ci && npm run lint && npm run build && npm test` (expected lint 0 errors, build succeeds, `17 passed | 3 expected fail`)

- [ ] **Step 5: Stage for review and stop**

```bash
git add .github/workflows/ci.yml README.md
git diff --cached --stat
```

After approval:

```bash
git commit -m "$(cat <<'EOF'
ci: run backend and frontend lint, build, and tests on every push

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

Do not push. Pushing happens only after the owner has committed `ingest.py` (see Task 4) and asks for it.

---

## After Plan 1

- The spec and this plan (`docs/superpowers/`) are committed only if the owner asks.
- Plan 2 (eval data and harness) is written next. It uses `tests.fakes.FakeOpenAI` and the `database` and `db_session` fixtures from this plan.
- D3, D4, and D6 each get their own small, reviewed fix. In the same change, the matching test switches from `it.fails` to `it`.
