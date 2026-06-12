import json
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_session
from app.models.requests import ChatRequest
from app.models.responses import ChatResponse
from app.services.agent import run_agent
from app.services.generation import build_prompt, stream_answer
from app.services.retrieval import search_similar_chunks

router = APIRouter(prefix="/chat", tags=["chat"])


async def get_openai_client(request: Request) -> AsyncOpenAI:
    return request.app.state.openai_client


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    session: AsyncSession = Depends(get_session),
    client: AsyncOpenAI = Depends(get_openai_client),
) -> ChatResponse:
    result = await run_agent(request.question, session, client, top_k=request.top_k)
    return ChatResponse(
        answer=result.answer,
        sources=result.sources,
        tool_calls=result.tool_calls,
    )


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    session: AsyncSession = Depends(get_session),
    client: AsyncOpenAI = Depends(get_openai_client),
) -> StreamingResponse:
    similar_chunks = await search_similar_chunks(
        request.question, session, client, top_k=request.top_k
    )
    prompt = build_prompt(request.question, similar_chunks)

    async def event_stream() -> AsyncGenerator[str, None]:
        sources_event = json.dumps({"type": "sources", "data": similar_chunks})
        yield f"data: {sources_event}\n\n"

        async for token in stream_answer(prompt, client):
            token_event = json.dumps({"type": "token", "data": token})
            yield f"data: {token_event}\n\n"

        yield 'data: {"type": "done"}\n\n'

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
