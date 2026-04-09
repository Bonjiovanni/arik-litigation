#!/usr/bin/env python3
"""
PDF Package Builder
-------------------
Downloads PDFs from Google Drive share links, checks/runs OCR as needed,
merges into a single PDF with cover page, headers/footers, and optional
keyword highlighting.

Dependencies:
    pip install requests pymupdf ocrmypdf
    Tesseract must be installed for OCR:
        https://github.com/UB-Mannheim/tesseract/wiki
"""

import os
import re
import json
import threading
import requests
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote

try:
    import fitz  # PyMuPDF
except ImportError:
    raise SystemExit("PyMuPDF not installed.  Run: pip install pymupdf")

try:
    import ocrmypdf
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

# ---------------------------------------------------------------------------
# Config persistence
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "pdf_package_builder.json"
DEFAULT_OUTPUT_DIR = r"C:\Users\arika\OneDrive\Litigation\08_INCOMING\Query PDFs"


def load_config():
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"last_output_dir": DEFAULT_OUTPUT_DIR}


def save_config(cfg):
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Keyword parsing
# ---------------------------------------------------------------------------

def parse_keywords(raw):
    """
    Parse a comma-separated keyword string. Quotes are optional.
    '  "trust", "beneficiary" , asset ' -> ['trust', 'beneficiary', 'asset']
    """
    keywords = []
    for part in raw.split(","):
        kw = part.strip().strip('"').strip("'").strip()
        if kw:
            keywords.append(kw)
    return keywords


# ---------------------------------------------------------------------------
# Google Drive download
# ---------------------------------------------------------------------------

def extract_file_id(url):
    for pattern in [r"/file/d/([a-zA-Z0-9_-]+)", r"[?&]id=([a-zA-Z0-9_-]+)"]:
        m = re.search(pattern, url)
        if m:
            return m.group(1)
    return None


def download_gdrive(url, dest_dir):
    file_id = extract_file_id(url)
    if not file_id:
        raise ValueError("Cannot parse file ID from URL")

    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})

    dl_url = f"https://drive.google.com/uc?export=download&id={file_id}"
    r = session.get(dl_url, stream=True, timeout=30)
    r.raise_for_status()

    # Virus-scan warning bypass
    if "text/html" in r.headers.get("Content-Type", ""):
        html = r.text
        m = re.search(r"confirm=([0-9A-Za-z_-]+)", html)
        token = m.group(1) if m else "t"
        dl_url = f"https://drive.google.com/uc?export=download&id={file_id}&confirm={token}"
        r = session.get(dl_url, stream=True, timeout=90)
        r.raise_for_status()

    # Filename from Content-Disposition
    cd = r.headers.get("Content-Disposition", "")
    m = re.search(r"filename\*=UTF-8''([^;\n]+)", cd)
    if m:
        filename = unquote(m.group(1).strip())
    else:
        m = re.search(r'filename=["\']?([^"\';\n]+)', cd)
        filename = m.group(1).strip().strip('"\'') if m else f"{file_id}.pdf"

    if not filename.lower().endswith(".pdf"):
        filename += ".pdf"

    dest = Path(dest_dir) / filename
    if dest.exists():
        for i in range(1, 1000):
            candidate = dest.parent / f"{dest.stem}_{i}.pdf"
            if not candidate.exists():
                dest = candidate
                break

    with open(dest, "wb") as f:
        for chunk in r.iter_content(65536):
            if chunk:
                f.write(chunk)

    return dest, filename


# ---------------------------------------------------------------------------
# OCR helpers
# ---------------------------------------------------------------------------

def has_text_layer(filepath, min_chars=100):
    """Return True if the PDF has enough extractable text to be considered OCR'd."""
    doc = fitz.open(str(filepath))
    total = 0
    for i in range(min(5, len(doc))):
        total += len(doc[i].get_text().strip())
    doc.close()
    return total >= min_chars


