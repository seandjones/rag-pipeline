from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from openai import AsyncOpenAI

from app.config import get_settings
from app.db.migrations import ensure_schema
from app.routers import chat, documents, ingest

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await ensure_schema()
    app.state.openai_client = AsyncOpenAI(api_key=settings.openai_api_key or None)
    yield
    await app.state.openai_client.close()


app = FastAPI(
    title="RAG Pipeline",
    description="Agentic RAG Pipeline using OpenAI and PostgreSQL with pgvector",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest.router)
app.include_router(chat.router)
app.include_router(documents.router)


@app.get("/health", tags=["meta"])
async def health() -> dict:
    return {"status": "ok"}
