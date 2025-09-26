#!/usr/bin/env python3
"""
scripts/data_processor_historical.py

Purpose:
  - Xử lý dữ liệu lịch sử từ CafeF (2000-2025)
  - Làm sạch, chuẩn hóa và chuyển đổi dữ liệu historical
  - Tính toán các chỉ báo kỹ thuật cho dữ liệu lịch sử
  - Lưu trữ dưới dạng Parquet theo cấu trúc phân vùng theo năm

Usage:
  python scripts/data_processor_historical.py <input_dir> <output_dir>
  python scripts/data_processor_historical.py staging/20250925/historical parquet
"""

import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path
import logging
from datetime import datetime
import argparse
from tqdm import tqdm

# Đường dẫn gốc của project
SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("data_processor_historical")

def calculate_technical_indicators(df):
    """Tính toán các chỉ báo kỹ thuật"""
    df = df.copy()
    
    # Sắp xếp theo ngày để tính toán chỉ báo đúng
    df = df.sort_values('date')
    
    # Moving Averages
    df['ma_5'] = df['close'].rolling(window=5).mean()
    df['ma_10'] = df['close'].rolling(window=10).mean()
    df['ma_20'] = df['close'].rolling(window=20).mean()
    df['ma_50'] = df['close'].rolling(window=50).mean()
    df['ma_200'] = df['close'].rolling(window=200).mean()
    
    # Exponential Moving Averages
    df['ema_12'] = df['close'].ewm(span=12).mean()
    df['ema_26'] = df['close'].ewm(span=26).mean()
    
    # RSI
    def calculate_rsi(prices, window=14):
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    df['rsi'] = calculate_rsi(df['close'])
    
    # MACD
    df['macd'] = df['ema_12'] - df['ema_26']
    df['macd_signal'] = df['macd'].ewm(span=9).mean()
    df['macd_histogram'] = df['macd'] - df['macd_signal']
    
    # Bollinger Bands
    rolling_mean = df['close'].rolling(window=20).mean()
    rolling_std = df['close'].rolling(window=20).std()
    df['bb_upper'] = rolling_mean + (rolling_std * 2)
    df['bb_lower'] = rolling_mean - (rolling_std * 2)
    df['bb_middle'] = rolling_mean
    
    # Volume indicators
    df['volume_ma_10'] = df['volume'].rolling(window=10).mean()
    df['volume_ratio'] = df['volume'] / df['volume_ma_10']
    
    # Price change indicators
    df['price_change'] = df['close'] - df['open']
    df['price_change_pct'] = (df['price_change'] / df['open']) * 100
    df['daily_return'] = df['close'].pct_change()
    
    return df

def clean_and_process_historical_data(df):
    """Làm sạch và xử lý dữ liệu lịch sử"""
    logger.info(f"Processing {len(df)} records")
    
    # Chuẩn hóa tên cột
    df.columns = [col.strip().lower().replace('<', '').replace('>', '') for col in df.columns]
    
    # Đổi tên cột theo chuẩn
    column_mapping = {
        'ticker': 'symbol',
        'dtyyyymmdd': 'date',
        'open': 'open',
        'high': 'high', 
        'low': 'low',
        'close': 'close',
        'volume': 'volume'
    }
    df = df.rename(columns=column_mapping)
    
    # Chuyển đổi kiểu dữ liệu
    df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
    df['symbol'] = df['symbol'].astype(str).str.upper().str.strip()
    
    # Chuyển đổi các cột giá và volume thành numeric
    price_columns = ['open', 'high', 'low', 'close', 'volume']
    for col in price_columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Lọc bỏ dữ liệu không hợp lệ
    df = df.dropna(subset=['symbol', 'date'])
    df = df[df['close'] > 0]  # Giá phải > 0
    df = df[df['volume'] >= 0]  # Volume >= 0
    
    # Thêm cột year để partition
    df['year'] = df['date'].dt.year
    
    logger.info(f"After cleaning: {len(df)} records")
    return df

