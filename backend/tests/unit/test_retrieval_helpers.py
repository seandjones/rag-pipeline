from app.services.retrieval import _to_pgvector


def test_to_pgvector_formats_a_bracketed_comma_list():
    assert _to_pgvector([0.5, -1.0, 2]) == "[0.5,-1.0,2]"


def test_to_pgvector_empty_list():
    assert _to_pgvector([]) == "[]"
