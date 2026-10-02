# Tests, CI, and RAG Eval Harness: Design

- **Date:** 2026-09-23
- **Status:** Draft, awaiting review
- **Branch:** `feature/tests-and-evals`

## Goal

Add three things to this repo:

1. A test suite for the existing backend and frontend, run by GitHub Actions on every push and pull request.
2. A fixed, synthetic evaluation dataset: security policies for a fictional company, plus a hand-checked question set.
3. An eval harness that scores both answer pipelines, saves each run, and compares runs, so quality changes can be measured instead of guessed.

The end product is a documented improvement loop in `backend/evals/RESULTS.md`: a baseline, a targeted change, and the measured before and after.

## Non-goals

- Changing production behavior while building the harness. Defects that tests or evals uncover are fixed as separate changes, each reviewed and approved on its own.
- Running the evals in CI. They cost OpenAI credits and need an API key, so they run by hand.
- Adopting an eval framework (Ragas, DeepEval, promptfoo). The harness is written here so every metric can be explained.
- Touching the uncommitted Google Drive ingestion work (`gdrive.py` and the related edits to `ingest.py`, `config.py`, `requests.py`, `requirements.txt`, `.env.example`).

## Working agreement

- All work happens on `feature/tests-and-evals`.
- Nothing is committed until the repo owner has reviewed the diff.
- Any edit to an existing file is listed for approval before it is made, including lint fixes.

## Current state

- Backend: FastAPI, async SQLAlchemy, asyncpg, pgvector, and the OpenAI SDK. The Dockerfiles use Python 3.12.
- Frontend: React 19, TypeScript, Redux Toolkit and RTK Query, React Router, and Vite. The Dockerfiles use Node 22.
- There are no tests and no CI.
- There are two answer paths:
  - `POST /chat` runs `run_agent`, an agentic tool-calling loop over `vector_search` and `list_documents`.
  - `POST /chat/stream` does a single retrieval, builds a prompt with `build_prompt`, and streams the answer through `stream_answer` using `_SYSTEM_PROMPT`.

### Known defects found during design

These are recorded now so the tests and evals can confirm them. None are fixed as part of the harness work.

| ID | Where | Defect | Expected to surface in |
|---|---|---|---|
| D1 | `services/agent.py` | The agent's system prompt has no refusal instruction, so unanswerable questions may get invented answers. The single-retrieval path says "I cannot find this information in the document." | Eval refusal scores |
| D2 | `services/agent.py` | `run_agent` loops `while True` with no cap on model calls. | Harness call-limit guard |
| D3 | `features/chat/ChatPage.tsx` | On success, `addMessage` pushes a second assistant message with the same id as the placeholder instead of replacing it. The empty placeholder keeps `isStreaming: true`, both messages share a React key, and `setMessageSources` updates the placeholder rather than the answer. | `ChatPage.test.tsx` |
| D4 | `features/chat/ChatPage.tsx` | The `useCallback` dependency list leaves out `messages`, so the history sent to `/chat` comes from the first render and is always empty. `eslint` already warns about this (`react-hooks/exhaustive-deps`). | `ChatPage.test.tsx` |
| D5 | `backend/=0.0.9` | A tracked, empty file, most likely left behind by an unquoted `pip install python-multipart>=0.0.9`. | Cleanup, with approval |
| D6 | `features/chat/AgentSteps.tsx` | `String(tc.args.query as string)` turns a missing query into the string "undefined", so a `list_documents` step shows “undefined”. | `AgentSteps.test.tsx` |

## Part 1: Test setup and CI

### Backend

**New files**

