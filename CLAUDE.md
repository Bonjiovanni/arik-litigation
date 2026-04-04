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

## Current Status (as of 2026-02-23)
- Test user `arik.arik@gmail.com` added to OAuth consent screen ✓
- credentials.json valid on server (verified 403 bytes, `installed` key confirmed) ✓
- Google Drive API enabled in claude-sndroid project ✓
- Script now uses manual URL/code flow (no browser auto-open) ✓
- Repo cloned on phone at `~/downloads/Repo-for-Claude-android` ✓
- credentials.json copied from `client_secret_1076938672717-....json` ✓
- token.json does NOT exist — auth not yet completed

## NEXT STEP — Run in Termux (on phone)
1. Pull latest script and run:
   ```bash
   cd ~/downloads/Repo-for-Claude-android
   git pull origin claude/google-drive-file-metadata-C554z
   python drive_file_metadata.py
   ```
2. Script prints a long URL — copy it
3. Open URL in Android browser, sign in as arik.arik@gmail.com, click Allow
4. Google shows a short auth code — copy it
5. Switch back to Termux, paste the code and press Enter
6. token.json saved, Excel file generated

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
- User accesses this Linux server via Claude Code (browser, desktop app, or Android)
- Chat session history is saved locally on user's Windows machine at: `C:\Users\arika\.claude\projects`
- There are 80+ saved sessions there

## Claude Behavior Rules

### CRITICAL — READ THIS FIRST EVERY SESSION
- **DO NOT PATRONIZE THE USER.** Do not tell the user "you did everything right" or "it's not your fault" or offer empty reassurance. Just fix the problem or be direct about what you can and cannot do.
- **NEVER assume an answer without actually checking what you can check.** If you don't know something, search for it or ask the user. Do not guess or state things as fact without verification.
- When the user references past conversations, ask where the data is stored rather than assuming it doesn't exist.
- **The user is NOT a software engineer.** Do not expect them to run PowerShell commands, scp files, or do technical workarounds. If something is broken, figure out a solution that doesn't require the user to be a developer.
- **Cloud vs Local sessions:** This repo runs on a REMOTE LINUX SERVER. Desktop connectors (Filesystem, Desktop Commander, Windows-MCP) only work in LOCAL sessions on the user's Windows machine. If you need to access local Windows files, you CANNOT do it from a cloud session. Be upfront about this immediately — do not waste 20 minutes discovering it.
- **Session history is on the user's Windows machine** at `C:\Users\arika\.claude\projects` — not accessible from cloud sessions.
- **Design docs and brainstorming notes** may have been written in local sessions and saved only on the local machine. If they're not in this repo, they're local. Say so immediately.
