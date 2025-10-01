#!/usr/bin/env python3
"""
Sync Obsidian Vault notes to Google Drive using checksums and Google Drive API
Usage: python push2Google.py [--init] [--setup]

Requirements: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
"""

import os
import hashlib
import json
import argparse
import pickle
from pathlib import Path
from datetime import datetime

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False

# Configuration
# googleSync is in Documents, Obsidian Vault is also in Documents (sibling folder)
VAULT_PATH = Path(__file__).parent.parent / "Obsidian Vault"
CHECKSUM_FILE = Path(__file__).parent / ".checksums.json"
TOKEN_FILE = Path(__file__).parent / ".google_token.pickle"
CREDENTIALS_FILE = Path(__file__).parent / "credentials.json"

# Google Drive folder ID from your URL
DRIVE_FOLDER_ID = "1rtokeqgAen02UyJDbPtBVCyczk5ssqhG"

# Google Drive API scopes
SCOPES = ['https://www.googleapis.com/auth/drive']

def calculate_checksum(file_path):
    """Calculate SHA256 checksum of a file"""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha256.update(chunk)
    return sha256.hexdigest()

def load_checksums():
    """Load existing checksums from file"""
    if CHECKSUM_FILE.exists():
        with open(CHECKSUM_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_checksums(checksums):
    """Save checksums to file"""
    with open(CHECKSUM_FILE, 'w') as f:
        json.dump(checksums, f, indent=2)

def get_all_notes():
    """Get all markdown files in vault"""
    return list(VAULT_PATH.glob('**/*.md'))

def get_google_drive_service():
    """Authenticate and return Google Drive API service"""
    if not GOOGLE_API_AVAILABLE:
        print("Error: Google API libraries not installed")
        print("Run: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")
        return None

    if not CREDENTIALS_FILE.exists():
        print(f"\nError: {CREDENTIALS_FILE} not found")
        print("\nTo set up Google Drive API:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Create a new project (or select existing)")
        print("3. Enable Google Drive API")
        print("4. Create OAuth 2.0 credentials (Desktop app)")
        print("5. Download credentials.json to this folder")
        print(f"   Save as: {CREDENTIALS_FILE}")
        return None

    creds = None

    # Load saved token if exists
    if TOKEN_FILE.exists():
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)

    # If no valid credentials, authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)

        # Save token for future use
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)

    return build('drive', 'v3', credentials=creds)

def get_drive_file_id(service, filename, parent_folder_id):
    """Get file ID from Google Drive by name and parent folder"""
    # Escape single quotes in filename for query
    escaped_filename = filename.replace("'", "\\'")
    query = f"name='{escaped_filename}' and '{parent_folder_id}' in parents and trashed=false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get('files', [])
    return files[0]['id'] if files else None

def get_or_create_folder(service, folder_name, parent_folder_id):
    """Get or create a folder in Google Drive"""
    # Escape single quotes in folder name
    escaped_folder_name = folder_name.replace("'", "\\'")
    query = f"name='{escaped_folder_name}' and '{parent_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get('files', [])

    if files:
        return files[0]['id']

    # Create folder if it doesn't exist
    file_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_folder_id]
    }
    folder = service.files().create(body=file_metadata, fields='id').execute()
    return folder.get('id')

def upload_to_drive(service, file_path, parent_folder_id, file_id=None):
    """Upload or update file in Google Drive"""
    file_metadata = {
        'name': file_path.name,
        'parents': [parent_folder_id]
    }

    media = MediaFileUpload(str(file_path), resumable=True)

    if file_id:
        # Update existing file
        file = service.files().update(
            fileId=file_id,
            media_body=media
        ).execute()
    else:
        # Create new file
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()

    return file.get('id')

def delete_from_drive(service, file_id):
    """Delete file from Google Drive"""
    service.files().delete(fileId=file_id).execute()

