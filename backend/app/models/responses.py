from pydantic import BaseModel


class IngestResponse(BaseModel):
    status: str
    job_id: str


class JobStatus(BaseModel):
    job_id: str
    status: str  # pending | running | complete | failed
    files_indexed: int = 0
    chunks_stored: int = 0
    error: str | None = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[str]
    tool_calls: list[dict] = []


class DocumentsResponse(BaseModel):
    documents: list[str]
    total: int
