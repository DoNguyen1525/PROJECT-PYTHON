# scripts/api_demo_fast.py
from fastapi import FastAPI, HTTPException, Query
import sqlite3
import duckdb
from typing import Optional
from pydantic import BaseModel
import pandas as pd

app = FastAPI()
SQLITE_DB = "metadata/symbol_index.sqlite"
DUCKDB_CONN = duckdb.connect()

def init_db():
    """Khởi tạo database và tạo bảng nếu chưa tồn tại"""
    from pathlib import Path
    # Đảm bảo thư mục tồn tại
    db_path = Path(SQLITE_DB)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(SQLITE_DB)
    cursor = conn.cursor()
    
    # Tạo bảng symbol_index nếu chưa tồn tại
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS symbol_index (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        exchange TEXT,
        file_path TEXT,
        member_name TEXT,
        last_update TEXT
    )
    """)
    
    # Tạo index để tìm kiếm nhanh hơn
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_symbol ON symbol_index(symbol)")
    
    # Thêm một số mã chứng khoán mẫu nếu bảng trống
    cursor.execute("SELECT COUNT(*) FROM symbol_index")
    count = cursor.fetchone()[0]
    
    if count == 0:
        # Thêm một số mã chứng khoán mẫu
        sample_symbols = [
            # HOSE - Sàn HCMC
            ('VNM', 'HOSE', 'staging/20250925/raw/CafeF.HSX.25.09.2025.csv', 'VNM.csv'),
            ('FPT', 'HOSE', 'staging/20250925/raw/CafeF.HSX.25.09.2025.csv', 'FPT.csv'),
            ('VIC', 'HOSE', 'staging/20250925/raw/CafeF.HSX.25.09.2025.csv', 'VIC.csv'),
            ('BVH', 'HOSE', 'staging/20250925/raw/CafeF.HSX.25.09.2025.csv', 'BVH.csv'),
            ('MSN', 'HOSE', 'staging/20250925/raw/CafeF.HSX.25.09.2025.csv', 'MSN.csv'),
            ('HPG', 'HOSE', 'staging/20250925/raw/CafeF.HSX.25.09.2025.csv', 'HPG.csv'),
            ('VCB', 'HOSE', 'staging/20250925/raw/CafeF.HSX.25.09.2025.csv', 'VCB.csv'),
            ('TCB', 'HOSE', 'staging/20250925/raw/CafeF.HSX.25.09.2025.csv', 'TCB.csv'),
            # HNX - Sàn Hà Nội
            ('ACB', 'HNX', 'staging/20250925/raw/CafeF.HNX.25.09.2025.csv', 'ACB.csv'),
            ('SHS', 'HNX', 'staging/20250925/raw/CafeF.HNX.25.09.2025.csv', 'SHS.csv'),
            ('PVS', 'HNX', 'staging/20250925/raw/CafeF.HNX.25.09.2025.csv', 'PVS.csv'),
            # UPCOM
            ('ACV', 'UPCOM', 'staging/20250925/raw/CafeF.UPCOM.25.09.2025.csv', 'ACV.csv'),
            ('VGC', 'UPCOM', 'staging/20250925/raw/CafeF.UPCOM.25.09.2025.csv', 'VGC.csv'),
        ]
        
        cursor.executemany(
            "INSERT INTO symbol_index (symbol, exchange, file_path, member_name) VALUES (?, ?, ?, ?)",
            sample_symbols
        )
    
    conn.commit()
    conn.close()
    print("Database initialized successfully!")

# Khởi tạo database khi khởi động app
init_db()

def get_sqlite_conn():
    return sqlite3.connect(SQLITE_DB)

@app.get("/")
def home():
    """Trang chủ API"""
    return {
        "name": "CafeF Data API",
        "description": "API để truy xuất dữ liệu chứng khoán từ CafeF",
        "version": "1.0",
        "endpoints": [
            {"path": "/", "method": "GET", "description": "Thông tin về API"},
            {"path": "/symbols", "method": "GET", "description": "Danh sách các mã chứng khoán"},
            {"path": "/search", "method": "GET", "description": "Tìm kiếm mã chứng khoán (dùng param q=từ_khóa)"},
            {"path": "/symbol/{symbol}", "method": "GET", "description": "Dữ liệu của một mã chứng khoán cụ thể"},
            {"path": "/docs", "method": "GET", "description": "Tài liệu API tự động (Swagger UI)"}
        ]
    }

@app.get("/symbols")
def list_symbols(limit: int = 100):
    conn = get_sqlite_conn()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT symbol, exchange FROM symbol_index ORDER BY symbol LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    return [{"symbol": r[0], "exchange": r[1]} for r in rows]

@app.get("/search")
def search_symbols(q: str = Query(..., description="Từ khóa tìm kiếm (mã hoặc tên)")):
    """
    Tìm kiếm mã chứng khoán dựa trên từ khóa.
    Tìm kiếm không phân biệt hoa thường và tìm kiếm một phần của mã.
    """
    if not q or len(q.strip()) < 1:
        raise HTTPException(status_code=400, detail="Cần nhập từ khóa tìm kiếm")
        
    # Chuẩn bị từ khóa tìm kiếm
    search_term = f"%{q.strip().upper()}%"
    
    conn = get_sqlite_conn()
    cur = conn.cursor()
    # Tìm kiếm theo mã chứng khoán
    cur.execute("""
    SELECT symbol, exchange, file_path, last_update 
    FROM symbol_index 
    WHERE UPPER(symbol) LIKE ? 
    ORDER BY symbol
    LIMIT 20
    """, (search_term,))
    
    rows = cur.fetchall()
    conn.close()
    
    if not rows:
        # Không tìm thấy kết quả nào, trả về mảng rỗng
        return []
    
    # Trả về kết quả dạng danh sách
    return [{
        "symbol": r[0], 
        "exchange": r[1], 
        "file_path": r[2],
        "last_update": r[3]
    } for r in rows]

@app.get("/exchanges")
def list_exchanges():
    """Liệt kê các sàn giao dịch có sẵn trong hệ thống"""
    conn = get_sqlite_conn()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT exchange, COUNT(*) as symbol_count FROM symbol_index GROUP BY exchange ORDER BY exchange")
    rows = cur.fetchall()
    conn.close()
    return [{"exchange": r[0] or "Unknown", "symbol_count": r[1]} for r in rows]

@app.get("/exchange/{exchange}")
def get_symbols_by_exchange(exchange: str, limit: int = 100):
    """Lấy danh sách mã chứng khoán của một sàn cụ thể"""
    conn = get_sqlite_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT symbol, exchange, file_path, last_update 
        FROM symbol_index 
        WHERE UPPER(exchange) = UPPER(?) 
        ORDER BY symbol
        LIMIT ?
    """, (exchange, limit))
    rows = cur.fetchall()
    conn.close()
    
    if not rows:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy sàn giao dịch: {exchange}")
    
    return [{
        "symbol": r[0], 
        "exchange": r[1],
        "file_path": r[2],
        "last_update": r[3]
    } for r in rows]

