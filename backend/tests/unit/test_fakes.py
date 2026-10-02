import math

import pytest

from tests.fakes import DIMENSIONS, FakeOpenAI, fake_embedding, text_reply


def test_fake_embedding_is_deterministic_normalized_and_case_insensitive():
    vector = fake_embedding("Backups are retained")

    assert vector == fake_embedding("backups ARE retained")
    assert len(vector) == DIMENSIONS
    assert math.isclose(sum(v * v for v in vector), 1.0)


def test_texts_that_share_words_are_closer():
    query = fake_embedding("how long are backups retained")
    near = fake_embedding("backups are retained for 35 days")
    far = fake_embedding("multi factor authentication is required")

    assert math.dist(query, near) < math.dist(query, far)


def test_empty_text_gives_a_zero_vector():
    assert fake_embedding("") == [0.0] * DIMENSIONS


async def test_batch_embeddings_keep_their_input_order():
    client = FakeOpenAI()

    response = await client.embeddings.create(model="m", input=["alpha", "beta"])

    assert [item.index for item in response.data] == [0, 1]
    assert response.data[1].embedding == fake_embedding("beta")
    assert client.embedding_calls == [{"model": "m", "input": ["alpha", "beta"]}]


async def test_chat_replies_come_back_in_order_and_calls_are_recorded():
    client = FakeOpenAI([text_reply("first")])
    client.queue(text_reply("second"))
    messages = [{"role": "user", "content": "hi"}]

    first = await client.chat.completions.create(model="m", messages=messages)
    messages.append({"role": "assistant", "content": "later"})
    second = await client.chat.completions.create(model="m", messages=messages)

    assert first.choices[0].message.content == "first"
    assert second.choices[0].message.content == "second"
    assert client.chat_calls[0]["messages"] == [{"role": "user", "content": "hi"}]


async def test_running_out_of_replies_fails_loudly():
    client = FakeOpenAI()

    with pytest.raises(AssertionError, match="ran out of scripted chat replies"):
        await client.chat.completions.create(model="m", messages=[])
