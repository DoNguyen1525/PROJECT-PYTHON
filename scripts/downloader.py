#!/usr/bin/env python3
"""
scripts/downloader.py

Purpose:
  - find CafeF "Upto" zip for a date (default yesterday)
  - HEAD/ETag check to skip if unchanged
  - download with resume (Range) into staging/<date>/CafeF.SolieuGD.Upto<date>.zip
  - extract into staging/<date>/raw/
  - update metadata/ingest_manifest.json and metadata/downloaded_files.sqlite

Usage:
  python scripts/downloader.py                 # default yesterday
  python scripts/downloader.py 20250925        # specific date
  python scripts/downloader.py --no-scrape 20250925   # use template URL only
"""
import sys
import os
import time
import json
import math
import hashlib
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup  # pip install beautifulsoup4

# ---------------- CONFIG ----------------
# Get the script directory and project root
SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent
ROOT = PROJECT_ROOT
STAGING = ROOT / "staging"
META_DIR = ROOT / "metadata"
MANIFEST_JSON = META_DIR / "ingest_manifest.json"
DB_PATH = META_DIR / "downloaded_files.sqlite"

# Template fallback URL - Updated for historical data format
TEMPLATE_URL = "https://cafef1.mediacdn.vn/data/ami_data/{date}/CafeF.SolieuGD.Upto{date_short}.zip"
INDEX_PAGE = "https://cafef.vn/du-lieu/du-lieu-download.chn"

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
HEADERS = {"User-Agent": USER_AGENT}

CHUNK_SIZE = 1024 * 64
MAX_RETRIES = 5
BACKOFF_INITIAL = 1.0
# ----------------------------------------

def ensure_dirs():
    META_DIR.mkdir(parents=True, exist_ok=True)
    STAGING.mkdir(parents=True, exist_ok=True)

