import os

from openai import OpenAI
from sqlalchemy import create_engine, text

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

engine = create_engine(
    "postgresql://postgres:postgres@localhost/ragdemo"
)
def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 100) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
        start = end
    return chunks

def get_embedding(text: str) -> list[float]:
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding

def store_embedding(text: str, embedding: list[float]):
    with engine.connect() as connection:
        connection.execute(
            text("INSERT INTO document_chunks (content, embedding) VALUES (:content, :embedding)"),
            {"content": text, "embedding": embedding}
        )

def query_database(query: str) -> str:
    with engine.connect() as connection:
        result = connection.execute(text(query))
        return "\n".join([str(row) for row in result])