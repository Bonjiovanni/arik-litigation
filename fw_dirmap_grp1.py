"""
fw_dirmap_grp1.py
-----------------
Group 1 utility module for the litigation file-walker directory mapper agent.

Contains three foundational functions:

  pick_scan_dirs()
      Presents a native Windows IFileOpenDialog for multi-folder selection.
      Falls back to a plain input() prompt if COM/ctypes is unavailable.

  validate_and_normalize_path(raw)
      Cleans, resolves, and validates a raw path string, returning a
      normalized forward-slash absolute path.

  generate_run_id()
      Returns a timestamped run ID string in the format DIRMAP_YYYYMMDD_HHMMSS.
"""

import os
import ctypes
import ctypes.wintypes
from datetime import datetime


# --- pick_scan_dirs

def pick_scan_dirs() -> list[str]:
    """
    Open a native Windows IFileOpenDialog to let the user select one or more
    folders. Falls back to a plain input() prompt if COM/ctypes fails.

    Returns:
        list[str]: Selected folder paths as raw strings (not normalized).
                   Empty list if the user cancels the dialog.
    """
    FOS_ALLOWMULTISELECT = 0x00000200
    FOS_PICKFOLDERS      = 0x00000020

    CLSID_FileOpenDialog = "{DC1C5A9C-E88A-4DDE-A5A1-60F82A20AEF7}"
    IID_IFileOpenDialog  = "{D57C7288-D4AD-4768-BE02-9D969532D960}"
    IID_IShellItemArray  = "{B63EA76D-1F85-456F-A19C-48159EFA858B}"
    IID_IShellItem       = "{43826D1E-E718-42EE-BC55-A1E261C37BFE}"

    try:
        ole32    = ctypes.windll.ole32
        shell32  = ctypes.windll.shell32

        ole32.CoInitialize(None)

        # --- Create the FileOpenDialog COM object
        clsid = ctypes.create_string_buffer(16)
        iid_dlg = ctypes.create_string_buffer(16)
        iid_arr = ctypes.create_string_buffer(16)

        ole32.CLSIDFromString(CLSID_FileOpenDialog,  clsid)
        ole32.IIDFromString(IID_IFileOpenDialog,     iid_dlg)
        ole32.IIDFromString(IID_IShellItemArray,     iid_arr)

        dialog_ptr = ctypes.c_void_p()
        hr = ole32.CoCreateInstance(
            clsid,
            None,
            0x1,            # CLSCTX_INPROC_SERVER
            iid_dlg,
            ctypes.byref(dialog_ptr),
        )
        if hr != 0:
            raise OSError(f"CoCreateInstance failed: HRESULT {hr:#010x}")

        vtable = ctypes.cast(dialog_ptr, ctypes.POINTER(ctypes.c_void_p))
        vtable_ptr = ctypes.cast(vtable[0], ctypes.POINTER(ctypes.c_void_p))

        PROTO_GetOptions = ctypes.WINFUNCTYPE(
            ctypes.HRESULT, ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32)
        )
        PROTO_SetOptions = ctypes.WINFUNCTYPE(
            ctypes.HRESULT, ctypes.c_void_p, ctypes.c_uint32
        )

        get_options_fn = PROTO_GetOptions(vtable_ptr[10])
        set_options_fn = PROTO_SetOptions(vtable_ptr[9])

        current_opts = ctypes.c_uint32(0)
        hr = get_options_fn(dialog_ptr, ctypes.byref(current_opts))
        if hr != 0:
            raise OSError(f"GetOptions failed: HRESULT {hr:#010x}")

        new_opts = current_opts.value | FOS_PICKFOLDERS | FOS_ALLOWMULTISELECT
        hr = set_options_fn(dialog_ptr, new_opts)
        if hr != 0:
            raise OSError(f"SetOptions failed: HRESULT {hr:#010x}")

        PROTO_Show = ctypes.WINFUNCTYPE(ctypes.HRESULT, ctypes.c_void_p, ctypes.c_void_p)
        show_fn = PROTO_Show(vtable_ptr[3])
        hr = show_fn(dialog_ptr, None)

        CANCELLED = ctypes.c_long(0x800704C7).value
        if hr == CANCELLED:
            return []
        if hr != 0:
            raise OSError(f"Show failed: HRESULT {hr:#010x}")

        PROTO_GetResults = ctypes.WINFUNCTYPE(
            ctypes.HRESULT, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)
        )
        get_results_fn = PROTO_GetResults(vtable_ptr[27])
        arr_ptr = ctypes.c_void_p()
        hr = get_results_fn(dialog_ptr, ctypes.byref(arr_ptr))
        if hr != 0:
            raise OSError(f"GetResults failed: HRESULT {hr:#010x}")

        arr_vtable = ctypes.cast(
            ctypes.cast(arr_ptr, ctypes.POINTER(ctypes.c_void_p))[0],
            ctypes.POINTER(ctypes.c_void_p),
        )

        PROTO_GetCount = ctypes.WINFUNCTYPE(
            ctypes.HRESULT, ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32)
        )
        PROTO_GetItemAt = ctypes.WINFUNCTYPE(
            ctypes.HRESULT, ctypes.c_void_p, ctypes.c_uint32, ctypes.POINTER(ctypes.c_void_p)
        )

        get_count_fn   = PROTO_GetCount(arr_vtable[7])
        get_item_at_fn = PROTO_GetItemAt(arr_vtable[8])

        item_count = ctypes.c_uint32(0)
        hr = get_count_fn(arr_ptr, ctypes.byref(item_count))
        if hr != 0:
            raise OSError(f"IShellItemArray::GetCount failed: HRESULT {hr:#010x}")

        SIGDN_FILESYSPATH = ctypes.c_int(0x80058000)

        PROTO_GetDisplayName = ctypes.WINFUNCTYPE(
            ctypes.HRESULT, ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_wchar_p)
        )
        PROTO_Release = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)

        paths: list[str] = []
        for i in range(item_count.value):
            item_ptr = ctypes.c_void_p()
            hr = get_item_at_fn(arr_ptr, i, ctypes.byref(item_ptr))
            if hr != 0:
                continue

            item_vtable = ctypes.cast(
                ctypes.cast(item_ptr, ctypes.POINTER(ctypes.c_void_p))[0],
                ctypes.POINTER(ctypes.c_void_p),
            )
            get_display_name_fn = PROTO_GetDisplayName(item_vtable[5])
            release_item_fn     = PROTO_Release(item_vtable[2])

            path_buf = ctypes.c_wchar_p()
            hr = get_display_name_fn(item_ptr, SIGDN_FILESYSPATH.value, ctypes.byref(path_buf))
            if hr == 0 and path_buf.value:
                paths.append(path_buf.value)
                ole32.CoTaskMemFree(path_buf)

            release_item_fn(item_ptr)

        arr_release_fn = PROTO_Release(arr_vtable[2])
        arr_release_fn(arr_ptr)

        dlg_release_fn = PROTO_Release(vtable_ptr[2])
        dlg_release_fn(dialog_ptr)

        ole32.CoUninitialize()
        return paths

    except Exception as exc:
        print(
            f"\n[fw_dirmap_grp1] WARNING: Native folder dialog unavailable ({exc}).\n"
            "Falling back to manual path entry.\n"
            "Enter one folder path per line. Press Enter on a blank line when done.\n"
        )
        paths: list[str] = []
        while True:
            line = input("  Folder path (blank to finish): ")
            if not line.strip():
                break
            paths.append(line)
        return paths


