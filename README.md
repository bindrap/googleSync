# Obsidian Vault to Google Drive Sync

Bi-directional sync between your Obsidian markdown notes and Google Drive using checksums to detect changes.

## Features

- **Bi-directional sync**: Push local changes to Drive and pull Drive changes locally
- **Checksum-based tracking**: Uses SHA256 to detect new, modified, and deleted files
- **Modification time tracking**: Detects changes using Google Drive's modifiedTime
- **Folder structure preservation**: Maintains your folder hierarchy in Google Drive
- **Google Drive API integration**: Direct sync to your Google Drive folder
- **Incremental sync**: Only uploads/downloads changed files
- **Deletion support**: Removes files from Drive when deleted locally
- **Persistent authentication**: OAuth token saved locally for future runs

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Google Drive API Setup

The `credentials.json` file is already configured with your OAuth 2.0 credentials:
- **Client ID**: `683416396764-868cf34a3eieflhdkrsvq454dqgq4tgk.apps.googleusercontent.com`
- **Drive Folder ID**: `1rtokeqgAen02UyJDbPtBVCyczk5ssqhG` (Notes folder)

If you need to reconfigure:
```bash
python push2Google.py --setup
```

### 3. First-Time Authentication

Initialize checksums and authenticate:

```bash
python push2Google.py --init
python push2Google.py
```

The first run will:
1. Open a browser window (or provide a URL to visit manually)
2. Ask you to login with `pbindra97@gmail.com`
3. Request permission to access Google Drive (full drive access scope)
4. Save authentication token locally (`.google_token.pickle`)

**Note**: Both scripts now use the `drive` scope for full read/write access, allowing detection and deletion of all files, not just those created by the app.

## Usage

### Daily Workflow

**Start of day - Pull changes from Google Drive:**
```bash
cd /mnt/c/Users/bindrap/Documents/googleSync
source googleVirtualEnv/bin/activate
python pullFromGoogle.py
```

**End of day - Push changes to Google Drive:**
```bash
python push2Google.py
```

### Push to Google Drive (Upload)

Push local changes, new files, and deletions to Google Drive:

```bash
python push2Google.py
```

This will:
- Upload new `.md` files to Google Drive
- Update modified files in Google Drive
- Delete files from Google Drive that were deleted locally
- Create folder structure in Google Drive matching your local vault

### Pull from Google Drive (Download)

Pull new files and changes from Google Drive to local vault:

```bash
python pullFromGoogle.py
```

This will:
- Download new `.md` files from Google Drive
- Update locally modified files with Drive versions
- Preserve folder structure from Google Drive

**Preview changes without downloading:**
```bash
python pullFromGoogle.py --dry-run
```

### Check Status

```bash
python push2Google.py --show-status
```

### View Setup Instructions

```bash
python push2Google.py --setup
```

### Reinitialize Checksums

```bash
python push2Google.py --init
```

## How It Works

### Push (push2Google.py)
1. **Checksum Calculation**: Calculates SHA256 hash of each `.md` file in the vault
2. **Change Detection**: Compares current checksums with stored checksums (`.checksums.json`)
3. **Sync Operations**:
   - **New files**: Uploaded to Google Drive (creates folders as needed)
   - **Modified files**: Updated in Google Drive
   - **Deleted files**: Removed from Google Drive (including empty folders)
4. **Tracking**: Stores Drive file IDs and checksums for future comparisons

### Pull (pullFromGoogle.py)
1. **Drive Scan**: Recursively lists all `.md` files in your Google Drive Notes folder
2. **Change Detection**: Compares Drive files with local checksums and modification times
3. **Download Operations**:
   - **New files in Drive**: Downloaded to local vault
   - **Modified files in Drive**: Detected via `modifiedTime` comparison and updated locally
   - **Different Drive ID**: File was replaced in Drive, re-downloaded
   - **Deleted local files**: Re-downloaded if still in Drive
4. **Tracking**: Updates local checksums with Drive file IDs and modification timestamps

## File Structure

```
Documents/
├── googleSync/
│   ├── push2Google.py          # Push to Google Drive
│   ├── pullFromGoogle.py       # Pull from Google Drive
│   ├── credentials.json         # OAuth credentials
│   ├── requirements.txt         # Python dependencies
│   ├── README.md               # This file
│   ├── .checksums.json         # File checksums (auto-generated)
│   ├── .google_token.pickle    # OAuth token (auto-generated)
│   └── googleVirtualEnv/       # Python virtual environment
└── Obsidian Vault/
    ├── [your markdown files]
    └── [folders with markdown files]
```

## Security Notes

- **Never commit** `credentials.json` or `.google_token.pickle` to public repositories
- The scripts use OAuth scope `drive` for full read/write access to all Drive files
- Authentication token is stored locally and reused
- Both push and pull scripts share the same authentication token

## Troubleshooting

### Missing credentials.json
Run `python push2Google.py --setup` for instructions to download from Google Cloud Console

### Authentication errors or permission issues
Delete `.google_token.pickle` and run the script again to re-authenticate:
```bash
rm .google_token.pickle
python push2Google.py  # or pullFromGoogle.py
```

### Files not syncing from Google Drive
- Ensure both scripts use the same OAuth scope (`drive`)
- Re-authenticate by deleting the token file
- Check that files are actually `.md` files (not Google Docs)

### Import errors
Install dependencies: `pip install -r requirements.txt`

## Testing Checklist

- [x] ✅ Upload new files to Google Drive
- [x] ✅ Create folder structure in Google Drive
- [x] ✅ Handle filenames with apostrophes (e.g., "Mel's Task.md")
- [x] ✅ Modify existing file → uploads to Drive
- [x] ✅ Delete file locally → deleted in Drive
- [x] ✅ Delete folder locally → deleted in Drive (when empty)
- [x] ✅ Add new file in Drive → downloads locally
- [x] ✅ Modify file in Drive → updates locally (via modifiedTime tracking)

## Notes

- Only `.md` files are synced (images and other files are ignored)
- The vault path is `Documents/Obsidian Vault/` (sibling folder to `googleSync/`)
- Checksums are stored in `googleSync/.checksums.json`
- Folder structure is preserved in both directions
- Use `push2Google.py` at end of day, `pullFromGoogle.py` at start of day


![alt text](image.png)

![alt text](image-1.png)