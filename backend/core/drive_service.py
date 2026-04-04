import os
import re
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.service_account import Credentials

SCOPES = ['https://www.googleapis.com/auth/drive']


class DriveService:
    def __init__(self, credentials_path: str, root_folder_id: str):
        creds = Credentials.from_service_account_file(credentials_path, scopes=SCOPES)
        service = build('drive', 'v3', credentials=creds)
        self.files = service.files()
        self.root_folder_id = root_folder_id

    def _sanitize_folder_name(self, name: str) -> str:
        return re.sub(r'[\\/:*?"<>|]', '_', name).strip() or "Untitled"

    def get_or_create_folder(self, folder_name: str) -> str:
        """Get existing folder by name under root, or create it. Returns folder ID."""
        safe_name = self._sanitize_folder_name(folder_name)
        query = (
            f"name='{safe_name}' and "
            f"'{self.root_folder_id}' in parents and "
            f"mimeType='application/vnd.google-apps.folder' and trashed=false"
        )
        results = self.files.list(q=query, fields="files(id, name)").execute()
        existing = results.get('files', [])
        if existing:
            return existing[0]['id']
        metadata = {
            'name': safe_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [self.root_folder_id],
        }
        folder = self.files.create(body=metadata, fields='id').execute()
        print(f"[DriveService] Created folder: {safe_name}")
        return folder['id']

    def upload_clip(self, local_path: str, filename: str, folder_id: str) -> str:
        """Upload a clip to Drive folder. Returns shareable view URL."""
        media = MediaFileUpload(local_path, mimetype='video/mp4', resumable=True)
        metadata = {'name': filename, 'parents': [folder_id]}
        file = self.files.create(
            body=metadata, media_body=media, fields='id,webViewLink'
        ).execute()
        self.files.permissions().create(
            fileId=file['id'],
            body={'type': 'anyone', 'role': 'reader'},
        ).execute()
        print(f"[DriveService] Uploaded {filename} → {file['webViewLink']}")
        return file['webViewLink']
