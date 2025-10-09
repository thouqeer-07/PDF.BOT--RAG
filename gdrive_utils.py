# gdrive_utils.py
import streamlit as st
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io
import json

def get_drive_service():
    """Handle Google OAuth and return Drive service."""
    # Step 1: If user not connected, show the Connect button
    if "google_creds" not in st.session_state:
        client_config = {
            "web": {
                "client_id": st.secrets["GOOGLE_CLIENT_ID"],
                "client_secret": st.secrets["GOOGLE_CLIENT_SECRET"],
                "redirect_uris": [st.secrets["REDIRECT_URI"]],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        }
        flow = Flow.from_client_config(
            client_config,
            scopes=["https://www.googleapis.com/auth/drive.file"],
            redirect_uri=st.secrets["REDIRECT_URI"],
        )

        auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline")
        st.markdown(f"[🔑 Connect Google Drive]({auth_url})")
        st.stop()

    # Step 2: Use saved credentials
    creds_info = st.session_state["google_creds"]
    creds = Credentials.from_authorized_user_info(creds_info)
    return build("drive", "v3", credentials=creds)


def handle_oauth_callback():
    """Handles OAuth callback (after consent screen)."""
    if "code" in st.query_params:
        code = st.query_params["code"]
        client_config = {
            "web": {
                "client_id": st.secrets["GOOGLE_CLIENT_ID"],
                "client_secret": st.secrets["GOOGLE_CLIENT_SECRET"],
                "redirect_uris": [st.secrets["REDIRECT_URI"]],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        }
        flow = Flow.from_client_config(
            client_config,
            scopes=["https://www.googleapis.com/auth/drive.file"],
            redirect_uri=st.secrets["REDIRECT_URI"],
        )
        flow.fetch_token(code=code)
        creds = flow.credentials
        st.session_state["google_creds"] = json.loads(creds.to_json())
        st.success("✅ Connected to Google Drive!")
        st.rerun()


def upload_pdf_to_drive(drive_service, pdf_name, pdf_bytes):
    """Uploads PDF bytes to Drive."""
    media = MediaIoBaseUpload(io.BytesIO(pdf_bytes), mimetype="application/pdf")
    file_metadata = {"name": pdf_name}
    uploaded = (
        drive_service.files()
        .create(body=file_metadata, media_body=media, fields="id, webViewLink")
        .execute()
    )
    return uploaded


def download_pdf_from_drive(drive_service, file_id):
    """Downloads PDF from Drive and returns bytes."""
    request = drive_service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseUpload(fh, mimetype="application/pdf")
    request.execute()
    file = drive_service.files().get_media(fileId=file_id).execute()
    return file
