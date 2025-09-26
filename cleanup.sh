#!/bin/bash
# cleanup.sh - Dọn dẹp các file tạm thời và cache

echo "🧹 Bắt đầu dọn dẹp dự án..."

# Xóa Python cache
echo "🔸 Xóa __pycache__ folders..."
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null

# Xóa file .pyc
echo "🔸 Xóa .pyc files..."
find . -name "*.pyc" -delete 2>/dev/null

# Xóa .DS_Store (macOS)
echo "🔸 Xóa .DS_Store files..."
find . -name ".DS_Store" -delete 2>/dev/null

# Xóa log files cũ (hơn 30 ngày)
echo "🔸 Xóa log files cũ..."
find logs/ -name "*.log" -mtime +30 -delete 2>/dev/null

# Hiển thị kết quả
echo "✅ Dọn dẹp hoàn tất!"
echo "📊 Dung lượng hiện tại:"
du -sh .