def run_ocr(filepath, log_fn):
    """
    Run OCR on filepath via ocrmypdf.  Returns the path to the OCR'd file
    (a new _ocr.pdf sibling); the original is left untouched.
    """
    if not OCR_AVAILABLE:
        log_fn("    ! ocrmypdf not installed — skipping OCR, file included as-is.")
        return filepath

    out_path = filepath.parent / (filepath.stem + "_ocr.pdf")
    log_fn(f"    Running OCR on {filepath.name} ...")
    try:
        ocrmypdf.ocr(
            str(filepath),
            str(out_path),
            skip_text=True,
            language="eng",
            progress_bar=False,
        )
        log_fn("    OCR complete.")
        return out_path
    except Exception as e:
        log_fn(f"    OCR failed: {e}  — file included as-is.")
        if out_path.exists():
            out_path.unlink()
        return filepath


# ---------------------------------------------------------------------------
# Cover page
# ---------------------------------------------------------------------------

def create_cover(package_name, toc_entries, run_dt):
    """Return a single-page fitz.Document with package name and TOC."""
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    m = 72  # 1-inch margin
    y = m

    # Title
    page.insert_text((m, y + 26), package_name, fontsize=22, fontname="helv")
    y += 48
    page.insert_text(
        (m, y + 10), f"Generated: {run_dt}",
        fontsize=9, fontname="helv", color=(0.4, 0.4, 0.4),
    )
    y += 26
    page.draw_line((m, y), (612 - m, y), color=(0, 0, 0), width=0.5)
    y += 20
    page.insert_text((m, y + 12), "TABLE OF CONTENTS", fontsize=11, fontname="helv")
    y += 30

    for entry in toc_entries:
        if y > 792 - m:
            break
        status = entry["status"]
        if status in ("included", "ocr_added"):
            prefix = "[OCR added]  " if status == "ocr_added" else ""
            color = (0.05, 0.4, 0.05) if status == "ocr_added" else (0, 0, 0)
            pg_label = f"p. {entry['page_start']}"
        else:
            prefix = "[FAILED — not included]  "
            color = (0.7, 0, 0)
            pg_label = ""

        page.insert_text(
            (m + 10, y + 9),
            prefix + entry["filename"],
            fontsize=9, fontname="helv", color=color,
        )
        if pg_label:
            page.insert_text(
                (612 - m - 55, y + 9), pg_label,
                fontsize=9, fontname="helv", color=color,
            )
        y += 15

    return doc


# ---------------------------------------------------------------------------
# Headers / footers
# ---------------------------------------------------------------------------

def add_decorations(doc, page_manifest, run_dt):
    """
    page_manifest[i] = source filename label for page i.
    Page 0 is always the cover.
    Header: run date/time, top-right, 9 pt.
    Footer left: source filename, 9 pt.
    Footer right: page X / total, 9 pt.
    """
    fs = 9
    total = len(doc)
    mx = 40  # horizontal margin for decorations

    for i, page in enumerate(doc):
        r = page.rect
        footer_y = r.height - 20
        header_y = 14

        # Header — date/time, top-right
        page.insert_text(
            (r.width - mx - 120, header_y),
            run_dt, fontsize=fs, fontname="helv", color=(0.45, 0.45, 0.45),
        )

        # Footer left — source filename
        src = page_manifest[i] if i < len(page_manifest) else ""
        if len(src) > 80:
            src = src[:77] + "..."
        page.insert_text(
            (mx, footer_y),
            src, fontsize=fs, fontname="helv", color=(0.45, 0.45, 0.45),
        )

        # Footer right — page number
        page.insert_text(
            (r.width - mx - 50, footer_y),
            f"{i + 1} / {total}",
            fontsize=fs, fontname="helv", color=(0.45, 0.45, 0.45),
        )


# ---------------------------------------------------------------------------
# Keyword highlighting
# ---------------------------------------------------------------------------

