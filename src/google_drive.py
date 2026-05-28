import streamlit as st
import io
import json
from typing import Any, Dict, List
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

SCOPES = ["https://www.googleapis.com/auth/drive"]


def create_drive_service(credentials_path: str):
    credentials = service_account.Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]),
        scopes=["https://www.googleapis.com/auth/drive"]
    )
    return build("drive", "v3", credentials=credentials, cache_discovery=False)


def _escape_query_value(value: str) -> str:
    return value.replace("'", "\\'")


def list_folder_files(service, folder_id: str) -> List[Dict[str, Any]]:
    query = f"'{folder_id}' in parents and trashed = false"
    fields = "nextPageToken, files(id,name,mimeType,parents)"
    files: List[Dict[str, Any]] = []
    page_token = None

    while True:
        response = service.files().list(
            q=query,
            fields=fields,
            pageToken=page_token,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        ).execute()
        files.extend(response.get("files", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return files


def find_files_by_name(service, folder_id: str, name: str) -> List[Dict[str, Any]]:
    escaped_name = _escape_query_value(name)
    query = f"'{folder_id}' in parents and trashed = false and name = '{escaped_name}'"
    response = service.files().list(
        q=query,
        fields="files(id,name,mimeType,parents)",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
    ).execute()
    return response.get("files", [])


def get_file_metadata(service, file_id: str, fields: str = "id,name,mimeType,driveId,parents") -> Dict[str, Any]:
    return service.files().get(
        fileId=file_id,
        supportsAllDrives=True,
        fields=fields,
    ).execute()


def search_files_by_name_global(service, name: str) -> List[Dict[str, Any]]:
    escaped_name = _escape_query_value(name)
    query = f"name = '{escaped_name}' and trashed = false"
    files: List[Dict[str, Any]] = []
    page_token = None
    fields = "nextPageToken, files(id,name,mimeType,parents,driveId)"

    while True:
        response = service.files().list(
            q=query,
            fields=fields,
            pageToken=page_token,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            corpora="allDrives",
        ).execute()
        files.extend(response.get("files", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return files


def get_folder_name(service, folder_id: str) -> str:
    try:
        metadata = get_file_metadata(service, folder_id, fields="id,name,mimeType,driveId,parents")
        return metadata.get("name", "<unknown>")
    except Exception:
        return "<unknown>"


def download_file_bytes(service, file_id: str) -> bytes:
    request = service.files().get_media(fileId=file_id, supportsAllDrives=True)
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)
    done = False

    while not done:
        _, done = downloader.next_chunk()

    buffer.seek(0)
    return buffer.read()


def download_json_file(service, file_id: str) -> Any:
    raw = download_file_bytes(service, file_id)
    return json.loads(raw.decode("utf-8"))


def upload_file(service, folder_id: str, name: str, content: bytes, mime_type: str) -> Dict[str, Any]:
    """
    Upload a file to Google Drive.

    If a file with the same name already exists in the target folder, update the
    most recently modified matching file instead of creating duplicates.
    """
    media = MediaIoBaseUpload(io.BytesIO(content), mimetype=mime_type, resumable=True)

    query = (
        f"'{folder_id}' in parents and "
        f"name = '{name}' and "
        "trashed = false"
    )

    existing = service.files().list(
        q=query,
        fields="files(id, name, modifiedTime)",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
    ).execute().get("files", [])

    if existing:
        existing.sort(key=lambda f: f.get("modifiedTime", ""), reverse=True)
        file_id = existing[0]["id"]

        print(f"Updating existing Google Drive file: {name} ({file_id})")

        updated_file = service.files().update(
            fileId=file_id,
            media_body=media,
            fields="id, name, webViewLink, webContentLink",
            supportsAllDrives=True,
        ).execute()

        return updated_file

    print(f"Creating new Google Drive file: {name}")

    file_metadata = {
        "name": name,
        "parents": [folder_id],
    }

    uploaded_file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id, name, webViewLink, webContentLink",
        supportsAllDrives=True,
    ).execute()

    return uploaded_file



def update_file_content(service, file_id: str, content: bytes, mime_type: str) -> Dict[str, Any]:
    """
    Update the contents of an existing Google Drive file.
    Used for status.json and any other file that should be updated in place.
    """
    media = MediaIoBaseUpload(io.BytesIO(content), mimetype=mime_type, resumable=True)

    updated_file = service.files().update(
        fileId=file_id,
        media_body=media,
        fields="id, name, webViewLink, webContentLink",
        supportsAllDrives=True,
    ).execute()

    return updated_file


def create_or_update_json_file(service, folder_id: str, name: str, data: Any) -> Dict[str, Any]:
    existing_files = find_files_by_name(service, folder_id, name)
    content = json.dumps(data, indent=2).encode("utf-8")

    if existing_files:
        return update_file_content(service, existing_files[0]["id"], content, "application/json")

    return upload_file(service, folder_id, name, content, "application/json")


def trash_files_by_name(service, folder_id: str, name: str, keep_file_id: str | None = None) -> int:
    """
    Move files with a matching name in a Google Drive folder to Trash.

    Used to clean old generic files such as vergo_report.pdf after the generator
    starts saving descriptive report filenames.
    """
    safe_name = name.replace("'", "\\'")

    query = (
        f"'{folder_id}' in parents and "
        f"name = '{safe_name}' and "
        "trashed = false"
    )

    results = service.files().list(
        q=query,
        fields="files(id, name, modifiedTime)",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
    ).execute()

    files = results.get("files", [])
    trashed_count = 0

    for file in files:
        file_id = file.get("id")

        if keep_file_id and file_id == keep_file_id:
            continue

        print(f"Trashing old Google Drive file: {file.get('name')} ({file_id})")

        service.files().update(
            fileId=file_id,
            body={"trashed": True},
            supportsAllDrives=True,
        ).execute()

        trashed_count += 1

    return trashed_count

