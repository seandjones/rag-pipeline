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
    assert results[1] == "Source: logs.md\naudit logs are retained for one year"


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