def sync_to_google_drive():
    """Sync modified files to Google Drive"""
    service = get_google_drive_service()
    if not service:
        return

    old_checksums = load_checksums()
    new_checksums = {}

    notes = get_all_notes()
    print(f"Found {len(notes)} markdown files")

    new_files = []
    modified_files = []
    deleted_files = []

    # Check for new and modified files
    for note in notes:
        rel_path = note.relative_to(VAULT_PATH)
        rel_path_str = str(rel_path)

        checksum = calculate_checksum(note)
        new_checksums[rel_path_str] = {
            'checksum': checksum,
            'modified': datetime.fromtimestamp(note.stat().st_mtime).isoformat(),
            'drive_id': old_checksums.get(rel_path_str, {}).get('drive_id')
        }

        if rel_path_str not in old_checksums:
            new_files.append(rel_path_str)
        elif old_checksums[rel_path_str]['checksum'] != checksum:
            modified_files.append(rel_path_str)

    # Check for deleted files
    for old_file in old_checksums:
        if old_file not in new_checksums:
            deleted_files.append(old_file)

    # Report changes
    if new_files:
        print(f"\nNew files ({len(new_files)}):")
        for f in new_files:
            print(f"  + {f}")

    if modified_files:
        print(f"\nModified files ({len(modified_files)}):")
        for f in modified_files:
            print(f"  * {f}")

    if deleted_files:
        print(f"\nDeleted files ({len(deleted_files)}):")
        for f in deleted_files:
            print(f"  - {f}")

    if not (new_files or modified_files or deleted_files):
        print("\nNo changes detected")
        return

    # Sync to Google Drive
    print(f"\nSyncing to Google Drive folder: {DRIVE_FOLDER_ID}")

    # Track folder mappings
    folder_cache = {}

    # Upload new and modified files
    for file_path_str in new_files + modified_files:
        file_path = VAULT_PATH / file_path_str
        rel_path = Path(file_path_str)

        # Handle subfolder structure
        parent_id = DRIVE_FOLDER_ID
        if rel_path.parent != Path('.'):
            # Create folder structure
            folder_parts = rel_path.parent.parts
            for i, folder_name in enumerate(folder_parts):
                folder_key = '/'.join(folder_parts[:i+1])
                if folder_key not in folder_cache:
                    folder_cache[folder_key] = get_or_create_folder(service, folder_name, parent_id)
                parent_id = folder_cache[folder_key]

        # Get existing file ID if it's a modified file
        file_id = new_checksums[file_path_str].get('drive_id')
        if not file_id:
            file_id = get_drive_file_id(service, file_path.name, parent_id)

        # Upload/update file
        drive_id = upload_to_drive(service, file_path, parent_id, file_id)
        new_checksums[file_path_str]['drive_id'] = drive_id

        status = "Updated" if file_path_str in modified_files else "Uploaded"
        print(f"  {status}: {file_path_str}")

    # Delete files from Google Drive
    for file_path_str in deleted_files:
        drive_id = old_checksums[file_path_str].get('drive_id')
        if drive_id:
            try:
                delete_from_drive(service, drive_id)
                print(f"  Removed: {file_path_str}")
            except Exception as e:
                print(f"  Error removing {file_path_str}: {e}")

    # Save new checksums
    save_checksums(new_checksums)
    print(f"\nSync complete! Updated checksums saved")

def main():
    parser = argparse.ArgumentParser(description='Sync Obsidian notes to Google Drive')
    parser.add_argument('--init', action='store_true', help='Initialize checksums without syncing')
    parser.add_argument('--show-status', action='store_true', help='Show current sync status')
    parser.add_argument('--setup', action='store_true', help='Show setup instructions')

    args = parser.parse_args()

    if args.setup:
        print("Google Drive API Setup Instructions:")
        print("\n1. Go to https://console.cloud.google.com/")
        print("2. Create a new project or select existing one")
        print("3. Enable Google Drive API:")
        print("   - Go to 'APIs & Services' > 'Library'")
        print("   - Search for 'Google Drive API'")
        print("   - Click 'Enable'")
        print("4. Create credentials:")
        print("   - Go to 'APIs & Services' > 'Credentials'")
        print("   - Click 'Create Credentials' > 'OAuth client ID'")
        print("   - Choose 'Desktop app'")
        print("   - Download the JSON file")
        print(f"5. Save the downloaded file as: {CREDENTIALS_FILE}")
        print("\n6. Install required packages:")
        print("   pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")
        print("\n7. Run: python push2Google.py --init")
        print("8. Then run: python push2Google.py")
        return

    if args.show_status:
        old_checksums = load_checksums()
        notes = get_all_notes()
        print(f"Vault path: {VAULT_PATH}")
        print(f"Total notes: {len(notes)}")
        print(f"Tracked files: {len(old_checksums)}")
        print(f"Drive folder ID: {DRIVE_FOLDER_ID}")
        return

    if args.init:
        print("Initializing checksums...")
        checksums = {}
        notes = get_all_notes()
        for note in notes:
            rel_path = str(note.relative_to(VAULT_PATH))
            checksums[rel_path] = {
                'checksum': calculate_checksum(note),
                'modified': datetime.fromtimestamp(note.stat().st_mtime).isoformat()
            }
        save_checksums(checksums)
        print(f"Initialized {len(checksums)} files")
        return

    sync_to_google_drive()

if __name__ == '__main__':
    main()
