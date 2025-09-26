import os
import sqlite3
import pandas as pd
from datetime import datetime
from pathlib import Path
import zipfile

DB_PATH = "metadata/symbol_index.sqlite"
RAW_PATH = "staging"   # giống README

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS symbol_index (
        symbol TEXT,
        exchange TEXT,
        file_path TEXT,
        member_name TEXT,         -- nếu zip: nội dung member
        first_date TEXT,
        last_date TEXT,
        record_count INTEGER,
        last_ingested_at TEXT,
        PRIMARY KEY(symbol, file_path, member_name)
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS ingest_log (
        file_path TEXT PRIMARY KEY,
        sha256 TEXT,
        members_count INTEGER,
        status TEXT,
        last_processed_at TEXT
    )
    """)
    conn.commit()
    return conn

def detect_exchange(filename: str) -> str:
    if "HSX" in filename.upper(): return "HSX"
    if "HNX" in filename.upper(): return "HNX"
    if "UPCOM" in filename.upper(): return "UPCOM"
    return "UNKNOWN"

def process_csv_handle(handle, exchange, file_path, member_name, conn):
    chunksize = 200_000
    stats = {}
    for chunk in pd.read_csv(handle, chunksize=chunksize):
        chunk.columns = [c.strip().lower() for c in chunk.columns]
        if "ticker" not in chunk.columns or "date" not in chunk.columns:
            continue
        for symbol, grp in chunk.groupby("ticker"):
            fdate = pd.to_datetime(grp["date"]).min()
            ldate = pd.to_datetime(grp["date"]).max()
            count = len(grp)
            if symbol not in stats:
                stats[symbol] = [fdate, ldate, count]
            else:
                stats[symbol][0] = min(stats[symbol][0], fdate)
                stats[symbol][1] = max(stats[symbol][1], ldate)
                stats[symbol][2] += count
    cur = conn.cursor()
    for symbol, (fdate, ldate, count) in stats.items():
        cur.execute("""
            INSERT OR REPLACE INTO symbol_index
            (symbol, exchange, file_path, member_name, first_date, last_date, record_count, last_ingested_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (symbol, exchange, file_path, member_name,
              fdate.strftime("%Y-%m-%d"), ldate.strftime("%Y-%m-%d"),
              count, datetime.now().isoformat()))
    conn.commit()

def index_file(file_path, conn):
    exchange = detect_exchange(file_path)
    print(f"Indexing {file_path} ({exchange})")
    if file_path.lower().endswith(".zip"):
        with zipfile.ZipFile(file_path, "r") as z:
            for member in z.namelist():
                if not member.lower().endswith(".csv"):
                    continue
                key = (file_path, member)
                # check if already processed for any symbols (optional)
                with z.open(member) as fh:
                    process_csv_handle(fh, exchange, file_path, member, conn)
    else:
        with open(file_path, "rb") as fh:
            process_csv_handle(fh, exchange, file_path, None, conn)

def main():
    conn = init_db()
    for root, _, files in os.walk(RAW_PATH):
        for f in files:
            if not f.lower().endswith((".csv", ".zip")):
                continue
            path = os.path.join(root, f)
            index_file(path, conn)
    conn.close()
    print("Indexing done")

