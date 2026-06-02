# RAG Pipeline (FastAPI + OpenAI + Postgres pgvector)

This service lets you ingest local files into a pgvector-backed index and ask questions over those files.

## 1) Start Postgres with pgvector

From this folder:

```bash
docker compose up -d
```

## 2) Install backend dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install fastapi uvicorn sqlalchemy psycopg2-binary openai pydantic
```

## 3) Set environment variables

```bash
export OPENAI_API_KEY="your_key_here"
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/ragdemo"
export EMBEDDING_MODEL="text-embedding-3-small"
export CHAT_MODEL="gpt-4o-mini"
```

## 4) Run the API

```bash
uvicorn main:app --reload --port 8001
```

On startup, the app creates the pgvector extension and the `document_chunks` table automatically.

## 5) Ingest local files

Call `POST /ingest-local` with a local directory path that the API process can access.

```bash
curl -X POST "http://127.0.0.1:8001/ingest-local" \
    -H "Content-Type: application/json" \
    -d '{
        "directory": "/Users/seanjones/agents/RAG-pipeline",
        "patterns": ["*.md", "*.txt", "*.py"],
        "chunk_size": 1000,
        "overlap": 100
    }'
```

Expected response shape:

```json
{
    "message": "Ingestion complete",
    "files_indexed": 3,
    "chunks_stored": 18
}
```

## 6) Ask a question

```bash
curl -X POST "http://127.0.0.1:8001/chat" \
    -H "Content-Type: application/json" \
    -d '{
        "question": "What does this project do?",
        "top_k": 5
    }'
```

Response shape:

```json
{
    "answer": "...",
    "context_count": 5
}
```

## Notes

- Large folders can take time because every chunk makes an embeddings API call.

## Contributing

Pull requests are welcome. For major changes, please open an issue first
to discuss what you would like to change.

Please make sure to update tests as appropriate.

## License

[MIT](https://choosealicense.com/licenses/mit/)