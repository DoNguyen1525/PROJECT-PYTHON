#!/usr/bin/env python3
"""
scripts/data_processor.py

Purpose:
  - Xử lý dữ liệu thô từ CafeF
  - Làm sạch, chuẩn hóa và chuyển đổi dữ liệu
  - Tính toán các chỉ báo kỹ thuật
  - Lưu trữ dưới dạng Parquet theo cấu trúc phân vùng

Usage:
  python scripts/data_processor.py <input_dir> <output_dir>
  python scripts/data_processor.py staging/20250926/raw parquet
"""

import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path
import logging
from datetime import datetime
import argparse

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("data_processor")

def analyze_raw_data(file_path):
    """Phân tích cấu trúc file CSV gốc"""
    logger.info(f"Analyzing file: {file_path}")
    try:
        # Đọc mẫu dữ liệu
        sample = pd.read_csv(file_path, nrows=100)
        
        # Phân tích cấu trúc
        logger.info(f"Columns: {', '.join(sample.columns)}")
        logger.info(f"Data types: {sample.dtypes}")
        
        # Kiểm tra giá trị null
        null_counts = sample.isnull().sum()
        if null_counts.sum() > 0:
            logger.warning(f"Found null values: {null_counts[null_counts > 0]}")
        
        # Kiểm tra các giá trị duy nhất trong một số cột quan trọng
        if 'ticker' in sample.columns:
            logger.info(f"Sample tickers: {', '.join(sample['ticker'].unique()[:5])}")
        
        return True
    except Exception as e:
        logger.error(f"Error analyzing file {file_path}: {e}")
        return False

def clean_data(df):
    """Làm sạch và chuẩn hóa dữ liệu"""
    # 1. Chuẩn hóa tên cột
    df.columns = [c.strip().lower().replace('<', '').replace('>', '') for c in df.columns]
    
    # Xử lý các tên cột từ CafeF (chuyển đổi <Ticker> thành ticker, <DTYYYYMMDD> thành date, v.v.)
    rename_map = {
        'ticker': 'ticker', 
        'dtyyyymmdd': 'date',
        'open': 'open',
        'high': 'high',
        'low': 'low',
        'close': 'close',
        'volume': 'volume'
    }
    
    # Áp dụng ánh xạ tên cột
    df = df.rename(columns=rename_map)
    
    # 2. Kiểm tra các cột bắt buộc
    required_cols = ['ticker', 'date']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        logger.error(f"Missing required columns: {', '.join(missing_cols)}")
        return None
    
    # 3. Chuẩn hóa mã chứng khoán
    df['symbol'] = df['ticker'].str.strip().str.upper()
    
    # 4. Chuyển đổi ngày tháng
    try:
        # Định dạng cho cột date từ CafeF (YYYYMMDD)
        if df['date'].dtype == 'int64' or df['date'].dtype == 'int32' or (df['date'].dtype == 'object' and df['date'].str.isdigit().all()):
            # Chuyển đổi từ dạng 20250925 sang định dạng ngày
            df['date'] = pd.to_datetime(df['date'].astype(str), format='%Y%m%d', errors='coerce')
        else:
            # Xử lý các định dạng khác
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
        
        df = df.dropna(subset=['date'])  # Loại bỏ các hàng có ngày không hợp lệ
    except Exception as e:
        logger.error(f"Error converting date column: {e}")
        return None
    
    # 5. Chuyển đổi kiểu dữ liệu cho các cột số
    numeric_cols = ['open', 'high', 'low', 'close', 'volume']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # 6. Kiểm tra và xử lý dữ liệu giá không hợp lệ
    price_cols = [col for col in ['open', 'high', 'low', 'close'] if col in df.columns]
    if price_cols:
        # Loại bỏ các hàng có giá âm
        df = df[df[price_cols].gt(0).all(axis=1)]
        
        # Kiểm tra quan hệ giữa OHLC (nếu đầy đủ)
        if all(col in df.columns for col in ['open', 'high', 'low', 'close']):
            valid_ohlc = (df['high'] >= df['open']) & (df['high'] >= df['close']) & \
                         (df['low'] <= df['open']) & (df['low'] <= df['close'])
            invalid_count = (~valid_ohlc).sum()
            if invalid_count > 0:
                logger.warning(f"Found {invalid_count} rows with invalid OHLC relationships")
                df = df[valid_ohlc]
    
    # 7. Xử lý volume (nếu có)
    if 'volume' in df.columns:
        df['volume'] = df['volume'].fillna(0).astype(float)
        df.loc[df['volume'] < 0, 'volume'] = 0
    
    # 8. Loại bỏ dữ liệu trùng lặp
    df = df.drop_duplicates(subset=['symbol', 'date'])
    
    return df

