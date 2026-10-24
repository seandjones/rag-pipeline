# Eval Dataset Implementation Plan (Plan 2 of 3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the fixed evaluation data for the RAG pipeline: nine synthetic security policies for a fictional company, a 40-question answer key, and free integrity tests that keep both honest.

**Architecture:**
- A small `backend/evals/dataset.py` module loads the question set (validated with pydantic) and the corpus, and provides the text-matching helpers the integrity tests use. Plan 3's scorers reuse those helpers.
- The corpus contract lives in `tests/unit/test_eval_corpus.py`: each document's header, the sentences that carry its facts word for word, its length, and a rule that no number appears unless the fact sheet put it there.
- The answer-key checks live in `tests/unit/test_eval_dataset.py`.

**Tech Stack:** Python 3.11/3.12, pydantic 2 (already a dependency), pytest; Markdown documents; JSONL.

**Spec:** `docs/superpowers/specs/2026-09-23-tests-and-eval-harness-design.md` (Part 2). Plan 1 (tests and CI) is merged into this branch. Plan 3 builds the eval harness (Part 3).

## Global Constraints

- Work on branch `feature/tests-and-evals`.
- **No commits without review.** Implementers never run `git add`, `git rm`, `git commit`, `git stash`, `git checkout`, `git reset`, `git restore`, or `git push`. Each task ends by listing its files for the repo owner, who reviews and commits them himself.
- Do not change application code under `backend/app/` or `frontend/`.
- Fictional company **Quillmark Systems** only. No real company, person, product, or vendor names anywhere in the corpus.
- Every corpus document's first line is exactly: `Fictional company. Synthetic document created for RAG evaluation.`
- Corpus text is plain ASCII: no em-dashes, en-dashes, or curly quotes. Prose in the README has no em-dashes.
- New Python code stays within 100 columns and passes `ruff check .` (rule sets E, F, I).
- The backend venv is Python 3.11 locally; CI uses 3.12. Nothing here may need 3.12-only features.
- The question set has exactly 18 `single_fact`, 8 `multi_doc`, 5 `version_conflict`, and 9 `unanswerable` items (spec Part 2).

## Local environment notes

- Backend commands run from `backend/` with `source .venv/bin/activate`. The tests in this plan need no database. The full suite's integration tests need `export TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5433/ragdemo_test`, with this repo's Postgres running on port 5433 (`POSTGRES_PORT=5433 docker compose up -d postgres` from the repo root).

## File Structure

```
backend/
  evals/
    __init__.py                        NEW  (empty) makes `evals` importable
    dataset.py                         NEW  EvalItem model, load_dataset, load_corpus,
                                            normalize, fact_present, mentions_term
    README.md                          NEW  what the data is and how it is checked
    corpus/                            NEW  nine Markdown policies (Task 3)
    datasets/policies_v1.jsonl         NEW  40-question answer key (Task 4)
  tests/
    integration/test_api.py            EDIT fake_openai fixture restores app.state (Task 1)
    unit/test_eval_dataset_loader.py   NEW  tests for evals/dataset.py
    unit/test_eval_corpus.py           NEW  the corpus contract (fact sheet)
    unit/test_eval_dataset.py          NEW  answer-key integrity checks
    unit/test_answer_key_cases.py      NEW  pinned correct and wrong answers
```

---

### Task 1: Restore app.state after the API tests

This carries over a ruling from Plan 1's final review. The `fake_openai` fixture sets `app.state.openai_client` and never puts it back, so a later test that touches `app` could silently inherit the fake. Plan 3 reuses these fixtures, so it gets fixed first.

**Files:**
- Modify: `backend/tests/integration/test_api.py:1-18`

**Interfaces:**
- Consumes: `tests.fakes.FakeOpenAI`; `app.main.app` (a FastAPI app whose `state` is a Starlette `State`, which supports `del`).
- Produces: the `fake_openai` fixture, now a generator fixture that yields the `FakeOpenAI` and restores `app.state` afterwards. The fixture name is unchanged, so the `api` fixture and all tests keep working.

- [ ] **Step 1: Add the import**

In `backend/tests/integration/test_api.py`, change the first import lines from:

```python
import asyncio

import httpx
```

to:

```python
import asyncio
from collections.abc import Iterator

import httpx
```

- [ ] **Step 2: Make the fixture restore app.state**

Replace:

```python
@pytest.fixture
def fake_openai() -> FakeOpenAI:
    client = FakeOpenAI()
    # The routers read the client from app.state, which the lifespan normally fills in.
    app.state.openai_client = client
    return client
```

with:

```python
@pytest.fixture
def fake_openai() -> Iterator[FakeOpenAI]:
    client = FakeOpenAI()
    # The routers read the client from app.state, which the lifespan normally fills in.
    # Put back whatever was there afterwards, so no later test inherits this fake.
    had_client = hasattr(app.state, "openai_client")
    previous = getattr(app.state, "openai_client", None)
    app.state.openai_client = client
    yield client
    if had_client:
        app.state.openai_client = previous
    else:
        del app.state.openai_client
```

- [ ] **Step 3: Run the suite and lint**

Run (from `backend/`, with `TEST_DATABASE_URL` set as in the environment notes): `pytest -q && ruff check .`
Expected: `47 passed`, then `All checks passed!`

- [ ] **Step 4: Confirm the restore actually happens**

Run (from `backend/`):

```bash
python - <<'EOF'
import os, sys
os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]
os.environ["OPENAI_API_KEY"] = "x"
sys.path.insert(0, ".")
import pytest
code = pytest.main(["-q", "-p", "no:cacheprovider", "tests/integration/test_api.py"])
from app.main import app
print("exit", code, "| openai_client left on app.state:", hasattr(app.state, "openai_client"))
EOF
```

Expected: `6 passed`, then `exit 0 | openai_client left on app.state: False`.

- [ ] **Step 5: Stop for owner review**

Files for the owner: `backend/tests/integration/test_api.py`. Suggested message: `test: restore app.state after API tests`.

---

### Task 2: The eval dataset module

**Files:**
- Create: `backend/evals/__init__.py` (empty), `backend/evals/dataset.py`
- Test: `backend/tests/unit/test_eval_dataset_loader.py`

**Interfaces:**
- Consumes: pydantic 2 (`BaseModel`, `ConfigDict`, `ValidationError`).
- Produces (used by Tasks 3 and 4, and by Plan 3):
  - `evals.dataset.EVALS_DIR`, `CORPUS_DIR`, `DATASETS_DIR: Path`
  - `Category = Literal["single_fact", "multi_doc", "version_conflict", "unanswerable"]`
  - `EvalItem` (pydantic, `extra="forbid"`) with fields `id: str`, `category: Category`, `question: str`, `expected_sources: list[str]`, `reference_answer: str`, `must_include: list[list[str]]`, `must_not_include: list[str] = []`, `should_refuse: bool`, `absent_terms: list[str] = []`, `notes: str = ""`
  - `load_dataset(path: Path) -> list[EvalItem]`, which raises `ValueError("<file> line <n>: ...")` on a bad record
  - `load_corpus(directory: Path = CORPUS_DIR) -> dict[str, str]`, mapping file name to text for `*.md`, sorted
  - `normalize(text: str) -> str`, which lowercases and collapses whitespace
  - `fact_present(text: str, alternatives: list[str]) -> bool`, a whole-word match after normalizing, allowing a plural "s" or "es" on the last word; blank alternatives never match (so "4 hours" does not match "24 hours")
  - `mentions_term(text: str, term: str) -> bool`, the same whole-word match for a single term

