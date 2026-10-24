"""Load the eval question sets and the synthetic policy corpus, and match facts in text."""

import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError

EVALS_DIR = Path(__file__).resolve().parent
CORPUS_DIR = EVALS_DIR / "corpus"
DATASETS_DIR = EVALS_DIR / "datasets"

Category = Literal["single_fact", "multi_doc", "version_conflict", "unanswerable"]


class EvalItem(BaseModel):
    """One question and its answer key."""

    model_config = ConfigDict(extra="forbid")

    id: str
    category: Category
    question: str
    expected_sources: list[str]
    reference_answer: str
    must_include: list[list[str]]
    must_not_include: list[str] = []
    should_refuse: bool
    absent_terms: list[str] = []
    notes: str = ""


def load_dataset(path: Path) -> list[EvalItem]:
    """Parse a JSONL question set, naming the line of any record that fails validation."""
    items: list[EvalItem] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            items.append(EvalItem.model_validate_json(line))
        except ValidationError as exc:
            raise ValueError(f"{path.name} line {line_no}: {exc}") from exc
    return items


def load_corpus(directory: Path = CORPUS_DIR) -> dict[str, str]:
    """Return {file name: text} for every Markdown document in the corpus."""
    return {p.name: p.read_text(encoding="utf-8") for p in sorted(directory.glob("*.md"))}


_WHITESPACE = re.compile(r"\s+")
# Model output often uses typographic dashes and quotes; fold them to ASCII before matching.
_TYPOGRAPHY = str.maketrans(
    {
        **{chr(code): "-" for code in range(0x2010, 0x2016)},
        "\u2212": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
    }
)


def normalize(text: str) -> str:
    """Fold typographic dashes and quotes, collapse whitespace, and lowercase.

    So line wrapping, "AES\u2011256", and "aren\u2019t" never hide a match.
    """
    return _WHITESPACE.sub(" ", text.translate(_TYPOGRAPHY)).strip().lower()


def _whole_phrase(phrase: str) -> re.Pattern[str]:
    """Match a phrase as whole words, allowing a plural "s" or "es" on its last word."""
    return re.compile(rf"(?<!\w){re.escape(phrase)}(?:s|es)?(?!\w)")


def fact_present(text: str, alternatives: list[str]) -> bool:
    """True when any accepted wording of a fact appears in the text as whole words.

    Whole-word matching keeps near misses honest: "4 hours" does not match "24 hours", and
    "ten" does not match "retention". Blank alternatives never match.
    """
    haystack = normalize(text)
    return any(
        alt.strip() and _whole_phrase(normalize(alt)).search(haystack) for alt in alternatives
    )


def mentions_term(text: str, term: str) -> bool:
    """True when the term appears as a whole word or phrase, ignoring case and line breaks.

    So "SLA" does not match "translate", and "99.9%" still matches despite its symbol.
    """
    return fact_present(text, [term])
