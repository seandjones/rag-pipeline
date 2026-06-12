from sqlalchemy import text

from app.db.engine import get_engine


async def ensure_schema() -> None:
    async with get_engine().begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.execute(
            text("""
                CREATE TABLE IF NOT EXISTS document_chunks (
                    id BIGSERIAL PRIMARY KEY,
                    source_path TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    embedding VECTOR(1536) NOT NULL
                )
            """)
        )

        # Backward-compatible migration for tables created before source metadata.
        await conn.execute(
            text("ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS source_path TEXT")
        )
        await conn.execute(
            text("ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS chunk_index INTEGER")
        )
        await conn.execute(
            text("""
                UPDATE document_chunks
                SET source_path = COALESCE(source_path, 'unknown')
                WHERE source_path IS NULL
            """)
        )
        await conn.execute(
            text("""
                UPDATE document_chunks
                SET chunk_index = COALESCE(chunk_index, 0)
                WHERE chunk_index IS NULL
            """)
        )
        await conn.execute(
            text("ALTER TABLE document_chunks ALTER COLUMN source_path SET NOT NULL")
        )
        await conn.execute(
            text("ALTER TABLE document_chunks ALTER COLUMN chunk_index SET NOT NULL")
        )
        await conn.execute(
            text("""
                CREATE UNIQUE INDEX IF NOT EXISTS uq_document_chunks_source_chunk
                ON document_chunks (source_path, chunk_index)
            """)
        )
