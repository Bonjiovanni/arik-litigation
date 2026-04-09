"""
ELynah Forum Scraper
====================
Scrapes BearLover's posts (u=2143) and all community responses in those threads.

CURRENT CUTOFF: 7 days ago (smoke test mode)
For full production run, change CUTOFF_DATE to: datetime(2025, 8, 1, tzinfo=timezone.utc)

Auto-detects Colab vs local:
  - Colab : output goes to Google Drive (survives session drops)
  - Local : output goes to elynah_output/ next to the script

Output structure:
  <OUTPUT_DIR>/
    elynah_forum.db        SQLite — primary store
    checkpoint.json        Resume state (re-run anytime to continue)
    scraper.log
    exports/
      threads.csv
      posts.csv
      post_quotes.csv
      posts.parquet         (requires pyarrow)
      post_quotes.parquet

Colab setup (run in a notebook cell before executing this script):
  from google.colab import drive
  drive.mount('/content/drive')
  !pip install requests beautifulsoup4 pandas pyarrow -q
  !python "/content/drive/MyDrive/Hockey Analysis/elynah/elynah_scraper.py"

Local setup:
  pip install requests beautifulsoup4 pandas pyarrow
  python elynah_scraper.py
"""

import requests
import time
import json
import os
import re
import sqlite3
import csv
import logging
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup

# ── Environment detection (Colab vs local) ────────────────────────────────────

IN_COLAB = os.path.exists("/content/drive")

if IN_COLAB:
    OUTPUT_DIR = "/content/drive/MyDrive/Hockey Analysis/elynah/elynah_output"
else:
    OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "elynah_output")

DB_PATH     = os.path.join(OUTPUT_DIR, "elynah_forum.db")
EXPORTS_DIR = os.path.join(OUTPUT_DIR, "exports")
CHECKPOINT  = os.path.join(OUTPUT_DIR, "checkpoint.json")

# ── Configuration ─────────────────────────────────────────────────────────────

BASE_URL        = "https://elf.elynah.com/index.php"
TARGET_USER_ID  = 2143
TARGET_USERNAME = "BearLover"
BOARD_ID        = 1

# Full production run cutoff
CUTOFF_DATE = datetime(2025, 8, 1, tzinfo=timezone.utc)

REQUEST_DELAY = 1.5   # seconds between requests — be polite to the server

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; hobbyist-research-bot/1.0)"
}

# ── Logging ───────────────────────────────────────────────────────────────────

os.makedirs(OUTPUT_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(OUTPUT_DIR, "scraper.log")),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

# ── Database schema ───────────────────────────────────────────────────────────

SCHEMA = """
CREATE TABLE IF NOT EXISTS threads (
    topic_id         INTEGER PRIMARY KEY,
    title            TEXT,
    board_id         INTEGER,
    url              TEXT,
    starter_username TEXT,
    total_replies    INTEGER,
    total_views      INTEGER,
    last_post_date   TEXT,
    scraped_at       TEXT
);

CREATE TABLE IF NOT EXISTS posts (
    post_id              TEXT PRIMARY KEY,    -- SMF msg ID e.g. "msg284888"
    topic_id             INTEGER,
    author               TEXT,
    post_date            TEXT,                -- ISO 8601
    post_date_raw        TEXT,                -- original string from page
    position_in_thread   INTEGER,             -- 1-based order within thread
    is_bearlover         INTEGER,             -- 1/0
    own_text             TEXT,                -- body with all quote blocks stripped
    raw_html             TEXT,                -- full post body HTML
    likes                INTEGER DEFAULT 0,   -- "N people like this"
    response_lag_seconds INTEGER,             -- seconds since prior post in thread
    scraped_at           TEXT,
    FOREIGN KEY (topic_id) REFERENCES threads(topic_id)
);

CREATE TABLE IF NOT EXISTS post_quotes (
    quote_id             INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id              TEXT,
    quoted_author        TEXT,
    quoted_text          TEXT,
    is_quoting_bearlover INTEGER,             -- 1/0
    FOREIGN KEY (post_id) REFERENCES posts(post_id)
);

CREATE INDEX IF NOT EXISTS idx_posts_topic   ON posts(topic_id);
CREATE INDEX IF NOT EXISTS idx_posts_author  ON posts(author);
CREATE INDEX IF NOT EXISTS idx_posts_date    ON posts(post_date);
CREATE INDEX IF NOT EXISTS idx_posts_likes   ON posts(likes);
CREATE INDEX IF NOT EXISTS idx_quotes_post   ON post_quotes(post_id);
CREATE INDEX IF NOT EXISTS idx_quotes_bl     ON post_quotes(is_quoting_bearlover);
"""