- [ ] **Step 1: Write the failing tests**

`backend/tests/unit/test_eval_dataset_loader.py`:

```python
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
```

- [ ] **Step 2: Run them to verify they fail**

Run (from `backend/`): `pytest tests/unit/test_eval_dataset_loader.py -q`
Expected: collection error, `ModuleNotFoundError: No module named 'evals'`.

- [ ] **Step 3: Write the module**

Create an empty `backend/evals/__init__.py`.

`backend/evals/dataset.py`:

```python
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
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/unit/test_eval_dataset_loader.py -q && ruff check .`
Expected: `22 passed`, then `All checks passed!`

- [ ] **Step 5: Stop for owner review**

Files for the owner: `backend/evals/__init__.py`, `backend/evals/dataset.py`, `backend/tests/unit/test_eval_dataset_loader.py`. Suggested message: `feat(evals): add eval dataset loader and text matching helpers`.

---

### Task 3: The Quillmark policy corpus

The corpus contract (the fact sheet) is written first as a test. The nine documents are then written to satisfy it. The fact sheet is the ground truth every later score is measured against, so the sentences in it are fixed: copy them exactly. Everything else in each document is supporting prose that you write.

**Files:**
- Test: `backend/tests/unit/test_eval_corpus.py`
- Create: the nine files in `backend/evals/corpus/` named in the test's `DOCUMENTS`

**Interfaces:**
- Consumes (Task 2): `evals.dataset.CORPUS_DIR`, `load_corpus`, `normalize`.
- Produces (used by Task 4 and Plan 3): `backend/evals/corpus/*.md`, the nine documents. Task 4's answer key relies on the exact required sentences below, on the superseded policy's conflicting values, and on the prose rules (especially the banned terms).

- [ ] **Step 1: Write the corpus contract test**

`backend/tests/unit/test_eval_corpus.py`:

```python
"""The synthetic policy corpus must match its fact sheet exactly.

Every eval score is measured against these documents, so this file is the contract: each
document's header, the sentences that carry its facts (verbatim), its length, and a rule that
no number appears unless the fact sheet put it there.
"""

import re

import pytest

from evals.dataset import CORPUS_DIR, load_corpus, normalize

SYNTHETIC_LABEL = "Fictional company. Synthetic document created for RAG evaluation."
_NUMBER = re.compile(r"\d+(?:\.\d+)?")

DOCUMENTS = {
    "information-security-policy.md": {
        "title": "Information Security Policy",
        "version": "3.1",
        "effective": "January 15, 2026",
        "owner": "Chief Information Security Officer",
        "words": (500, 1200),
        "required": [
            "This policy is owned by the Chief Information Security Officer (CISO).",
            "All security policies are reviewed at least annually and approved by the Security"
            " Steering Committee.",
            "The Security Steering Committee meets quarterly and includes the CISO, the Chief"
            " Technology Officer, the VP of People, and the General Counsel.",
            "New employees and contractors must complete security awareness training within 30"
            " days of their start date and every year after that.",
            "Phishing simulation exercises are sent to all staff monthly.",
            "Exceptions to any security policy must be requested through the security exceptions"
            " process, approved by the CISO, and last no longer than 90 days, with at most one"
            " renewal.",
            "Quillmark classifies information into four levels: Public, Internal, Confidential,"
            " and Restricted.",
            "Customer data is always classified as Restricted.",
            "Violations of this policy may result in disciplinary action, up to and including"
            " termination of employment or contract.",
        ],
    },
    "access-control-policy.md": {
        "title": "Access Control Policy",
        "version": "2.0",
        "effective": "March 1, 2026",
        "owner": "Chief Information Security Officer",
        "words": (500, 1200),
        "required": [
            "This version supersedes Access Control Policy v1.0.",
            "Multi-factor authentication (MFA) is required for all workforce accounts, including"
            " employees and contractors.",
            "Administrators of production systems must use phishing-resistant MFA in the form of"
            " hardware security keys.",
            "User access reviews are performed quarterly by each system owner.",
            "Privileged access is reviewed monthly.",
            "When a person leaves Quillmark, all of their access is revoked within 4 hours of the"
            " termination time recorded in the HR system.",
            "Passwords must be at least 14 characters long.",
            "Passwords are not rotated on a fixed schedule; a password must be changed when"
            " compromise is suspected.",
            "Accounts are locked for 15 minutes after 10 consecutive failed login attempts.",
            "Production administration consoles end a session after 15 minutes of inactivity.",
            "Access requests must be approved by the requester's manager and by the system owner.",
            "Shared accounts are prohibited for employees, contractors, and vendors, except for"
            " break-glass accounts.",
            "Break-glass account credentials are stored in the password vault, and every use is"
            " logged and reviewed within 1 business day.",
        ],
    },
    "access-control-policy-v1-superseded.md": {
        "title": "Access Control Policy",
        "version": "1.0",
        "effective": "June 1, 2023",
        "owner": "IT Department",
        "words": (400, 700),
        "required": [
            "Status: SUPERSEDED by Access Control Policy v2.0, effective March 1, 2026. Retained"
            " for audit history only.",
            "Multi-factor authentication (MFA) is required for remote access only.",
            "User access reviews are performed semi-annually, every six months, by the IT"
            " department.",
            "When a person leaves Quillmark, all of their access is revoked within 72 hours of"
            " their last working day.",
            "Passwords must be at least 10 characters long and must be changed every 90 days.",
        ],
    },
    "incident-response-plan.md": {
        "title": "Incident Response Plan",
        "version": "2.2",
        "effective": "February 1, 2026",
        "owner": "Chief Information Security Officer",
        "words": (500, 1200),
        "required": [
            "Incidents are classified into four severity levels: SEV-1 (critical), SEV-2 (high),"
            " SEV-3 (moderate), and SEV-4 (low).",
            "A SEV-1 is a confirmed breach of Restricted data or a full outage of the production"
            " platform.",
            "For a SEV-1, an incident commander must be assigned within 15 minutes of detection;"
            " for a SEV-2, within 1 hour.",
            "The on-call security engineer serves as incident commander and escalates every SEV-1"
            " to the CISO immediately.",
            "When a breach of customer data is confirmed, Quillmark notifies affected customers"
            " within 72 hours of confirmation.",
            "A blameless postmortem is required for every SEV-1 and SEV-2 incident and must be"
            " completed within 5 business days of resolution.",
            "Tabletop exercises are held twice a year.",
            "Incident records are retained for 3 years.",
        ],
    },
    "vendor-management-policy.md": {
        "title": "Vendor Management Policy",
        "version": "1.4",
        "effective": "March 1, 2026",
        "owner": "Head of Procurement",
        "words": (500, 1200),
        "required": [
            "Vendors are assigned one of three risk tiers.",
            "Tier 1 vendors have access to Restricted data or are critical to delivering the"
            " Quillmark platform.",
            "Tier 2 vendors have access to Confidential data.",
            "Tier 3 vendors have no access to non-public Quillmark data.",
            "Tier 1 vendors must provide a SOC 2 Type II report or an ISO 27001 certificate before"
            " a contract is signed and every year after that.",
            "Vendor risk is reassessed annually for Tier 1, every two years for Tier 2, and at"
            " contract renewal for Tier 3.",
            "Vendors must notify Quillmark of any security incident affecting Quillmark data within"
            " 24 hours of discovering it.",
            "When a vendor contract ends, the vendor must return or destroy Quillmark data and"
            " certify the destruction within 60 days.",
            "Vendor user accounts in Quillmark systems are included in the quarterly user access"
            " review.",
            "The vendor inventory is owned by Procurement and reviewed quarterly by the Security"
            " team.",
        ],
    },
    "data-retention-and-deletion-policy.md": {
        "title": "Data Retention and Deletion Policy",
        "version": "2.0",
        "effective": "January 15, 2026",
        "owner": "General Counsel",
        "words": (500, 1200),
        "required": [
            "Customer data is deleted within 30 days after a customer contract terminates, unless"
            " a legal hold applies.",
            "Backups are retained for 35 days and then permanently deleted.",
            "Application and audit logs are retained for one year.",
            "Employee records are retained for 7 years after an employee leaves.",
            "Each deletion is recorded in the deletion register, and customers may request a"
            " certificate of deletion.",
            "Only the General Counsel can place or release a legal hold, and a legal hold suspends"
            " scheduled deletion.",
        ],
    },
    "encryption-and-key-management-standard.md": {
        "title": "Encryption and Key Management Standard",
        "version": "1.3",
        "effective": "January 15, 2026",
        "owner": "Platform Security team",
        "words": (500, 1200),
        "required": [
            "Data at rest, including databases, object storage, and backups, is encrypted with"
            " AES-256.",
            "Data in transit must use TLS 1.2 or higher, and TLS 1.3 is preferred.",
            "TLS 1.0 and TLS 1.1 are disabled on all Quillmark endpoints.",
            "Encryption keys are managed in a cloud key management service, and customer data"
            " encryption keys are rotated annually or immediately when compromise is suspected.",
            "Company laptops must use full-disk encryption, enforced through mobile device"
            " management.",
            "Secrets such as API keys and passwords must be stored in the secrets manager and never"
            " committed to source code.",
            "Secret scanning runs on every commit.",
            "The Platform Security team owns key management.",
        ],
    },
    "business-continuity-and-disaster-recovery-plan.md": {
        "title": "Business Continuity and Disaster Recovery Plan",
        "version": "1.2",
        "effective": "January 15, 2026",
        "owner": "VP of Engineering",
        "words": (500, 1200),
        "required": [
            "The production platform has a recovery time objective (RTO) of 4 hours and a recovery"
            " point objective (RPO) of 1 hour.",
            "Production runs in a primary region and a secondary region, and the secondary region"
            " can take over all production traffic.",
            "A full disaster recovery failover test is performed annually.",
            "Backup restore tests are performed quarterly.",
            "This plan is owned by the VP of Engineering.",
            "The plan is reviewed annually and after every SEV-1 incident.",
        ],
    },
    "change-management-policy.md": {
        "title": "Change Management Policy",
        "version": "2.1",
        "effective": "January 15, 2026",
        "owner": "VP of Engineering",
        "words": (500, 1200),
        "required": [
            "Every production code change requires review and approval by at least one engineer"
            " other than the author.",
            "Changes reach production only through the CI/CD pipeline; direct changes to"
            " production are prohibited except during an emergency.",
            "Emergency changes must be approved by the on-call engineering lead and reviewed"
            " within 2 business days after deployment.",
            "Infrastructure changes are made through infrastructure as code and follow the same"
            " review rules as application code.",
            "High-risk changes must include a documented rollback plan.",
            "A production change freeze is in effect from December 20 through January 3 each"
            " year.",
        ],
    },
}

NAMES = sorted(DOCUMENTS)


@pytest.fixture(scope="module")
def corpus() -> dict[str, str]:
    return load_corpus(CORPUS_DIR)


def test_corpus_contains_exactly_the_planned_documents(corpus):
    assert sorted(corpus) == NAMES


@pytest.mark.parametrize("name", NAMES)
def test_document_starts_with_the_label_and_header(corpus, name):
    spec = DOCUMENTS[name]
    lines = corpus[name].splitlines()

    assert lines[0] == SYNTHETIC_LABEL
    for expected in (
        f"# {spec['title']}",
        f"Version: {spec['version']}",
        f"Effective date: {spec['effective']}",
        f"Owner: {spec['owner']}",
    ):
        assert expected in lines, f"{name}: missing header line {expected!r}"


@pytest.mark.parametrize("name", NAMES)
def test_required_sentences_appear_verbatim(corpus, name):
    text = normalize(corpus[name])

    missing = [s for s in DOCUMENTS[name]["required"] if normalize(s) not in text]

    assert missing == []


@pytest.mark.parametrize("name", NAMES)
def test_length_is_in_range(corpus, name):
    low, high = DOCUMENTS[name]["words"]
    count = len(corpus[name].split())

    assert low <= count <= high, f"{name}: {count} words, expected {low} to {high}"


@pytest.mark.parametrize("name", NAMES)
def test_no_number_appears_unless_the_fact_sheet_put_it_there(corpus, name):
    spec = DOCUMENTS[name]
    fact_sheet = " ".join([*spec["required"], spec["version"], spec["effective"]])
    allowed = set(_NUMBER.findall(fact_sheet))

    extra = sorted(set(_NUMBER.findall(corpus[name])) - allowed)

    assert extra == [], f"{name}: numbers not in the fact sheet: {extra}"


@pytest.mark.parametrize("name", NAMES)
def test_text_is_plain_ascii(corpus, name):
    # No em-dashes, en-dashes, or curly quotes: they break exact matching and the house style.
    assert sorted({ch for ch in corpus[name] if not ch.isascii()}) == []
```

- [ ] **Step 2: Run it to verify it fails**

Run (from `backend/`): `pytest tests/unit/test_eval_corpus.py -q`
Expected: failures, because `backend/evals/corpus/` does not exist yet. `test_corpus_contains_exactly_the_planned_documents` fails with `[] == [...]`, and the parametrized tests error with `KeyError`.

- [ ] **Step 3: Write the nine documents**

Create `backend/evals/corpus/` and write one Markdown file per entry in `DOCUMENTS`, using these rules.

**Layout of every document:**

```
Fictional company. Synthetic document created for RAG evaluation.

# <title>

Version: <version>
Effective date: <effective>
Owner: <owner>

## Purpose
## Scope
## Roles and responsibilities
## Policy            (use ### subsections that suit the document)
## Enforcement and review
```

- The first line, the `# title` line, and the three metadata lines must match the test's values exactly, each on its own line.
- In `access-control-policy-v1-superseded.md`, put its status sentence ("Status: SUPERSEDED by ...") on its own line directly under the metadata lines. In `access-control-policy.md`, put "This version supersedes Access Control Policy v1.0." directly under the metadata lines.
- Use `##` and `###` headings and `-` bullets only. No numbered headings or numbered lists.

**Required sentences:**

- Every string in the document's `required` list must appear word for word, as plain text, inside the document's prose. Line breaks inside a sentence are fine.
- Do not add bold, italics, links, or backticks inside a required sentence.
- Place each sentence where it belongs logically. For example, the training sentence goes in a training subsection.

**Supporting prose:** write it around the required sentences, covering purpose, scope, who does what, how the process works, and how the document is reviewed. Realistic, plain, and specific in wording, but these rules are strict:

- **Introduce no new quantities.** No digits, durations, frequencies, dates, percentages, or counts that are not already in that document's required sentences or metadata. This applies to spelled-out numbers too ("three", "weekly"). The test enforces digits; the reviewer checks words.
- **Do not contradict or restate a fact with a different value.** You may refer back to a required fact in words ("the review described above").
- **No names** of real companies, people, products, cloud providers, or vendors. Refer to people by role only (for example "the CISO", "system owners", "the on-call security engineer").
- **Never mention these terms**, in any document and in any form (singular or plural). Questions in Task 4 depend on their absence:
  - bug bounty
  - headcount, or the number of employees
  - AWS, Amazon, Azure, Google Cloud, GCP
  - insurance
  - penetration test, pen test, pentest
  - support ticket
  - personal device, BYOD, bring your own
  - Data Protection Officer, DPO
  - uptime, service level agreement, SLA
  - budget
  - background check, criminal record, reference check
- **In `access-control-policy.md` (the current policy) only, never use these phrases**, which belong to the superseded version: "semi-annual", "semiannual", "every six months", "twice a year", "72 hours", "three days", "10 characters", "ten characters", "90 days", "every 90", "ninety days", "remote access only", "only for remote access", "only required for remote".
- **In the superseded policy,** keep the prose brief and historical. It must not mention anything the current version added: hardware security keys, privileged access reviews, lockouts, break-glass accounts.
- **Length:** stay within the `words` range in the test (500 to 1,200 words; the superseded policy 400 to 700).
- **Characters:** plain ASCII only. Use straight quotes, plain hyphens, and no em-dashes or en-dashes.

- [ ] **Step 4: Run the contract test**

Run: `pytest tests/unit/test_eval_corpus.py -q`
Expected: `46 passed`. If a test fails, fix the document, never the test.

- [ ] **Step 5: Self-check the prose rules the test cannot see**

Run (from `backend/`):

```bash
grep -inE "bug bount|headcount|number of employees|\bAWS\b|amazon|azure|google cloud|\bGCP\b|insurance|penetration|pen ?test|support ticket|personal device|\bBYOD\b|bring your own|data protection officer|\bDPO\b|uptime|service level|\bSLA|budget|background check|criminal record|reference check" evals/corpus/*.md || echo "no banned terms"
grep -inE "semi-?annual|every six months|twice a year|72 hours|three days|10 characters|ten characters|90 days|every 90|ninety days|remote access only|only for remote|only required for remote" evals/corpus/access-control-policy.md || echo "current policy is clean"
```

Expected: `no banned terms` and `current policy is clean`. Then reread each document once for spelled-out quantities that are not in its fact sheet, and remove any you find.

- [ ] **Step 6: Lint**

Run: `ruff check .`
Expected: `All checks passed!`

- [ ] **Step 7: Stop for owner review**

Files for the owner: `backend/tests/unit/test_eval_corpus.py` and `backend/evals/corpus/*.md` (nine files). Suggested message: `feat(evals): add synthetic Quillmark policy corpus and its fact sheet`.

---

### Task 4: The policies_v1 answer key

**Files:**
- Test: `backend/tests/unit/test_eval_dataset.py`, `backend/tests/unit/test_answer_key_cases.py`
- Create: `backend/evals/datasets/policies_v1.jsonl`, `backend/evals/README.md`

**Interfaces:**
- Consumes (Task 2): `DATASETS_DIR`, `load_dataset`, `load_corpus`, `fact_present`, `mentions_term`. Consumes (Task 3): the nine corpus documents.
- Produces (used by Plan 3): `backend/evals/datasets/policies_v1.jsonl`, 40 `EvalItem` records. For unanswerable items, `reference_answer` is exactly `I cannot find this information in the document.`

- [ ] **Step 1: Write the integrity tests**

`backend/tests/unit/test_eval_dataset.py`:

```python
"""Integrity checks for the policies_v1 answer key.

These run in CI for free. A typo in the answer key fails the build instead of quietly
skewing every eval score.
"""

from collections import Counter

import pytest

from evals.dataset import DATASETS_DIR, fact_present, load_corpus, load_dataset, mentions_term

DATASET = DATASETS_DIR / "policies_v1.jsonl"
CURRENT_ACCESS_POLICY = "access-control-policy.md"
SUPERSEDED_ACCESS_POLICY = "access-control-policy-v1-superseded.md"
REFUSAL = "I cannot find this information in the document."


@pytest.fixture(scope="module")
def items():
    return load_dataset(DATASET)


@pytest.fixture(scope="module")
def corpus():
    return load_corpus()


def _answerable(items):
    return [item for item in items if item.category != "unanswerable"]


def test_ids_are_unique(items):
    counts = Counter(item.id for item in items)

    assert [item_id for item_id, n in counts.items() if n > 1] == []


def test_category_counts_match_the_spec(items):
    assert Counter(item.category for item in items) == {
        "single_fact": 18,
        "multi_doc": 8,
        "version_conflict": 5,
        "unanswerable": 9,
    }


def test_expected_sources_exist_in_the_corpus(items, corpus):
    missing = [(item.id, s) for item in items for s in item.expected_sources if s not in corpus]

    assert missing == []


def test_the_superseded_policy_is_never_an_expected_source(items):
    assert [i.id for i in items if SUPERSEDED_ACCESS_POLICY in i.expected_sources] == []


def test_answerable_items_have_sources_and_facts_and_expect_an_answer(items):
    bad = [
        item.id
        for item in _answerable(items)
        if item.should_refuse or not item.expected_sources or not item.must_include
        or item.absent_terms
    ]

    assert bad == []


def test_every_required_fact_appears_in_its_expected_sources(items, corpus):
    missing = []
    for item in _answerable(items):
        text = "\n".join(corpus[source] for source in item.expected_sources)
        missing += [(item.id, fact) for fact in item.must_include if not fact_present(text, fact)]

    assert missing == []


def test_multi_doc_items_need_every_listed_document(items, corpus):
    problems = []
    for item in items:
        if item.category != "multi_doc":
            continue
        if len(item.expected_sources) < 2:
            problems.append((item.id, "fewer than two sources"))
            continue
        for source in item.expected_sources:
            if not any(fact_present(corpus[source], fact) for fact in item.must_include):
                problems.append((item.id, f"{source} supplies none of the required facts"))

    assert problems == []


def test_version_conflict_items_trap_the_superseded_policy(items, corpus):
    problems = []
    for item in items:
        if item.category != "version_conflict":
            continue
        if item.expected_sources != [CURRENT_ACCESS_POLICY] or not item.must_not_include:
            problems.append((item.id, "cite only the current policy; list forbidden values"))
            continue
        if not fact_present(corpus[SUPERSEDED_ACCESS_POLICY], item.must_not_include):
            problems.append((item.id, "no forbidden value appears in the superseded policy"))
        if fact_present(corpus[CURRENT_ACCESS_POLICY], item.must_not_include):
            problems.append((item.id, "a forbidden value appears in the current policy"))

    assert problems == []


def test_version_conflict_answers_never_match_the_superseded_policy(items, corpus):
    # Otherwise an answer copied from the superseded policy could satisfy a required fact.
    leaks = [
        (item.id, fact)
        for item in items
        if item.category == "version_conflict"
        for fact in item.must_include
        if fact_present(corpus[SUPERSEDED_ACCESS_POLICY], fact)
    ]

    assert leaks == []


def test_unanswerable_items_expect_a_refusal_and_name_absent_terms(items):
    bad = [
        item.id
        for item in items
        if item.category == "unanswerable"
        and (not item.should_refuse or item.expected_sources or item.must_include
             or not item.absent_terms or item.reference_answer != REFUSAL)
    ]

    assert bad == []


def test_absent_terms_never_appear_anywhere_in_the_corpus(items, corpus):
    found = [
        (item.id, term, name)
        for item in items
        for term in item.absent_terms
        for name, text in corpus.items()
        if mentions_term(text, term)
    ]

    assert found == []


def test_reference_answers_pass_their_own_checks(items):
    # A correct answer must never fail its own answer key, so the reference answer is the
    # first thing every check is tried against.
    problems = []
    for item in _answerable(items):
        problems += [
            (item.id, "missing", fact)
            for fact in item.must_include
            if not fact_present(item.reference_answer, fact)
        ]
        if fact_present(item.reference_answer, item.must_not_include):
            problems.append((item.id, "forbidden", item.must_not_include))

    assert problems == []
```