def init_db():
    # Check if the database file exists and is valid
    if DB_PATH.exists():
        try:
            # Try to connect and verify it's a valid database
            test_conn = sqlite3.connect(DB_PATH)
            test_conn.cursor().execute("SELECT name FROM sqlite_master LIMIT 1")
            test_conn.close()
        except sqlite3.DatabaseError:
            # If not valid, rename it and create new one
            backup = DB_PATH.with_suffix(f".bak.{int(time.time())}")
            print(f"[init_db] Invalid database file. Backing up to {backup}")
            DB_PATH.rename(backup)
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS downloaded_files (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      date_str TEXT UNIQUE NOT NULL,
      url TEXT,
      path TEXT,
      sha256 TEXT,
      size INTEGER,
      last_modified TEXT,
      etag TEXT,
      downloaded_at TEXT,
      status TEXT,
      members_count INTEGER,
      note TEXT
    )""")
    conn.commit()
    return conn

def load_manifest():
    if MANIFEST_JSON.exists():
        try:
            return json.loads(MANIFEST_JSON.read_text(encoding="utf8"))
        except Exception:
            return {}
    return {}

def save_manifest(d):
    MANIFEST_JSON.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf8")

def parse_date_arg():
    # CLI: allow --no-scrape flag optionally
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    date_str = args[0] if args else None
    if not date_str:
        dt = datetime.now() - timedelta(days=1)
        date_str = dt.strftime("%Y%m%d")
    # validate
    try:
        datetime.strptime(date_str, "%Y%m%d")
    except ValueError:
        print("Date must be YYYYMMDD")
        sys.exit(2)
    return date_str

def should_scrape():
    return "--no-scrape" not in sys.argv

def find_url_by_scrape(date_str):
    """
    Scrape CafeF index page for links that contain date_str or Upto{date}
    Return first suitable zip URL or None
    """
    try:
        resp = requests.get(INDEX_PAGE, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        candidates = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if date_str in href or f"Upto{date_str}" in href or "SolieuGD" in href:
                # make absolute
                url = urljoin(INDEX_PAGE, href)
                if url.endswith(".zip") or "ami_data" in url:
                    candidates.append(url)
        if candidates:
            # prefer .zip explicit
            for url in candidates:
                if url.endswith(".zip"):
                    return url
            return candidates[0]
    except Exception as e:
        print("[scrape] error:", e)
    return None

def head_request(url):
    """
    Do HEAD to fetch ETag/Last-Modified/Content-Length/Accept-Ranges
    Fallback to GET Range 0-0 if HEAD not allowed.
    """
    try:
        r = requests.head(url, headers=HEADERS, allow_redirects=True, timeout=20)
        if r.status_code == 200:
            return r.headers
        # some servers disallow HEAD -> try small GET
        r = requests.get(url, headers={**HEADERS, "Range": "bytes=0-0"}, stream=True, timeout=20)
        r.raise_for_status()
        return r.headers
    except Exception as e:
        print("[head] warning:", e)
        return {}

def sha256_file(path, block=65536):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(block), b""):
            h.update(chunk)
    return h.hexdigest()

def download_with_resume(url, dest_path, existing_headers):
    """
    Tối ưu: Tải file với hỗ trợ resume nếu server cho phép
    """
    # Chuẩn bị file tạm và kiểm tra kích thước nếu đã tồn tại
    tmp = dest_path.with_suffix(dest_path.suffix + ".part")
    tmp.parent.mkdir(parents=True, exist_ok=True)
    existing_size = tmp.stat().st_size if tmp.exists() else 0
    
    # Xử lý headers
    headers = dict(HEADERS)
    accept_ranges = existing_headers and existing_headers.get("Accept-Ranges", "").lower() != ""
    
    # Thêm Range header nếu có thể resume
    if existing_size > 0 and accept_ranges:
        headers["Range"] = f"bytes={existing_size}-"
        mode = "ab"
        print(f"[download] resume from {existing_size} bytes")
    else:
        mode = "wb"
    
    # Retry logic với exponential backoff
    for attempt in range(MAX_RETRIES):
        try:
            with requests.get(url, headers=headers, stream=True, timeout=60) as r:
                if r.status_code in (403, 404):
                    return {"error": f"HTTP {r.status_code}"}
                r.raise_for_status()
                
                # Stream download
                with open(tmp, mode) as f:
                    for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                        if chunk:
                            f.write(chunk)
                
                # Hoàn thành download
                sha = sha256_file(tmp)
                size = tmp.stat().st_size
                
                # Di chuyển file tạm thành file đích
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                os.replace(tmp, dest_path)
                return {"sha256": sha, "size": size}
        
        except Exception as e:
            wait = BACKOFF_INITIAL * (2 ** attempt)
            print(f"[download] attempt {attempt+1} failed: {e}. backoff {wait:.1f}s")
            time.sleep(wait)
    
    return {"error": "failed after retries"}

def extract_zip(zip_path, out_dir):
    import zipfile
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(out_dir)
            members = zf.namelist()
        (out_dir / "manifest.json").write_text(json.dumps({"zip": str(zip_path), "members": members}, indent=2), encoding="utf8")
        return True, members
    except Exception as e:
        print("[extract] error:", e)
        return False, []

def upsert_db(conn, date_str, meta):
    cur = conn.cursor()
    cur.execute("SELECT id FROM downloaded_files WHERE date_str=?", (date_str,))
    row = cur.fetchone()
    if row:
        cur.execute("""UPDATE downloaded_files SET url=?, path=?, sha256=?, size=?, last_modified=?, etag=?, downloaded_at=?, status=?, members_count=?, note=?
                       WHERE date_str=?""",
                    (meta.get("url"), meta.get("path"), meta.get("sha256"), meta.get("size"),
                     meta.get("last_modified"), meta.get("etag"), meta.get("downloaded_at"),
                     meta.get("status"), meta.get("members_count"), meta.get("note"), date_str))
    else:
        cur.execute("""INSERT INTO downloaded_files(date_str, url, path, sha256, size, last_modified, etag, downloaded_at, status, members_count, note)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                    (date_str, meta.get("url"), meta.get("path"), meta.get("sha256"), meta.get("size"),
                     meta.get("last_modified"), meta.get("etag"), meta.get("downloaded_at"),
                     meta.get("status"), meta.get("members_count"), meta.get("note")))
    conn.commit()

