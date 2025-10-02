# Obsidian Vault to Google Drive Sync

Bi-directional sync between your Obsidian markdown notes and Google Drive using checksums to detect changes.

## Features

- **Bi-directional sync**: Push local changes to Drive and pull Drive changes locally
- **Checksum-based tracking**: Uses SHA256 to detect new, modified, and deleted files
- **Modification time tracking**: Detects changes using Google Drive's modifiedTime
- **Folder structure preservation**: Maintains your folder hierarchy in Google Drive
- **Google Drive API integration**: Direct sync to your Google Drive folder
- **Incremental sync**: Only uploads/downloads changed files
- **Deletion support**: Removes files from Drive when deleted locally (if tracked in checksums)
- **Empty folder cleanup**: Automatically removes empty folders from Google Drive
- **404 error handling**: Gracefully handles files that were manually deleted from Drive
- **Automatic recovery**: Creates new files when stored file IDs become invalid
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

### Daily Workflow - Recommended

**Option 1: Push changes to Google Drive (most common):**
```bash
cd /mnt/c/Users/bindrap/Documents/googleSync
source googleVirtualEnv/bin/activate
python push2Google.py
```

**Option 2: Pull changes from Google Drive:**
```bash
python pullFromGoogle.py
```

**⚠️ Note**: `sync.py` has known issues and should NOT be used. Use `push2Google.py` and `pullFromGoogle.py` separately instead.

### Push to Google Drive (Upload)

Push local changes, new files, and deletions to Google Drive:

```bash
python push2Google.py
```

This will:
- Upload new `.md` files to Google Drive
- Update modified files in Google Drive
- Delete files from Google Drive that were deleted locally (if tracked)
- Handle 404 errors gracefully when files were manually deleted from Drive
- Create new files if stored file IDs are invalid
- Remove empty folders from Google Drive automatically
- Create folder structure in Google Drive matching your local vault

### Pull from Google Drive (Download)

Pull new files and changes from Google Drive to local vault:

```bash
python pullFromGoogle.py
```

This will:
- Download new `.md` files from Google Drive
- Update locally modified files with Drive versions
- Delete local files that were removed from Drive
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

### Manually Clean Empty Folders

```bash
python push2Google.py --clean-folders
```

Note: Empty folder cleanup runs automatically during normal sync, but this flag can be used to clean folders manually.

## How It Works

### Push (push2Google.py)
1. **Checksum Calculation**: Calculates SHA256 hash of each `.md` file in the vault
2. **Change Detection**: Compares current checksums with stored checksums (`.checksums.json`)
3. **Sync Operations**:
   - **New files**: Uploaded to Google Drive (creates folders as needed)
   - **Modified files**: Updated in Google Drive (or created fresh if file ID is invalid)
   - **Deleted files**: Removed from Google Drive (if tracked in checksums)
   - **Empty folders**: Recursively scanned and removed from Google Drive
4. **Error Handling**:
   - 404 errors on update → creates new file
   - 404 errors on delete → skips (already deleted)
5. **Tracking**: Stores Drive file IDs and checksums for future comparisons

### Pull (pullFromGoogle.py)
1. **Drive Scan**: Recursively lists all `.md` files in your Google Drive Notes folder
2. **Change Detection**: Compares Drive files with local checksums and modification times
3. **Download Operations**:
   - **New files in Drive**: Downloaded to local vault
   - **Modified files in Drive**: Detected via `modifiedTime` comparison and updated locally
   - **Different Drive ID**: File was replaced in Drive, re-downloaded
   - **Deleted local files**: Re-downloaded if still in Drive
   - **Deleted from Drive**: Removed locally if no longer in Drive
4. **Tracking**: Updates local checksums with Drive file IDs and modification timestamps

## File Structure

```
Documents/
├── googleSync/
│   ├── push2Google.py          # Push to Google Drive
│   ├── pullFromGoogle.py       # Pull from Google Drive
│   ├── sync.py                 # ⚠️ DO NOT USE - has known issues
│   ├── credentials.json        # OAuth credentials
│   ├── requirements.txt        # Python dependencies
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

### Files not syncing to/from Google Drive
- Ensure both scripts use the same OAuth scope (`drive`)
- Re-authenticate by deleting the token file
- Check that files are actually `.md` files (not Google Docs)

### 404 Errors when pushing
The script now handles these automatically by creating new files when stored IDs are invalid

### Files appear in wrong location in Drive
- Orphaned files (not tracked in checksums) need manual deletion
- Run `pullFromGoogle.py` to sync Drive state to local
- Or delete orphaned files manually from Drive

### Import errors
Install dependencies: `pip install -r requirements.txt`

## Known Limitations

1. **Orphaned files in Drive**: `push2Google.py` won't detect files that exist in Drive but were never tracked in the checksum file. These need to be:
   - Deleted manually from Drive, OR
   - Synced using `pullFromGoogle.py` which will download them and add to checksums

2. **sync.py issues**: The bidirectional sync script has known issues and should not be used. Use `push2Google.py` and `pullFromGoogle.py` separately.

3. **File types**: Only `.md` files are synced (images and other files are ignored)

## Testing Checklist

- [x] ✅ Upload new files to Google Drive
- [x] ✅ Create folder structure in Google Drive
- [x] ✅ Handle filenames with apostrophes (e.g., "Mel's Task.md")
- [x] ✅ Modify existing file → uploads to Drive
- [x] ✅ Delete file locally → deleted in Drive
- [x] ✅ Delete folder locally → deleted in Drive (when empty)
- [x] ✅ Empty folders automatically cleaned from Drive on every sync
- [x] ✅ Handle 404 errors when file manually deleted from Drive
- [x] ✅ Create new file when stored ID is invalid
- [x] ✅ Add new file in Drive → downloads locally (via pull)
- [x] ✅ Modify file in Drive → updates locally (via pull with modifiedTime tracking)
- [x] ✅ Delete file from Drive → deleted locally (via pull)

## Notes

- Only `.md` files are synced (images and other files are ignored)
- The vault path is `Documents/Obsidian Vault/` (sibling folder to `googleSync/`)
- Checksums are stored in `googleSync/.checksums.json`
- Folder structure is preserved in both directions
- Use `push2Google.py` when you make local changes
- Use `pullFromGoogle.py` when changes are made in Drive (other device, manual edits, etc.)
- All modifications to files are tracked via timestamps in `.checksums.json`