- [ ] **Step 2: Run them to verify they fail**

Run (from `backend/`): `pytest tests/unit/test_eval_dataset.py -q`
Expected: errors with `FileNotFoundError` for `evals/datasets/policies_v1.jsonl`.

- [ ] **Step 3: Write the answer key**

Create `backend/evals/datasets/policies_v1.jsonl` with exactly these 40 lines. Copy them programmatically from this plan rather than retyping them, and end the file with a newline:

```jsonl
{"id": "sf-01", "category": "single_fact", "question": "Who owns Quillmark's information security policy?", "expected_sources": ["information-security-policy.md"], "reference_answer": "The Chief Information Security Officer (CISO).", "must_include": [["Chief Information Security Officer", "CISO"]], "must_not_include": [], "should_refuse": false, "notes": "Policy ownership."}
{"id": "sf-02", "category": "single_fact", "question": "How soon after starting must new employees complete security awareness training?", "expected_sources": ["information-security-policy.md"], "reference_answer": "Within 30 days of their start date.", "must_include": [["30 days", "thirty days", "30-day"]], "must_not_include": [], "should_refuse": false, "notes": "Training deadline. Training then repeats every year."}
{"id": "sf-03", "category": "single_fact", "question": "How long can a single security policy exception last?", "expected_sources": ["information-security-policy.md"], "reference_answer": "No longer than 90 days.", "must_include": [["90 days", "ninety days", "90-day"]], "must_not_include": [], "should_refuse": false, "notes": "Exception limit, asked per exception so the renewal does not make it ambiguous. The CISO approves exceptions, and each can be renewed at most once."}
{"id": "sf-04", "category": "single_fact", "question": "What are Quillmark's data classification levels?", "expected_sources": ["information-security-policy.md"], "reference_answer": "Four levels: Public, Internal, Confidential, and Restricted.", "must_include": [["Public"], ["Internal"], ["Confidential"], ["Restricted"]], "must_not_include": [], "should_refuse": false, "notes": "All four levels must be named."}
{"id": "sf-05", "category": "single_fact", "question": "What kind of MFA must administrators of production systems use?", "expected_sources": ["access-control-policy.md"], "reference_answer": "Phishing-resistant MFA in the form of hardware security keys.", "must_include": [["hardware security key", "security key", "hardware key"]], "must_not_include": [], "should_refuse": false, "notes": "Admin MFA type."}
{"id": "sf-06", "category": "single_fact", "question": "How many failed login attempts lock an account?", "expected_sources": ["access-control-policy.md"], "reference_answer": "10 consecutive failed login attempts.", "must_include": [["10", "ten"]], "must_not_include": ["15 failed", "15 attempts", "15 consecutive", "fifteen failed", "fifteen attempts", "fifteen consecutive"], "should_refuse": false, "notes": "Near-miss: the account then stays locked for 15 minutes; 15 is the lock duration, not the threshold."}
{"id": "sf-07", "category": "single_fact", "question": "How often is privileged access reviewed?", "expected_sources": ["access-control-policy.md"], "reference_answer": "Monthly.", "must_include": [["monthly", "every month", "once a month"]], "must_not_include": [], "should_refuse": false, "notes": "Near-miss: user access reviews are quarterly."}
{"id": "sf-08", "category": "single_fact", "question": "How quickly must an incident commander be assigned for a SEV-1 incident?", "expected_sources": ["incident-response-plan.md"], "reference_answer": "Within 15 minutes of detection.", "must_include": [["15 minutes", "fifteen minutes", "15-minute"]], "must_not_include": [], "should_refuse": false, "notes": "Near-miss: SEV-2 is within 1 hour."}
{"id": "sf-09", "category": "single_fact", "question": "How long does the team have to finish a postmortem after a SEV-2 incident?", "expected_sources": ["incident-response-plan.md"], "reference_answer": "Within 5 business days of resolution.", "must_include": [["5 business days", "five business days"]], "must_not_include": [], "should_refuse": false, "notes": "Postmortem deadline. Postmortems are blameless."}
{"id": "sf-10", "category": "single_fact", "question": "How often are incident response tabletop exercises held?", "expected_sources": ["incident-response-plan.md"], "reference_answer": "Twice a year.", "must_include": [["twice a year", "two times a year", "every six months", "semi-annual", "semi-annually", "semiannual", "semiannually"]], "must_not_include": [], "should_refuse": false, "notes": "Tabletop cadence."}
{"id": "sf-11", "category": "single_fact", "question": "What assurance report must a Tier 1 vendor provide?", "expected_sources": ["vendor-management-policy.md"], "reference_answer": "A SOC 2 Type II report or an ISO 27001 certificate.", "must_include": [["SOC 2 Type II", "SOC 2 Type 2", "SOC2 Type II", "ISO 27001", "ISO/IEC 27001"]], "must_not_include": [], "should_refuse": false, "notes": "Tier 1 assurance, required before signing and every year after that."}
{"id": "sf-12", "category": "single_fact", "question": "How often are Tier 2 vendors reassessed?", "expected_sources": ["vendor-management-policy.md"], "reference_answer": "Every two years.", "must_include": [["every two years", "every 2 years", "every 24 months", "biennial", "biennially"]], "must_not_include": [], "should_refuse": false, "notes": "Near-miss: Tier 1 is annual, Tier 3 at renewal."}
{"id": "sf-13", "category": "single_fact", "question": "How long are backups kept?", "expected_sources": ["data-retention-and-deletion-policy.md"], "reference_answer": "35 days.", "must_include": [["35 days", "thirty-five days", "thirty five days", "35-day"]], "must_not_include": [], "should_refuse": false, "notes": "Backups are then permanently deleted. Near-miss: logs are kept one year."}
{"id": "sf-14", "category": "single_fact", "question": "How long are audit logs retained?", "expected_sources": ["data-retention-and-deletion-policy.md"], "reference_answer": "One year.", "must_include": [["one year", "1 year", "a year", "12 months", "365 days"]], "must_not_include": [], "should_refuse": false, "notes": "Near-miss: backups are kept 35 days."}
{"id": "sf-15", "category": "single_fact", "question": "What encryption algorithm protects data at rest?", "expected_sources": ["encryption-and-key-management-standard.md"], "reference_answer": "AES-256.", "must_include": [["AES-256", "AES 256", "AES256", "256-bit AES"]], "must_not_include": [], "should_refuse": false, "notes": "Encryption at rest."}
{"id": "sf-16", "category": "single_fact", "question": "What is the minimum TLS version allowed for data in transit?", "expected_sources": ["encryption-and-key-management-standard.md"], "reference_answer": "TLS 1.2.", "must_include": [["TLS 1.2", "TLS version 1.2", "TLS v1.2", "TLSv1.2", "TLS1.2"]], "must_not_include": [], "should_refuse": false, "notes": "Near-miss: TLS 1.3 is preferred, not the minimum; TLS 1.0 and 1.1 are disabled."}
{"id": "sf-17", "category": "single_fact", "question": "What are the recovery time objective and recovery point objective for the production platform?", "expected_sources": ["business-continuity-and-disaster-recovery-plan.md"], "reference_answer": "An RTO of 4 hours and an RPO of 1 hour.", "must_include": [["4 hours", "four hours", "4-hour"], ["1 hour", "one hour", "1-hour"]], "must_not_include": [], "should_refuse": false, "notes": "Both values required."}
{"id": "sf-18", "category": "single_fact", "question": "How soon after deployment must an emergency change be reviewed?", "expected_sources": ["change-management-policy.md"], "reference_answer": "Within 2 business days after deployment.", "must_include": [["2 business days", "two business days", "2 working days", "two working days"]], "must_not_include": [], "should_refuse": false, "notes": "Emergency change review. The change is approved by the on-call engineering lead."}
{"id": "md-01", "category": "multi_doc", "question": "A Tier 1 vendor discovers a breach that exposed Quillmark customer data. How quickly must the vendor tell Quillmark, and how quickly must Quillmark notify affected customers once the breach is confirmed?", "expected_sources": ["vendor-management-policy.md", "incident-response-plan.md"], "reference_answer": "The vendor must notify Quillmark within 24 hours of discovering the incident, and Quillmark notifies affected customers within 72 hours of confirming the breach.", "must_include": [["24 hours", "twenty-four hours", "24-hour"], ["72 hours", "seventy-two hours", "72-hour"]], "must_not_include": [], "should_refuse": false, "notes": "Vendor clock plus customer notification clock."}
{"id": "md-02", "category": "multi_doc", "question": "What classification does customer data have, and how long after a contract ends is it deleted?", "expected_sources": ["information-security-policy.md", "data-retention-and-deletion-policy.md"], "reference_answer": "Customer data is Restricted, and it is deleted within 30 days after the contract terminates.", "must_include": [["Restricted"], ["30 days", "thirty days", "30-day"]], "must_not_include": [], "should_refuse": false, "notes": "Classification plus deletion deadline; a legal hold suspends deletion."}
{"id": "md-03", "category": "multi_doc", "question": "A new vendor will process Quillmark customer data. How is that data classified, which risk tier does the vendor fall into, and what assurance report does it need before the contract is signed?", "expected_sources": ["information-security-policy.md", "vendor-management-policy.md"], "reference_answer": "Customer data is Restricted, so the vendor is Tier 1 and must provide a SOC 2 Type II report or an ISO 27001 certificate before signing.", "must_include": [["Restricted"], ["Tier 1"], ["SOC 2 Type II", "SOC 2 Type 2", "SOC2 Type II", "ISO 27001", "ISO/IEC 27001"]], "must_not_include": [], "should_refuse": false, "notes": "Needs the classification rule to pick the tier."}
{"id": "md-04", "category": "multi_doc", "question": "What kind of MFA must administrators of production systems use, and if one of them needs an exception to that requirement, who approves it and how long can it last?", "expected_sources": ["access-control-policy.md", "information-security-policy.md"], "reference_answer": "Hardware security keys. The CISO approves exceptions, and an exception lasts no longer than 90 days.", "must_include": [["hardware security key", "security key", "hardware key"], ["CISO", "Chief Information Security Officer"], ["90 days", "ninety days", "90-day"]], "must_not_include": [], "should_refuse": false, "notes": "The MFA requirement is only in the access policy; the exception rules are only in the security policy. Exceptions go through the security exceptions process and can be renewed at most once."}
{"id": "md-05", "category": "multi_doc", "question": "After a SEV-1 incident is resolved, what follow-up do the incident response plan and the business continuity plan each require?", "expected_sources": ["incident-response-plan.md", "business-continuity-and-disaster-recovery-plan.md"], "reference_answer": "A blameless postmortem within 5 business days of resolution, and a review of the business continuity and disaster recovery plan.", "must_include": [["postmortem", "post-mortem"], ["5 business days", "five business days"], ["business continuity", "continuity plan", "disaster recovery plan", "BC/DR", "BCDR"], ["review", "reviewed", "reviewing"]], "must_not_include": [], "should_refuse": false, "notes": "One follow-up from each plan; the continuity plan's follow-up is a review."}
{"id": "md-06", "category": "multi_doc", "question": "During an emergency hotfix, a developer wants to add a new API key directly in the code. Where must the key be kept instead, who approves the emergency change, and how soon after deployment must it be reviewed?", "expected_sources": ["encryption-and-key-management-standard.md", "change-management-policy.md"], "reference_answer": "In the secrets manager. The on-call engineering lead approves the emergency change, and it must be reviewed within 2 business days after deployment.", "must_include": [["secrets manager", "secret manager"], ["on-call engineering lead", "on-call lead"], ["2 business days", "two business days", "2 working days", "two working days"]], "must_not_include": [], "should_refuse": false, "notes": "Secrets rule from the encryption standard (keys are never committed to source code); emergency approval and review from change management."}
{"id": "md-07", "category": "multi_doc", "question": "How are backups encrypted, and how long are they kept?", "expected_sources": ["encryption-and-key-management-standard.md", "data-retention-and-deletion-policy.md"], "reference_answer": "Backups are encrypted at rest with AES-256 and retained for 35 days.", "must_include": [["AES-256", "AES 256", "AES256", "256-bit AES"], ["35 days", "thirty-five days", "thirty five days", "35-day"]], "must_not_include": [], "should_refuse": false, "notes": "Encryption standard plus retention policy."}
{"id": "md-08", "category": "multi_doc", "question": "When a vendor contract ends, what must the vendor do with Quillmark data, and are vendors allowed to use shared accounts in Quillmark systems?", "expected_sources": ["vendor-management-policy.md", "access-control-policy.md"], "reference_answer": "The vendor must return or destroy Quillmark data and certify the destruction within 60 days. Shared accounts are prohibited for vendors; only break-glass accounts are allowed.", "must_include": [["60 days", "sixty days", "60-day"], ["prohibited", "prohibit", "prohibits", "not allowed", "not permitted", "aren't allowed", "aren't permitted", "cannot use", "can't use", "may not use", "must not use", "only allowed", "only permitted", "except break-glass", "except for break-glass", "no shared", "banned", "disallowed", "forbidden"]], "must_not_include": [], "should_refuse": false, "notes": "Contract-end rule only in the vendor policy; the shared-account ban only in the access policy."}
{"id": "vc-01", "category": "version_conflict", "question": "How often are user access reviews performed?", "expected_sources": ["access-control-policy.md"], "reference_answer": "Quarterly.", "must_include": [["quarterly", "every quarter", "every three months"]], "must_not_include": ["semi-annual", "semi-annually", "semiannual", "semiannually", "every six months", "twice a year"], "should_refuse": false, "notes": "Each system owner runs the review. v1.0 said semi-annually."}
{"id": "vc-02", "category": "version_conflict", "question": "How quickly is a departing person's access revoked?", "expected_sources": ["access-control-policy.md"], "reference_answer": "Within 4 hours of termination.", "must_include": [["4 hours", "four hours", "4-hour"]], "must_not_include": ["72 hours", "72-hour", "three days"], "should_refuse": false, "notes": "Measured from the termination time recorded in the HR system. v1.0 said 72 hours."}
{"id": "vc-03", "category": "version_conflict", "question": "What is the minimum password length?", "expected_sources": ["access-control-policy.md"], "reference_answer": "14 characters.", "must_include": [["14 characters", "fourteen characters", "14-character", "14"]], "must_not_include": ["10 characters", "ten characters", "10-character"], "should_refuse": false, "notes": "v1.0 said 10 characters."}
{"id": "vc-04", "category": "version_conflict", "question": "How often do passwords have to be changed?", "expected_sources": ["access-control-policy.md"], "reference_answer": "Not on a fixed schedule; a password must be changed when compromise is suspected.", "must_include": [["compromise", "compromised", "compromising"]], "must_not_include": ["90 days", "90-day", "every 90", "ninety days", "annually", "every year", "once a year", "yearly"], "should_refuse": false, "notes": "v1.0 required rotation every 90 days. The yearly forbidden values catch a mix-up with the encryption key rotation rule."}
{"id": "vc-05", "category": "version_conflict", "question": "Which accounts require multi-factor authentication?", "expected_sources": ["access-control-policy.md"], "reference_answer": "All workforce accounts, including employees and contractors.", "must_include": [["all workforce accounts", "every workforce account", "including employees and contractors", "all employees", "all employee and contractor accounts"]], "must_not_include": ["remote access only", "only for remote access", "only required for remote"], "should_refuse": false, "notes": "Production administrators additionally need hardware security keys. v1.0 required MFA for remote access only."}
{"id": "un-01", "category": "unanswerable", "question": "What is the payout range for Quillmark's bug bounty program?", "expected_sources": [], "reference_answer": "I cannot find this information in the document.", "must_include": [], "must_not_include": [], "should_refuse": true, "absent_terms": ["bug bounty", "bug bounties"], "notes": "No bug bounty program is described."}
{"id": "un-02", "category": "unanswerable", "question": "How many employees does Quillmark have?", "expected_sources": [], "reference_answer": "I cannot find this information in the document.", "must_include": [], "must_not_include": [], "should_refuse": true, "absent_terms": ["headcount", "number of employees"], "notes": "Headcount is never stated."}
{"id": "un-03", "category": "unanswerable", "question": "Which cloud provider hosts Quillmark's production environment?", "expected_sources": [], "reference_answer": "I cannot find this information in the document.", "must_include": [], "must_not_include": [], "should_refuse": true, "absent_terms": ["AWS", "Amazon", "Azure", "Google Cloud", "GCP"], "notes": "The documents say cloud and regions but never name a provider."}
{"id": "un-04", "category": "unanswerable", "question": "What is the coverage limit of Quillmark's cyber insurance policy?", "expected_sources": [], "reference_answer": "I cannot find this information in the document.", "must_include": [], "must_not_include": [], "should_refuse": true, "absent_terms": ["insurance"], "notes": "Insurance is never mentioned."}
{"id": "un-05", "category": "unanswerable", "question": "How often are external penetration tests performed?", "expected_sources": [], "reference_answer": "I cannot find this information in the document.", "must_include": [], "must_not_include": [], "should_refuse": true, "absent_terms": ["penetration test", "pen test", "pentest"], "notes": "Penetration testing is never mentioned."}
{"id": "un-06", "category": "unanswerable", "question": "What is the annual budget for Quillmark's security program?", "expected_sources": [], "reference_answer": "I cannot find this information in the document.", "must_include": [], "must_not_include": [], "should_refuse": true, "absent_terms": ["budget"], "notes": "No budget figure or process appears anywhere."}
{"id": "un-07", "category": "unanswerable", "question": "Does Quillmark run background checks on new hires?", "expected_sources": [], "reference_answer": "I cannot find this information in the document.", "must_include": [], "must_not_include": [], "should_refuse": true, "absent_terms": ["background check", "criminal record", "reference check"], "notes": "Hiring checks are never mentioned; only training after hire is."}
{"id": "un-08", "category": "unanswerable", "question": "Who is Quillmark's Data Protection Officer?", "expected_sources": [], "reference_answer": "I cannot find this information in the document.", "must_include": [], "must_not_include": [], "should_refuse": true, "absent_terms": ["Data Protection Officer", "DPO"], "notes": "No such role appears."}
{"id": "un-09", "category": "unanswerable", "question": "What uptime percentage does Quillmark guarantee in its customer SLA?", "expected_sources": [], "reference_answer": "I cannot find this information in the document.", "must_include": [], "must_not_include": [], "should_refuse": true, "absent_terms": ["uptime", "service level agreement", "SLA"], "notes": "RTO and RPO are stated, but no uptime commitment."}
```