def calculate_indicators(df, symbol):
    """Tính toán các chỉ báo kỹ thuật"""
    # Đảm bảo dữ liệu được sắp xếp theo ngày
    df = df.sort_values('date')
    
    # Kiểm tra đủ cột cần thiết
    required_cols = ['close', 'high', 'low', 'volume']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        logger.warning(f"Symbol {symbol}: Missing columns for indicators: {', '.join(missing_cols)}")
        return df
    
    try:
        # Moving Averages
        for period in [5, 10, 20, 50, 100, 200]:
            df[f'MA{period}'] = df['close'].rolling(window=period, min_periods=1).mean()
        
        # Exponential Moving Averages
        for period in [5, 10, 20, 50]:
            df[f'EMA{period}'] = df['close'].ewm(span=period, adjust=False).mean()
        
        # RSI (Relative Strength Index)
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=14, min_periods=1).mean()
        avg_loss = loss.rolling(window=14, min_periods=1).mean()
        
        rs = avg_gain / avg_loss
        df['RSI14'] = 100 - (100 / (1 + rs))
        
        # MACD (Moving Average Convergence Divergence)
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_Histogram'] = df['MACD'] - df['MACD_Signal']
        
        # Bollinger Bands
        df['BB_Middle'] = df['close'].rolling(window=20, min_periods=1).mean()
        df['BB_Std'] = df['close'].rolling(window=20, min_periods=1).std()
        df['BB_Upper'] = df['BB_Middle'] + (df['BB_Std'] * 2)
        df['BB_Lower'] = df['BB_Middle'] - (df['BB_Std'] * 2)
        
        # ATR (Average True Range)
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift()).abs()
        low_close = (df['low'] - df['close'].shift()).abs()
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['ATR14'] = true_range.rolling(window=14, min_periods=1).mean()
        
        # Stochastic Oscillator
        low_min = df['low'].rolling(window=14, min_periods=1).min()
        high_max = df['high'].rolling(window=14, min_periods=1).max()
        df['Stoch_K'] = 100 * ((df['close'] - low_min) / (high_max - low_min))
        df['Stoch_D'] = df['Stoch_K'].rolling(window=3, min_periods=1).mean()
        
        # Volume Moving Average
        df['Volume_MA20'] = df['volume'].rolling(window=20, min_periods=1).mean()
        
        # Price change
        df['Price_Change'] = df['close'].pct_change() * 100
        df['Price_Change_5D'] = (df['close'] / df['close'].shift(5) - 1) * 100
        
        logger.info(f"Successfully calculated indicators for {symbol}")
        return df
    
    except Exception as e:
        logger.error(f"Error calculating indicators for {symbol}: {e}")
        return df

