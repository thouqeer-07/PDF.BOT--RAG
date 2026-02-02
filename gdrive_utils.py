
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

    """Handles Google OAuth (Streamlit + MongoDB compatible) and returns authorized Drive service."""
    from pymongo import MongoClient
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import Flow, InstalledAppFlow
    from googleapiclient.discovery import build
    import json, urllib.parse, os

    from config import MONGO_URI, SCOPES, REDIRECT_URI, OAUTH_PORT
    client = MongoClient(MONGO_URI)
    db = client["pdfbot"]
    chats_col = db["users"]

    username = st.session_state.get("username") or st.session_state.get("persist_username")
    # Try to restore username from OAuth 'state' param if missing
    if not username:
        query_params = st.query_params
        state_username = query_params.get("state")
        if state_username:
            st.session_state["username"] = state_username
            username = state_username
    if not username:
        st.error("Please log in before connecting to Google Drive.")
        st.stop()

    # --- Load client config from secrets ---
    client_config = json.loads(st.secrets["GOOGLE_CLIENT_SECRET_FILE"])

    # --- Try to load creds from session or MongoDB ---
    creds_info = st.session_state.get("google_creds")
    if not creds_info:
        user_data = chats_col.find_one({"username": username})
        creds_info = user_data.get("google_creds") if user_data else None

    # --- If credentials exist and valid, return Drive service immediately ---
    if creds_info:
        try:
            creds = Credentials.from_authorized_user_info(creds_info)
            if creds and creds.valid:
                st.session_state["google_creds"] = creds_info
                st.session_state["drive_connected"] = True
                print(f"[DEBUG] Returning cached Drive service for {username}")
                # No rerun needed for cached credentials
                return build("drive", "v3", credentials=creds)

            # Try refresh if expired
            if creds.expired and creds.refresh_token:
                from google.auth.transport.requests import Request
                creds.refresh(Request())
                refreshed = json.loads(creds.to_json())
                st.session_state["google_creds"] = refreshed
                chats_col.update_one(
                    {"username": username},
                    {"$set": {"google_creds": refreshed}},
                    upsert=True
                )
                print(f"[DEBUG] Token refreshed for {username}")
                # No rerun needed for refreshed credentials
                return build("drive", "v3", credentials=creds)
        except Exception as e:
            print(f"[DEBUG] Invalid creds for {username}: {e}")
            st.warning("Stored Google credentials invalid or expired. Please reconnect.")

    # --- Handle OAuth (Cloud mode) ---
    if REDIRECT_URI and not REDIRECT_URI.startswith("http://localhost"):
        flow = Flow.from_client_config(client_config, scopes=SCOPES, redirect_uri=REDIRECT_URI)

        # --- Check for OAuth code in query params ---
        query_params = st.query_params
        code = query_params.get("code")
        state = query_params.get("state")


        # --- Save OAuth code instantly to Mongo if present ---
        if code:
            print(f"[DEBUG] OAuth code received for user {username}: {code[:10]}...")
            chats_col.update_one(
                {"username": username},
                {"$set": {"google_oauth_code": code}},
                upsert=True
            )
            st.session_state["google_oauth_code"] = code
            # Remove ?code=... from URL to avoid rerun loop
            st.query_params

        # --- Reuse code from Mongo or session if exists ---
        code = st.session_state.get("google_oauth_code") or \
               (chats_col.find_one({"username": username}) or {}).get("google_oauth_code")

        if not code:
            # No code found — show Connect button
            print(f"[DEBUG] No OAuth code found for {username}.")
            auth_url, _ = flow.authorization_url(prompt="consent", state=username)
            st.markdown(f"### 🔗 [Connect to Google Drive]({auth_url})")
            st.stop()
            

        # --- Exchange code for token ---
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

            # Save creds and clear old code
            chats_col.update_one(
                {"username": username},
                {"$set": {
                    "google_creds": creds_info,
                    "google_oauth_data": oauth_data
                }, "$unset": {"google_oauth_code": ""}},
                upsert=True
            )

            # Update Streamlit session
            st.session_state["google_creds"] = creds_info
            st.session_state["google_oauth_data"] = oauth_data
            st.session_state["drive_connected"] = True

            #st.success("✅ Google Drive connected successfully!")
            st.success("Go Back to the main app and refresh to continue.")
            print(f"[DEBUG] OAuth success for {username}")
            st.rerun()
            return build("drive", "v3", credentials=creds)
        

        except Exception as e:
            print(f"[DEBUG] OAuth error for {username}: {e}")
            st.error(f"Google OAuth failed: {e}")
            auth_url, _ = flow.authorization_url(prompt="consent")
            st.markdown(f"[Retry Google Connection]({auth_url})")
            st.stop()

    # --- Handle local development OAuth ---
    else:
        flow = InstalledAppFlow.from_client_config(client_config, scopes=SCOPES)
        creds = flow.run_local_server(port=int(OAUTH_PORT), prompt="consent", authorization_prompt_message="")
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

        st.session_state["google_creds"] = creds_info
        st.session_state["google_oauth_data"] = oauth_data

        chats_col.update_one(
            {"username": username},
            {"$set": {"google_creds": creds_info, "google_oauth_data": oauth_data}},
            upsert=True
        )

        st.success("✅ Google Drive connected locally!")
        st.success("Go Back to the main app to continue.")
        print(f"[DEBUG] Local OAuth success for {username}")
        st.rerun()
        return build("drive", "v3", credentials=creds)



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
