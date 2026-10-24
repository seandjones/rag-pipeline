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
