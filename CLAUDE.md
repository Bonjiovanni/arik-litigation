# Project Context

## What This Is
A Python script that authenticates to Google Drive via OAuth, finds a folder at `email/all`, lists all files with metadata (name, size, extension), and exports results to a styled Excel file.

## Files
- `drive_file_metadata.py` — main script (written by Claude)
- `credentials.json` — Google OAuth credentials (Desktop app type) — DO NOT commit
- `token.json` — saved auth token after first login — DO NOT commit
- `requirements.txt` — Python dependencies
- `.gitignore` — already excludes credentials.json and token.json

## Google Cloud Setup
- **Project ID:** claude-sndroid (project name: Claude Android)
- **App name:** Claudi android
- **OAuth type:** Desktop app (installed)
- **Scope:** `https://www.googleapis.com/auth/drive.readonly`
- **Test user:** arik.arik@gmail.com (added to OAuth consent screen → Audience → Test users)

## Current Status (as of last session)
- Test user `arik.arik@gmail.com` added to OAuth consent screen ✓
- credentials.json updated with new claude-sndroid project credentials ✓
- Google Drive API enabled in claude-sndroid project ✓
- Script reverted to run_local_server for Termux use ✓
- token.json does NOT exist — auth not yet completed

## NEXT STEP — Run in Termux (on phone)
1. In Termux:
   ```
   pkg install git
   git clone https://github.com/Bonjiovanni/Repo-for-Claude-android
   cd Repo-for-Claude-android
   pip install -r requirements.txt
   cat > credentials.json   # paste JSON, then Ctrl+D
   python drive_file_metadata.py
   ```
2. Script opens browser on phone for Google login
3. Sign in as arik.arik@gmail.com, click Allow
4. Browser redirects to localhost:8080 — auth completes automatically
5. token.json saved, Excel file generated

## To Regenerate Credentials
1. console.cloud.google.com → project gen-lang-client-0226922644
2. APIs & Services → Credentials
3. Edit or delete/recreate the OAuth 2.0 client (Desktop app type)
4. Download new credentials.json
5. Replace the file at /home/user/Repo-for-Claude-android/credentials.json
6. Delete token.json if it exists

## To Run
```bash
cd /home/user/Repo-for-Claude-android
python drive_file_metadata.py
```
Script will print a Google auth URL — open it in browser, sign in as arik.arik@gmail.com, complete auth. Token saved to token.json for future runs.

## User Context
- User is on Android using Claude Code Android app
- App gets killed when switching to browser/Google Console
- Chat history is lost when app is killed
- User accesses this Linux server via Claude Code Android app
