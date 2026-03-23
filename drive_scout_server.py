"""
drive_scout_server.py
---------------------
Drive Scout — backend server.

Serves the UI, runs PowerShell scans with live streaming counts,
and pushes updates to the browser via WebSocket.

Install deps:  pip install fastapi uvicorn
Run:           python drive_scout_server.py
Opens at:      http://localhost:8765
"""

import sys
if sys.version_info < (3, 11):
    sys.exit("Drive Scout requires Python 3.11+. Run with: py -3.11 drive_scout_server.py")

import asyncio
import json
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
import uvicorn

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

app = FastAPI()

OUTPUT_DIR = Path(__file__).parent / "drive_scout_output"
OUTPUT_DIR.mkdir(exist_ok=True)

UI_FILE = Path(__file__).parent / "drive_scout.html"

# ---------------------------------------------------------------------------
# Google Sheets config
# ---------------------------------------------------------------------------

SHEETS_CREDENTIALS = r"C:\Users\arika\Repo-for-Claude-android\NewGoogleCLientSecret.json"
SHEETS_TOKEN       = r"C:\Users\arika\Repo-for-Claude-android\token_sheets.json"
SHEETS_SCOPES      = ["https://www.googleapis.com/auth/spreadsheets"]
SHEETS_ID          = "1JLt5IMkIyKYey8dT3VEDav8g9YZuHgsg5A46xK8pmDk"
SHEETS_BATCH_SIZE  = 2000

# Column layout for the output sheet.
# If the sheet is empty or wiped, these are written as row 1 automatically.
# Col A: full_path      — full Windows path to the file
# Col B: directory      — parent folder path
# Col C: filename       — file name with extension
# Col D: extension      — lowercase file extension (e.g. .pdf)
# Col E: size_mb        — file size in MB, rounded to 1 decimal place
# Col F: modified_date  — file last-modified date (YYYY-MM-DD)
# Col G: scanned_at     — date/time this row was written (YYYY-MM-DD HH:MM:SS)
SHEETS_HEADER = [
    "full_path",
    "directory",
    "filename",
    "extension",
    "size_mb",
    "modified_date",
    "scanned_at",
]


# ---------------------------------------------------------------------------
# WebSocket manager
# ---------------------------------------------------------------------------

class ConnectionManager:
    def __init__(self):
        self._connections: dict[str, WebSocket] = {}

    async def connect(self, client_id: str, ws: WebSocket):
        await ws.accept()
        self._connections[client_id] = ws

    def disconnect(self, client_id: str):
        self._connections.pop(client_id, None)

    async def broadcast(self, data: dict):
        dead = []
        for cid, ws in self._connections.items():
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(cid)
        for cid in dead:
            self.disconnect(cid)


manager = ConnectionManager()


# ---------------------------------------------------------------------------
# Scan state
# ---------------------------------------------------------------------------

HISTORY_FILE = OUTPUT_DIR / "scan_history.json"

scans: dict[str, dict] = {}
active_procs: dict[str, asyncio.subprocess.Process] = {}


def load_history():
    """Load persisted scan history from disk on startup."""
    if HISTORY_FILE.exists():
        try:
            data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
            for r in data:
                scans[r["id"]] = r
        except Exception:
            pass


def save_history():
    """Persist completed scans to disk."""
    done = [r for r in scans.values() if r.get("status") in ("done", "error", "stopped")]
    try:
        HISTORY_FILE.write_text(json.dumps(done, default=str), encoding="utf-8")
    except Exception:
        pass


def new_scan(paths: list[str], scan_type: str, workers: int,
             exclude: list[str], depth: Optional[int]) -> dict:
    sid = str(uuid.uuid4())[:8].upper()
    record = {
        "id":         sid,
        "paths":      paths,
        "scan_type":  scan_type,   # "dirs" | "files"
        "workers":    workers,
        "exclude":    exclude,
        "depth":      depth,
        "status":     "queued",    # queued|running|done|error|stopped
        "count":      0,
        "start_time": None,
        "end_time":   None,
        "output_file": str(OUTPUT_DIR / f"{sid}_{scan_type}.csv"),
        "error":      None,
    }
    scans[sid] = record
    return record


