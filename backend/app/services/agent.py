import json
from dataclasses import dataclass, field

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.services.retrieval import list_documents, search_similar_chunks

settings = get_settings()

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "vector_search",
            "description": (
                "Search the knowledge base for document chunks relevant to a query. "
                "Use this before answering any question."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to find relevant content.",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of results to return (default 5).",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_documents",
            "description": "List all document source paths available in the knowledge base.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]


@dataclass
class AgentResponse:
    answer: str
    sources: list[str] = field(default_factory=list)
    tool_calls: list[dict] = field(default_factory=list)


async def run_agent(
    question: str,
    session: AsyncSession,
    client: AsyncOpenAI,
    top_k: int = 5,
    history: list[dict] | None = None,
) -> AgentResponse:
    messages: list[ChatCompletionMessageParam] = [
        {
            "role": "system",
            "content": (
                "You are a helpful assistant with access to a knowledge base. "
                "Always use the vector_search tool to find relevant information before answering. "
                "Answer only based on retrieved content."
            ),
        },
        *(history or []),
        {"role": "user", "content": question},
    ]

    collected_sources: list[str] = []
    tool_call_log: list[dict] = []

    while True:
        response = await client.chat.completions.create(
            model=settings.chat_model,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )

        choice = response.choices[0]
        messages.append(choice.message)  # type: ignore[arg-type]

        if choice.finish_reason == "stop":
            return AgentResponse(
                answer=choice.message.content or "",
                sources=list(dict.fromkeys(collected_sources)),
                tool_calls=tool_call_log,
            )

        if choice.finish_reason == "tool_calls" and choice.message.tool_calls:
            for tool_call in choice.message.tool_calls:
                fn_name = tool_call.function.name
                fn_args = json.loads(tool_call.function.arguments)
                tool_call_log.append({"name": fn_name, "args": fn_args})

                if fn_name == "vector_search":
                    results = await search_similar_chunks(
                        query=fn_args["query"],
                        session=session,
                        client=client,
                        top_k=fn_args.get("top_k", top_k),
                    )
                    collected_sources.extend(results)
                    tool_result = "\n\n".join(results) or "No results found."

                elif fn_name == "list_documents":
                    docs = await list_documents(session)
                    tool_result = "\n".join(docs) or "No documents indexed yet."

                else:
                    tool_result = f"Unknown tool: {fn_name}"

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": tool_result,
                    }
                )
        else:
            return AgentResponse(
                answer=choice.message.content or "",
                sources=list(dict.fromkeys(collected_sources)),
                tool_calls=tool_call_log,
            )
