import os
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# Column mapping — matches spreadsheet layout:
# A: Youtube video url
# B: is downloaded
# C: is processing
# D: is processed
# E: upload instagram
COL_URL = "A"
COL_DOWNLOADED = "B"
COL_PROCESSING = "C"
COL_PROCESSED = "D"
COL_UPLOADED_INSTAGRAM = "E"


class SheetsService:
    def __init__(self, credentials_path: str, spreadsheet_id: str):
        creds = Credentials.from_service_account_file(credentials_path, scopes=SCOPES)
        service = build('sheets', 'v4', credentials=creds)
        self.sheet = service.spreadsheets()
        self.spreadsheet_id = spreadsheet_id

    def get_unprocessed_videos(self) -> list:
        """Return rows where is processing = FALSE and is processed = FALSE."""
        result = self.sheet.values().get(
            spreadsheetId=self.spreadsheet_id,
            range="A2:E"
        ).execute()
        rows = result.get('values', [])

        unprocessed = []
        for i, row in enumerate(rows):
            url = row[0].strip() if len(row) > 0 else ""
            is_processing = row[2].strip().upper() if len(row) > 2 else ""
            is_processed = row[3].strip().upper() if len(row) > 3 else ""
            if url and is_processing != "TRUE" and is_processed != "TRUE":
                unprocessed.append({
                    "row_index": i + 2,  # +1 for 1-indexed, +1 for header row
                    "url": url,
                })
        return unprocessed

    def get_processed_not_uploaded(self) -> list:
        """Return rows where is processed = TRUE but uploaded on instagram is not TRUE."""
        result = self.sheet.values().get(
            spreadsheetId=self.spreadsheet_id,
            range="A2:E"
        ).execute()
        rows = result.get('values', [])

        pending_upload = []
        for i, row in enumerate(rows):
            url = row[0].strip() if len(row) > 0 else ""
            is_processed = row[3].strip().upper() if len(row) > 3 else ""
            uploaded = row[4].strip().upper() if len(row) > 4 else ""
            if url and is_processed == "TRUE" and uploaded != "TRUE":
                pending_upload.append({
                    "row_index": i + 2,
                    "url": url,
                })
        return pending_upload

    def mark_downloaded(self, row_index: int):
        self._update_cell(f"{COL_DOWNLOADED}{row_index}", "TRUE")

    def mark_processing(self, row_index: int):
        self._update_cell(f"{COL_PROCESSING}{row_index}", "TRUE")

    def unmark_processing(self, row_index: int):
        self._update_cell(f"{COL_PROCESSING}{row_index}", "FALSE")

    def mark_processed(self, row_index: int):
        self._update_cell(f"{COL_PROCESSED}{row_index}", "TRUE")

    def mark_uploaded_instagram(self, row_index: int):
        self._update_cell(f"{COL_UPLOADED_INSTAGRAM}{row_index}", "TRUE")

    def _update_cell(self, cell_range: str, value: str):
        self.sheet.values().update(
            spreadsheetId=self.spreadsheet_id,
            range=cell_range,
            valueInputOption="RAW",
            body={"values": [[value]]}
        ).execute()