- [ ] **Step 4: Run the integrity tests**

Run: `pytest tests/unit/test_eval_dataset.py -q`
Expected: `12 passed`.

If a test fails, the corpus from Task 3 is the likely cause, for example a banned term or a superseded value in the current policy. Report it rather than editing the answer key; the answer key is fixed by this plan.

- [ ] **Step 4b: Pin answers a real model could give**

`backend/tests/unit/test_answer_key_cases.py`:

```python
"""Pinned answers for the policies_v1 answer key.

Each case is an answer a real model could plausibly give. Correct answers must pass the
item's code-based checks and wrong ones must fail, so later edits to accepted wordings
cannot quietly loosen or tighten the key. The cases come from the answer-key reviews.
"""

import pytest

from evals.dataset import DATASETS_DIR, fact_present, load_dataset

ITEMS = {item.id: item for item in load_dataset(DATASETS_DIR / "policies_v1.jsonl")}


def _passes(item_id: str, answer: str) -> bool:
    item = ITEMS[item_id]
    has_facts = all(fact_present(answer, fact) for fact in item.must_include)
    return has_facts and not fact_present(answer, item.must_not_include)


CORRECT = [
    ("sf-05", "They must use hardware keys."),
    ("sf-12", "Tier 2 vendors are reassessed biennially."),
    ("sf-13", "Backups have a 35-day retention period."),
    ("sf-15", "Data at rest uses AES\u2011256."),
    ("sf-16", "TLS v1.2 at minimum."),
    ("sf-17", "A 4-hour RTO and a 1-hour RPO."),
    ("vc-01", "Every quarter."),
    ("vc-02", "Within 4 hours of the termination time."),
    ("vc-03", "A 14-character minimum."),
    ("vc-04", "The password must be changed if it is compromised."),
    ("md-03", "Customer data is Restricted; the vendor is Tier 1 and needs a SOC2 Type II report."),
    ("md-04", "Hardware security keys; the CISO can approve an exception for at most 90 days."),
    ("md-05", "A postmortem within 5 business days, and a review of the continuity plan."),
    ("md-08", "Vendors cannot use shared accounts; destruction is certified within 60 days."),
    ("md-08", "Within 60 days. No: shared accounts are only allowed as break-glass accounts."),
    ("md-08", "Vendors aren\u2019t allowed shared accounts; destruction is certified in 60 days."),
]

WRONG = [
    ("sf-03", "Up to 190 days."),
    ("sf-06", "Accounts lock for 10 minutes after 15 failed attempts."),
    ("sf-09", "Within 15 business days."),
    ("sf-17", "RTO is 24 hours and RPO is 11 hours."),
    ("vc-01", "Semi-annually."),
    ("vc-02", "Access is revoked within 24 hours."),
    ("vc-02", "There is a 72-hour window to revoke access, or 4 hours for urgent cases."),
    ("vc-04", "Every 90 days."),
    ("vc-04", "On a 90-day cycle, or when compromised."),
    ("vc-04", "Rotated annually or immediately when compromise is suspected."),
    ("vc-05", "Employees and contractors need MFA when connecting from outside company networks."),
    ("md-04", "Yes, the CISO can approve an exception for up to 90 days with one renewal."),
    ("md-05", "A postmortem within 5 business days; the business continuity plan also applies."),
    ("md-08", "Shared accounts are prohibited for vendors."),
    ("md-08", "I can't find anything about shared accounts, but destruction is due in 60 days."),
    ("md-08", "Data must not be kept past 60 days. Vendors may use shared accounts with approval."),
]


@pytest.mark.parametrize(("item_id", "answer"), CORRECT)
def test_correct_answers_pass(item_id, answer):
    assert _passes(item_id, answer)


@pytest.mark.parametrize(("item_id", "answer"), WRONG)
def test_wrong_answers_fail(item_id, answer):
    assert not _passes(item_id, answer)
```