- `backend/requirements-dev.txt`: pytest, pytest-asyncio, pytest-cov, ruff, httpx. httpx is listed explicitly because none of the app's dependencies install it.
- `backend/pyproject.toml`: pytest settings (`asyncio_mode = "auto"`, an `integration` marker, `testpaths = ["tests"]`) and ruff settings (line length 100; rule sets E, F, I).
- `backend/tests/conftest.py`:
  - Sets `DATABASE_URL` from `TEST_DATABASE_URL` (default `postgresql://postgres:postgres@localhost:5432/ragdemo_test`) and a dummy `OPENAI_API_KEY` before any `app` import, because `app.config.get_settings()` and `app.db.engine.get_engine()` are cached at import time.
  - Refuses to run unless the database name ends in `_test`, so the truncating fixtures can never touch a real database.
  - Provides a session fixture that creates `ragdemo_test` if it is missing, runs `ensure_schema()`, and truncates `document_chunks` before each integration test.
  - Skips integration tests with a clear message when Postgres is unreachable.
- `backend/tests/fakes.py`: `FakeOpenAI`, which offers `embeddings.create` and `chat.completions.create`.
  - Embeddings are deterministic 1536-dimension vectors built by hashing each word into a bucket and normalizing, so texts that share words land closer together and retrieval tests stay meaningful.
  - Chat completions come from a script supplied by each test: a queue of responses, each either tool calls or final content.
  - Every call is recorded so tests can check what was sent.

**Unit tests** (`backend/tests/unit/`, no database)

| File | Covers |
|---|---|
| `test_chunker.py` | `chunk_text`: empty input, input shorter than one chunk, exact boundary, overlap positions, and the `chunk_size <= overlap` error. `normalize_patterns`: bare extensions, dotted extensions, globs, blanks, and the default fallback. `read_files`: nested folders, pattern filtering, duplicate matches, empty files skipped. |
| `test_config.py` | `async_database_url`: rewrites `postgresql://` and `postgres://`, keeps `+asyncpg` URLs as they are, rejects an empty URL. |
| `test_retrieval_helpers.py` | `_to_pgvector` formatting. |
| `test_agent.py` | `run_agent` with `FakeOpenAI`: a tool call then a final answer (sources collected and de-duplicated, tool calls logged); `list_documents` tool; unknown tool name; chat history placed between the system and user messages; a non-`stop`, non-`tool_calls` finish reason. Retrieval is replaced with a stub so no database is needed. |

**Integration tests** (`backend/tests/integration/`, real pgvector)

| File | Covers |
|---|---|
| `test_retrieval_db.py` | `store_embedding` insert and upsert on `(source_path, chunk_index)`; `search_similar_chunks` ordering with hand-built vectors; `list_documents`; `delete_document` row count. |
| `test_api.py` | Through `httpx.AsyncClient` with `ASGITransport`, with the app's OpenAI client replaced by `FakeOpenAI`: `GET /health`; `POST /chat` returns an answer, sources, and tool calls; `GET /documents` and `DELETE /documents/{path}`; `POST /ingest/local` on a temp folder, then polling `GET /ingest/jobs/{id}` until complete; a 400 for a missing folder; a 404 for an unknown job id. |

### Frontend

**New dev dependencies:** vitest, @testing-library/react, @testing-library/user-event, @testing-library/jest-dom, jsdom, msw.

**Configuration**

- Test settings go in `vite.config.ts`, using `defineConfig` from `vitest/config`: jsdom environment, a setup file, coverage through v8, and `VITE_API_URL=http://localhost/api` so RTK Query has an absolute URL under Node's `fetch`.
- `coverage/` is added to `frontend/.gitignore` and to eslint's ignored paths.
- New files:
  - `src/test/setup.ts`: jest-dom matchers and the MSW server lifecycle.
  - `src/test/server.ts`: default MSW handlers for `/api/chat`, `/api/documents`, and `/api/ingest/*`.
  - `src/test/renderWithStore.tsx`: renders a component with a fresh store.
- **Edit to an existing file (needs approval):** `src/app/store.ts` gets a `makeStore()` factory so each test starts from a clean store. `store` stays exported as `makeStore()`, so app behavior does not change.
- **New scripts in `package.json`:** `test` (`vitest run`), `test:watch` (`vitest`), `coverage` (`vitest run --coverage`).

**Tests**

