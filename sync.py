#!/usr/bin/env python3
"""
Bidirectional sync between Obsidian Vault and Google Drive
Usage: python sync.py [--dry-run]

This script:
1. Pulls changes from Google Drive (downloads new/modified files, deletes removed files)
2. Pushes local changes to Google Drive (uploads new/modified files, deletes removed files)
3. Cleans up empty folders in both locations
"""

import subprocess
import sys
import argparse
from pathlib import Path

def run_script(script_name, args=[]):
    """Run a Python script and return success status"""
    cmd = [sys.executable, str(Path(__file__).parent / script_name)] + args

    print(f"\n{'=' * 80}")
    print(f"Running: {script_name}")
    print(f"{'=' * 80}\n")

    result = subprocess.run(cmd)
    return result.returncode == 0

def main():
    parser = argparse.ArgumentParser(
        description='Bidirectional sync between Obsidian Vault and Google Drive'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be synced without making changes'
    )

    args = parser.parse_args()

    print("=" * 80)
    print("BIDIRECTIONAL SYNC: Obsidian Vault <-> Google Drive")
    print("=" * 80)

    # Step 1: Pull from Google Drive
    pull_args = ['--dry-run'] if args.dry_run else []
    if not run_script('pullFromGoogle.py', pull_args):
        print("\n❌ Pull failed! Aborting sync.")
        sys.exit(1)

    # Step 2: Push to Google Drive (skip in dry-run mode)
    if not args.dry_run:
        if not run_script('push2Google.py'):
            print("\n❌ Push failed!")
            sys.exit(1)
    else:
        print("\n[DRY RUN] Skipping push to Google Drive")

    print("\n" + "=" * 80)
    print("✅ SYNC COMPLETE!")
    print("=" * 80)
    print("\nYour Obsidian Vault and Google Drive are now in sync.")

if __name__ == '__main__':
    main()