Run: `pytest tests/unit/test_answer_key_cases.py -q`
Expected: `32 passed`.

- [ ] **Step 5: Write the README**

`backend/evals/README.md`:

```markdown
# RAG evals

This folder holds the evaluation data for the RAG pipeline: a small synthetic policy corpus and a question set with a hand-checked answer key. The harness that scores the pipeline against them comes in a later change.

## The corpus

`corpus/` contains nine short security policies for Quillmark Systems, a fictional B2B software company. Every document starts with "Fictional company. Synthetic document created for RAG evaluation." None of the companies, people, or products are real.

The documents are written to be checkable. Every fact is specific (a number, a deadline, an owner). `tests/unit/test_eval_corpus.py` holds the fact sheet: the sentences each document must contain word for word, plus a rule that no number appears unless the fact sheet put it there.

Some traps are planted on purpose:

- **An outdated policy.** `access-control-policy-v1-superseded.md` is marked superseded and disagrees with the current Access Control Policy: semi-annual reviews instead of quarterly, 72 hours to revoke access instead of 4, and so on. A good answer uses the current version.
- **Near misses.** Similar facts sit close together, such as backups kept 35 days and logs kept one year, so an answer that grabs the wrong number gets caught.
- **Answers that span documents.** Some questions need facts from two policies, such as a vendor breach that also starts the customer notification clock.
- **Questions with no answer.** Some questions sound reasonable, but the documents never cover them. The right response is "I cannot find this information in the document."

## The question set

`datasets/policies_v1.jsonl` has 40 questions, one JSON object per line.

| Category | Count | What it tests |
|---|---|---|
| `single_fact` | 18 | Find one fact in one document |
| `multi_doc` | 8 | Combine facts from two documents |
| `version_conflict` | 5 | Use the current policy, never the superseded one |
| `unanswerable` | 9 | Refuse instead of guessing |

Each record lists the documents that should be retrieved, a short reference answer, the facts the answer must include (each with accepted wordings), values it must not include, and whether it should refuse. Unanswerable questions also list terms that never appear in the corpus.

`tests/unit/test_eval_dataset.py` checks the answer key in CI:

- ids are unique and the category counts match;
- every expected document exists;
- every required fact really appears in its documents;
- every reference answer passes its own checks;
- every multi-document question draws at least one required fact from each of its documents;
- every version trap is real: at least one forbidden value appears in the superseded policy, and none appears in the current one;
- none of the terms behind an unanswerable question appears anywhere in the corpus.

Facts and terms match as whole words, so "4 hours" does not match "24 hours". Typographic dashes and quotes are folded to plain ASCII first, so "AES-256" written with a non-breaking hyphen still matches.

`tests/unit/test_answer_key_cases.py` pins answers a real model could give: correct ones must pass the code-based checks and wrong ones must fail, so later edits to accepted wordings cannot quietly change what the key accepts.

## Scoring rules worth knowing

- **Reference answers say only what the question asks.** Extra details live in each record's `notes`, so a concise correct answer is not marked as missing something.
- **Mentioning a superseded value fails a version question, even as a contrast.** For example, "Quarterly (v1.0 said semi-annually)" fails `vc-01`. A good answer states the current policy only.

## Changing the data

Any edit to the corpus or the questions becomes a new version (`policies_v2.jsonl`), so scores from different answer keys are never compared.
```

