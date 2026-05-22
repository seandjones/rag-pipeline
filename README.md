# seanjones.io rag pipeline

RAG pipeline for searching internal documents via google drive

## Architecture

### 1. Documents

### 2. Chunking

### 3. Embeddings

### 4. Vector DB (pgvector)

### 5. User Question

### 6. Similarity Search

### 7. Relevant Chunks

### 8. LLM Prompt

### 9. Answer

### Core Components & Flow

#### 1. Entry Points & API Layer
- **main.py**: FastAPI application entry point with lifespan management
- **api/chat.py**: REST API endpoints for chat functionality
- **/docs**: Swagger UI for testing

#### 2. Docker setup
- **compose.yaml**: main docker entry point
```
    docker compose up
```
##### get docker instance information
```
    docker ps -a 
```

## Contributing

Pull requests are welcome. For major changes, please open an issue first
to discuss what you would like to change.

Please make sure to update tests as appropriate.

## License

[MIT](https://choosealicense.com/licenses/mit/)