@app.get("/symbol/{symbol}")
def get_symbol(symbol: str, start: Optional[str] = None, end: Optional[str] = None, indicators: bool = True):
    # 1) Check symbol exists in index
    conn = get_sqlite_conn()
    cur = conn.cursor()
    cur.execute("SELECT file_path, member_name FROM symbol_index WHERE symbol = ? LIMIT 1", (symbol,))
    row = cur.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Symbol not found in index")
    
    # 2) Tạo dữ liệu mẫu nếu không có file Parquet
    try:
        # Thử đọc file Parquet nếu có
        start_condition = f"AND date >= '{start}'" if start else ""
        end_condition = f"AND date <= '{end}'" if end else ""
        q = f"""
        SELECT *
        FROM parquet_scan('parquet/symbol={symbol}/*/*.parquet')
        WHERE 1=1 {start_condition} {end_condition}
        ORDER BY date
        """
        df = DUCKDB_CONN.execute(q).fetchdf()
    except Exception as e:
        # Nếu không có file Parquet, tạo dữ liệu mẫu
        print(f"Không thể đọc file Parquet cho {symbol}: {e}")
        print("Tạo dữ liệu mẫu...")
        
        # Tạo dữ liệu mẫu cho biểu đồ
        import numpy as np
        from datetime import datetime, timedelta
        
        # Tạo 100 ngày giao dịch
        end_date = datetime.now()
        if end:
            try:
                end_date = datetime.strptime(end, "%Y-%m-%d")
            except:
                pass
                
        start_date = end_date - timedelta(days=100)
        if start:
            try:
                start_date = datetime.strptime(start, "%Y-%m-%d")
            except:
                pass
        
        # Tạo dãy ngày
        dates = [(start_date + timedelta(days=i)).strftime("%Y-%m-%d") 
                for i in range((end_date - start_date).days + 1)]
        
        # Tạo dữ liệu giả
        np.random.seed(int(symbol.encode().hex(), 16) % 100000)  # Seed dựa trên tên symbol
        base_price = np.random.randint(10, 100)
        prices = np.cumsum(np.random.normal(0, 1, len(dates))) + base_price
        prices = np.maximum(prices, base_price * 0.5)  # Đảm bảo giá không âm
        
        # Tạo DataFrame
        df = pd.DataFrame({
            'date': dates,
            'open': prices * np.random.uniform(0.98, 1.0, len(dates)),
            'high': prices * np.random.uniform(1.0, 1.05, len(dates)),
            'low': prices * np.random.uniform(0.95, 0.99, len(dates)),
            'close': prices,
            'volume': np.random.randint(100000, 1000000, len(dates))
        })
    
    if df.empty:
        return {"symbol": symbol, "data": []}

    if indicators:
        df = df.sort_values("date")
        # compute sample indicators (or rely on precomputed columns)
        df['MA20'] = df['close'].rolling(20, min_periods=1).mean()
        df['RSI14'] = 100.0 - (100.0 / (1.0 + df['close'].diff().clip(lower=0).ewm(alpha=1/14, adjust=False).mean() / ( -df['close'].diff().clip(upper=0).ewm(alpha=1/14, adjust=False).mean() )))
        # Convert to records
    records = df.to_dict(orient="records")
    return {"symbol": symbol, "count": len(records), "data": records}