def process_historical_csv(file_path, output_dir, exchange):
    """Xử lý file CSV lịch sử lớn"""
    logger.info(f"Processing historical file: {file_path.name} ({exchange})")
    
    chunk_size = 100000  # Xử lý 100k records mỗi lần
    total_processed = 0
    
    # Đọc và xử lý theo chunk để tiết kiệm memory
    chunks = pd.read_csv(file_path, chunksize=chunk_size)
    
    for chunk_idx, chunk in enumerate(chunks):
        logger.info(f"Processing chunk {chunk_idx + 1}")
        
        # Làm sạch dữ liệu
        clean_data = clean_and_process_historical_data(chunk)
        if clean_data.empty:
            continue
        
        # Nhóm theo symbol để tính technical indicators
        symbols_data = []
        for symbol, symbol_data in clean_data.groupby('symbol'):
            if len(symbol_data) < 20:  # Bỏ qua symbol có ít hơn 20 ngày dữ liệu
                continue
                
            # Tính technical indicators
            symbol_with_indicators = calculate_technical_indicators(symbol_data)
            symbols_data.append(symbol_with_indicators)
            
            logger.info(f"Calculated indicators for {symbol}")
        
        if not symbols_data:
            continue
            
        # Gộp tất cả symbols
        processed_data = pd.concat(symbols_data, ignore_index=True)
        
        # Lưu theo partition (symbol + year)
        for (symbol, year), group in processed_data.groupby(['symbol', 'year']):
            output_path = Path(output_dir) / f"symbol={symbol}" / f"year={year}" / "data.parquet"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Xử lý NaN và infinity values
            numeric_columns = group.select_dtypes(include=[np.number]).columns
            group[numeric_columns] = group[numeric_columns].replace([np.inf, -np.inf], np.nan)
            
            # Lưu hoặc append vào file parquet
            if output_path.exists():
                existing_data = pd.read_parquet(output_path)
                # Merge và deduplicate theo date
                combined = pd.concat([existing_data, group], ignore_index=True)
                combined = combined.drop_duplicates(subset=['symbol', 'date'], keep='last')
                combined = combined.sort_values('date')
                combined.to_parquet(output_path, index=False)
                logger.info(f"Updated {output_path} with {len(group)} new records")
            else:
                group.to_parquet(output_path, index=False)
                logger.info(f"Created {output_path} with {len(group)} records")
        
        total_processed += len(processed_data)
    
    logger.info(f"Total processed {total_processed} records for {exchange}")
    return True

def process_directory(input_dir, output_dir):
    """Xử lý thư mục chứa dữ liệu historical"""
    input_path = PROJECT_ROOT / input_dir if not Path(input_dir).is_absolute() else Path(input_dir)
    output_path = PROJECT_ROOT / output_dir if not Path(output_dir).is_absolute() else Path(output_dir)
    
    logger.info(f"Processing historical data from: {input_path}")
    logger.info(f"Output directory: {output_path}")
    
    # Tìm tất cả file historical CSV
    historical_files = []
    patterns = ["*Upto*.csv", "*Historical*.csv", "*historical*.csv"]
    for pattern in patterns:
        historical_files.extend(list(input_path.rglob(pattern)))
    
    if not historical_files:
        logger.error(f"No historical CSV files found in {input_path}")
        return False
    
    logger.info(f"Found {len(historical_files)} historical files")
    
    success_count = 0
    for csv_file in historical_files:
        try:
            # Phát hiện exchange từ tên file
            if "HSX" in csv_file.name.upper():
                exchange = "HSX"
            elif "HNX" in csv_file.name.upper():
                exchange = "HNX"
            elif "UPCOM" in csv_file.name.upper():
                exchange = "UPCOM"
            else:
                exchange = "UNKNOWN"
                logger.warning(f"Cannot detect exchange for {csv_file.name}")
            
            success = process_historical_csv(csv_file, output_path, exchange)
            if success:
                success_count += 1
                
        except Exception as e:
            logger.error(f"Error processing {csv_file}: {e}")
            continue
    
    logger.info(f"Successfully processed {success_count}/{len(historical_files)} files")
    return success_count > 0

def parse_args():
    """Xử lý tham số dòng lệnh"""
    parser = argparse.ArgumentParser(description="Process historical stock data into Parquet format")
    parser.add_argument("input_dir", help="Directory containing historical CSV files")
    parser.add_argument("output_dir", help="Directory for output Parquet files")
    parser.add_argument("--chunk-size", type=int, default=100000, help="Chunk size for processing large files")
    return parser.parse_args()

def main():
    """Hàm chính"""
    args = parse_args()
    
    logger.info(f"Starting historical data processing: {args.input_dir} -> {args.output_dir}")
    success = process_directory(args.input_dir, args.output_dir)
    
    if success:
        logger.info("Historical data processing completed successfully")
        return 0
    else:
        logger.error("Historical data processing failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())