# ── Database init ─────────────────────────────────────────────────────────────

def init_db(db_path):
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    conn.commit()
    return conn

# ── Checkpoint ────────────────────────────────────────────────────────────────

def load_checkpoint():
    if os.path.exists(CHECKPOINT):
        with open(CHECKPOINT) as f:
            return json.load(f)
    return {
        "showposts_done": False,
        "showposts_last_start": 0,
        "topic_ids_found": [],
        "topics_scraped": [],
        "phase": "showposts"
    }

def save_checkpoint(cp):
    with open(CHECKPOINT, "w") as f:
        json.dump(cp, f, indent=2)

# ── HTTP ──────────────────────────────────────────────────────────────────────

def fetch(url, retries=3):
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            r.raise_for_status()
            return r.text
        except Exception as e:
            log.warning(f"Fetch error (attempt {attempt+1}/{retries}): {e}")
            time.sleep(REQUEST_DELAY * 2)
    log.error(f"Failed after {retries} attempts: {url}")
    return None

# ── Date parsing ──────────────────────────────────────────────────────────────

MONTHS = {
    "January":1, "February":2, "March":3,    "April":4,
    "May":5,     "June":6,     "July":7,      "August":8,
    "September":9,"October":10,"November":11, "December":12
}

def parse_smf_date(raw: str):
    """Parse SMF date strings into UTC datetime. Returns None on failure."""
    if not raw:
        return None
    raw = raw.strip()
    now = datetime.now(tz=timezone.utc)

    if raw.lower().startswith("today"):
        m = re.search(r"(\d+:\d+:\d+\s+[AP]M)", raw, re.IGNORECASE)
        if m:
            t = datetime.strptime(m.group(1), "%I:%M:%S %p")
            return now.replace(hour=t.hour, minute=t.minute, second=t.second, microsecond=0)
        return now

    if raw.lower().startswith("yesterday"):
        base = now - timedelta(days=1)
        m = re.search(r"(\d+:\d+:\d+\s+[AP]M)", raw, re.IGNORECASE)
        if m:
            t = datetime.strptime(m.group(1), "%I:%M:%S %p")
            return base.replace(hour=t.hour, minute=t.minute, second=t.second, microsecond=0)
        return base

    # Standard: "Month DD, YYYY, HH:MM:SS AM/PM"
    m = re.match(
        r"(\w+)\s+(\d+),\s+(\d{4}),\s+(\d+):(\d+):(\d+)\s+([AP]M)",
        raw, re.IGNORECASE
    )
    if m:
        month_name, day, year, hour, minute, second, ampm = m.groups()
        month = MONTHS.get(month_name)
        if not month:
            return None
        hour = int(hour)
        if ampm.upper() == "PM" and hour != 12:
            hour += 12
        elif ampm.upper() == "AM" and hour == 12:
            hour = 0
        try:
            return datetime(int(year), month, int(day),
                            hour, int(minute), int(second), tzinfo=timezone.utc)
        except ValueError:
            return None
    return None

# ── Likes extraction ──────────────────────────────────────────────────────────

def extract_likes(soup_element) -> int:
    """Returns like count from 'N people like this' / '1 person likes this'. 0 if absent."""
    text = soup_element.get_text()
    m = re.search(r"(\d+)\s+(?:people|person)\s+likes?\s+this", text, re.IGNORECASE)
    return int(m.group(1)) if m else 0

# ── Post body extraction ──────────────────────────────────────────────────────

