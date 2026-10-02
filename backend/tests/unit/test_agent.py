import pytest

from app.services import agent
from app.services.agent import run_agent
from tests.fakes import FakeOpenAI, text_reply, tool_reply


@pytest.fixture
def search_calls(monkeypatch):
    """Replace vector search with a stub that returns one chunk named after the query."""
    calls: list[dict] = []

    async def fake_search(query, session, client, top_k=5):
        calls.append({"query": query, "top_k": top_k})
        return [f"Source: {query}.md\nchunk about {query}"]

    monkeypatch.setattr(agent, "search_similar_chunks", fake_search)
    return calls


def _tool_messages(chat_call: dict) -> list[dict]:
    return [m for m in chat_call["messages"] if isinstance(m, dict) and m.get("role") == "tool"]


async def test_searches_then_answers(search_calls):
    client = FakeOpenAI(
        [tool_reply(("vector_search", {"query": "mfa"})), text_reply("MFA is required.")]
    )

    result = await run_agent("Is MFA required?", session=None, client=client)

    assert result.answer == "MFA is required."
    assert result.sources == ["Source: mfa.md\nchunk about mfa"]
    assert result.tool_calls == [{"name": "vector_search", "args": {"query": "mfa"}}]
    tool_messages = _tool_messages(client.chat_calls[1])
    assert tool_messages == [
        {"role": "tool", "tool_call_id": "call_0", "content": "Source: mfa.md\nchunk about mfa"}
    ]


async def test_duplicate_sources_are_collapsed(search_calls):
    client = FakeOpenAI(
        [
            tool_reply(("vector_search", {"query": "mfa"}), ("vector_search", {"query": "mfa"})),
            text_reply("done"),
        ]
    )

    result = await run_agent("Is MFA required?", session=None, client=client)

    assert result.sources == ["Source: mfa.md\nchunk about mfa"]
    assert len(result.tool_calls) == 2


async def test_top_k_comes_from_the_tool_call_or_the_default(search_calls):
    client = FakeOpenAI(
        [
            tool_reply(
                ("vector_search", {"query": "a"}),
                ("vector_search", {"query": "b", "top_k": 7}),
            ),
            text_reply("done"),
        ]
    )

    await run_agent("q", session=None, client=client, top_k=3)

    assert search_calls == [{"query": "a", "top_k": 3}, {"query": "b", "top_k": 7}]


async def test_empty_search_tells_the_model_nothing_was_found(monkeypatch):
    async def no_results(query, session, client, top_k=5):
        return []

    monkeypatch.setattr(agent, "search_similar_chunks", no_results)
    client = FakeOpenAI([tool_reply(("vector_search", {"query": "x"})), text_reply("done")])

    result = await run_agent("q", session=None, client=client)

    assert _tool_messages(client.chat_calls[1])[0]["content"] == "No results found."
    assert result.sources == []


@pytest.mark.parametrize(
    ("documents", "expected"),
    [(["a.md", "b.md"], "a.md\nb.md"), ([], "No documents indexed yet.")],
)
async def test_list_documents_tool(monkeypatch, documents, expected):
    async def fake_list(session):
        return documents

    monkeypatch.setattr(agent, "list_documents", fake_list)
    client = FakeOpenAI([tool_reply(("list_documents", {})), text_reply("done")])

    await run_agent("What documents are there?", session=None, client=client)

    assert _tool_messages(client.chat_calls[1])[0]["content"] == expected


async def test_unknown_tool_is_reported_back_to_the_model():
    client = FakeOpenAI([tool_reply(("delete_everything", {})), text_reply("done")])

    result = await run_agent("q", session=None, client=client)

    assert _tool_messages(client.chat_calls[1])[0]["content"] == "Unknown tool: delete_everything"
    assert result.tool_calls == [{"name": "delete_everything", "args": {}}]


async def test_history_sits_between_system_prompt_and_question():
    history = [
        {"role": "user", "content": "earlier question"},
        {"role": "assistant", "content": "earlier answer"},
    ]
    client = FakeOpenAI([text_reply("done")])

    await run_agent("new question", session=None, client=client, history=history)

    messages = client.chat_calls[0]["messages"]
    assert messages[0]["role"] == "system"
    assert messages[1:3] == history
    assert messages[3] == {"role": "user", "content": "new question"}


async def test_other_finish_reasons_return_whatever_text_there_is():
    client = FakeOpenAI([text_reply("partial answer", finish_reason="length")])

    result = await run_agent("q", session=None, client=client)

    assert result.answer == "partial answer"
    assert result.sources == []
