from typing import Literal

from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    directory: str = Field(..., description="Absolute or relative path to local folder")
    patterns: list[str] = Field(default_factory=lambda: ["*.txt", "*.md", "*.pdf"])
    chunk_size: int = 1000
    overlap: int = 100


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    question: str
    top_k: int = 5
    messages: list[HistoryMessage] = []
