#!/usr/bin/env python3
"""
Pull notes from Google Drive to local Obsidian Vault
Usage: python pullFromGoogle.py [--dry-run]
"""

import os
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
    from googleapiclient.http import MediaIoBaseDownload
    import io
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False

# Configuration
VAULT_PATH = Path(__file__).parent.parent / "Obsidian Vault"
CHECKSUM_FILE = Path(__file__).parent / ".checksums.json"
TOKEN_FILE = Path(__file__).parent / ".google_token.pickle"
CREDENTIALS_FILE = Path(__file__).parent / "credentials.json"

# Google Drive folder ID
DRIVE_FOLDER_ID = "1rtokeqgAen02UyJDbPtBVCyczk5ssqhG"

# Google Drive API scopes
SCOPES = ['https://www.googleapis.com/auth/drive']

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

def get_google_drive_service():
    """Authenticate and return Google Drive API service"""
    if not GOOGLE_API_AVAILABLE:
        print("Error: Google API libraries not installed")
        print("Run: pip install -r requirements.txt")
        return None

    if not CREDENTIALS_FILE.exists():
        print(f"Error: {CREDENTIALS_FILE} not found")
        print("Run push2Google.py first to set up credentials")
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

def list_drive_files(service, folder_id, path=""):
    """Recursively list all files in Google Drive folder"""
    files_dict = {}

    # Query for all items in this folder
    query = f"'{folder_id}' in parents and trashed=false"
    results = service.files().list(
        q=query,
        fields="files(id, name, mimeType, modifiedTime)",
        pageSize=1000
    ).execute()

    items = results.get('files', [])

    for item in items:
        item_name = item['name']
        item_id = item['id']
        mime_type = item['mimeType']

        if mime_type == 'application/vnd.google-apps.folder':
            # Recursively list folder contents
            subfolder_path = f"{path}/{item_name}" if path else item_name
            subfiles = list_drive_files(service, item_id, subfolder_path)
            files_dict.update(subfiles)
        elif (item_name.endswith('.md') or item_name.endswith('.txt') or
              item_name.endswith('.png') or item_name.endswith('.jpg') or
              item_name.endswith('.jpeg') or item_name.endswith('.gif') or
              item_name.endswith('.webp') or item_name.endswith('.svg')):
            # Add file to dict
            file_path = f"{path}/{item_name}" if path else item_name
            files_dict[file_path] = {
                'id': item_id,
                'modified': item['modifiedTime']
            }

    return files_dict

def download_file(service, file_id, local_path):
    """Download a file from Google Drive"""
    request = service.files().get_media(fileId=file_id)

    # Ensure parent directory exists
    local_path.parent.mkdir(parents=True, exist_ok=True)

    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)

    done = False
    while not done:
        status, done = downloader.next_chunk()

    # Write to file
    with open(local_path, 'wb') as f:
        f.write(fh.getvalue())

def calculate_checksum(file_path):
    """Calculate SHA256 checksum of a file"""
    import hashlib
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha256.update(chunk)
    return sha256.hexdigest()

def cleanup_empty_folders(path):
    """Recursively remove empty folders"""
    # Folders to preserve even when empty
    PRESERVE_FOLDERS = {'img', 'weekly', 'neovim'}

    for item in path.iterdir():
        if item.is_dir():
            cleanup_empty_folders(item)
            # Try to remove if empty and not in preserve list
            try:
                if not any(item.iterdir()) and item.name.lower() not in PRESERVE_FOLDERS:
                    item.rmdir()
                    print(f"  Removed empty folder: {item.relative_to(VAULT_PATH)}")
            except OSError:
                pass  # Not empty or can't be removed

def pull_from_google_drive(dry_run=False):
    """Pull new/modified files from Google Drive"""
    service = get_google_drive_service()
    if not service:
        return

    print(f"Scanning Google Drive folder: {DRIVE_FOLDER_ID}")
    drive_files = list_drive_files(service, DRIVE_FOLDER_ID)
    print(f"Found {len(drive_files)} files in Google Drive (markdown, text, and images)")

    local_checksums = load_checksums()

    new_files = []
    modified_files = []
    deleted_files = []

    # Check for new and modified files
    for file_path, drive_info in drive_files.items():
        drive_id = drive_info['id']
        drive_modified = drive_info['modified']
        local_path = VAULT_PATH / file_path

        if file_path not in local_checksums:
            new_files.append(file_path)
        elif local_checksums[file_path].get('drive_id') != drive_id:
            # Different file ID means it was replaced in Drive
            modified_files.append(file_path)
        elif local_checksums[file_path].get('drive_modified') != drive_modified:
            # File was modified in Drive (different modification time)
            modified_files.append(file_path)
        elif not local_path.exists():
            # File was deleted locally
            new_files.append(file_path)

    # Check for files deleted from Drive
    for file_path in local_checksums:
        if file_path not in drive_files:
            deleted_files.append(file_path)

    # Report changes
    if new_files:
        print(f"\nNew files in Drive ({len(new_files)}):")
        for f in new_files:
            print(f"  + {f}")

    if modified_files:
        print(f"\nModified files in Drive ({len(modified_files)}):")
        for f in modified_files:
            print(f"  * {f}")

    if deleted_files:
        print(f"\nDeleted from Drive ({len(deleted_files)}):")
        for f in deleted_files:
            print(f"  - {f}")

    if not (new_files or modified_files or deleted_files):
        print("\nNo new changes in Google Drive")
        return

    if dry_run:
        print("\n[DRY RUN] No files were downloaded")
        return

    # Download files
    print("\nDownloading files from Google Drive...")

    for file_path in new_files + modified_files:
        drive_info = drive_files[file_path]
        local_path = VAULT_PATH / file_path

        try:
            download_file(service, drive_info['id'], local_path)

            # Update checksums
            checksum = calculate_checksum(local_path)
            local_checksums[file_path] = {
                'checksum': checksum,
                'modified': datetime.fromtimestamp(local_path.stat().st_mtime).isoformat(),
                'drive_id': drive_info['id'],
                'drive_modified': drive_info['modified']
            }

            status = "Updated" if file_path in modified_files else "Downloaded"
            print(f"  {status}: {file_path}")
        except Exception as e:
            print(f"  Error downloading {file_path}: {e}")

    # Delete local files that were deleted from Drive
    for file_path in deleted_files:
        local_path = VAULT_PATH / file_path
        try:
            if local_path.exists():
                local_path.unlink()
                print(f"  Removed: {file_path}")
            # Remove from checksums
            del local_checksums[file_path]
        except Exception as e:
            print(f"  Error removing {file_path}: {e}")

    # Clean up empty local folders
    if deleted_files:
        print("\nCleaning up empty local folders...")
        cleanup_empty_folders(VAULT_PATH)

    # Save updated checksums
    save_checksums(local_checksums)
    print(f"\nPull complete! Updated checksums saved")

def main():
    parser = argparse.ArgumentParser(description='Pull notes from Google Drive to Obsidian Vault')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be downloaded without downloading')

    args = parser.parse_args()

    pull_from_google_drive(dry_run=args.dry_run)

if __name__ == '__main__':
    main()