def extract_post_parts(body_div):
    """
    Returns (own_text, raw_html, quotes) where:
      own_text = post text with all quote blocks stripped
      raw_html = full inner HTML
      quotes   = list of {quoted_author, quoted_text, is_quoting_bearlover}

    This SMF theme uses:
      <blockquote class="bbc_standard_quote">
        <cite><a href="...">Quote from: Username on Date</a></cite>
        ...quoted text...
      </blockquote>
    """
    raw_html = str(body_div)

    quotes = []
    for bq in body_div.find_all("blockquote", class_="bbc_standard_quote"):
        cite = bq.find("cite")
        quoted_author = "unknown"
        if cite:
            cite_text = cite.get_text()
            am = re.search(r"Quote from:\s*(.+?)\s+on\s+", cite_text)
            if am:
                quoted_author = am.group(1).strip()
            cite.decompose()  # remove cite before extracting quoted text
        quoted_text = bq.get_text(separator=" ", strip=True)
        quotes.append({
            "quoted_author": quoted_author,
            "quoted_text": quoted_text,
            "is_quoting_bearlover": 1 if quoted_author.lower() == TARGET_USERNAME.lower() else 0
        })

    # Strip all blockquotes to get own_text
    soup_copy = BeautifulSoup(raw_html, "html.parser")
    for bq in soup_copy.find_all("blockquote", class_="bbc_standard_quote"):
        bq.decompose()
    own_text = re.sub(r"\s+", " ", soup_copy.get_text(separator=" ", strip=True)).strip()

    return own_text, raw_html, quotes

# ── URL helpers ───────────────────────────────────────────────────────────────

def extract_topic_id(url: str):
    m = re.search(r"topic=(\d+)", url)
    return int(m.group(1)) if m else None

def extract_msg_id(url: str):
    m = re.search(r"msg[=#](\d+)", url)
    return f"msg{m.group(1)}" if m else None

# ── Phase 1: BearLover showposts crawl ───────────────────────────────────────

def crawl_showposts(conn, cp):
    """
    Paginate BearLover's showposts pages.
    Collect topic IDs and store BL's own posts. Stop at CUTOFF_DATE.
    """
    log.info(f"=== Phase 1: showposts crawl (cutoff: {CUTOFF_DATE.date()}) ===")

    topic_ids = set(cp.get("topic_ids_found", []))
    start = cp.get("showposts_last_start", 0)
    hit_cutoff = False

    while not hit_cutoff:
        url = (f"{BASE_URL}?action=profile;u={TARGET_USER_ID}"
               f";area=showposts;sa=messages;start={start}")
        log.info(f"  showposts start={start}")

        html = fetch(url)
        if not html:
            break

        if "Messages - BearLover" not in html:
            log.error("  Unexpected page content — stopping")
            break

        soup = BeautifulSoup(html, "html.parser")

        # Actual showposts structure for this SMF theme:
        # Each post is a div.windowbg containing:
        #   div.topic_details > h5 > a[href*=topic] (topic link with msg anchor)
        #   div.topic_details > span.smalltext      (date)
        #   div.post > div.inner                    (post body)
        post_blocks = soup.find_all("div", class_="windowbg")

        if not post_blocks:
            log.info("  No post blocks found — end of showposts")
            break

        posts_this_page = 0
        for block in post_blocks:
            posts_this_page += 1

            # Date from span.smalltext inside topic_details
            date_raw = ""
            smalltext = block.find("span", class_="smalltext")
            if smalltext:
                date_raw = re.sub(r"\s+", " ", smalltext.get_text(separator=" ", strip=True)).strip()

            post_date = parse_smf_date(date_raw)

            if post_date and post_date < CUTOFF_DATE:
                log.info(f"  Hit cutoff at: {date_raw} — stopping")
                hit_cutoff = True
                break

            # Topic link — in h5 inside div.topic_details
            topic_details = block.find("div", class_="topic_details")
            topic_link = None
            if topic_details:
                topic_link = topic_details.find("a", href=re.compile(r"topic=\d+.*msg\d+"))
            if not topic_link:
                continue

            topic_id = extract_topic_id(topic_link.get("href", ""))
            msg_id   = extract_msg_id(topic_link.get("href", ""))
            if not topic_id:
                continue

            topic_ids.add(topic_id)

            # Post body is in div.post > div.inner
            body_div = block.find("div", class_="inner")
            if not body_div:
                body_div = block.find("div", class_="post")
            if not body_div:
                continue

            own_text, raw_html, quotes = extract_post_parts(body_div)
            likes = extract_likes(block)

            if msg_id:
                try:
                    conn.execute("""
                        INSERT OR IGNORE INTO posts
                        (post_id, topic_id, author, post_date, post_date_raw,
                         position_in_thread, is_bearlover, own_text, raw_html,
                         likes, scraped_at)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?)
                    """, (
                        msg_id, topic_id, TARGET_USERNAME,
                        post_date.isoformat() if post_date else None,
                        date_raw, None, 1, own_text, raw_html, likes,
                        datetime.now(timezone.utc).isoformat()
                    ))
                    for q in quotes:
                        conn.execute("""
                            INSERT INTO post_quotes
                            (post_id, quoted_author, quoted_text, is_quoting_bearlover)
                            VALUES (?,?,?,?)
                        """, (msg_id, q["quoted_author"], q["quoted_text"],
                              q["is_quoting_bearlover"]))
                    conn.commit()
                except Exception as e:
                    log.warning(f"  DB insert error {msg_id}: {e}")

        log.info(f"  start={start}: {posts_this_page} posts processed, "
                 f"{len(topic_ids)} unique topics so far")

        if hit_cutoff or posts_this_page == 0:
            break

        start += 15
        cp["showposts_last_start"] = start
        cp["topic_ids_found"] = list(topic_ids)
        save_checkpoint(cp)
        time.sleep(REQUEST_DELAY)

    cp["showposts_done"] = True
    cp["topic_ids_found"] = list(topic_ids)
    cp["phase"] = "threads"
    save_checkpoint(cp)
    log.info(f"Phase 1 complete — {len(topic_ids)} threads to scrape")
    return topic_ids

