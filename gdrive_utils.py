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
    """Handles Google OAuth and returns authorized Drive service."""
    # Import MongoDB client
    from pymongo import MongoClient
    from config import MONGO_URI
    client = MongoClient(MONGO_URI)
    db = client["pdfbot"]
    chats_col = db["users"]

    username = st.session_state.get("username")
    creds_info = None

    # Try to load credentials and code from session state first
    if "google_creds" in st.session_state:
        creds_info = st.session_state["google_creds"]
        oauth_code = st.session_state.get("google_oauth_code")
    # If not in session, try to load from MongoDB
    elif username:
        user_data = chats_col.find_one({"username": username})
        creds_info = user_data.get("google_creds") if user_data else None
        oauth_code = user_data.get("google_oauth_code") if user_data else None

    # If still not found, run OAuth flow and store
    if not creds_info:
        import urllib.parse
        redirect_uri = REDIRECT_URI
        query_params = st.query_params
        code = query_params.get("code", [None])[0] or oauth_code

        if redirect_uri and not redirect_uri.startswith("http://localhost"):
            # Cloud/web flow
            flow = Flow.from_client_config(client_config, scopes=SCOPES, redirect_uri=redirect_uri)
            if code:
                flow.fetch_token(code=code)
                creds = flow.credentials

                # Save immediately to session and MongoDB
                creds_info = json.loads(creds.to_json())
                st.session_state["google_creds"] = creds_info
                st.session_state["google_oauth_code"] = code
                if username:
                    chats_col.update_one(
                        {"username": username},
                        {"$set": {"google_creds": creds_info, "google_oauth_code": code}},
                        upsert=True
                    )

                # Clear the code from URL and reload app
                st.query_params
                st.rerun()
                st.toast("Connected to Google Drive!", icon="✅")
            else:
                auth_url, _ = flow.authorization_url(prompt="consent")
                st.markdown(f"[Connect to Google Drive]({auth_url})")
                st.stop()
        else:
            # Local development
            flow = InstalledAppFlow.from_client_config(client_config, scopes=SCOPES)
            creds = flow.run_local_server(port=int(OAUTH_PORT), prompt="consent", authorization_prompt_message="")

            # Save immediately after OAuth
            creds_info = json.loads(creds.to_json())
            st.session_state["google_creds"] = creds_info
            if username:
                chats_col.update_one(
                    {"username": username},
                    {"$set": {"google_creds": creds_info}},
                    upsert=True
                )
            st.toast("Connected to Google Drive!", icon="✅")
            st.success("Google Drive authentication successful. Please login again to continue.")
            st.session_state.clear()
            st.session_state["auth_interface"] = "login"
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
