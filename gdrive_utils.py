# gdrive_utils.py
import streamlit as st
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io
import json
import os
from google_auth_oauthlib.flow import Flow
from pymongo import MongoClient
from dotenv import load_dotenv
def handle_oauth_callback():
    """Backward-compatible stub — now handled directly in get_drive_service()."""
    return get_drive_service()

load_dotenv()

from config import GOOGLE_CLIENT_SECRET, REDIRECT_URI
client_config = json.loads(st.secrets["GOOGLE_CLIENT_SECRET_FILE"])

from config import SCOPES
flow = Flow.from_client_config(client_config, scopes=SCOPES)


# Temporary port for OAuth, must be different from Streamlit's (8501)
from config import OAUTH_PORT

def get_drive_service():
    """Handles Google OAuth, persists code + creds in MongoDB, returns Drive service."""
    from config import MONGO_URI, SCOPES, REDIRECT_URI
    client = MongoClient(MONGO_URI)
    db = client["pdfbot"]
    users_col = db["users"]

    username = st.session_state.get("username")
    user_data = users_col.find_one({"username": username}) if username else None

    creds_info = None

    # 1️⃣ Check existing stored credentials
    if user_data and user_data.get("google_creds"):
        creds_info = user_data["google_creds"]

    # 2️⃣ If credentials exist, use them directly
    if creds_info:
        creds = Credentials.from_authorized_user_info(creds_info)
        if creds and creds.valid:
            return build("drive", "v3", credentials=creds)

    # 3️⃣ Otherwise handle OAuth redirect
    redirect_uri = REDIRECT_URI
    query_params = st.query_params
    code = query_params.get("code")

    # Persist code in MongoDB so we can recover it after rerun
    if code and username:
        users_col.update_one(
            {"username": username},
            {"$set": {"google_oauth_code": code}},
            upsert=True
        )
    elif not code and user_data and user_data.get("google_oauth_code"):
        code = user_data["google_oauth_code"]

    flow = Flow.from_client_config(client_config, scopes=SCOPES, redirect_uri=redirect_uri)

    if not code:
        # Start OAuth process
        auth_url, _ = flow.authorization_url(prompt="consent")
        st.markdown(f"[Connect to Google Drive]({auth_url})")
        st.stop()

    # 4️⃣ Fetch token from code
    try:
        flow.fetch_token(code=code)
        creds = flow.credentials
        creds_info = json.loads(creds.to_json())

        oauth_data = {
            "access_token": creds_info.get("token"),
            "refresh_token": creds_info.get("refresh_token"),
            "token_uri": creds_info.get("token_uri"),
            "client_id": creds_info.get("client_id"),
            "client_secret": creds_info.get("client_secret"),
            "scopes": creds_info.get("scopes"),
            "raw": creds_info
        }

        # 5️⃣ Save all OAuth info in MongoDB
        users_col.update_one(
            {"username": username},
            {"$set": {
                "google_creds": creds_info,
                "google_oauth_data": oauth_data,
                "google_oauth_code": code
            }},
            upsert=True
        )

        # 6️⃣ Save to Streamlit session
        st.session_state["google_creds"] = creds_info
        st.session_state["google_oauth_data"] = oauth_data
        st.session_state["drive_connected"] = True

        st.toast("Connected to Google Drive!", icon="✅")
        return build("drive", "v3", credentials=creds)

    except Exception as e:
        st.error(f"Google OAuth failed: {e}")
        auth_url, _ = flow.authorization_url(prompt="consent")
        st.markdown(f"[Retry Google Connection]({auth_url})")
        st.stop()


    # ...existing code...
def get_or_create_user_folder(drive_service, username):
    """Get or create a folder for the user in Google Drive. Returns folder ID."""
    # Search for folder
    query = f"mimeType='application/vnd.google-apps.folder' and name='{username}' and trashed=false"
    results = drive_service.files().list(q=query, fields="files(id, name)").execute()
    folders = results.get('files', [])
    if folders:
        return folders[0]['id']
    # Create folder if not found
    file_metadata = {
        'name': username,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    folder = drive_service.files().create(body=file_metadata, fields='id').execute()
    return folder['id']

def upload_pdf_to_drive(drive_service, pdf_name, pdf_bytes, username=None):
    """Uploads PDF to the user's folder in Google Drive."""
    folder_id = None
    if username:
        folder_id = get_or_create_user_folder(drive_service, username)
        # Check for existing file in user's folder
        query = f"name='{pdf_name}' and '{folder_id}' in parents and trashed=false"
        results = drive_service.files().list(q=query, fields="files(id, name, webViewLink)").execute()
        files = results.get('files', [])
        if files:
            # Return the existing file info
            return {"id": files[0]["id"], "webViewLink": files[0].get("webViewLink", "")}
    # If not found, upload new file
    media = MediaIoBaseUpload(io.BytesIO(pdf_bytes), mimetype="application/pdf")
    file_metadata = {"name": pdf_name}
    if folder_id:
        file_metadata["parents"] = [folder_id]
    uploaded = (
        drive_service.files()
        .create(body=file_metadata, media_body=media, fields="id, webViewLink")
        .execute()
    )
    return uploaded



def list_user_files(drive_service, username):
    """List all files in the user's folder on Google Drive."""
    folder_id = get_or_create_user_folder(drive_service, username)
    query = f"'{folder_id}' in parents and trashed=false"
    results = drive_service.files().list(q=query, fields="files(id, name)").execute()
    return results.get('files', [])

def delete_pdf_from_drive(drive_service, file_id, username=None):
    """Delete PDF from the user's folder in Google Drive."""
    if username:
        # Optionally verify file is in user's folder
        user_files = list_user_files(drive_service, username)
        if not any(f['id'] == file_id for f in user_files):
            raise Exception("File not found in user's folder.")
    drive_service.files().delete(fileId=file_id).execute()

def download_pdf_from_drive(drive_service, file_id, username=None):
    """Downloads PDF from the user's folder in Google Drive."""
    if username:
        user_files = list_user_files(drive_service, username)
        if not any(f['id'] == file_id for f in user_files):
            raise Exception("File not found in user's folder.")
    request = drive_service.files().get_media(fileId=file_id)
    return request.execute()