def highlight_keywords(doc, keywords, start_page=1):
    """
    Highlight each keyword (+ 3 words on either side) in orange on every page
    from start_page onward.  Case-insensitive, partial-word match.
    Returns total highlight count across all keywords.
    """
    total_count = 0

    for page_idx in range(start_page, len(doc)):
        page = doc[page_idx]
        # words: (x0, y0, x1, y1, word, block_no, line_no, word_no)
        words = page.get_text("words")
        if not words:
            continue

        for kw in keywords:
            kw_lower = kw.lower()
            match_indices = [
                i for i, w in enumerate(words) if kw_lower in w[4].lower()
            ]
            for mi in match_indices:
                start = max(0, mi - 3)
                end = min(len(words) - 1, mi + 3)
                rects = [
                    fitz.Rect(w[0], w[1], w[2], w[3])
                    for w in words[start:end + 1]
                ]
                annot = page.add_highlight_annot(rects)
                annot.set_colors(stroke=(1, 0.65, 0))  # orange
                annot.update()
                total_count += 1

    return total_count


# ---------------------------------------------------------------------------
# Filename safety / auto-increment
# ---------------------------------------------------------------------------

def next_path(path):
    path = Path(path)
    if not path.exists():
        return path
    for i in range(1, 10000):
        candidate = path.parent / f"{path.stem}_{i}{path.suffix}"
        if not candidate.exists():
            return candidate
    raise RuntimeError("Cannot find a free output filename.")


# ---------------------------------------------------------------------------
# Main build pipeline
# ---------------------------------------------------------------------------

def build_package(package_name, links, output_dir, keywords, log_fn):
    run_dt = datetime.now().strftime("%Y-%m-%d  %H:%M")
    os.makedirs(output_dir, exist_ok=True)
    links = [l.strip() for l in links if l.strip()]

    # ── Phase 1: Download ────────────────────────────────────────────────────
    log_fn("── Phase 1: Downloading ─────────────────────────────")
    dl_results = []
    for i, url in enumerate(links, 1):
        log_fn(f"  [{i}/{len(links)}] {url[:72]}...")
        try:
            fpath, fname = download_gdrive(url, output_dir)
            log_fn(f"    OK: {fname}")
            dl_results.append({"url": url, "status": "ok", "filepath": fpath, "filename": fname})
        except Exception as e:
            log_fn(f"    FAILED: {e}")
            dl_results.append({
                "url": url, "status": "failed",
                "error": str(e),
                "filename": extract_file_id(url) or url,
            })

    ok_results = [r for r in dl_results if r["status"] == "ok"]
    failed_dl  = [r for r in dl_results if r["status"] == "failed"]

    # ── Phase 2: OCR check / repair ─────────────────────────────────────────
    log_fn("\n── Phase 2: OCR Check ───────────────────────────────")
    for r in ok_results:
        if has_text_layer(r["filepath"]):
            log_fn(f"  OK  (text layer present): {r['filename']}")
            r["ocr_added"] = False
        else:
            log_fn(f"  NO text layer: {r['filename']}")
            r["filepath"] = run_ocr(r["filepath"], log_fn)
            r["ocr_added"] = True

    # ── Phase 3: Merge ───────────────────────────────────────────────────────
    log_fn("\n── Phase 3: Merging ─────────────────────────────────")
    merged = fitz.open()
    page_manifest = []   # index i → source label for page i (page 0 = cover)
    toc_entries   = []
    current_page  = 2    # 1-indexed; page 1 is the cover
    merge_failed  = []

    for r in ok_results:
        try:
            src = fitz.open(str(r["filepath"]))
            n = len(src)
            status = "ocr_added" if r["ocr_added"] else "included"
            toc_entries.append({
                "filename": r["filename"],
                "status": status,
                "page_start": current_page,
            })
            merged.insert_pdf(src)
            page_manifest.extend([r["filename"]] * n)
            current_page += n
            src.close()
            log_fn(f"  {r['filename']}  ({n} pages)")
        except Exception as e:
            log_fn(f"  MERGE FAILED — {r['filename']}: {e}")
            merge_failed.append((r["filename"], str(e)))
            toc_entries.append({"filename": r["filename"], "status": "failed"})

    for r in failed_dl:
        toc_entries.append({"filename": r["filename"], "status": "failed"})

    # ── Phase 4: Cover page ──────────────────────────────────────────────────
    log_fn("\n── Phase 4: Cover page ──────────────────────────────")
    cover = create_cover(package_name, toc_entries, run_dt)
    merged.insert_pdf(cover, start_at=0)
    cover.close()
    # Cover page label for footer
    page_manifest.insert(0, package_name)

    # ── Phase 5: Headers / footers ───────────────────────────────────────────
    log_fn("── Phase 5: Headers / footers ───────────────────────")
    add_decorations(merged, page_manifest, run_dt)

    # ── Phase 6: Keyword highlighting ────────────────────────────────────────
    highlight_count = 0
    if keywords:
        kw_display = ", ".join(f'"{k}"' for k in keywords)
        log_fn(f"── Phase 6: Highlighting {kw_display} ──────────────")
        highlight_count = highlight_keywords(merged, keywords, start_page=1)
        log_fn(f"  {highlight_count} highlight(s) added")

    # ── Save ─────────────────────────────────────────────────────────────────
    safe_name = re.sub(r'[<>:"/\\|?*]', "_", package_name).strip()
    out_path  = next_path(Path(output_dir) / f"{safe_name}.pdf")
    merged.save(str(out_path), garbage=4, deflate=True)
    total_pages = len(merged)
    merged.close()

    all_failed = (
        [(r["filename"], r.get("error", "")) for r in failed_dl]
        + merge_failed
    )

    return {
        "output":          out_path,
        "toc_entries":     toc_entries,
        "failed":          all_failed,
        "total_pages":     total_pages,
        "highlight_count": highlight_count,
    }


