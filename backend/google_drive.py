import os
import io
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle

class GoogleDriveStorage:
    def __init__(self, folder_id=None):
        self.folder_id = folder_id or '1Xj0wc8Hhtbu96pgp-65GmgW6jZ1Zo_7v'
        self.creds = None
        self.service = None
        self.authenticate()

    def authenticate(self):
        """Authenticate with Google Drive API"""
        SCOPES = ['https://www.googleapis.com/auth/drive.file']

        creds = None
        # The file token.pickle stores the user's access and refresh tokens
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)

        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                # Find the credentials file
                creds_file = None
                for file in os.listdir('.'):
                    if file.endswith('.json') and 'client_secret' in file:
                        creds_file = file
                        break

                if not creds_file:
                    print("Google Drive credentials file not found. Please ensure client_secret_*.json is in the root directory.")
                    return False

                flow = InstalledAppFlow.from_client_secrets_file(creds_file, SCOPES)
                creds = flow.run_local_server(port=0)

            # Save the credentials for the next run
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)

        try:
            self.service = build('drive', 'v3', credentials=creds)
            return True
        except Exception as e:
            print(f"Google Drive authentication failed: {e}")
            return False

    def upload_file(self, file_data, filename, mimetype='application/octet-stream'):
        """Upload a file to Google Drive"""
        if not self.service:
            raise Exception("Google Drive not authenticated")

        try:
            file_metadata = {
                'name': filename,
                'parents': [self.folder_id]
            }

            media = MediaIoBaseUpload(io.BytesIO(file_data), mimetype=mimetype, resumable=True)

            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,webViewLink,webContentLink'
            ).execute()

            return {
                'file_id': file.get('id'),
                'web_view_link': file.get('webViewLink'),
                'web_content_link': file.get('webContentLink')
            }
        except Exception as e:
            raise Exception(f"Failed to upload file to Google Drive: {str(e)}")

    def download_file(self, file_id):
        """Download a file from Google Drive"""
        if not self.service:
            raise Exception("Google Drive not authenticated")

        try:
            request = self.service.files().get_media(fileId=file_id)
            file_data = io.BytesIO()
            downloader = MediaIoBaseDownload(file_data, request)

            done = False
            while done is False:
                status, done = downloader.next_chunk()

            return file_data.getvalue()
        except Exception as e:
            raise Exception(f"Failed to download file from Google Drive: {str(e)}")

    def delete_file(self, file_id):
        """Delete a file from Google Drive"""
        if not self.service:
            raise Exception("Google Drive not authenticated")

        try:
            self.service.files().delete(fileId=file_id).execute()
            return True
        except Exception as e:
            raise Exception(f"Failed to delete file from Google Drive: {str(e)}")

    def get_file_info(self, file_id):
        """Get file information from Google Drive"""
        if not self.service:
            raise Exception("Google Drive not authenticated")

        try:
            file = self.service.files().get(fileId=file_id, fields='id,name,mimeType,size,createdTime,modifiedTime,webViewLink,webContentLink').execute()
            return file
        except Exception as e:
            raise Exception(f"Failed to get file info from Google Drive: {str(e)}")

# Global instance
google_drive = GoogleDriveStorage()
