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
