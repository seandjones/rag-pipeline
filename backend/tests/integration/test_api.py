import asyncio
from collections.abc import Iterator

import httpx
import pytest

from app.main import app
from app.services.retrieval import store_embedding
from tests.fakes import FakeOpenAI, fake_embedding, text_reply, tool_reply

pytestmark = pytest.mark.integration


@pytest.fixture
def fake_openai() -> Iterator[FakeOpenAI]:
    client = FakeOpenAI()
    # The routers read the client from app.state, which the lifespan normally fills in.
    # Put back whatever was there afterwards, so no later test inherits this fake.
    had_client = hasattr(app.state, "openai_client")
    previous = getattr(app.state, "openai_client", None)
    app.state.openai_client = client
    yield client
    if had_client:
        app.state.openai_client = previous
    else:
        del app.state.openai_client


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
