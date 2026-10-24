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