def scan_summary(r: dict) -> dict:
    start, end = r.get("start_time"), r.get("end_time")
    elapsed = ""
    if start:
        t0 = datetime.fromisoformat(start)
        t1 = datetime.fromisoformat(end) if end else datetime.now()
        s  = int((t1 - t0).total_seconds())
        elapsed = f"{s // 60}:{s % 60:02d}"
    return {
        "id":           r["id"],
        "paths":        r["paths"],
        "scan_type":    r["scan_type"],
        "status":       r["status"],
        "count":        r["count"],
        "subdir_count": r.get("subdir_count", 0),
        "file_count":   r.get("file_count",   0),
        "size_bytes":   r.get("size_bytes",   0),
        "elapsed":      elapsed,
        "start_time":   r.get("start_time"),
        "error":        r.get("error"),
    }


# ---------------------------------------------------------------------------
# System extension filter — injected into every PS scan script
# ---------------------------------------------------------------------------

SYSTEM_EXTENSIONS = sorted([
    ".acm", ".ax", ".cab", ".cat", ".cpl", ".cur",
    ".dll", ".drv", ".efi", ".evt", ".evtx", ".exe",
    ".fon", ".hlp", ".ico", ".lnk",
    ".manifest", ".msi", ".msm", ".msp", ".mst",
    ".mui", ".mum", ".nls", ".ocx", ".pdb", ".rll",
    ".scr", ".sys", ".tlb", ".ttc", ".ttf", ".vxd", ".wim",
])

# PowerShell array literal, e.g. @('.dll','.exe', ...)
_PS_SYS_EXTS = "@(" + ",".join(f"'{e}'" for e in SYSTEM_EXTENSIONS) + ")"


# ---------------------------------------------------------------------------
# PowerShell scripts — streaming via stdout, writing CSV via StreamWriter
# ---------------------------------------------------------------------------

def _ps_dir_scan(path: str) -> str:
    """
    Dir scan: enumerate immediate contents, emit aggregate counts only.
    No CSV is written — stats (SUBDIRS/FILES/SIZE) are the output.
    System-type extensions are excluded from counts.
    """
    return f"""
$p = "{path}"
$sysExts = {_PS_SYS_EXTS}
$subdirs = @(Get-ChildItem -LiteralPath $p -Directory -Force -ErrorAction SilentlyContinue)
$files   = @(Get-ChildItem -LiteralPath $p -File    -Force -ErrorAction SilentlyContinue |
             Where-Object {{ $sysExts -notcontains $_.Extension.ToLower() }})
$size    = ($files | Measure-Object -Property Length -Sum).Sum
if (-not $size) {{ $size = 0 }}
Write-Host "SUBDIRS:$($subdirs.Count)"
Write-Host "FILES:$($files.Count)"
Write-Host "SIZE:$size"
Write-Host "DONE:$($files.Count)"
"""