| File | Covers |
|---|---|
| `features/chat/chatSlice.test.ts` | Each reducer, including actions that target an unknown id (no-op). |
| `features/chat/ChatInput.test.tsx` | Enter submits the trimmed text and clears the box; Shift+Enter does not submit; empty input is ignored; the disabled state shows "Thinking…" and blocks submission. |
| `features/chat/SourceCitations.test.tsx` | Renders nothing with no sources; singular and plural labels; the toggle sets `aria-expanded`; the excerpt is cut at 200 characters with an ellipsis. |
| `features/chat/AgentSteps.test.tsx` | Each step shows the tool name and its query; a step without a query shows no query text (fails on current code: D6). |
| `features/chat/ChatPage.test.tsx` | A question shows the answer exactly once, with its sources and agent steps (fails on current code: D3). A second question sends the first turn as history (fails on current code: D4). An API error shows the error message. "Clear" empties the conversation. |

The tests for D3, D4, and D6 are written against the correct behavior and will fail until those defects are fixed. They are checked in with `it.fails(...)` so CI stays green and the failure is documented. Each is switched to `it(...)` in the same change that fixes its defect.

### CI (`.github/workflows/ci.yml`)

Triggers: `push` and `pull_request`.

- **backend** job: `ubuntu-latest`, Python 3.12.
  - A `pgvector/pgvector:pg16` service container with a health check; `TEST_DATABASE_URL` points at it.
  - `REQUIRE_DATABASE=1`, which makes the database fixture fail instead of skip, so a broken service container turns the build red instead of silently skipping the integration tests.
  - Steps: install `requirements.txt` and `requirements-dev.txt`, `ruff check`, `pytest --cov=app`.
  - `ruff format --check` is left out on purpose: it would force reformatting every existing file, which is churn unrelated to this work.
- **frontend** job: Node 22.
  - Steps: `npm ci`, `npm run lint`, `npm run build` (runs `tsc -b`), `npm test`.
- `README.md` gets a CI status badge and a "Running tests" section.

If ruff flags existing files, the fixes are listed for approval before they are applied. If approval is not given, the affected rules or files are excluded in `pyproject.toml` with a comment explaining why.

## Part 2: Eval data

### Corpus (`backend/evals/corpus/`)

Nine Markdown documents for a fictional B2B software company, **Quillmark Systems**. Each begins with the line: "Fictional company. Synthetic document created for RAG evaluation."

1. `information-security-policy.md`
2. `access-control-policy.md` (v2.0, current)
3. `access-control-policy-v1-superseded.md` (v1.0, marked superseded by v2.0, with deliberately conflicting values)
4. `incident-response-plan.md`
5. `vendor-management-policy.md`
6. `data-retention-and-deletion-policy.md`
7. `encryption-and-key-management-standard.md`
8. `business-continuity-and-disaster-recovery-plan.md`
9. `change-management-policy.md`

Guidelines for writing them:

- Each document runs roughly 500 to 1,200 words, so the default 1,000-character chunking produces several chunks per document.
- Facts are specific and checkable: frequencies, deadlines, owners, thresholds, versions.
- Near-miss facts are planted on purpose (for example, backups kept 35 days versus logs kept one year) to catch answers that grab the wrong number.
- No real company, person, product, or vendor names. Vendor examples use generic descriptions ("a payroll provider").

### Question set (`backend/evals/datasets/policies_v1.jsonl`)

About 40 questions:

| Category | Target count | Purpose |
|---|---|---|
| `single_fact` | 18 | One fact from one document |
| `multi_doc` | 8 | Needs facts from two documents |
| `version_conflict` | 5 | Must give the v2.0 value and never the superseded v1.0 value |
| `unanswerable` | 9 | Plausible but not covered; the correct response is a refusal |

Record format (one JSON object per line):

```json
{
  "id": "ac-003",
  "category": "version_conflict",
  "question": "How often are user access reviews performed?",
  "expected_sources": ["access-control-policy.md"],
  "reference_answer": "Quarterly, led by each system owner.",
  "must_include": [["quarterly", "every three months", "every quarter"]],
  "must_not_include": ["semi-annual", "twice a year", "every six months"],
  "should_refuse": false,
  "notes": "v1.0 said semi-annual; v2.0 changed it to quarterly."
}
```

