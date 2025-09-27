import os
import sqlite3
import pandas as pd
from datetime import datetime
from pathlib import Path
import csv

# Get the script directory and project root
SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent
DB_PATH = PROJECT_ROOT / "metadata" / "symbol_index.sqlite"
PARQUET_PATH = PROJECT_ROOT / "parquet"  # chỉ cần dữ liệu đã xử lý

# Global exchange mapping - load từ dữ liệu thực tế
EXCHANGE_MAP = {}

def load_exchange_mapping():
    """Load symbol-to-exchange mapping từ raw data files"""
    global EXCHANGE_MAP
    
    data_dir = PROJECT_ROOT / "staging" / "Data"
    
    # Files cho từng sàn
    files = {
        "HOSE": "CafeF.HSX.Upto25.09.2025.csv",
        "HNX": "CafeF.HNX.Upto25.09.2025.csv", 
        "UPCOM": "CafeF.UPCOM.Upto25.09.2025.csv"
    }
    
    for exchange, filename in files.items():
        file_path = data_dir / filename
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        symbol = row['<Ticker>'].strip()
                        if symbol:
                            EXCHANGE_MAP[symbol] = exchange
                print(f"Loaded {len([s for s in EXCHANGE_MAP.values() if s == exchange])} symbols for {exchange}")
            except Exception as e:
                print(f"Error loading {filename}: {e}")
        else:
            print(f"File not found: {file_path}")
    
    print(f"Total symbols loaded: {len(EXCHANGE_MAP)}")
    return len(EXCHANGE_MAP) > 0

def init_db():
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS symbol_index (
        symbol TEXT,
        exchange TEXT,               -- HSX/HNX/UPCOM based on symbol pattern
        file_path TEXT,
        member_name TEXT,            -- NULL cho parquet files
        first_date TEXT,
        last_date TEXT,
        record_count INTEGER,
        last_ingested_at TEXT,
        PRIMARY KEY(symbol, file_path)
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS ingest_log (
        file_path TEXT PRIMARY KEY,
        status TEXT,
        last_processed_at TEXT
    )
    """)
    conn.commit()
    return conn

def detect_exchange(symbol: str) -> str:
    """Detect exchange từ thông tin thực tế từ data files"""
    if not symbol:
        return "UNKNOWN"
    
    # Lookup từ mapping được load từ data files
    return EXCHANGE_MAP.get(symbol, "UNKNOWN")

def process_parquet_file(file_path, conn):
    """Xử lý file parquet và index metadata"""
    try:
        df = pd.read_parquet(file_path)
        
        if df.empty:
            print(f"      Empty parquet file")
            return
            
        # Extract symbol từ path: parquet/symbol=AAA/year=2023/data.parquet
        path_parts = Path(file_path).parts
        symbol = None
        year = None
        
        for part in path_parts:
            if part.startswith('symbol='):
                symbol = part.split('=')[1]
            elif part.startswith('year='):
                year = part.split('=')[1]
        
        if not symbol:
            print(f"      Cannot extract symbol from path: {file_path}")
            return
            
        # Detect exchange từ symbol name
        exchange = detect_exchange(symbol)
        
        # Tính toán stats
        if 'date' in df.columns:
            first_date = df['date'].min()
            last_date = df['date'].max()
        else:
            first_date = last_date = None
            
        record_count = len(df)
        
        print(f"      Found symbol {symbol}, {record_count} records, date range: {first_date} to {last_date}")
        
        # Lưu vào database
        cur = conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO symbol_index
            (symbol, exchange, file_path, member_name, first_date, last_date, record_count, last_ingested_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (symbol, exchange, str(file_path), None,
              first_date.strftime("%Y-%m-%d") if first_date else None,
              last_date.strftime("%Y-%m-%d") if last_date else None,
              record_count, datetime.now().isoformat()))
        conn.commit()
        
    except Exception as e:
        print(f"      Error processing parquet file: {e}")

def index_file(file_path, conn):
    """Chỉ xử lý file parquet"""
    print(f"  → Indexing parquet: {file_path}")
    
    if not file_path.lower().endswith(".parquet"):
        print(f"    Skipping non-parquet file: {file_path}")
        return
    
    process_parquet_file(file_path, conn)

def main():
    # Load exchange mapping từ data files
    print("Loading exchange mapping từ raw data files...")
    if not load_exchange_mapping():
        print("WARNING: Could not load exchange mapping. All symbols will be marked as UNKNOWN.")
        print("Make sure you have extracted the data files in staging/Data/")
    
    # Ensure the metadata directory exists
    DB_PATH.parent.mkdir(exist_ok=True)
    
    conn = init_db()
    processed_files = 0
    
    print(f"Starting PARQUET indexing process...")
    print(f"Database path: {DB_PATH}")
    
    # Quét dữ liệu đã xử lý (parquet) - QUAN TRỌNG NHẤT!
    print(f"Scanning PROCESSED data: {PARQUET_PATH}")
    if PARQUET_PATH.exists():
        for root, _, files in os.walk(PARQUET_PATH):
            for f in files:
                if not f.lower().endswith(".parquet"):
                    continue
                if f.startswith("."):
                    continue
                    
                path = os.path.join(root, f)
                print(f"Processing: {path}")
                try:
                    index_file(path, conn)
                    processed_files += 1
                except Exception as e:
                    print(f"Error processing {path}: {e}")
    else:
        print(f"Parquet directory not found: {PARQUET_PATH}")
        print("Run data_processor_historical.py first to generate parquet files!")

    conn.close()
    print(f"Indexing completed! Processed {processed_files} parquet files.")
    
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
        cur.execute("SELECT exchange, COUNT(*) FROM symbol_index GROUP BY exchange ORDER BY COUNT(*) DESC")
        exchange_stats = cur.fetchall()
        
        print(f"Database now contains {symbol_count} unique symbols across {total_records} file entries.")
        if date_range[0] and date_range[1]:
            print(f"Date range: {date_range[0]} to {date_range[1]}")
        
        print("Exchange distribution:")
        for exchange, count in exchange_stats:
            print(f"  {exchange}: {count} entries")
        
        conn.close()

if __name__ == "__main__":
    main()

