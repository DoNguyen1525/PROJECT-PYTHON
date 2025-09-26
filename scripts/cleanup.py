#!/usr/bin/env python3
"""
scripts/cleanup.py

Purpose:
  - Dọn dẹp các file tạm, file trùng lặp
  - Xóa bỏ dữ liệu không cần thiết  
  - Tối ưu hóa không gian lưu trữ

Usage:
  python scripts/cleanup.py --dry-run     # Xem trước sẽ xóa gì
  python scripts/cleanup.py              # Thực hiện cleanup
  python scripts/cleanup.py --deep       # Deep cleanup (cẩn thận!)
"""

import os
import sys
from pathlib import Path
import logging
import argparse
from datetime import datetime, timedelta

SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("cleanup")

def cleanup_staging(dry_run=False):
    """Dọn dẹp thư mục staging"""
    staging_dir = PROJECT_ROOT / "staging"
    if not staging_dir.exists():
        return
    
    logger.info("Cleaning up staging directory...")
    
    # Xóa file .DS_Store
    ds_store_files = list(staging_dir.rglob(".DS_Store"))
    for file in ds_store_files:
        logger.info(f"Removing .DS_Store: {file}")
        if not dry_run:
            file.unlink()
    
    # Xóa các file ZIP nhỏ (< 1MB) khi đã có file historical lớn
    for date_dir in staging_dir.iterdir():
        if not date_dir.is_dir():
            continue
            
        historical_dir = date_dir / "historical"
        zip_files = list(date_dir.glob("*.zip"))
        
        if historical_dir.exists() and any(historical_dir.glob("*Upto*.csv")):
            # Có dữ liệu historical, xóa ZIP files nhỏ
            for zip_file in zip_files:
                if zip_file.stat().st_size < 1024 * 1024:  # < 1MB
                    logger.info(f"Removing small ZIP (have historical): {zip_file}")
                    if not dry_run:
                        zip_file.unlink()

def cleanup_logs(dry_run=False, keep_days=30):
    """Dọn dẹp log files cũ"""
    logs_dir = PROJECT_ROOT / "logs"
    if not logs_dir.exists():
        return
        
    logger.info(f"Cleaning up logs older than {keep_days} days...")
    
    cutoff_date = datetime.now() - timedelta(days=keep_days)
    
    for log_file in logs_dir.glob("*.log"):
        if log_file.stat().st_mtime < cutoff_date.timestamp():
            logger.info(f"Removing old log: {log_file}")
            if not dry_run:
                log_file.unlink()

def cleanup_temp_files(dry_run=False):
    """Xóa các file tạm"""
    logger.info("Cleaning up temporary files...")
    
    # Tìm các file .part, .tmp, .temp
    temp_patterns = ["**/*.part", "**/*.tmp", "**/*.temp", "**/*~"]
    
    for pattern in temp_patterns:
        temp_files = list(PROJECT_ROOT.rglob(pattern))
        for file in temp_files:
            logger.info(f"Removing temp file: {file}")
            if not dry_run:
                file.unlink()

def cleanup_empty_directories(dry_run=False):
    """Xóa các thư mục rỗng"""
    logger.info("Removing empty directories...")
    
    for root, dirs, files in os.walk(PROJECT_ROOT, topdown=False):
        for dir_name in dirs:
            dir_path = Path(root) / dir_name
            try:
                if not any(dir_path.iterdir()):  # Thư mục rỗng
                    logger.info(f"Removing empty directory: {dir_path}")
                    if not dry_run:
                        dir_path.rmdir()
            except (OSError, PermissionError):
                continue

def deep_cleanup(dry_run=False):
    """Deep cleanup - cẩn thận!"""
    logger.warning("Performing DEEP cleanup - this will remove more data!")
    
    # Xóa các file backup cũ hơn 7 ngày
    backup_patterns = ["**/*.bak", "**/*.backup", "**/*.old"]
    cutoff_date = datetime.now() - timedelta(days=7)
    
    for pattern in backup_patterns:
        backup_files = list(PROJECT_ROOT.rglob(pattern))
        for file in backup_files:
            if file.stat().st_mtime < cutoff_date.timestamp():
                logger.info(f"Removing old backup: {file}")
                if not dry_run:
                    file.unlink()

def show_disk_usage():
    """Hiển thị thống kê sử dụng disk"""
    logger.info("Disk usage statistics:")
    
    directories = ["staging", "parquet", "metadata", "logs"]
    
    for dir_name in directories:
        dir_path = PROJECT_ROOT / dir_name
        if dir_path.exists():
            total_size = sum(f.stat().st_size for f in dir_path.rglob('*') if f.is_file())
            logger.info(f"{dir_name}: {total_size / (1024*1024):.1f} MB")

def main():
    parser = argparse.ArgumentParser(description="Cleanup project files")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted")
    parser.add_argument("--deep", action="store_true", help="Perform deep cleanup")
    parser.add_argument("--keep-logs", type=int, default=30, help="Keep logs for N days")
    
    args = parser.parse_args()
    
    if args.dry_run:
        logger.info("DRY RUN - showing what would be deleted:")
    
    logger.info("Starting cleanup process...")
    
    show_disk_usage()
    
    cleanup_temp_files(args.dry_run)
    cleanup_staging(args.dry_run) 
    cleanup_logs(args.dry_run, args.keep_logs)
    cleanup_empty_directories(args.dry_run)
    
    if args.deep:
        deep_cleanup(args.dry_run)
    
    logger.info("Cleanup completed!")
    
    if not args.dry_run:
        show_disk_usage()

if __name__ == "__main__":
    main()