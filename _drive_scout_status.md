# Drive Scout — Google Sheets Status
Last updated: 2026-04-02

## Google Sheets Files

### 1. ScoutToSheets
**URL:** https://docs.google.com/spreadsheets/d/1JLt5IMkIyKYey8dT3VEDav8g9YZuHgsg5A46xK8pmDk/edit
**Code ref:** `SHEETS_ID` in `drive_scout_server.py`, `SHEET_FULL` in `type_export.py`

| Tab | Rows | Contents |
|-----|------|----------|
| Sheet1 | 361,407 | Full C:\ scan — run A34FBE61 (03/24 07:18, 28:37 duration) |
| OneDrive | 22,001 | Partial OneDrive scan — run FE51E1BF (03/24 20:31, errored at ~23,500 rows, hit 10M cell limit) |

---

### 2. ScoutToSheets_onedrive
**URL:** https://docs.google.com/spreadsheets/d/1LKyP637uGOvmvfXmmNaoN5sMZ23WcpkOfg4afIPrzxY/edit
**Code ref:** `SHEET_OD` in `type_export.py`

| Tab | Rows | Contents |
|-----|------|----------|
| Sheet1 | 257,274 | Full OneDrive scan — run 14F4CAF7 (03/24 23:37, 15:11 duration) |
| Sheet2 | 0 | Empty |

---

## Scan History Key (from scan_history.json)
Only deep-sheets runs write to Google Sheets. All other scan types (dirs, files, deep, deep-dirs) write to local CSV only.

| Run ID | Path | Files | Date | Result | Sheet |
|--------|------|-------|------|--------|-------|
| A34FBE61 | C:\ | 361,406 | 03/24 07:18 | ✅ done | ScoutToSheets / Sheet1 |
| FE51E1BF | C:\Users\arika\OneDrive | ~23,500 | 03/24 20:31 | ❌ error (10M cell limit) | ScoutToSheets / OneDrive (partial) |
| 14F4CAF7 | C:\Users\arika\OneDrive | 257,273 | 03/24 23:37 | ✅ done | ScoutToSheets_onedrive / Sheet1 |

## Notes
- `drive_scout_server.py` has only ONE hardcoded sheet ID (ScoutToSheets). The second sheet (ScoutToSheets_onedrive) was used by `type_export.py`, a separate one-off script.
- Credentials: `token_sheets.json` + `NewGoogleCLientSecret.json` in repo root.
- Row counts verified via Sheets API on 2026-04-02.
