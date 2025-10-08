from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
import io

def get_drive_service(credentials_dict):
    """Return authenticated Google Drive API service."""
    creds = service_account.Credentials.from_service_account_info(
        credentials_dict,
        scopes=["https://www.googleapis.com/auth/drive"]
    )
    return build("drive", "v3", credentials=creds)

def upload_pdf_to_drive(service, file_name, file_bytes, folder_id=None):
    """Upload PDF bytes to Google Drive."""

    metadata = {"name": file_name}
    if folder_id:
        metadata["parents"] = [folder_id]

    media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype="application/pdf")
    try:
        file = service.files().create(
            body=metadata,
            media_body=media,
            fields="id, webViewLink"
        ).execute()
        return {"id": file.get("id"), "webViewLink": file.get("webViewLink")}
    except Exception as e:
        import traceback
        print("[ERROR] Google Drive upload failed:")
        print(traceback.format_exc())
        raise

def download_pdf_from_drive(service, file_id):
    """Download PDF bytes from Google Drive."""
    request = service.files().get_media(fileId=file_id)
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    buf.seek(0)
    return buf.read()