- [ ] **Step 6: Run the whole backend suite and lint**

Run (from `backend/`, with `TEST_DATABASE_URL` set as in the environment notes): `pytest -q && ruff check .`
Expected: `159 passed` (47 existing, 22 loader, 46 corpus, 12 dataset, 32 pinned answer cases), then `All checks passed!`

- [ ] **Step 7: Stop for owner review**

Files for the owner: `backend/tests/unit/test_eval_dataset.py`, `backend/tests/unit/test_answer_key_cases.py`, `backend/evals/datasets/policies_v1.jsonl`, `backend/evals/README.md`. Suggested message: `feat(evals): add the policies_v1 answer key and its integrity tests`.

---

## Amendments from execution

The answer key, matcher, and tests above already include every change ruled during execution (see the SDD ledger). The corpus documents are not embedded in this plan, so the four corpus edits made after the final review are recorded here. Each replaces one sentence or line, matched across line wraps:

- `backend/evals/corpus/business-continuity-and-disaster-recovery-plan.md`: replace "The incident commander, who is appointed under the Incident Response Plan, coordinates communication with the rest of the company and with customers." with "The incident commander, as set out in the Incident Response Plan, coordinates communication within the company, and any notice to customers follows that plan."
- `backend/evals/corpus/business-continuity-and-disaster-recovery-plan.md`: replace "The incident commander keeps customers, leadership, and staff informed in plain terms about what is affected and what is being done." with "The incident commander keeps leadership and staff informed in plain terms about what is affected and what is being done."
- `backend/evals/corpus/incident-response-plan.md`: replace "The General Counsel advises on legal duties, reviews any notice sent to customers or regulators, and decides who may speak publicly." with "The General Counsel advises on legal duties, decides what any notice to customers or regulators says, and decides who may speak publicly."
- `backend/evals/corpus/vendor-management-policy.md`: replace "Effective date: January 15, 2026" with "Effective date: March 1, 2026"

The Vendor Management Policy now takes effect on March 1, 2026, the same day as Access Control Policy v2.0, because it refers to the quarterly access review that v2.0 introduced. The other three edits keep customer and regulator notices with the General Counsel, as the Incident Response Plan says.

## After Plan 2

- **The owner reviews the corpus and all 40 questions before v1 is frozen** (spec Part 2, "Review"). Any change to the questions or documents after that becomes `policies_v2`.
- Plan 3 (eval harness) is written next. It uses `evals.dataset` and the policies_v1 data from this plan.