- `must_include` is a list of required facts. Each fact is a list of accepted alternatives, matched case-insensitively after collapsing whitespace.
- `must_not_include` holds strings that must not appear.
- For `unanswerable` questions, `expected_sources` and `must_include` are empty and `should_refuse` is true.

### Dataset integrity tests (free, run in CI)

`backend/tests/unit/test_eval_dataset.py` checks that:

- every line parses and matches the record schema;
- ids are unique and categories are valid;
- every `expected_sources` entry exists in the corpus;
- for each answerable question, at least one alternative of every `must_include` fact appears in the text of its `expected_sources`;
- every `unanswerable` question has `should_refuse: true` and no expected sources;
- every `version_conflict` question has a non-empty `must_not_include` list.

### Versioning

Any edit to the corpus or the questions creates a new dataset version (`policies_v2.jsonl`). Each run records the dataset file name and a SHA-256 hash of the dataset plus the corpus, and `compare` refuses to compare runs whose hashes differ unless `--allow-dataset-mismatch` is passed.

### Review

All documents and questions are drafted first, then reviewed question by question by the repo owner before v1 is frozen.

## Part 3: Eval harness (`backend/evals/`)

### Modules

| Module | Responsibility |
|---|---|
| `config.py` | `EvalConfig`: target, dataset, top_k, chunk_size, overlap, repeats, concurrency, judge model (from `EVAL_JUDGE_MODEL`, defaulting to the app's `CHAT_MODEL`), max model calls per question (default 8), per-question timeout (default 90 s), refusal phrase ("I cannot find this information"). |
| `index.py` | Builds the eval index in a separate `ragdemo_eval` database. It uses the app's own `read_files`, `chunk_text`, `batch_embeddings`, and `store_embedding`. The index is keyed by a hash of the corpus plus chunk settings and rebuilt when that changes. |
| `instrumented_client.py` | Wraps `AsyncOpenAI`. It forwards every call unchanged, records tokens (from `usage`) and latency per question, and raises `CallLimitExceeded` when a question passes the model-call limit. |
| `targets.py` | Two targets with a shared result type (`answer`, `retrieved_sources` as ordered document names, `retrieved_context`, `tool_calls`, `latency_ms`, `tokens`, `error`). `agent` calls `run_agent`. `single_shot` calls `search_similar_chunks`, `build_prompt`, and `generate_answer`, the non-streaming equivalent of `/chat/stream`. Source document names are parsed from the `Source: <path>` prefix and reduced to the file name. |
| `scorers.py` | Code-based checks (below). Pure functions, unit-tested. |
| `judge.py` | Grading-model scoring (below). Prompt building and reply parsing are unit-tested with `FakeOpenAI`. |
| `run.py` | Command-line entry point. Runs the dataset against one target with bounded concurrency and repeats, then writes a results file. |
| `report.py` | Renders a Markdown summary for one run. |
| `compare.py` | Compares two runs: metric changes, plus questions that flipped between pass and fail. |
| `calibrate.py` | Runs the grading model on `datasets/judge_calibration_v1.jsonl` (about 12 hand-labeled answer and verdict pairs) and reports how often it agrees with the labels. |

### Code-based checks

- **Retrieval** (answerable questions only):
  - `hit_at_k`: at least one expected source was retrieved.
  - `recall_at_k`: the share of expected sources retrieved.
  - `mrr`: 1 divided by the rank of the first expected source, or 0 if none was retrieved.

  For the `agent` target, retrieval is scored on the de-duplicated union of everything its tool calls retrieved, in order.
- **Facts:** `facts_score` is the share of `must_include` facts matched. `forbidden_hit` is true if any `must_not_include` string appears.
- **Refusal:**
  - `refused` is true if the answer contains the refusal phrase.
  - A `correct_refusal` is `should_refuse` and `refused`.
  - A `false_refusal` is `not should_refuse` and `refused`.

### Grading model

Two rubrics. Each returns JSON `{"score": 0 | 1 | 2, "reason": "..."}` at temperature 0 with JSON output mode.

- **Correctness:** compares the answer to the reference answer. 2 = fully correct, 1 = partly correct or missing a detail, 0 = wrong or contradicts the reference.
- **Grounding:** checks every claim in the answer against the retrieved context. 2 = all supported, 1 = a minor unsupported detail, 0 = a material unsupported claim.

Both rubrics are skipped for `unanswerable` questions, which are scored by refusal alone. A reply that cannot be parsed is retried once, then recorded as `judge_error` and counted as a failure.

### Pass definition

- **Answerable:** `facts_score == 1`, no `forbidden_hit`, not `refused`, correctness 2, and grounding 2.
- **Unanswerable:** `refused`.
- **Any error** (timeout, call limit, API error) counts as a failure and is shown separately.

### Output

`run.py` writes `backend/evals/results/<UTC timestamp>-<label>-<target>.json` with:

- `meta`: label, target, git commit and whether the working tree had uncommitted changes, dataset file and hash, chat model, embedding model, judge model, top_k, chunk settings, repeats, start and end times.
- `items`: one record per question per repeat, with the answer, retrieved sources, tool calls, every score, judge reasons, tokens, latency, and any error.
- `summary`: pass rate and each metric, overall and by category, as a mean with min and max across repeats; total tokens; p50 and p95 latency.

`report.py` prints the summary as Markdown. `compare.py` prints metric changes and two lists: questions that went from pass to fail, and from fail to pass.

Raw results are gitignored (`backend/evals/results/`). Runs worth citing are summarized by hand in `backend/evals/RESULTS.md`.

### Commands

```bash
cd backend
python -m evals.run --target agent --label baseline --repeats 3
python -m evals.run --target single_shot --label baseline --repeats 3
python -m evals.report evals/results/<file>.json
python -m evals.compare evals/results/<before>.json evals/results/<after>.json
python -m evals.calibrate
```

These need Postgres running and `OPENAI_API_KEY` set.

### Harness tests (free, run in CI)

- `tests/unit/test_scorers.py`: every scorer, including multi-document recall, rank edge cases, alternative matching, and refusal combinations.
- `tests/unit/test_judge.py`: prompt contents, reply parsing, the retry on a malformed reply, and `judge_error`.
- `tests/unit/test_compare.py`: metric changes, flip detection, and the dataset hash check.
- `tests/integration/test_eval_run.py`: a full `run.py` on a three-question dataset and a two-document corpus using `FakeOpenAI` and the test database. It checks the results file structure and the summary math.

## Part 4: First improvement loop (after the harness is merged)

1. Run baselines for both targets with `--repeats 3`.
2. Read failures by category and write down a hypothesis for each pattern.
3. Make one change per iteration, each a separate reviewed change. The likely first candidate is D1 (a refusal instruction in the agent prompt), then D2 (a call cap in `run_agent`).
4. Rerun and compare. Keep a change only if the target metric improves and nothing flips from pass to fail without an explanation.
5. Record each iteration in `RESULTS.md`: the hypothesis, the change, the before and after metrics, and the flips.

## Build order

1. Backend test setup and unit tests.
2. Backend integration tests.
3. Frontend test setup and tests.
4. CI workflow and README section.
5. Corpus and question set drafts, then dataset integrity tests.
6. Review of the corpus and questions by the repo owner; freeze v1.
7. Harness modules, test-first.
8. Calibration set and calibration run.
9. Baseline runs; the first improvement loop begins (Part 4).

## Risks

- **Grader bias.** A grading model can be lenient or inconsistent. Mitigated by temperature 0, a rubric with a written reason, a stronger grading model when available, and the calibration check.
- **Run-to-run variance.** The app does not set a temperature, so answers vary. Mitigated by `--repeats` and by reporting the spread next to the mean.
- **Dataset overfitting.** Tuning the prompt against 40 questions can overfit them. Mitigated by recording every change, and by adding a held-out `policies_v2` set if the loop goes past a few iterations.
- **Local Python mismatch.** The local virtual environment is Python 3.11 and CI uses 3.12. The code avoids 3.12-only features so both work.
