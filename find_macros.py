"""
find_macros.py
Searches for .xlsm files modified since 1/1/2026 and lists all VBA macro
functions/subs found in each file.

Requires: pip install oletools
"""

import os
import sys
from datetime import datetime
from pathlib import Path

SEARCH_ROOT = r"C:\Users\arika\OneDrive"
CUTOFF_DATE = datetime(2026, 1, 1)


def check_oletools():
    try:
        from oletools.olevba import VBA_Parser
        return VBA_Parser
    except ImportError:
        print("ERROR: oletools not installed.")
        print("Run:  pip install oletools")
        sys.exit(1)


def extract_macros(filepath, VBA_Parser):
    """Return list of (type, name) tuples for all Sub/Function/Property in the file."""
    macros = []
    try:
        vba = VBA_Parser(str(filepath))
        if not vba.detect_vba_macros():
            return macros
        for (filename, stream_path, vba_filename, vba_code) in vba.extract_macros():
            for line in vba_code.splitlines():
                stripped = line.strip()
                # Match Sub, Function, Property Get/Let/Set
                for keyword in ("Sub ", "Function ", "Property Get ", "Property Let ", "Property Set "):
                    if stripped.lower().startswith(keyword.lower()):
                        # Skip End Sub / End Function etc.
                        if stripped.lower().startswith("end "):
                            break
                        # Extract the name (text before the first '(')
                        rest = stripped[len(keyword):]
                        name = rest.split("(")[0].strip()
                        if name:
                            macros.append((keyword.strip(), name))
                        break
        vba.close()
    except Exception as e:
        print(f"  [could not read: {e}]")
    return macros


def main():
    VBA_Parser = check_oletools()

    search_root = Path(SEARCH_ROOT)
    print(f"Searching under: {search_root}")
    print(f"Modified since:  {CUTOFF_DATE.strftime('%Y-%m-%d')}")
    print("=" * 70)

    found_files = 0
    files_with_macros = 0

    for xlsm in search_root.rglob("*.xlsm"):
        try:
            mtime = datetime.fromtimestamp(xlsm.stat().st_mtime)
        except OSError:
            continue

        if mtime < CUTOFF_DATE:
            continue

        found_files += 1
        rel = xlsm.relative_to(search_root)
        print(f"\n[{mtime.strftime('%Y-%m-%d')}]  {rel}")

        macros = extract_macros(xlsm, VBA_Parser)
        if macros:
            files_with_macros += 1
            seen = set()
            for kind, name in macros:
                key = (kind, name)
                if key not in seen:
                    seen.add(key)
                    print(f"    {kind:<20} {name}")
        else:
            print("    (no macros found)")

    print("\n" + "=" * 70)
    print(f"Files scanned (since {CUTOFF_DATE.strftime('%Y-%m-%d')}): {found_files}")
    print(f"Files with macros: {files_with_macros}")


if __name__ == "__main__":
    main()
