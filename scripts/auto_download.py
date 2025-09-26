#!/usr/bin/env python3
"""
scripts/auto_download.py

Purpose:
  - Chạy tự động download hằng ngày cho CafeF data
  - Có thể chạy như một dịch vụ hoặc định kỳ (cron job)
  - Tự động bỏ qua nếu đã tải ngày hiện tại/ngày hôm qua
  - Ghi log vào thư mục logs/

Usage:
  python scripts/auto_download.py              # chạy một lần cho ngày hôm qua
  python scripts/auto_download.py --daemon     # chạy liên tục mỗi ngày (thời gian cấu hình)
  python scripts/auto_download.py --time 08:00 # chỉ định giờ chạy (khi ở chế độ daemon)
"""
import os
import sys
import time
import logging
import argparse
from pathlib import Path
from datetime import datetime, timedelta
import subprocess

# Đường dẫn gốc của project
ROOT = Path(__file__).parent.parent.absolute()
LOGS_DIR = ROOT / "logs"
DOWNLOADER = ROOT / "scripts" / "downloader.py"

# Cấu hình logging
LOGS_DIR.mkdir(exist_ok=True)
log_file = LOGS_DIR / f"auto_download_{datetime.now().strftime('%Y%m%d')}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("auto_download")

def parse_args():
    parser = argparse.ArgumentParser(description="Tự động tải dữ liệu CafeF hằng ngày")
    parser.add_argument("--daemon", action="store_true", help="Chạy liên tục như dịch vụ")
    parser.add_argument("--time", default="08:00", help="Thời gian chạy hằng ngày (HH:MM), mặc định 08:00")
    return parser.parse_args()

def run_downloader(date_str=None):
    """Chạy downloader.py với date_str hoặc mặc định là ngày hôm qua"""
    cmd = [sys.executable, str(DOWNLOADER)]
    if date_str:
        cmd.append(date_str)
    
    logger.info(f"Chạy downloader: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        logger.info(f"Kết quả: [exitcode={result.returncode}]")
        if result.stdout:
            for line in result.stdout.splitlines():
                logger.info(f"STDOUT: {line}")
        if result.stderr:
            for line in result.stderr.splitlines():
                logger.error(f"STDERR: {line}")
        return result.returncode == 0
    except Exception as e:
        logger.error(f"Lỗi chạy downloader: {e}")
        return False
        
def run_data_processor(date_str):
    """Chạy data_processor.py để làm sạch và xử lý dữ liệu"""
    DATA_PROCESSOR = ROOT / "scripts" / "data_processor.py"
    if not DATA_PROCESSOR.exists():
        logger.warning(f"Không tìm thấy file data_processor.py tại {DATA_PROCESSOR}")
        return False
    
    input_dir = f"staging/{date_str}/raw"
    output_dir = "parquet"
    
    cmd = [sys.executable, str(DATA_PROCESSOR), input_dir, output_dir]
    
    logger.info(f"Chạy data_processor: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        logger.info(f"Kết quả xử lý dữ liệu: [exitcode={result.returncode}]")
        if result.stdout:
            for line in result.stdout.splitlines():
                logger.info(f"STDOUT: {line}")
        if result.stderr:
            for line in result.stderr.splitlines():
                logger.error(f"STDERR: {line}")
        return result.returncode == 0
    except Exception as e:
        logger.error(f"Lỗi chạy data_processor: {e}")
        return False

def get_next_run_time(time_str):
    """Tính thời gian chạy kế tiếp dựa vào giờ cấu hình"""
    now = datetime.now()
    hour, minute = map(int, time_str.split(':'))
    
    next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    
    # Nếu đã qua giờ chạy của ngày hôm nay, đặt thời gian chạy cho ngày mai
    if next_run <= now:
        next_run += timedelta(days=1)
        
    return next_run

def daemon_mode(time_str):
    """Chạy ở chế độ daemon, tự động tải dữ liệu theo giờ cấu hình mỗi ngày"""
    logger.info(f"Khởi động ở chế độ daemon, sẽ chạy mỗi ngày lúc {time_str}")
    
    while True:
        next_run = get_next_run_time(time_str)
        
        # Tính thời gian cần chờ đến lần chạy kế tiếp
        wait_seconds = (next_run - datetime.now()).total_seconds()
        logger.info(f"Lần chạy kế tiếp: {next_run.strftime('%Y-%m-%d %H:%M:%S')} "
                   f"(sau {wait_seconds/3600:.1f} giờ)")
        
        # Chờ đến thời gian chạy kế tiếp
        time.sleep(wait_seconds)
        
        # Đã đến giờ chạy, download dữ liệu của ngày hôm qua
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
        logger.info(f"Bắt đầu tải dữ liệu cho ngày {yesterday}")
        download_success = run_downloader()
        
        if download_success:
            # Sau khi tải thành công, tiến hành làm sạch và xử lý dữ liệu
            logger.info(f"Bắt đầu làm sạch và xử lý dữ liệu cho ngày {yesterday}")
            process_success = run_data_processor(yesterday)
            if process_success:
                logger.info(f"Hoàn thành xử lý dữ liệu ngày {yesterday}")
            else:
                logger.error(f"Xử lý dữ liệu ngày {yesterday} thất bại")
        
        # Chờ 1 phút để tránh chạy nhiều lần
        time.sleep(60)

def main():
    args = parse_args()
    
    logger.info("=== Khởi động auto_download.py ===")
    
    # Kiểm tra file downloader.py
    if not DOWNLOADER.exists():
        logger.error(f"Không tìm thấy file downloader.py tại {DOWNLOADER}")
        return 1
    
    if args.daemon:
        try:
            daemon_mode(args.time)
        except KeyboardInterrupt:
            logger.info("Nhận tín hiệu dừng, thoát chương trình")
            return 0
    else:
        # Chế độ chạy một lần cho ngày hôm qua
        logger.info("Chạy một lần cho ngày hôm qua")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
        download_success = run_downloader()
        
        if download_success:
            # Sau khi tải thành công, tiến hành làm sạch và xử lý dữ liệu
            logger.info(f"Bắt đầu làm sạch và xử lý dữ liệu cho ngày {yesterday}")
            process_success = run_data_processor(yesterday)
            if process_success:
                logger.info(f"Hoàn thành xử lý dữ liệu ngày {yesterday}")
            else:
                logger.error(f"Xử lý dữ liệu ngày {yesterday} thất bại")
        
        return 0 if download_success else 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
