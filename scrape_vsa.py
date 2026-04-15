"""
scrape_vsa.py — Scrape Vermont Statutes Annotated chapters to markdown files.

Usage:
    python scrape_vsa.py

Scrapes all chapters for configured titles from legislature.vermont.gov
and saves as individual markdown files.
"""

import httpx
import os
import re
import sys
import io
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = 'https://legislature.vermont.gov/statutes'
OUT_ROOT = r'C:\Users\arika\OneDrive\Litigation\Statutes\Vermont'

# Titles to scrape — use zero-padded numbers for URL
TITLES = {
    '08': 'Insurance',
    '09': 'Commerce and Trade',
    '12': 'Court Procedure',
    '13': 'Crimes and Criminal Procedure',
    '14': 'Decedents Estates and Fiduciary Relations',
    '14A': 'Trusts',
    '15': 'Domestic Relations',
    '27': 'Property',
}

# For filenames: use unpadded numbers (VSA_8.1 not VSA_08.1)
TITLE_UNPADDED = {
    '08': '8', '09': '9', '12': '12', '13': '13',
    '14': '14', '14A': '14A', '15': '15', '27': '27',
}

client = httpx.Client(follow_redirects=True, timeout=60)


def get_chapters(title_padded):
    """Fetch title page and return [(ch_num_padded, ch_name), ...]"""
    url = f'{BASE}/title/{title_padded}'
    resp = client.get(url)
    if resp.status_code != 200:
        print(f'  ERROR: {url} returned {resp.status_code}')
        return []

    html = resp.text
    chapters = []
    seen = set()

    for m in re.finditer(
        r'href="[^"]*statutes/chapter/\d+\w?/(\d+)"[^>]*>(.*?)</a>',
        html, re.DOTALL
    ):
        ch_num, link_text = m.group(1), m.group(2)
        if ch_num in seen:
            continue
        seen.add(ch_num)
        ch_name = re.sub(r'<[^>]+>', '', link_text).strip()
        ch_name = re.sub(r'^Chapter\s+\d+\w?\s*:\s*', '', ch_name).strip()
        chapters.append((ch_num, ch_name))

    return chapters


def fetch_full_chapter(title_padded, ch_num_padded):
    """Fetch full chapter text and return list of (section_header, section_body) tuples."""
    url = f'{BASE}/fullchapter/{title_padded}/{ch_num_padded}'
    resp = client.get(url)
    if resp.status_code != 200:
        return None, url

    html = resp.text

    # Extract statute sections from list items
    sections = []
    for li in re.finditer(r'<li><p></p>(.*?)</li>', html, re.DOTALL):
        block = li.group(1)
        if not block.strip() or block.strip() == '<p></p>':
            continue

        text = block
        # Section headers → ## heading
        text = re.sub(
            r'<p[^>]*><b>([^<]+)</b></p>',
            lambda m: f'\n## {m.group(1).strip()}\n',
            text
        )
        # Any remaining bold
        text = re.sub(r'<b>(.*?)</b>', r'**\1**', text)
        # Paragraphs → newlines, preserving indent via leading spaces
        # Detect indent level from style
        def p_replace(m):
            style = m.group(1) or ''
            indent_match = re.search(r'text-indent:\s*([\d.]+)px', style)
            margin_match = re.search(r'margin-left:\s*([\d.]+)px', style)
            indent = 0
            if indent_match:
                indent = int(float(indent_match.group(1)) / 19)  # ~19px per level
            if margin_match:
                indent = max(indent, int(float(margin_match.group(1)) / 19))
            return '\n' + ('   ' * indent)

        text = re.sub(r'<p([^>]*)>', p_replace, text)
        text = re.sub(r'</p>', '', text)
        # Strip remaining HTML
        text = re.sub(r'<[^>]+>', '', text)
        # Fix section symbol
        text = text.replace('\xa7', '§')
        # Clean whitespace
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = text.strip()

        if text:
            sections.append(text)

    return sections, url


def write_chapter(title_padded, title_name, ch_num_padded, ch_name, sections, url):
    """Write a chapter markdown file."""
    t = TITLE_UNPADDED[title_padded]
    ch_int = ch_num_padded.lstrip('0') or '0'

    folder = os.path.join(OUT_ROOT, f'Title {t}')
    os.makedirs(folder, exist_ok=True)

    filename = f'VSA_{t}.{ch_int} {ch_name}.md'
    # Sanitize filename
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    filepath = os.path.join(folder, filename)

    md = f'# VSA Title {t}, Chapter {ch_int}: {ch_name}\n\n'
    md += f'**Title {t}:** {title_name}\n'
    md += f'**Source:** {url}\n'
    md += f'**Retrieved:** 2026-04-10\n\n'
    md += '---\n\n'

    for s in sections:
        md += s + '\n\n'

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(md)

    return filepath


def main():
    index_entries = []
    total_chapters = 0
    total_sections = 0
    errors = []

    for title_padded, title_name in TITLES.items():
        t = TITLE_UNPADDED[title_padded]
        print(f'\n{"="*60}')
        print(f'Title {t}: {title_name}')
        print(f'{"="*60}')

        chapters = get_chapters(title_padded)
        if not chapters:
            errors.append(f'Title {t}: no chapters found')
            continue

        print(f'  Found {len(chapters)} chapters')
        index_entries.append((t, title_name, []))

        for ch_num, ch_name in chapters:
            sections, url = fetch_full_chapter(title_padded, ch_num)
            if sections is None:
                print(f'  Ch {ch_num} {ch_name}: FAILED')
                errors.append(f'VSA_{t}.{ch_num.lstrip("0")} {ch_name}: fetch failed')
                continue

            filepath = write_chapter(
                title_padded, title_name, ch_num, ch_name, sections, url
            )
            ch_int = ch_num.lstrip('0') or '0'
            print(f'  VSA_{t}.{ch_int} {ch_name} — {len(sections)} sections')
            index_entries[-1][2].append((ch_int, ch_name, len(sections)))
            total_chapters += 1
            total_sections += len(sections)

            # Be polite to the server
            time.sleep(0.3)

    # Write index.md
    index_md = '# Vermont Statutes — Index\n\n'
    index_md += f'**Retrieved:** 2026-04-10\n'
    index_md += f'**Source:** https://legislature.vermont.gov/statutes/\n'
    index_md += f'**Titles:** {len(TITLES)}\n'
    index_md += f'**Chapters:** {total_chapters}\n'
    index_md += f'**Sections:** {total_sections}\n\n'
    index_md += '---\n\n'

    for t, title_name, chs in index_entries:
        index_md += f'## Title {t}: {title_name}\n\n'
        for ch_int, ch_name, sec_count in chs:
            index_md += f'- VSA_{t}.{ch_int} {ch_name} ({sec_count} sections)\n'
        index_md += '\n'

    index_path = os.path.join(OUT_ROOT, 'index.md')
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(index_md)

    # Summary
    print(f'\n{"="*60}')
    print(f'DONE: {total_chapters} chapters, {total_sections} sections')
    print(f'Index: {index_path}')
    if errors:
        print(f'\nERRORS ({len(errors)}):')
        for e in errors:
            print(f'  {e}')
    print(f'{"="*60}')


if __name__ == '__main__':
    main()