def _ps_file_scan(path: str, output_csv: str) -> str:
    """
    File scan: enumerate immediate files, emit aggregate counts AND write CSV.
    System-type extensions are excluded.
    """
    return f"""
$p = "{path}"
$sysExts = {_PS_SYS_EXTS}
$subdirs = @(Get-ChildItem -LiteralPath $p -Directory -Force -ErrorAction SilentlyContinue)
$files   = @(Get-ChildItem -LiteralPath $p -File    -Force -ErrorAction SilentlyContinue |
             Where-Object {{ $sysExts -notcontains $_.Extension.ToLower() }})
$size    = ($files | Measure-Object -Property Length -Sum).Sum
if (-not $size) {{ $size = 0 }}
Write-Host "SUBDIRS:$($subdirs.Count)"
Write-Host "FILES:$($files.Count)"
Write-Host "SIZE:$size"
$out = [System.IO.StreamWriter]::new("{output_csv}", $false, [System.Text.Encoding]::UTF8)
$out.WriteLine('"full_path","directory","filename","extension","size_bytes","modified_date"')
$n = 0
$files | ForEach-Object {{
    $n++
    $line = '"{{0}}","{{1}}","{{2}}","{{3}}",{{4}},"{{5}}"' -f `
        $_.FullName.Replace('"','""'), `
        $_.DirectoryName.Replace('"','""'), `
        $_.Name.Replace('"','""'), `
        $_.Extension.ToLower().Replace('"','""'), `
        $_.Length, `
        $_.LastWriteTime.ToString('yyyy-MM-dd')
    $out.WriteLine($line)
}}
$out.Flush(); $out.Close()
Write-Host "DONE:$n"
"""


def _ps_deep_file_scan(paths: list[str], output_csv: str) -> str:
    """Deep recursive file scan — used when explicitly requested. System extensions excluded."""
    path_array = ",".join(f'"{p}"' for p in paths)
    return f"""
$paths = @({path_array})
$sysExts = {_PS_SYS_EXTS}
$out = [System.IO.StreamWriter]::new("{output_csv}", $false, [System.Text.Encoding]::UTF8)
$out.WriteLine('"full_path","directory","filename","extension","size_bytes","modified_date"')
$n = 0
foreach ($p in $paths) {{
    Get-ChildItem -LiteralPath $p -Recurse -File -Force -ErrorAction SilentlyContinue |
    Where-Object {{ $sysExts -notcontains $_.Extension.ToLower() }} |
    ForEach-Object {{
        $n++
        $line = '"{{0}}","{{1}}","{{2}}","{{3}}",{{4}},"{{5}}"' -f `
            $_.FullName.Replace('"','""'), `
            $_.DirectoryName.Replace('"','""'), `
            $_.Name.Replace('"','""'), `
            $_.Extension.ToLower().Replace('"','""'), `
            $_.Length, `
            $_.LastWriteTime.ToString('yyyy-MM-dd')
        $out.WriteLine($line)
        if ($n % 500 -eq 0) {{ Write-Host "COUNT:$n" }}
    }}
}}
$out.Flush(); $out.Close()
Write-Host "DONE:$n"
"""


def _ps_deep_dir_scan(path: str, output_csv: str) -> str:
    """
    Deep dir scan: enumerate ALL directories recursively, report per-directory
    direct file count and size (system extensions excluded).
    Single Get-ChildItem -Recurse -File pass for speed, then grouped by directory.
    CSV columns: full_path, dir_name, depth, direct_file_count, direct_size_bytes
    """
    return f"""
$p = "{path}"
$sysExts = {_PS_SYS_EXTS}
$out = [System.IO.StreamWriter]::new("{output_csv}", $false, [System.Text.Encoding]::UTF8)
$out.WriteLine('"full_path","dir_name","depth","direct_file_count","direct_size_bytes"')

# Collect all directories
$allDirs = @{{}}
$rootItem = Get-Item -LiteralPath $p -ErrorAction SilentlyContinue
if ($rootItem) {{ $allDirs[$rootItem.FullName.ToLower()] = $rootItem.FullName }}
Get-ChildItem -LiteralPath $p -Recurse -Directory -Force -ErrorAction SilentlyContinue |
    ForEach-Object {{ $allDirs[$_.FullName.ToLower()] = $_.FullName }}
Write-Host "SUBDIRS:$($allDirs.Count)"

# Single-pass file enumeration grouped by directory
$dirStats = @{{}}
Get-ChildItem -LiteralPath $p -Recurse -File -Force -ErrorAction SilentlyContinue |
    Where-Object {{ $sysExts -notcontains $_.Extension.ToLower() }} |
    ForEach-Object {{
        $dk = $_.DirectoryName.ToLower()
        if (-not $dirStats.ContainsKey($dk)) {{ $dirStats[$dk] = @{{ count=0; size=[long]0 }} }}
        $dirStats[$dk].count++
        $dirStats[$dk].size += $_.Length
    }}

# Write one row per directory, sorted by path
$n = 0
foreach ($dk in ($allDirs.Keys | Sort-Object)) {{
    $fp      = $allDirs[$dk]
    $parts   = $fp.TrimEnd('\\').Split('\\')
    $dirName = $parts[-1]
    $depth   = $parts.Count - 1
    $stats   = if ($dirStats.ContainsKey($dk)) {{ $dirStats[$dk] }} else {{ @{{ count=0; size=[long]0 }} }}
    $n++
    $line = '"' + $fp.Replace('"','""') + '","' + $dirName.Replace('"','""') + '",' + $depth + ',' + $stats.count + ',' + $stats.size
    $out.WriteLine($line)
    if ($n % 100 -eq 0) {{ Write-Host "COUNT:$n" }}
}}
$out.Flush(); $out.Close()
Write-Host "DONE:$n"
"""


