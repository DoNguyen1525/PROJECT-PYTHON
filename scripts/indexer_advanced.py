import os
import sqlite3
import pandas as pd
from datetime import datetime
from pathlib import Path
import zipfile

# Get the script directory and project root
SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent
DB_PATH = PROJECT_ROOT / "metadata" / "symbol_index.sqlite"
RAW_PATH = PROJECT_ROOT / "staging"   # giống README

def init_db():
    conn = sqlite3.connect(str(DB_PATH))
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
    chunks_processed = 0
    
    try:
        for chunk in pd.read_csv(handle, chunksize=chunksize):
            chunks_processed += 1
            # Clean column names - remove angle brackets and convert to lowercase
            chunk.columns = [c.strip().lower().replace('<', '').replace('>', '') for c in chunk.columns]
            
            # Print columns for debugging
            if chunks_processed == 1:
                print(f"      Columns found: {list(chunk.columns)}")
            
            # Look for ticker column (various possible names)
            ticker_col = None
            date_col = None
            
            for col in chunk.columns:
                if col in ['ticker', 'symbol', 'stock']:
                    ticker_col = col
                if col in ['date', 'dtyyyymmdd', 'datetime', 'dt']:
                    date_col = col
            
            if not ticker_col or not date_col:
                print(f"      Warning: Missing ticker or date columns. Found columns: {list(chunk.columns)}")
                print(f"      Ticker column: {ticker_col}, Date column: {date_col}")
                continue
                
            for symbol, grp in chunk.groupby(ticker_col):
                try:
                    # Handle different date formats
                    if date_col == 'dtyyyymmdd':
                        # Convert YYYYMMDD to datetime
                        dates = pd.to_datetime(grp[date_col].astype(str), format='%Y%m%d')
                    else:
                        dates = pd.to_datetime(grp[date_col])
                        
                    fdate = dates.min()
                    ldate = dates.max()
                    count = len(grp)
                    if symbol not in stats:
                        stats[symbol] = [fdate, ldate, count]
                    else:
                        stats[symbol][0] = min(stats[symbol][0], fdate)
                        stats[symbol][1] = max(stats[symbol][1], ldate)
                        stats[symbol][2] += count
                except Exception as e:
                    print(f"      Error processing symbol {symbol}: {e}")
                    continue
        
        print(f"      Processed {chunks_processed} chunks, found {len(stats)} symbols")
        
    except Exception as e:
        print(f"      Error reading CSV: {e}")
        return
    
    if not stats:
        print(f"      No valid data found")
        return
        
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
    print(f"      Indexed {len(stats)} symbols to database")

def index_file(file_path, conn):
    exchange = detect_exchange(file_path)
    print(f"  → Indexing {file_path} ({exchange})")
    
    if file_path.lower().endswith(".zip"):
        with zipfile.ZipFile(file_path, "r") as z:
            members = [m for m in z.namelist() if m.lower().endswith(".csv")]
            print(f"    Found {len(members)} CSV files in ZIP")
            for member in members:
                print(f"    Processing ZIP member: {member}")
                with z.open(member) as fh:
                    process_csv_handle(fh, exchange, file_path, member, conn)
    else:
        with open(file_path, "rb") as fh:
            process_csv_handle(fh, exchange, file_path, None, conn)

def main():
    # Ensure the metadata directory exists
    DB_PATH.parent.mkdir(exist_ok=True)
    
    conn = init_db()
    processed_files = 0
    
    print(f"Starting indexing process...")
    print(f"Database path: {DB_PATH}")
    print(f"Scanning directory: {RAW_PATH}")
    
    for root, _, files in os.walk(RAW_PATH):
        for f in files:
            # Xử lý cả file CSV thường và historical
            if not f.lower().endswith((".csv", ".zip")):
                continue
            # Bỏ qua các file manifest và metadata
            if "manifest" in f.lower() or f.startswith("."):
                continue
                
            path = os.path.join(root, f)
            print(f"Processing: {path}")
            try:
                index_file(path, conn)
                processed_files += 1
            except Exception as e:
                print(f"Error processing {path}: {e}")
    
    conn.close()
    print(f"Indexing completed! Processed {processed_files} files.")
    
    # Show some stats
    if processed_files > 0:
        conn = sqlite3.connect(str(DB_PATH))
        cur = conn.cursor()
        cur.execute("SELECT COUNT(DISTINCT symbol) FROM symbol_index")
        symbol_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM symbol_index")
        total_records = cur.fetchone()[0]
        cur.execute("SELECT MIN(first_date), MAX(last_date) FROM symbol_index")
        date_range = cur.fetchone()
        print(f"Database now contains {symbol_count} unique symbols across {total_records} file entries.")
        if date_range[0] and date_range[1]:
            print(f"Date range: {date_range[0]} to {date_range[1]}")
        conn.close()

if __name__ == "__main__":
    main()

