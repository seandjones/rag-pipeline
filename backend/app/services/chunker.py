import io
from pathlib import Path

import pypdf


def extract_text_from_pdf_bytes(content: bytes) -> str:
    try:
        reader = pypdf.PdfReader(io.BytesIO(content))
        return "\n".join(
            page.extract_text() for page in reader.pages if page.extract_text()
        ).strip()
    except Exception as exc:
        print(f"Error extracting PDF from bytes: {exc}")
        return ""


def extract_text_from_pdf(file_path: Path) -> str:
    try:
        reader = pypdf.PdfReader(str(file_path))
        text = "\n".join(
            page.extract_text() for page in reader.pages if page.extract_text()
        )
        return text.strip()
    except Exception as exc:
        print(f"Error extracting text from {file_path}: {exc}")
        return ""


def normalize_patterns(patterns: list[str]) -> list[str]:
    normalized: list[str] = []
    for pattern in patterns:
        cleaned = pattern.strip()
        if not cleaned:
            continue
        if "*" not in cleaned and "?" not in cleaned and "[" not in cleaned:
            if cleaned.startswith("."):
                cleaned = f"*{cleaned}"
            elif "/" not in cleaned:
                cleaned = f"*.{cleaned}"
        normalized.append(cleaned)
    return normalized or ["*.txt", "*.md"]


def chunk_text(content: str, chunk_size: int = 1000, overlap: int = 100) -> list[str]:
    if chunk_size <= overlap:
        raise ValueError("chunk_size must be larger than overlap")
    chunks: list[str] = []
    start = 0
    while start < len(content):
        end = min(start + chunk_size, len(content))
        chunks.append(content[start:end])
        if end == len(content):
            break
        start += chunk_size - overlap
    return chunks


def read_files(directory: str, patterns: list[str]) -> list[tuple[str, str]]:
    base_dir = Path(directory).expanduser().resolve()
    normalized = normalize_patterns(patterns)
    files_with_content: list[tuple[str, str]] = []
    seen_paths: set[str] = set()
    for pattern in normalized:
        for file_path in base_dir.rglob(pattern):
            if not file_path.is_file():
                continue
            file_key = str(file_path)
            if file_key in seen_paths:
                continue
            if file_path.suffix.lower() == ".pdf":
                content = extract_text_from_pdf(file_path)
            else:
                content = file_path.read_text(encoding="utf-8", errors="ignore").strip()
            if content:
                files_with_content.append((file_key, content))
                seen_paths.add(file_key)
    return files_with_content