def process_csv_file(file_path, output_dir):
    """Xử lý một file CSV và lưu ra Parquet"""
    logger.info(f"Processing file: {file_path}")
    
    try:
        # Đọc file CSV, bỏ qua hàng đầu tiên nếu nó không phải dữ liệu (tiêu đề CSV từ CafeF thường có hàng đầu)
        df = pd.read_csv(file_path, skiprows=lambda x: x == 0 and '<Ticker>' not in open(file_path).readline())
        
        # Phân tích cấu trúc
        if df.empty:
            logger.warning(f"Empty file: {file_path}")
            return False
        
        # Làm sạch dữ liệu
        df_clean = clean_data(df)
        if df_clean is None or df_clean.empty:
            logger.error(f"Failed to clean data from {file_path}")
            return False
        
        # Xử lý từng mã chứng khoán
        symbols = df_clean['symbol'].unique()
        logger.info(f"Found {len(symbols)} symbols in {file_path}")
        
        for symbol in symbols:
            symbol_df = df_clean[df_clean['symbol'] == symbol].copy()
            
            # Tính toán chỉ báo kỹ thuật
            symbol_df = calculate_indicators(symbol_df, symbol)
            
            # Tạo cấu trúc thư mục phân vùng
            years = symbol_df['date'].dt.year.unique()
            for year in years:
                year_df = symbol_df[symbol_df['date'].dt.year == year]
                
                # Tạo đường dẫn đầu ra
                parquet_dir = Path(output_dir) / f"symbol={symbol}" / f"year={year}"
                parquet_dir.mkdir(parents=True, exist_ok=True)
                parquet_path = parquet_dir / "data.parquet"
                
                # Kiểm tra nếu file đã tồn tại
                if parquet_path.exists():
                    # Đọc dữ liệu hiện có
                    try:
                        existing_df = pd.read_parquet(parquet_path)
                        # Gộp với dữ liệu mới
                        combined_df = pd.concat([existing_df, year_df])
                        # Loại bỏ dữ liệu trùng lặp
                        combined_df = combined_df.drop_duplicates(subset=['date']).sort_values('date')
                        # Ghi lại file
                        combined_df.to_parquet(parquet_path, index=False)
                        logger.info(f"Updated {parquet_path} with {len(year_df)} new records")
                    except Exception as e:
                        logger.error(f"Error updating {parquet_path}: {e}")
                        # Nếu lỗi, ghi đè file
                        year_df.to_parquet(parquet_path, index=False)
                else:
                    # Tạo file mới
                    year_df.to_parquet(parquet_path, index=False)
                    logger.info(f"Created {parquet_path} with {len(year_df)} records")
        
        return True
    
    except Exception as e:
        logger.error(f"Error processing {file_path}: {e}")
        return False

def process_directory(input_dir, output_dir):
    """Xử lý tất cả các file CSV trong thư mục"""
    input_path = Path(input_dir)
    if not input_path.exists():
        logger.error(f"Input directory not found: {input_dir}")
        return False
    
    # Tạo thư mục đầu ra nếu chưa tồn tại
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Tìm tất cả các file CSV
    csv_files = list(input_path.glob("**/*.csv"))
    logger.info(f"Found {len(csv_files)} CSV files in {input_dir}")
    
    # Xử lý từng file
    success_count = 0
    for file_path in csv_files:
        if process_csv_file(file_path, output_dir):
            success_count += 1
    
    logger.info(f"Successfully processed {success_count}/{len(csv_files)} files")
    return success_count > 0

def parse_args():
    """Xử lý tham số dòng lệnh"""
    parser = argparse.ArgumentParser(description="Process raw stock data into Parquet format")
    parser.add_argument("input_dir", help="Directory containing raw CSV files")
    parser.add_argument("output_dir", help="Directory for output Parquet files")
    parser.add_argument("--force", action="store_true", help="Force overwrite existing data")
    return parser.parse_args()

def main():
    """Hàm chính"""
    args = parse_args()
    
    logger.info(f"Starting data processing: {args.input_dir} -> {args.output_dir}")
    success = process_directory(args.input_dir, args.output_dir)
    
    if success:
        logger.info("Data processing completed successfully")
        return 0
    else:
        logger.error("Data processing failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
