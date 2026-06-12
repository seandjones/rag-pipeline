from openai import AsyncOpenAI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.embeddings import get_embedding


def _to_pgvector(embedding: list[float]) -> str:
    return "[" + ",".join(str(v) for v in embedding) + "]"


async def search_similar_chunks(
    query: str,
    session: AsyncSession,
    client: AsyncOpenAI,
    top_k: int = 5,
) -> list[str]:
    query_embedding = await get_embedding(query, client)
    query_vector = _to_pgvector(query_embedding)
    result = await session.execute(
        text("""
            SELECT source_path, content
            FROM document_chunks
            ORDER BY embedding <-> CAST(:query_embedding AS vector)
            LIMIT :top_k
        """),
        {"query_embedding": query_vector, "top_k": top_k},
    )
    rows = result.fetchall()
    return [f"Source: {source_path}\n{content}" for source_path, content in rows]


async def store_embedding(
    content: str,
    embedding: list[float],
    source_path: str,
    chunk_index: int,
    session: AsyncSession,
) -> None:
    await session.execute(
        text("""
            INSERT INTO document_chunks (source_path, chunk_index, content, embedding)
            VALUES (:source_path, :chunk_index, :content, CAST(:embedding AS vector))
            ON CONFLICT (source_path, chunk_index)
            DO UPDATE SET
                content = EXCLUDED.content,
                embedding = EXCLUDED.embedding
        """),
        {
            "source_path": source_path,
            "chunk_index": chunk_index,
            "content": content,
            "embedding": _to_pgvector(embedding),
        },
    )


async def list_documents(session: AsyncSession) -> list[str]:
    result = await session.execute(
        text("SELECT DISTINCT source_path FROM document_chunks ORDER BY source_path")
    )
    return [row[0] for row in result.fetchall()]


async def delete_document(source_path: str, session: AsyncSession) -> int:
    result = await session.execute(
        text("DELETE FROM document_chunks WHERE source_path = :path"),
        {"path": source_path},
    )
    await session.commit()
    return result.rowcount