# ── Phase 2: Full thread scrape ───────────────────────────────────────────────

def scrape_thread(conn, topic_id: int):
    """Fetch all pages of a thread. Store every post with author/date/text/likes/quotes."""

    url = f"{BASE_URL}?topic={topic_id}.0"
    html = fetch(url)
    if not html:
        return

    soup = BeautifulSoup(html, "html.parser")

    # Title from h2
    title = f"Thread {topic_id}"
    h2 = soup.find("h2")
    if h2:
        title = re.sub(r"^(Re:\s*)+", "", h2.get_text(strip=True)).strip()

    # Highest page offset from pagination links
    last_start = 0
    for link in soup.find_all("a", href=re.compile(rf"topic={topic_id}\.\d+")):
        m = re.search(rf"topic={topic_id}\.(\d+)", link["href"])
        if m:
            last_start = max(last_start, int(m.group(1)))

    try:
        conn.execute("""
            INSERT OR IGNORE INTO threads
            (topic_id, title, board_id, url, scraped_at)
            VALUES (?,?,?,?,?)
        """, (topic_id, title, BOARD_ID,
              f"https://elf.elynah.com/index.php?topic={topic_id}.0",
              datetime.now(timezone.utc).isoformat()))
        conn.commit()
    except Exception as e:
        log.warning(f"  Thread insert error {topic_id}: {e}")

    page_starts = list(range(0, last_start + 15, 15))
    log.info(f"  topic={topic_id} '{title[:55]}' — {len(page_starts)} page(s)")

    all_posts = []

    for page_idx, page_start in enumerate(page_starts):
        if page_idx > 0:
            page_url = f"{BASE_URL}?topic={topic_id}.{page_start}"
            html = fetch(page_url)
            if not html:
                continue
            soup = BeautifulSoup(html, "html.parser")
            time.sleep(REQUEST_DELAY)

        # Thread page structure (confirmed from live HTML):
        #   div.windowbg id="msg284775"     ← outer wrapper, id IS the msg ID
        #     div.post_wrapper
        #       div.poster > h4 > a         ← author
        #       div id="msg_284775"         ← actual post body (underscore variant)
        wrappers = soup.find_all("div", class_="windowbg", id=re.compile(r"^msg\d+$"))

        for wrapper in wrappers:
            # msg_id directly from wrapper id — already correct format e.g. "msg284775"
            msg_id = wrapper.get("id")

            # Author — first profile link in the poster div
            author = ""
            poster = wrapper.find("div", class_="poster")
            if poster:
                pl = poster.find("a", href=re.compile(r"action=profile;u=\d+"))
                if pl:
                    author = pl.get_text(strip=True)

            # Date extraction — three sources in priority order:
            # 1. div.postinfo — always has original post date, most reliable
            # 2. a.smalltext — permalink anchor with date text
            # 3. span.smalltext — fallback, skip "Last Edit" lines
            date_raw = ""
            DATE_RE = r"((?:Today|Yesterday|\w+ \d+, \d{4}),?\s+(?:at\s+)?\d+:\d+:\d+\s+[AP]M)"

            postinfo = wrapper.find("div", class_="postinfo")
            if postinfo:
                full_text = re.sub(r"\s+", " ", postinfo.get_text(separator=" ", strip=True))
                for segment in re.split(r"Last Edit\s*:", full_text):
                    dm = re.search(DATE_RE, segment.strip(), re.IGNORECASE)
                    if dm:
                        date_raw = dm.group(1).strip()
                        break

            if not date_raw:
                for a in wrapper.find_all("a", class_="smalltext"):
                    text = re.sub(r"\s+", " ", a.get_text(separator=" ", strip=True))
                    dm = re.search(DATE_RE, text, re.IGNORECASE)
                    if dm:
                        date_raw = dm.group(1).strip()
                        break

            if not date_raw:
                smalltext = wrapper.find("span", class_="smalltext")
                if smalltext:
                    full_text = re.sub(r"\s+", " ", smalltext.get_text(separator=" ", strip=True))
                    for segment in re.split(r"Last Edit\s*:", full_text):
                        dm = re.search(DATE_RE, segment.strip(), re.IGNORECASE)
                        if dm:
                            date_raw = dm.group(1).strip()
                            break

            post_date = parse_smf_date(date_raw)

            if post_date is None or post_date < CUTOFF_DATE:
                continue

            # Post body: div id="msg_XXXXXX" (underscore variant) inside wrapper
            body_div = wrapper.find("div", id=re.compile(r"^msg_\d+$"))
            if not body_div:
                body_div = wrapper.find("div", class_=re.compile(r"\bpost\b|inner|post_body"))
            if not body_div:
                continue

            own_text, raw_html, quotes = extract_post_parts(body_div)
            likes  = extract_likes(wrapper)
            is_bl  = 1 if author.lower() == TARGET_USERNAME.lower() else 0

            all_posts.append({
                "msg_id": msg_id, "topic_id": topic_id, "author": author,
                "post_date": post_date, "post_date_raw": date_raw,
                "is_bearlover": is_bl, "own_text": own_text,
                "raw_html": raw_html, "likes": likes, "quotes": quotes
            })

    # Sort by date, compute position and response lag
    all_posts.sort(key=lambda p: p["post_date"] or datetime.min.replace(tzinfo=timezone.utc))

    prev_date = None
    for i, p in enumerate(all_posts):
        lag = None
        if prev_date and p["post_date"]:
            lag = int((p["post_date"] - prev_date).total_seconds())
        prev_date = p["post_date"]

        if not p["msg_id"]:
            continue

        try:
            conn.execute("""
                INSERT OR IGNORE INTO posts
                (post_id, topic_id, author, post_date, post_date_raw,
                 position_in_thread, is_bearlover, own_text, raw_html,
                 likes, response_lag_seconds, scraped_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                p["msg_id"], p["topic_id"], p["author"],
                p["post_date"].isoformat() if p["post_date"] else None,
                p["post_date_raw"], i + 1, p["is_bearlover"],
                p["own_text"], p["raw_html"],
                p["likes"], lag,
                datetime.now(timezone.utc).isoformat()
            ))
            for q in p["quotes"]:
                conn.execute("""
                    INSERT INTO post_quotes
                    (post_id, quoted_author, quoted_text, is_quoting_bearlover)
                    VALUES (?,?,?,?)
                """, (p["msg_id"], q["quoted_author"],
                      q["quoted_text"], q["is_quoting_bearlover"]))
            conn.commit()
        except Exception as e:
            log.warning(f"  Insert error {p['msg_id']}: {e}")

    log.info(f"  Stored {len(all_posts)} posts for topic={topic_id}")

# ── Phase 3: Export ───────────────────────────────────────────────────────────

def export(conn):
    os.makedirs(EXPORTS_DIR, exist_ok=True)
    log.info("=== Exporting ===")

    for table in ["threads", "posts", "post_quotes"]:
        out = os.path.join(EXPORTS_DIR, f"{table}.csv")
        cursor = conn.execute(f"SELECT * FROM {table}")
        cols = [d[0] for d in cursor.description]
        rows = cursor.fetchall()
        with open(out, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(cols)
            w.writerows(rows)
        log.info(f"  {table}.csv — {len(rows)} rows")

    try:
        import pandas as pd
        for table in ["posts", "post_quotes"]:
            df = pd.read_sql(f"SELECT * FROM {table}", conn)
            df.to_parquet(os.path.join(EXPORTS_DIR, f"{table}.parquet"), index=False)
            log.info(f"  {table}.parquet — {len(df)} rows")
    except ImportError:
        log.info("  pyarrow not available — skipping parquet")
    except Exception as e:
        log.warning(f"  Parquet error: {e}")

# ── Summary ───────────────────────────────────────────────────────────────────

def print_summary(conn):
    n_threads = conn.execute("SELECT COUNT(*) FROM threads").fetchone()[0]
    n_posts   = conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
    n_bl      = conn.execute("SELECT COUNT(*) FROM posts WHERE is_bearlover=1").fetchone()[0]
    n_quotes  = conn.execute("SELECT COUNT(*) FROM post_quotes").fetchone()[0]
    n_bl_qd   = conn.execute(
        "SELECT COUNT(*) FROM post_quotes WHERE is_quoting_bearlover=1"
    ).fetchone()[0]
    top_liked = conn.execute(
        "SELECT author, own_text, likes FROM posts ORDER BY likes DESC LIMIT 1"
    ).fetchone()

    print("\n" + "="*65)
    print("SCRAPE SUMMARY")
    print("="*65)
    print(f"Environment          : {'Google Colab' if IN_COLAB else 'Local'}")
    print(f"Cutoff date          : {CUTOFF_DATE.date()}")
    print(f"Threads scraped      : {n_threads}")
    print(f"Total posts stored   : {n_posts}")
    print(f"  BearLover posts    : {n_bl}")
    print(f"  Community posts    : {n_posts - n_bl}")
    print(f"Total quote records  : {n_quotes}")
    print(f"  Times BL quoted    : {n_bl_qd}")
    if top_liked:
        print(f"Most liked post      : {top_liked[2]} likes — by {top_liked[0]}")
        print(f"  \"{top_liked[1][:70]}...\"")
    print(f"\nDatabase  : {os.path.abspath(DB_PATH)}")
    print(f"Exports   : {os.path.abspath(EXPORTS_DIR)}")
    print("="*65)

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    log.info(f"ELynah Scraper starting")
    log.info(f"  Environment : {'Google Colab' if IN_COLAB else 'Local'}")
    log.info(f"  Output dir  : {OUTPUT_DIR}")
    log.info(f"  Cutoff date : {CUTOFF_DATE.date()}")

    conn = init_db(DB_PATH)
    cp   = load_checkpoint()

    # Phase 1 — showposts crawl
    if not cp.get("showposts_done"):
        topic_ids = crawl_showposts(conn, cp)
    else:
        topic_ids = set(cp.get("topic_ids_found", []))
        log.info(f"Phase 1 already done — {len(topic_ids)} topics from checkpoint")

    # Phase 2 — full thread scrape
    scraped   = set(cp.get("topics_scraped", []))
    remaining = [t for t in topic_ids if t not in scraped]
    log.info(f"=== Phase 2: {len(remaining)} threads remaining "
             f"({len(scraped)} already done) ===")

    for i, topic_id in enumerate(remaining, 1):
        log.info(f"Thread {i}/{len(remaining)} — topic_id={topic_id}")
        scrape_thread(conn, topic_id)
        scraped.add(topic_id)
        cp["topics_scraped"] = list(scraped)
        save_checkpoint(cp)
        time.sleep(REQUEST_DELAY)

    cp["phase"] = "done"
    save_checkpoint(cp)

    # Phase 3 — export
    export(conn)
    print_summary(conn)
    conn.close()
    log.info("Scrape complete.")

if __name__ == "__main__":
    main()
