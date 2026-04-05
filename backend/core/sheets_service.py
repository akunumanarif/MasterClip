import os
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# Column mapping — matches spreadsheet layout:
# A: Youtube video url
# B: is downloaded
# C: is processing
# D: is processed
# E: drive_url       ← Google Drive URL of the rendered clip
# F: instagram_url   ← Instagram post URL after upload (empty = not yet uploaded)
COL_URL = "A"
COL_DOWNLOADED = "B"
COL_PROCESSING = "C"
COL_PROCESSED = "D"
COL_DRIVE_URL = "E"
COL_INSTAGRAM_URL = "F"


class SheetsService:
    def __init__(self, credentials_path: str, spreadsheet_id: str):
        creds = Credentials.from_service_account_file(credentials_path, scopes=SCOPES)
        service = build('sheets', 'v4', credentials=creds)
        self.sheet = service.spreadsheets()
        self.spreadsheet_id = spreadsheet_id

    def get_unprocessed_videos(self) -> list:
        """Return rows where is_processing=FALSE and is_processed=FALSE."""
        result = self.sheet.values().get(
            spreadsheetId=self.spreadsheet_id,
            range="A2:F"
        ).execute()
        rows = result.get('values', [])

        unprocessed = []
        for i, row in enumerate(rows):
            url = row[0].strip() if len(row) > 0 else ""
            is_processing = row[2].strip().upper() if len(row) > 2 else ""
            is_processed = row[3].strip().upper() if len(row) > 3 else ""
            if url and is_processing != "TRUE" and is_processed != "TRUE":
                unprocessed.append({
                    "row_index": i + 2,
                    "url": url,
                })
        return unprocessed

    def get_pending_instagram_upload(self) -> list:
        """
        Return rows where is_processed=TRUE, drive_url is set (col E),
        but instagram_url is empty (col F) — ready for Instagram upload.
        """
        result = self.sheet.values().get(
            spreadsheetId=self.spreadsheet_id,
            range="A2:F"
        ).execute()
        rows = result.get('values', [])

        pending = []
        for i, row in enumerate(rows):
            url = row[0].strip() if len(row) > 0 else ""
            is_processed = row[3].strip().upper() if len(row) > 3 else ""
            drive_url = row[4].strip() if len(row) > 4 else ""
            instagram_url = row[5].strip() if len(row) > 5 else ""
            if url and is_processed == "TRUE" and drive_url and not instagram_url:
                pending.append({
                    "row_index": i + 2,
                    "url": url,
                    "drive_url": drive_url,
                })
        return pending

    def mark_downloaded(self, row_index: int):
        self._update_cell(f"{COL_DOWNLOADED}{row_index}", "TRUE")

    def mark_processing(self, row_index: int):
        self._update_cell(f"{COL_PROCESSING}{row_index}", "TRUE")

    def unmark_processing(self, row_index: int):
        self._update_cell(f"{COL_PROCESSING}{row_index}", "FALSE")

    def mark_processed(self, row_index: int):
        self._update_cell(f"{COL_PROCESSED}{row_index}", "TRUE")

    def store_drive_url(self, row_index: int, drive_url: str):
        """Store the Google Drive clip URL in col E."""
        self._update_cell(f"{COL_DRIVE_URL}{row_index}", drive_url)

    def store_instagram_url(self, row_index: int, instagram_url: str):
        """Store the Instagram post URL in col F (idempotency marker)."""
        self._update_cell(f"{COL_INSTAGRAM_URL}{row_index}", instagram_url)

    # Keep for backward compatibility
    def mark_uploaded_instagram(self, row_index: int):
        self._update_cell(f"{COL_INSTAGRAM_URL}{row_index}", "TRUE")

    def _update_cell(self, cell_range: str, value: str):
        self.sheet.values().update(
            spreadsheetId=self.spreadsheet_id,
            range=cell_range,
            valueInputOption="RAW",
            body={"values": [[value]]}
        ).execute()
