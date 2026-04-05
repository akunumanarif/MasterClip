import os
import re
import json
import tempfile
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaInMemoryUpload
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request


class DriveService:
    def __init__(self, token_path: str, root_folder_id: str):
        self._token_path = token_path
        with open(token_path) as f:
            token_data = json.load(f)
        creds = Credentials(
            token=token_data['token'],
            refresh_token=token_data['refresh_token'],
            token_uri=token_data['token_uri'],
            client_id=token_data['client_id'],
            client_secret=token_data['client_secret'],
            scopes=token_data['scopes'],
        )
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            token_data['token'] = creds.token
            with open(token_path, 'w') as f:
                json.dump(token_data, f, indent=2)
        service = build('drive', 'v3', credentials=creds)
        self.files = service.files()
        self.permissions = service.permissions()
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
        self.permissions.create(
            fileId=file['id'],
            body={'type': 'anyone', 'role': 'reader'},
        ).execute()
        print(f"[DriveService] Uploaded {filename} → {file['webViewLink']}")
        return file['webViewLink']

    def upload_caption(self, caption: dict, video_filename: str, folder_id: str) -> str:
        """
        Upload caption as a .txt file to Drive folder.
        Filename matches the video but with .txt extension.
        Returns shareable view URL.
        """
        txt_filename = os.path.splitext(video_filename)[0] + ".txt"
        hook = caption.get("hook", "")
        body = caption.get("caption", "")
        hashtags = " ".join(f"#{h}" for h in caption.get("hashtags", []))
        content = f"{hook}\n\n{body}\n\n{hashtags}".strip()

        media = MediaInMemoryUpload(
            content.encode("utf-8"),
            mimetype="text/plain",
            resumable=False
        )
        metadata = {"name": txt_filename, "parents": [folder_id]}
        file = self.files.create(
            body=metadata, media_body=media, fields="id,webViewLink"
        ).execute()
        self.permissions.create(
            fileId=file["id"],
            body={"type": "anyone", "role": "reader"},
        ).execute()
        print(f"[DriveService] Uploaded caption {txt_filename} → {file['webViewLink']}")
        return file["webViewLink"]
