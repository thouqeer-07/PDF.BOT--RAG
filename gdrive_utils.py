# gdrive_utils.py
import streamlit as st
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow, Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from pymongo import MongoClient
import io
import json
import os
from dotenv import load_dotenv

load_dotenv()

from config import (
    GOOGLE_CLIENT_SECRET,
    SCOPES,
    OAUTH_PORT,
    MONGO_URI,
)

def handle_oauth_callback():
    """Backward-compatible stub — now handled directly in get_drive_service()."""
    return get_drive_service()


def get_drive_service():
    """Handles Google OAuth and returns authorized Drive service."""
    client = MongoClient(MONGO_URI)
    db = client["pdfbot"]
    chats_col = db["users"]

    username = st.session_state.get("username")
    creds_info = None

    # Try to load credentials from session state first
    if "google_creds" in st.session_state:
        creds_info = st.session_state["google_creds"]

    # If not in session, try to load from MongoDB
    elif username:
        user_data = chats_col.find_one({"username": username})
        creds_info = user_data.get("google_creds") if user_data else None

    # If still not found, run OAuth flow and store
    if not creds_info:
        # Handle case where GOOGLE_CLIENT_SECRET is JSON string instead of a file path
        secret_value = GOOGLE_CLIENT_SECRET.strip()

        if secret_value.startswith("{"):
            temp_secret_path = "/tmp/client_secret.json"
            with open(temp_secret_path, "w") as f:
                f.write(secret_value)
            secret_path = temp_secret_path
        else:
            secret_path = secret_value  # file path

        # Run OAuth flow
        flow = InstalledAppFlow.from_client_secrets_file(secret_path, scopes=SCOPES)
        creds = flow.run_local_server(
            port=OAUTH_PORT, prompt="consent", authorization_prompt_message=""
        )

        creds_info = json.loads(creds.to_json())
        st.session_state["google_creds"] = creds_info

        # Store credentials in MongoDB for this user
        if username:
            chats_col.update_one(
                {"username": username},
                {"$set": {"google_creds": creds_info}},
                upsert=True,
            )

        st.toast("Connected to Google Drive!", icon="✅")

    creds = Credentials.from_authorized_user_info(creds_info)
    return build("drive", "v3", credentials=creds)


# -----------------------------------------------------------------------
# Drive utilities
# -----------------------------------------------------------------------

def get_or_create_user_folder(drive_service, username):
    """Get or create a folder for the user in Google Drive. Returns folder ID."""
    query = f"mimeType='application/vnd.google-apps.folder' and name='{username}' and trashed=false"
    results = drive_service.files().list(q=query, fields="files(id, name)").execute()
    folders = results.get('files', [])
    if folders:
        return folders[0]['id']

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
            return {"id": files[0]["id"], "webViewLink": files[0].get("webViewLink", "")}

    # Upload new file
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
