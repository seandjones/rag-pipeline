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
