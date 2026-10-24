import pytest

from app.services.chunker import chunk_text, normalize_patterns, read_files


def test_chunk_text_empty_input_gives_no_chunks():
    assert chunk_text("", chunk_size=10, overlap=2) == []


def test_chunk_text_short_input_is_one_chunk():
    assert chunk_text("abc", chunk_size=10, overlap=2) == ["abc"]


def test_chunk_text_input_exactly_one_chunk_long():
    assert chunk_text("a" * 10, chunk_size=10, overlap=2) == ["a" * 10]


def test_chunk_text_overlaps_consecutive_chunks():
    assert chunk_text("abcdefghij", chunk_size=4, overlap=1) == ["abcd", "defg", "ghij"]


@pytest.mark.parametrize(("chunk_size", "overlap"), [(5, 5), (5, 6)])
def test_chunk_text_rejects_overlap_not_smaller_than_chunk(chunk_size, overlap):
    with pytest.raises(ValueError, match="chunk_size must be larger than overlap"):
        chunk_text("abcdefghij", chunk_size=chunk_size, overlap=overlap)


@pytest.mark.parametrize(
    ("patterns", "expected"),
    [
        (["md"], ["*.md"]),
        ([".txt"], ["*.txt"]),
        (["*.pdf"], ["*.pdf"]),
        (["notes/readme"], ["notes/readme"]),
        ([" md ", ""], ["*.md"]),
        (["", "   "], ["*.txt", "*.md"]),
        ([], ["*.txt", "*.md"]),
    ],
)
def test_normalize_patterns(patterns, expected):
    assert normalize_patterns(patterns) == expected


def test_read_files_matches_patterns_recursively_and_skips_empty_files(tmp_path):
    (tmp_path / "a.md").write_text("  alpha  ")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.txt").write_text("beta")
    (tmp_path / "c.py").write_text("print('not matched')")
    (tmp_path / "empty.md").write_text("   ")

    files = dict(read_files(str(tmp_path), ["md", "txt"]))

    assert files == {
        str(tmp_path / "a.md"): "alpha",
        str(tmp_path / "sub" / "b.txt"): "beta",
    }


def test_read_files_returns_each_file_once_when_patterns_overlap(tmp_path):
    (tmp_path / "a.md").write_text("alpha")

    files = read_files(str(tmp_path), ["md", "*.md"])

    assert files == [(str(tmp_path / "a.md"), "alpha")]
