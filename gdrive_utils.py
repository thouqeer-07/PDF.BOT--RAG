import streamlit as st
from google_auth_oauthlib.flow import Flow
import pickle
import os
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import io

SCOPES = ["https://www.googleapis.com/auth/drive.file"]

def get_drive_service():
    creds = None

    # Load saved token if available
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)

    # If no valid credentials, start OAuth flow
    if not creds or not creds.valid:
        # ✅ FIX: query_params is a dict, not callable
        redirect_uri = st.query_params.get("redirect_uri", [None])[0] if hasattr(st, "query_params") else None

        flow = Flow.from_client_secrets_file(
            "client_secrets.json",
            scopes=SCOPES,
            redirect_uri=redirect_uri or "http://localhost:8501/"
        )

        auth_url, _ = flow.authorization_url(prompt="consent")
        st.markdown(f"[Authorize Google Drive access]({auth_url})")

        # Manual code input after granting access
        code = st.text_input("Paste the authorization code here:")
        if code:
            flow.fetch_token(code=code)
            creds = flow.credentials
            with open("token.pickle", "wb") as token:
                pickle.dump(creds, token)

    return creds



def upload_pdf_to_drive(drive_service, pdf_name, pdf_bytes):
    """Uploads a PDF from bytes to Google Drive and returns file info."""
    from googleapiclient.http import MediaIoBaseUpload
    file_metadata = {"name": pdf_name, "mimeType": "application/pdf"}
    media = MediaIoBaseUpload(io.BytesIO(pdf_bytes), mimetype="application/pdf")
    file = drive_service.files().create(body=file_metadata, media_body=media, fields="id,webViewLink").execute()
    return {"id": file.get("id"), "webViewLink": file.get("webViewLink")}


def download_pdf_from_drive(file_id, destination_path, drive_service=None):
    """Downloads a PDF file from Google Drive by file ID."""
    if drive_service is None:
        creds = get_drive_service()
        drive_service = build("drive", "v3", credentials=creds)

    request = drive_service.files().get_media(fileId=file_id)
    fh = io.FileIO(destination_path, "wb")
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    fh.close()
    return destination_path
