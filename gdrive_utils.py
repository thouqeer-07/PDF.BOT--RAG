import streamlit as st

# Write client_secrets.json from Streamlit secrets if available
if hasattr(st, "secrets") and "CLIENT_SECRETS_JSON" in st.secrets:
    with open("client_secrets.json", "w") as f:
        f.write(st.secrets["CLIENT_SECRETS_JSON"])

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
import io
import os
import pickle

# If modifying these SCOPES, delete the file token.pickle.
SCOPES = ["https://www.googleapis.com/auth/drive.file"]

def get_drive_service():
    """Authenticate user via OAuth and return Drive API service."""
    creds = None
    # The file token.pickle stores the user's access and refresh tokens.
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)
    # If there are no valid credentials, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "client_secrets.json", SCOPES)
            # Headless authentication: print URL and prompt for code
            auth_url, _ = flow.authorization_url(prompt='consent')
            print(f"Please go to this URL and authorize access: {auth_url}")
            code = input("Enter the authorization code here: ")
            creds = flow.fetch_token(code=code)
        # Save the credentials for the next run
        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)
    return build("drive", "v3", credentials=creds)

def upload_pdf_to_drive(service, file_name, file_bytes, folder_id=None):
    """Upload PDF bytes to Google Drive using OAuth user credentials."""
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
    """Download PDF bytes from Google Drive using OAuth user credentials."""
    request = service.files().get_media(fileId=file_id)
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    buf.seek(0)
    return buf.read()