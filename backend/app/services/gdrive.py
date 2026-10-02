import io

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from app.config import get_settings
from app.services.chunker import extract_text_from_pdf_bytes

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

_EXT_TO_MIME: dict[str, str] = {
    "txt": "text/plain",
    "md": "text/markdown",
    "pdf": "application/pdf",
}

# Google Workspace document types — exported as plain text via the export API
_WORKSPACE_MIMES = {
    "application/vnd.google-apps.document",
    "application/vnd.google-apps.spreadsheet",
    "application/vnd.google-apps.presentation",
}


def _build_service():
    settings = get_settings()
    if not settings.google_service_account_json:
        raise ValueError("GOOGLE_SERVICE_ACCOUNT_JSON is not configured")
    creds = service_account.Credentials.from_service_account_file(
        settings.google_service_account_json,
        scopes=SCOPES,
    )
    return build("drive", "v3", credentials=creds)


def _mime_query(patterns: list[str]) -> str:
    mimes: set[str] = set(_WORKSPACE_MIMES)
    for pattern in patterns:
        ext = pattern.lstrip("*.").lower()
        if mime := _EXT_TO_MIME.get(ext):
            mimes.add(mime)
    if len(mimes) == len(_WORKSPACE_MIMES):
        # No pattern matched — fall back to all supported native types
        mimes.update(_EXT_TO_MIME.values())
    return " or ".join(f"mimeType = '{m}'" for m in sorted(mimes))


def _list_files(service, folder_id: str, patterns: list[str]) -> list[dict]:
    query = f"'{folder_id}' in parents and trashed = false and ({_mime_query(patterns)})"
    files: list[dict] = []
    page_token = None
    while True:
        response = (
            service.files()
            .list(
                q=query,
                fields="nextPageToken, files(id, name, mimeType)",
                pageToken=page_token,
            )
            .execute()
        )
        files.extend(response.get("files", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break
    return files


def _fetch_content(service, file_id: str, file_name: str, mime_type: str) -> str:
    buf = io.BytesIO()
    if mime_type in _WORKSPACE_MIMES:
        request = service.files().export_media(fileId=file_id, mimeType="text/plain")
    else:
        request = service.files().get_media(fileId=file_id)

    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()

    content_bytes = buf.getvalue()

    if mime_type == "application/pdf" or file_name.lower().endswith(".pdf"):
        return extract_text_from_pdf_bytes(content_bytes)

    return content_bytes.decode("utf-8", errors="ignore").strip()


def read_drive_files(folder_id: str, patterns: list[str]) -> list[tuple[str, str]]:
    """Fetch files from a Drive folder; returns (source_path, content) tuples."""
    service = _build_service()
    files = _list_files(service, folder_id, patterns)

    results: list[tuple[str, str]] = []
    for file in files:
        file_id = file["id"]
        file_name = file["name"]
        mime_type = file["mimeType"]
        source_path = f"gdrive://{file_id}/{file_name}"
        try:
            content = _fetch_content(service, file_id, file_name, mime_type)
        except Exception as exc:
            print(f"Error fetching Drive file {file_name} ({file_id}): {exc}")
            continue
        if content:
            results.append((source_path, content))

    return results
