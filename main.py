import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from openai import OpenAI
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text

app = FastAPI(title="RAG Pipeline", description="RAG Pipeline using OpenAI and PostgreSQL")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost/ragdemo")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-4o-mini")

engine = create_engine(DB_URL)


class IngestRequest(BaseModel):
    directory: str = Field(..., description="Absolute or relative path to local folder")
    patterns: list[str] = Field(default_factory=lambda: ["*.txt", "*.md"])
    chunk_size: int = 1000
    overlap: int = 100


class ChatRequest(BaseModel):
    question: str
    top_k: int = 5


def ensure_schema() -> None:
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS document_chunks (
                    id BIGSERIAL PRIMARY KEY,
                    source_path TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    embedding VECTOR(1536) NOT NULL
                )
                """
            )
        )


def chunk_text(content: str, chunk_size: int = 1000, overlap: int = 100) -> list[str]:
    if chunk_size <= overlap:
        raise ValueError("chunk_size must be larger than overlap")

    chunks: list[str] = []
    start = 0
    while start < len(content):
        end = min(start + chunk_size, len(content))
        chunks.append(content[start:end])
        if end == len(content):
            break
        start += chunk_size - overlap
    return chunks


def embedding_to_pgvector(embedding: list[float]) -> str:
    return "[" + ",".join(str(value) for value in embedding) + "]"

def get_embedding(text: str) -> list[float]:
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text
    )
    return response.data[0].embedding

def store_embedding(content: str, embedding: list[float], source_path: str, chunk_index: int) -> None:
    embedding_literal = embedding_to_pgvector(embedding)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO document_chunks (source_path, chunk_index, content, embedding)
                VALUES (:source_path, :chunk_index, :content, CAST(:embedding AS vector))
                """
            ),
            {
                "source_path": source_path,
                "chunk_index": chunk_index,
                "content": content,
                "embedding": embedding_literal,
            },
        )

def query_database(query: str) -> str:
    with engine.connect() as connection:
        result = connection.execute(text(query))
        return "\n".join([str(row) for row in result])
    
def search_similar_chunks(query: str, top_k: int = 5) -> list[str]:
    query_embedding = get_embedding(query)
    query_vector = embedding_to_pgvector(query_embedding)
    with engine.begin() as connection:
        result = connection.execute(
            text("""
                SELECT source_path, content
                FROM document_chunks
                 ORDER BY embedding <-> CAST(:query_embedding AS vector)
                 LIMIT :top_k
            """),
            {"query_embedding": query_vector, "top_k": top_k}
        )
        chunks: list[tuple[str, str]] = []
        for row in result:
            source_path, content = row
            chunks.append((source_path, content))
        return [f"Source: {source_path}\n{content}" for source_path, content in chunks]

# cosine similarity function to compare query embedding with chunk embeddings
def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = sum(a * a for a in vec1) ** 0.5
    norm2 = sum(b * b for b in vec2) ** 0.5
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot_product / (norm1 * norm2)

def build_prompt(query: str, context: list[str]) -> str:
    prompt = "You are a helpful assistant. Using ONLY the following context to answer the question:\n\n"
    for i, chunk in enumerate(context):
        prompt += f"Chunk {i + 1}:\n{chunk}\n\n"
    prompt += f"Question: {query}\nAnswer:"
    return prompt

def generate_answer(prompt: str) -> str:
    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {
                "role": "system",
                "content": "Answer only from retrieved context. If context is insufficient, say so clearly.",
            },
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content.strip()


def read_files(directory: str, patterns: list[str]) -> list[tuple[str, str]]:
    base_dir = Path(directory).expanduser().resolve()
    files_with_content: list[tuple[str, str]] = []
    for pattern in patterns:
        for file_path in base_dir.rglob(pattern):
            if not file_path.is_file():
                continue
            content = file_path.read_text(encoding="utf-8", errors="ignore").strip()
            if content:
                files_with_content.append((str(file_path), content))
    return files_with_content


@app.on_event("startup")
def startup_event() -> None:
    ensure_schema()


@app.post("/ingest-local")
def ingest_local(request: IngestRequest):
    target_dir = Path(request.directory).expanduser().resolve()
    if not target_dir.exists() or not target_dir.is_dir():
        raise HTTPException(status_code=400, detail="directory must exist and be a folder")

    try:
        files = read_files(str(target_dir), request.patterns)
    except OSError as exc:
        raise HTTPException(status_code=400, detail=f"could not read files: {exc}") from exc

    if not files:
        return {"message": "No matching non-empty files found", "chunks_stored": 0}

    total_chunks = 0
    for source_path, content in files:
        chunks = chunk_text(content, chunk_size=request.chunk_size, overlap=request.overlap)
        for idx, chunk in enumerate(chunks):
            embedding = get_embedding(chunk)
            store_embedding(chunk, embedding, source_path=source_path, chunk_index=idx)
            total_chunks += 1

    return {
        "message": "Ingestion complete",
        "files_indexed": len(files),
        "chunks_stored": total_chunks,
    }


@app.post("/chat")
async def chat(request: ChatRequest):
    similar_chunks = search_similar_chunks(request.question, top_k=request.top_k)
    prompt = build_prompt(request.question, similar_chunks)
    answer = generate_answer(prompt)
    return {"answer": answer, "context_count": len(similar_chunks)}