def _ps_deep_file_scan_stdout(paths: list[str]) -> str:
    """Deep recursive file scan — streams rows to stdout instead of a CSV file.
    Each file line is emitted as ROW:<csv-line>. No StreamWriter used."""
    path_array = ",".join(f'"{p}"' for p in paths)
    return f"""
$paths = @({path_array})
$sysExts = {_PS_SYS_EXTS}
$n = 0
foreach ($p in $paths) {{
    Get-ChildItem -LiteralPath $p -Recurse -File -Force -ErrorAction SilentlyContinue |
    Where-Object {{ $sysExts -notcontains $_.Extension.ToLower() }} |
    ForEach-Object {{
        $n++
        $line = '"{{0}}","{{1}}","{{2}}","{{3}}",{{4}},"{{5}}"' -f `
            $_.FullName.Replace('"','""'), `
            $_.DirectoryName.Replace('"','""'), `
            $_.Name.Replace('"','""'), `
            $_.Extension.ToLower().Replace('"','""'), `
            $_.Length, `
            $_.LastWriteTime.ToString('yyyy-MM-dd')
        Write-Host "ROW:$line"
        if ($n % 500 -eq 0) {{ Write-Host "COUNT:$n" }}
    }}
}}
Write-Host "DONE:$n"
"""


# ---------------------------------------------------------------------------
# Google Sheets helpers
# ---------------------------------------------------------------------------

def get_sheets_service():
    """Return an authenticated Google Sheets API service, refreshing/creating token as needed."""
    creds = None
    token_path = Path(SHEETS_TOKEN)
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SHEETS_SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(SHEETS_CREDENTIALS, SHEETS_SCOPES)
            creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json())
    return build("sheets", "v4", credentials=creds)




# ---------------------------------------------------------------------------
# Scan execution
# ---------------------------------------------------------------------------