# ---------------------------------------------------------------------------
# GUI
# ---------------------------------------------------------------------------

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PDF Package Builder")
        self.cfg = load_config()
        self._build_ui()
        self.minsize(700, 680)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(3, weight=2)
        self.rowconfigure(5, weight=1)

    def _build_ui(self):
        p = {"padx": 12, "pady": 5}

        # Package name
        tk.Label(self, text="Package Name:", anchor="w").grid(
            row=0, column=0, sticky="w", **p)
        self.name_var = tk.StringVar()
        tk.Entry(self, textvariable=self.name_var, width=54).grid(
            row=0, column=1, columnspan=2, sticky="ew", **p)

        # Keywords
        tk.Label(self, text='Keywords (optional):\ncomma-separated,\nquotes optional',
                 anchor="nw", justify="left").grid(row=1, column=0, sticky="nw", **p)
        self.kw_var = tk.StringVar()
        tk.Entry(self, textvariable=self.kw_var, width=54).grid(
            row=1, column=1, columnspan=2, sticky="ew", **p)
        tk.Label(self, text='e.g.  "trust", "beneficiary", asset',
                 fg="#666", font=("Helvetica", 8)).grid(
            row=2, column=1, sticky="w", padx=12, pady=0)

        # Output folder
        tk.Label(self, text="Output Folder:", anchor="w").grid(
            row=3, column=0, sticky="nw", padx=12, pady=5)
        folder_frame = tk.Frame(self)
        folder_frame.grid(row=3, column=1, columnspan=2, sticky="new", padx=12, pady=5)
        self.dir_var = tk.StringVar(value=self.cfg.get("last_output_dir", DEFAULT_OUTPUT_DIR))
        tk.Entry(folder_frame, textvariable=self.dir_var, width=48).pack(side="left", fill="x", expand=True)
        tk.Button(folder_frame, text="Browse...", command=self._browse).pack(side="left", padx=(6, 0))

        # Links
        tk.Label(self, text="Google Drive Links\n(one per line):",
                 anchor="nw", justify="left").grid(row=4, column=0, sticky="nw", **p)
        self.links_text = scrolledtext.ScrolledText(self, width=56, height=14, wrap="word")
        self.links_text.grid(row=4, column=1, columnspan=2, sticky="nsew", **p)

        # Build button
        self.go_btn = tk.Button(
            self, text="Build Package", command=self._run,
            bg="#2a7a2a", fg="white",
            font=("Helvetica", 12, "bold"), padx=16, pady=8,
        )
        self.go_btn.grid(row=5, column=0, columnspan=3, pady=12)

        # Log
        tk.Label(self, text="Log:", anchor="w").grid(row=6, column=0, sticky="nw", **p)
        self.log_box = scrolledtext.ScrolledText(
            self, width=56, height=10, state="disabled", bg="#f5f5f5")
        self.log_box.grid(row=6, column=1, columnspan=2, sticky="nsew", **p)

        self.rowconfigure(4, weight=2)
        self.rowconfigure(6, weight=1)

    def _browse(self):
        d = filedialog.askdirectory(initialdir=self.dir_var.get())
        if d:
            self.dir_var.set(d)

    def _log(self, msg):
        """Thread-safe: schedule log append on the main thread."""
        self.after(0, lambda m=msg: self._log_direct(m))

    def _log_direct(self, msg):
        self.log_box.config(state="normal")
        self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")
        self.log_box.config(state="disabled")

    def _run(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showerror("Missing", "Enter a package name.")
            return

        raw_links = self.links_text.get("1.0", "end").strip().splitlines()
        links = [l.strip() for l in raw_links if l.strip()]
        if not links:
            messagebox.showerror("Missing", "Paste at least one Google Drive link.")
            return

        output_dir = self.dir_var.get().strip()
        if not output_dir:
            messagebox.showerror("Missing", "Set an output folder.")
            return

        keywords = parse_keywords(self.kw_var.get())

        # Persist folder choice
        self.cfg["last_output_dir"] = output_dir
        save_config(self.cfg)

        # Clear log and disable button
        self.log_box.config(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.config(state="disabled")
        self.go_btn.config(state="disabled", text="Working...")

        def worker():
            try:
                result = build_package(name, links, output_dir, keywords, self._log)

                included = [e for e in result["toc_entries"]
                            if e["status"] in ("included", "ocr_added")]
                failed   = result["failed"]

                self._log("\n── SUMMARY ──────────────────────────────────────")
                self._log(f"  Output      : {result['output']}")
                self._log(f"  Total pages : {result['total_pages']}")
                self._log(f"  Included ({len(included)}):")
                for e in included:
                    tag = "  [OCR added]" if e["status"] == "ocr_added" else ""
                    self._log(f"    {e['filename']}{tag}")
                if failed:
                    self._log(f"  Failed ({len(failed)}):")
                    for fname, err in failed:
                        self._log(f"    FAILED: {fname}" + (f"  ({err})" if err else ""))
                if keywords:
                    self._log(
                        f"  Keywords    : {', '.join(keywords)}"
                        f"  —  {result['highlight_count']} highlight(s)"
                    )

                summary = (
                    f"Package saved:\n{result['output']}\n\n"
                    f"{result['total_pages']} pages  |  "
                    f"{len(included)} docs included"
                )
                if failed:
                    summary += f"  |  {len(failed)} failed"
                if keywords:
                    summary += f"\n{result['highlight_count']} keyword highlight(s)"

                self.after(0, lambda: messagebox.showinfo("Done", summary))

            except Exception as e:
                self._log(f"\nFATAL ERROR: {e}")
                self.after(0, lambda: messagebox.showerror("Error", str(e)))
            finally:
                self.after(0, lambda: self.go_btn.config(state="normal", text="Build Package"))

        threading.Thread(target=worker, daemon=True).start()


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    App().mainloop()
