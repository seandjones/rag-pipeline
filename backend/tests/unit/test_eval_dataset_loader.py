import json

import pytest

from evals.dataset import fact_present, load_corpus, load_dataset, mentions_term, normalize


def _record(**overrides) -> dict:
    record = {
        "id": "x-01",
        "category": "single_fact",
        "question": "How long are backups kept?",
        "expected_sources": ["a.md"],
        "reference_answer": "35 days.",
        "must_include": [["35 days"]],
        "should_refuse": False,
    }
    record.update(overrides)
    return record


def test_load_dataset_parses_records_skips_blank_lines_and_fills_defaults(tmp_path):
    path = tmp_path / "set.jsonl"
    path.write_text(json.dumps(_record()) + "\n\n" + json.dumps(_record(id="x-02")) + "\n")

    items = load_dataset(path)

    assert [item.id for item in items] == ["x-01", "x-02"]
    assert items[0].must_not_include == []
    assert items[0].absent_terms == []
    assert items[0].notes == ""


@pytest.mark.parametrize(
    "bad",
    [{"unexpected_field": 1}, {"category": "trivia"}, {"should_refuse": "maybe"}],
)
def test_load_dataset_names_the_line_of_a_bad_record(tmp_path, bad):
    path = tmp_path / "set.jsonl"
    path.write_text(json.dumps(_record()) + "\n" + json.dumps(_record(**bad)) + "\n")

    with pytest.raises(ValueError, match="set.jsonl line 2"):
        load_dataset(path)


def test_load_corpus_reads_markdown_files_by_name(tmp_path):
    (tmp_path / "b.md").write_text("bee")
    (tmp_path / "a.md").write_text("ay")
    (tmp_path / "notes.txt").write_text("not a policy")

    assert load_corpus(tmp_path) == {"a.md": "ay", "b.md": "bee"}


def test_normalize_lowercases_and_collapses_whitespace():
    assert normalize("  Retained for\n  35   DAYS ") == "retained for 35 days"


def test_normalize_folds_typographic_dashes_and_quotes():
    text = "AES\u2011256 \u2013 aren\u2019t \u201cquoted\u201d"

    assert normalize(text) == "aes-256 - aren't \"quoted\""


@pytest.mark.parametrize(
    ("text", "alternatives", "expected"),
    [
        ("Backups are retained for 35\ndays.", ["35 days"], True),
        ("Backups are retained for 35 days.", ["thirty-five days", "35 days"], True),
        ("Logs are retained for one year.", ["35 days"], False),
        ("Access is revoked within 24 hours.", ["4 hours"], False),
        ("Retention rules apply.", ["ten"], False),
        ("Admins use hardware security keys.", ["hardware security key"], True),
        ("Anything at all.", ["", "  "], False),
        ("Data at rest uses AES\u2011256.", ["AES-256"], True),
        ("Vendors aren\u2019t allowed to share accounts.", ["aren't allowed"], True),
    ],
)
def test_fact_present_matches_any_alternative(text, alternatives, expected):
    assert fact_present(text, alternatives) is expected


@pytest.mark.parametrize(
    ("text", "term", "expected"),
    [
        ("Our SLA covers support hours.", "SLA", True),
        ("Our SLAs cover support hours.", "SLA", True),
        ("We translate documents.", "SLA", False),
        ("No penetration\ntest is described.", "penetration test", True),
        ("Bug bounties are not offered.", "bug bounty", False),
        ("Uptime of 99.9% is promised.", "99.9%", True),
    ],
)
def test_mentions_term_matches_whole_words_only(text, term, expected):
    assert mentions_term(text, term) is expected