# --- validate_and_normalize_path

def validate_and_normalize_path(raw: str) -> str:
    """
    Clean, resolve, and validate a raw path string.

    Processing steps applied in order:
      1. Strip surrounding whitespace.
      2. Strip surrounding single or double quotes.
      3. Expand a leading tilde to the current user's home directory.
      4. Convert to an absolute path.
      5. Normalize directory separators to forward slashes.
      6. Confirm the path exists and is a directory.

    Args:
        raw (str): The raw path string to process.

    Returns:
        str: A clean, absolute, forward-slash path string.

    Raises:
        ValueError: If the resolved path does not exist on disk, or exists
                    but is not a directory.
    """
    cleaned = raw.strip()
    if (cleaned.startswith('"') and cleaned.endswith('"')) or \
       (cleaned.startswith("'") and cleaned.endswith("'")):
        cleaned = cleaned[1:-1]

    cleaned = os.path.expanduser(cleaned)
    cleaned = os.path.abspath(cleaned)
    cleaned = cleaned.replace("\\", "/")

    if not os.path.exists(cleaned):
        raise ValueError(
            f"Path does not exist on disk: '{cleaned}'"
        )
    if not os.path.isdir(cleaned):
        raise ValueError(
            f"Path exists but is not a directory: '{cleaned}'"
        )

    return cleaned


# --- generate_run_id

def generate_run_id() -> str:
    """
    Generate a timestamped run ID for a directory-mapper session.

    The ID is based on local wall-clock time at the moment of the call.

    Returns:
        str: A run ID string in the format ``DIRMAP_YYYYMMDD_HHMMSS``.
             Example: ``"DIRMAP_20260315_143022"``
    """
    now = datetime.now()
    return now.strftime("DIRMAP_%Y%m%d_%H%M%S")