def main():
    ensure_dirs()
    conn = init_db()
    manifest = load_manifest()
    date_str = parse_date_arg()
    print("[main] target date:", date_str)

    url = None
    if should_scrape():
        url = find_url_by_scrape(date_str)
        if url:
            print("[main] found URL by scrape:", url)
    if not url:
        # Format date for URL: 20250925 -> 25092025
        date_formatted = date_str[-2:] + date_str[4:6] + date_str[:4]  # YYYYMMDD -> DDMMYYYY
        url = TEMPLATE_URL.format(date=date_str, date_short=date_formatted)
        print("[main] using template URL:", url)

    # HEAD
    hdrs = head_request(url)
    remote_etag = hdrs.get("ETag")
    remote_lastmod = hdrs.get("Last-Modified")
    remote_len = None
    if hdrs.get("Content-Length"):
        try:
            remote_len = int(hdrs.get("Content-Length"))
        except:
            remote_len = None

    prev = manifest.get(date_str)
    skip = False
    if prev:
        # Kiểm tra xem file thực tế có tồn tại không
        prev_path = prev.get("path")
        if prev_path and Path(prev_path).exists():
            if remote_etag and prev.get("etag") == remote_etag:
                print("[main] ETag matches previous -> skip")
                skip = True
            elif remote_lastmod and prev.get("last_modified") == remote_lastmod:
                print("[main] Last-Modified matches previous -> skip")
                skip = True
            elif remote_len and prev.get("size") == remote_len:
                print("[main] size matches previous -> skip")
                skip = True
        else:
            # File không tồn tại, cần tải lại
            print(f"[main] previous file not found at {prev_path}, will re-download")
            prev = None  # Reset to force download

    staging_dir = STAGING / date_str
    staging_dir.mkdir(parents=True, exist_ok=True)
    
    # Extract filename from URL, fallback to default pattern
    try:
        from urllib.parse import urlparse
        parsed_url = urlparse(url)
        zip_name = Path(parsed_url.path).name
        if not zip_name.endswith('.zip'):
            zip_name = f"CafeF.SolieuGD.Upto{date_str}.zip"
    except:
        zip_name = f"CafeF.SolieuGD.Upto{date_str}.zip"
    
    dest = staging_dir / zip_name
    print(f"[main] destination: {dest}")

    entry = {
        "url": url,
        "path": None,
        "sha256": None,
        "size": None,
        "last_modified": remote_lastmod,
        "etag": remote_etag,
        "downloaded_at": None,
        "status": None,
        "members_count": None,
        "note": None
    }

    if skip:
        print("[main] skipping download")
        entry.update(prev or {})
        entry["status"] = "skipped"
        manifest[date_str] = entry
        save_manifest(manifest)
        upsert_db(conn, date_str, entry)
        return

    # download
    print("[main] start download:", url)
    res = download_with_resume(url, dest, hdrs)
    if "error" in res:
        entry["status"] = "failed"
        entry["note"] = res.get("error")
        manifest[date_str] = entry
        save_manifest(manifest)
        upsert_db(conn, date_str, entry)
        print("[main] download failed")
        return

    entry["sha256"] = res.get("sha256")
    entry["size"] = res.get("size")
    entry["path"] = str(dest)
    entry["downloaded_at"] = datetime.utcnow().isoformat()
    entry["status"] = "downloaded"

    # extract
    out_raw = staging_dir / "raw"
    ok, members = extract_zip(dest, out_raw)
    if ok:
        entry["members_count"] = len(members)
        print(f"[main] extracted {len(members)} members to {out_raw}")
    else:
        entry["status"] = "failed"
        entry["note"] = "extract_failed"

    # update manifest and DB
    manifest[date_str] = entry
    save_manifest(manifest)
    upsert_db(conn, date_str, entry)
    print("[main] done.")

if __name__ == "__main__":
    main()
