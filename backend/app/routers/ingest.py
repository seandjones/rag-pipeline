import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Request, UploadFile
from openai import AsyncOpenAI

from app.db.engine import AsyncSessionLocal
from app.models.requests import IngestRequest
from app.models.responses import IngestResponse, JobStatus
from app.services.chunker import chunk_text, extract_text_from_pdf_bytes, normalize_patterns, read_files
from app.services.embeddings import batch_embeddings
from app.services.retrieval import store_embedding

router = APIRouter(prefix="/ingest", tags=["ingest"])

# In-memory job store — suitable for single-process deployments.
# Replace with Redis or a DB table for multi-instance setups.
_jobs: dict[str, JobStatus] = {}


async def get_openai_client(request: Request) -> AsyncOpenAI:
    return request.app.state.openai_client


async def _run_ingestion(
    job_id: str,
    ingest_request: IngestRequest,
    openai_client: AsyncOpenAI,
) -> None:
    _jobs[job_id].status = "running"
    try:
        target_dir = Path(ingest_request.directory).expanduser().resolve()
        patterns = normalize_patterns(ingest_request.patterns)
        files = read_files(str(target_dir), patterns)

        total_chunks = 0
        async with AsyncSessionLocal() as session:
            for source_path, content in files:
                chunks = chunk_text(
                    content.replace("\x00", ""),
                    chunk_size=ingest_request.chunk_size,
                    overlap=ingest_request.overlap,
                )
                embeddings = await batch_embeddings(chunks, openai_client)
                for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                    await store_embedding(chunk, embedding, source_path, idx, session)
                    total_chunks += 1
            await session.commit()

        _jobs[job_id].status = "complete"
        _jobs[job_id].files_indexed = len(files)
        _jobs[job_id].chunks_stored = total_chunks

    except Exception as exc:
        _jobs[job_id].status = "failed"
        _jobs[job_id].error = str(exc)


@router.post("/local", response_model=IngestResponse, status_code=202)
async def ingest_local(
    request: IngestRequest,
    background_tasks: BackgroundTasks,
    openai_client: AsyncOpenAI = Depends(get_openai_client),
) -> IngestResponse:
    target_dir = Path(request.directory).expanduser().resolve()
    if not target_dir.exists() or not target_dir.is_dir():
        raise HTTPException(
            status_code=400, detail="directory must exist and be a folder"
        )

    job_id = str(uuid.uuid4())
    _jobs[job_id] = JobStatus(job_id=job_id, status="pending")
    background_tasks.add_task(_run_ingestion, job_id, request, openai_client)
    return IngestResponse(status="accepted", job_id=job_id)


async def _run_upload_ingestion(
    job_id: str,
    file_data: list[tuple[str, bytes]],
    chunk_size: int,
    overlap: int,
    openai_client: AsyncOpenAI,
) -> None:
    _jobs[job_id].status = "running"
    try:
        total_chunks = 0
        async with AsyncSessionLocal() as session:
            for filename, content in file_data:
                if filename.lower().endswith(".pdf"):
                    text = extract_text_from_pdf_bytes(content)
                else:
                    try:
                        text = content.decode("utf-8", errors="ignore").strip()
                    except Exception:
                        continue
                if not text:
                    continue
                chunks = chunk_text(text.replace("\x00", ""), chunk_size=chunk_size, overlap=overlap)
                embeddings = await batch_embeddings(chunks, openai_client)
                for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                    await store_embedding(chunk, embedding, filename, idx, session)
                    total_chunks += 1
            await session.commit()

        _jobs[job_id].status = "complete"
        _jobs[job_id].files_indexed = len(file_data)
        _jobs[job_id].chunks_stored = total_chunks
    except Exception as exc:
        _jobs[job_id].status = "failed"
        _jobs[job_id].error = str(exc)


@router.post("/upload", response_model=IngestResponse, status_code=202)
async def ingest_upload(
    background_tasks: BackgroundTasks,
    files: Annotated[list[UploadFile], File()],
    chunk_size: Annotated[int, Form()] = 1000,
    overlap: Annotated[int, Form()] = 100,
    openai_client: AsyncOpenAI = Depends(get_openai_client),
) -> IngestResponse:
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    # Read all bytes before the response is sent — UploadFile is not readable in background tasks.
    file_data: list[tuple[str, bytes]] = [
        (upload.filename or "unknown", await upload.read()) for upload in files
    ]

    job_id = str(uuid.uuid4())
    _jobs[job_id] = JobStatus(job_id=job_id, status="pending")
    background_tasks.add_task(
        _run_upload_ingestion, job_id, file_data, chunk_size, overlap, openai_client
    )
    return IngestResponse(status="accepted", job_id=job_id)


@router.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str) -> JobStatus:
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return _jobs[job_id]
