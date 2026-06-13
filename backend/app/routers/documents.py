from fastapi import APIRouter, Depends

from app.db.engine import get_session
from app.models.responses import DocumentsResponse
from app.services.retrieval import delete_document, list_documents
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=DocumentsResponse)
async def get_documents(session: AsyncSession = Depends(get_session)) -> DocumentsResponse:
    docs = await list_documents(session)
    return DocumentsResponse(documents=docs, total=len(docs))


@router.delete("/{source_path:path}")
async def remove_document(
    source_path: str,
    session: AsyncSession = Depends(get_session),
) -> dict:
    count = await delete_document(source_path, session)
    return {"deleted_chunks": count, "source_path": source_path}