async def run_scan(scan_id: str):
    r = scans[scan_id]
    r["status"]     = "running"
    r["start_time"] = datetime.now().isoformat()
    r["subdir_count"] = 0
    r["file_count"]   = 0
    r["size_bytes"]   = 0
    await manager.broadcast({"type": "scan_update", "scan": scan_summary(r)})

    # Shallow scan: one path at a time, immediate contents only
    # Deep scan: recursive, used when scan_type == "deep"
    scan_type = r["scan_type"]

    if scan_type == "deep":
        script = _ps_deep_file_scan(r["paths"], r["output_file"])
    elif scan_type == "deep-dirs":
        script = _ps_deep_dir_scan(r["paths"][0], r["output_file"])
    elif scan_type == "files":
        script = _ps_file_scan(r["paths"][0], r["output_file"])
    else:  # "dirs"
        script = _ps_dir_scan(r["paths"][0])

    try:
        proc = await asyncio.create_subprocess_exec(
            "powershell", "-NoProfile", "-NonInteractive", "-Command", script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        active_procs[scan_id] = proc

        async for raw in proc.stdout:
            line = raw.decode("utf-8", errors="replace").strip()
            if line.startswith("SUBDIRS:"):
                r["subdir_count"] = int(line[8:])
                await manager.broadcast({"type": "scan_update", "scan": scan_summary(r)})
            elif line.startswith("FILES:"):
                r["file_count"] = int(line[6:])
                r["count"]      = int(line[6:])
                await manager.broadcast({"type": "scan_update", "scan": scan_summary(r)})
            elif line.startswith("SIZE:"):
                r["size_bytes"] = int(line[5:])
                await manager.broadcast({"type": "scan_update", "scan": scan_summary(r)})
            elif line.startswith("COUNT:"):
                count = int(line[6:])
                r["count"] = count
                await manager.broadcast({"type": "count_update",
                                         "scan_id": scan_id, "count": count})
            elif line.startswith("DONE:"):
                r["count"] = int(line[5:])

        await proc.wait()

        if r["status"] not in ("stopped",):
            r["status"] = "done" if proc.returncode == 0 else "error"

    except Exception as e:
        r["status"] = "error"
        r["error"]  = str(e)

    r["end_time"] = datetime.now().isoformat()
    active_procs.pop(scan_id, None)
    save_history()
    await manager.broadcast({"type": "scan_update", "scan": scan_summary(r)})


SHEETS_ROW_LIMIT = 700_000  # rows per tab before rolling to a new sheet tab


def _get_existing_sheet_titles(svc) -> list[str]:
    """Return list of existing sheet tab titles in the spreadsheet."""
    meta = svc.spreadsheets().get(spreadsheetId=SHEETS_ID).execute()
    return [s["properties"]["title"] for s in meta.get("sheets", [])]


def _create_sheet_tab(svc, title: str) -> None:
    """Add a new sheet tab with the given title."""
    svc.spreadsheets().batchUpdate(
        spreadsheetId=SHEETS_ID,
        body={"requests": [{"addSheet": {"properties": {"title": title}}}]},
    ).execute()


def _next_tab_name(existing: list[str]) -> str:
    """Return next sequential tab name: Inventory1, Inventory2, …"""
    n = 1
    while True:
        name = f"Inventory{n}"
        if name not in existing:
            return name
        n += 1


def _tab_has_header(svc, tab: str) -> bool:
    """Return True if the tab already has our header in A1."""
    result = svc.spreadsheets().values().get(
        spreadsheetId=SHEETS_ID, range=f"{tab}!A1:A1"
    ).execute()
    values = result.get("values", [])
    return bool(values and values[0] and values[0][0] == SHEETS_HEADER[0])


def _append_to_tab(svc, tab: str, rows: list) -> None:
    """Append rows to a specific named tab."""
    svc.spreadsheets().values().append(
        spreadsheetId=SHEETS_ID,
        range=f"{tab}!A1",
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={"values": rows},
    ).execute()


async def run_scan_to_sheets(scan_id: str):
    """Deep file scan that streams rows directly to Google Sheets instead of a local CSV.
    Automatically rolls over to a new tab every SHEETS_ROW_LIMIT rows."""
    r = scans[scan_id]
    r["status"]     = "running"
    r["start_time"] = datetime.now().isoformat()
    r["subdir_count"] = 0
    r["file_count"]   = 0
    r["size_bytes"]   = 0
    await manager.broadcast({"type": "scan_update", "scan": scan_summary(r)})

    script = _ps_deep_file_scan_stdout(r["paths"])
    buffer: list = []
    scanned_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows_in_tab = 0       # data rows written to current tab (excludes header)
    total_rows  = 0       # total data rows written across all tabs

    import csv as _csv
    import io

    def _init_tab(svc, tab: str) -> None:
        """Ensure tab exists and has a header row."""
        existing = _get_existing_sheet_titles(svc)
        if tab not in existing:
            _create_sheet_tab(svc, tab)
        if not _tab_has_header(svc, tab):
            _append_to_tab(svc, tab, [SHEETS_HEADER])

    def _roll_to_next_tab(svc) -> str:
        """Create the next Inventory tab, write header, return its name."""
        existing = _get_existing_sheet_titles(svc)
        new_tab  = _next_tab_name(existing)
        _create_sheet_tab(svc, new_tab)
        _append_to_tab(svc, new_tab, [SHEETS_HEADER])
        return new_tab

    try:
        service = await asyncio.get_event_loop().run_in_executor(None, get_sheets_service)

        # Determine starting tab — use Sheet1, or last Inventory tab
        existing_titles = await asyncio.get_event_loop().run_in_executor(
            None, _get_existing_sheet_titles, service
        )
        inventory_tabs = sorted(
            [t for t in existing_titles if t.startswith("Inventory")],
            key=lambda t: int(t[9:]) if t[9:].isdigit() else 0,
        )
        current_tab = inventory_tabs[-1] if inventory_tabs else "Sheet1"

        await asyncio.get_event_loop().run_in_executor(
            None, _init_tab, service, current_tab
        )

        proc = await asyncio.create_subprocess_exec(
            "powershell", "-NoProfile", "-NonInteractive", "-Command", script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        active_procs[scan_id] = proc

        async for raw in proc.stdout:
            line = raw.decode("utf-8", errors="replace").strip()
            if line.startswith("ROW:"):
                csv_line = line[4:]
                row = next(_csv.reader(io.StringIO(csv_line)))
                try:
                    row[4] = f"{int(row[4]) / 1_048_576:.1f}"
                except (IndexError, ValueError):
                    pass
                row.append(scanned_at)
                buffer.append(row)

                if len(buffer) >= SHEETS_BATCH_SIZE:
                    # Check if this batch would exceed the tab row limit
                    if rows_in_tab + len(buffer) >= SHEETS_ROW_LIMIT:
                        # Flush what fits, then roll over
                        headroom = SHEETS_ROW_LIMIT - rows_in_tab
                        if headroom > 0:
                            await asyncio.get_event_loop().run_in_executor(
                                None, _append_to_tab, service, current_tab, buffer[:headroom]
                            )
                            rows_in_tab += headroom
                            total_rows  += headroom
                            buffer = buffer[headroom:]

                        current_tab = await asyncio.get_event_loop().run_in_executor(
                            None, _roll_to_next_tab, service
                        )
                        rows_in_tab = 0
                        print(f"Switched to new sheet tab: {current_tab} at row {total_rows + 1}")

                    await asyncio.get_event_loop().run_in_executor(
                        None, _append_to_tab, service, current_tab, buffer
                    )
                    rows_in_tab += len(buffer)
                    total_rows  += len(buffer)
                    buffer = []

            elif line.startswith("COUNT:"):
                count = int(line[6:])
                r["count"] = count
                await manager.broadcast({"type": "count_update",
                                         "scan_id": scan_id, "count": count})
            elif line.startswith("DONE:"):
                r["count"] = int(line[5:])

        await proc.wait()

        # Flush remaining rows, rolling tab if needed
        if buffer:
            if rows_in_tab + len(buffer) >= SHEETS_ROW_LIMIT:
                headroom = SHEETS_ROW_LIMIT - rows_in_tab
                if headroom > 0:
                    await asyncio.get_event_loop().run_in_executor(
                        None, _append_to_tab, service, current_tab, buffer[:headroom]
                    )
                    total_rows += headroom
                    buffer = buffer[headroom:]
                current_tab = await asyncio.get_event_loop().run_in_executor(
                    None, _roll_to_next_tab, service
                )
                print(f"Switched to new sheet tab: {current_tab} at row {total_rows + 1}")

            if buffer:
                await asyncio.get_event_loop().run_in_executor(
                    None, _append_to_tab, service, current_tab, buffer
                )

        if r["status"] not in ("stopped",):
            r["status"] = "done" if proc.returncode == 0 else "error"

    except Exception as e:
        r["status"] = "error"
        r["error"]  = str(e)

    r["end_time"] = datetime.now().isoformat()
    active_procs.pop(scan_id, None)
    save_history()
    await manager.broadcast({"type": "scan_update", "scan": scan_summary(r)})


# ---------------------------------------------------------------------------
# Natural language parser
# ---------------------------------------------------------------------------

_PATH_HINTS = {
    "litigation":    r"C:\Users\arika\OneDrive\Litigation",
    "onedrive":      r"C:\Users\arika\OneDrive",
    "documents":     r"C:\Users\arika\Documents",
    "downloads":     r"C:\Users\arika\Downloads",
    "desktop":       r"C:\Users\arika\Desktop",
    "pictures":      r"C:\Users\arika\Pictures",
    "users":         r"C:\Users\arika",
    "repo":          r"C:\Users\arika\Repo-for-Claude-android",
    "cowork":        r"C:\Users\arika\OneDrive\CLaude Cowork",
}


def parse_nl(text: str, known_paths: list[str] = None) -> dict:
    low = text.lower()

    # Depth
    depth = None
    m = re.search(r'(\d+)\s+levels?\s+deep', low)
    if m:
        depth = int(m.group(1))

    # Scan type
    scan_type = "files" if "file" in low else "dirs"

    # Exclusions
    exclude = []
    ex = re.search(r'(?:except|excluding?|ignore|skip)\s+(.+?)(?:\s*,\s*|\s+and\s+|\s*$)', low)
    if ex:
        exclude = [e.strip() for e in re.split(r',|\band\b', ex.group(1)) if e.strip()]

    # Match paths from known tree first
    paths = []
    if known_paths:
        words = {w for w in re.findall(r'\b\w+\b', low) if len(w) > 3}
        for kp in known_paths:
            if any(w in kp.lower() for w in words):
                paths.append(kp)

    # Fall back to hardcoded hints
    if not paths:
        for keyword, path in _PATH_HINTS.items():
            if keyword in low and os.path.exists(path):
                paths.append(path)

    # Summary for confirmation card
    depth_str = f" to depth {depth}" if depth else ""
    excl_str  = f", excluding {', '.join(exclude)}" if exclude else ", no exclusions"
    type_str  = "FILE SCAN" if scan_type == "files" else "DIR SCAN"
    path_str  = ", ".join(paths) if paths else "(no matching paths found)"
    summary   = f"{type_str}: {path_str}{depth_str}{excl_str}"

    return {
        "paths":     paths,
        "depth":     depth,
        "exclude":   exclude,
        "scan_type": scan_type,
        "summary":   summary,
        "raw":       text,
    }


# ---------------------------------------------------------------------------
# Known system directories — marked in tree, skipped in bulk-select
# ---------------------------------------------------------------------------

SYSTEM_DIR_NAMES = {
    "$recycle.bin",
    "$sysreset",
    "$winreagent",
    "boot",
    "efi",
    "msocache",
    "program files",
    "program files (x86)",
    "programdata",
    "recovery",
    "system volume information",
    "windows",
    "windows.old",
}


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------

@app.get("/")
async def serve_ui():
    return FileResponse(str(UI_FILE))


@app.get("/api/drives")
async def get_drives():
    drives = []
    for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
        path = f"{letter}:\\"
        if os.path.exists(path):
            drives.append({"path": path, "name": f"{letter}:\\"})
    return {"drives": drives}


@app.get("/api/tree")
async def get_tree(path: str):
    try:
        children = []
        with os.scandir(path) as it:
            for e in it:
                try:
                    if e.is_dir(follow_symlinks=False):
                        has_kids = False
                        if os.access(e.path, os.R_OK):
                            try:
                                has_kids = any(
                                    x.is_dir(follow_symlinks=False)
                                    for x in os.scandir(e.path)
                                )
                            except (PermissionError, OSError):
                                pass
                        children.append({
                            "path":        e.path,
                            "name":        e.name,
                            "has_children": has_kids,
                            "is_system":   e.name.lower() in SYSTEM_DIR_NAMES,
                        })
                except (PermissionError, OSError):
                    pass
        children.sort(key=lambda x: x["name"].lower())
        return {"children": children}
    except PermissionError:
        return {"children": [], "error": "Permission denied"}
    except Exception as e:
        return {"children": [], "error": str(e)}


@app.post("/api/nl_parse")
async def nl_parse(body: dict):
    return parse_nl(body.get("text", ""), body.get("known_paths", []))


@app.post("/api/scan/start")
async def start_scan(body: dict):
    paths     = body.get("paths", [])
    scan_type = body.get("scan_type", "files")
    workers   = body.get("workers", 8)
    exclude   = body.get("exclude", [])
    depth     = body.get("depth")

    if not paths:
        return JSONResponse({"error": "No paths specified"}, status_code=400)

    r = new_scan(paths, scan_type, workers, exclude, depth)
    if scan_type == "deep-sheets":
        asyncio.create_task(run_scan_to_sheets(r["id"]))
    else:
        asyncio.create_task(run_scan(r["id"]))
    return {"scan_id": r["id"], "scan": scan_summary(r)}


@app.post("/api/scan/stop")
async def stop_scan(body: dict):
    sid  = body.get("scan_id")
    proc = active_procs.get(sid)
    if proc:
        try:
            proc.terminate()
        except Exception:
            pass
    r = scans.get(sid)
    if r:
        r["status"] = "stopped"
        await manager.broadcast({"type": "scan_update", "scan": scan_summary(r)})
    return {"ok": True}


@app.get("/api/open-output-dir")
async def open_output_dir():
    import subprocess
    subprocess.Popen(["explorer", str(OUTPUT_DIR)])
    return {"ok": True}


@app.get("/api/scans")
async def get_scans():
    return {"scans": [scan_summary(r) for r in scans.values()]}


@app.get("/api/scan/{scan_id}/data")
async def get_scan_data(scan_id: str, limit: int = 2000, offset: int = 0):
    import csv as _csv
    r = scans.get(scan_id)
    if not r:
        return JSONResponse({"error": "Not found"}, status_code=404)
    output_file = r.get("output_file", "")
    if not output_file or not Path(output_file).exists():
        return {"rows": [], "total": 0, "columns": [], "scan_type": r.get("scan_type")}
    try:
        with open(output_file, encoding="utf-8-sig") as f:  # utf-8-sig strips PowerShell BOM
            reader   = _csv.DictReader(f)
            columns  = list(reader.fieldnames or [])
            all_rows = list(reader)
        total = len(all_rows)
        rows  = all_rows[offset : offset + limit]
        return {"rows": rows, "total": total, "columns": columns,
                "offset": offset, "limit": limit, "scan_type": r.get("scan_type")}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.websocket("/ws/{client_id}")
async def ws_endpoint(ws: WebSocket, client_id: str):
    await manager.connect(client_id, ws)
    try:
        await ws.send_json({
            "type":  "init",
            "scans": [scan_summary(r) for r in scans.values()],
        })
        while True:
            await ws.receive_text()   # keep alive
    except WebSocketDisconnect:
        manager.disconnect(client_id)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    load_history()
    print(f"Drive Scout starting at http://localhost:8765  ({len(scans)} scans in history)")
    print("Ctrl+C to stop")
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="warning")
