from openai import AsyncOpenAI

from app.config import get_settings

settings = get_settings()


async def get_embedding(text: str, client: AsyncOpenAI) -> list[float]:
    response = await client.embeddings.create(
        model=settings.embedding_model,
        input=text,
    )
    return response.data[0].embedding


async def batch_embeddings(texts: list[str], client: AsyncOpenAI) -> list[list[float]]:
    if not texts:
        return []
    response = await client.embeddings.create(
        model=settings.embedding_model,
        input=texts,
    )
    return [item.embedding for item in sorted(response.data, key=lambda x: x.index)]
