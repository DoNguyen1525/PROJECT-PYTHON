<<<<<<< HEAD

# CafeF Data Downloader & Stock Analysis

🚀 Hệ thống tải dữ liệu giao dịch từ CafeF, xử lý, tính toán các chỉ báo kỹ thuật, và cung cấp API để truy vấn dữ liệu chứng khoán.

## 📋 Mục lục
- [Tính năng chính](#-tính-năng-chính)
- [Cấu trúc dự án](#-cấu-trúc-dự-án)
- [Yêu cầu hệ thống](#-yêu-cầu-hệ-thống)
- [Cài đặt trên macOS](#-cài-đặt-trên-macos)
- [Cài đặt trên Windows](#-cài-đặt-trên-windows)
- [Cấu hình](#-cấu-hình)
- [Cách sử dụng](#-cách-sử-dụng)
- [API Documentation](#-api-documentation)
- [Troubleshooting](#-troubleshooting)
- [Bảo trì](#-bảo-trì)

## 🌟 Tính năng chính

- ✅ **Tải dữ liệu tự động** từ CafeF theo ngày/tự động hàng ngày
- 📊 **Tính toán chỉ báo kỹ thuật** (MA, RSI, v.v.)
- 🗄️ **Lưu trữ hiệu quả** với Parquet format
- 🔍 **API RESTful** để truy vấn dữ liệu
- 📱 **Swagger UI** tích hợp
- 🔄 **Xử lý dữ liệu theo batch**
- 📈 **Hỗ trợ múi giờ Việt Nam**

## 📁 Cấu trúc dự án

```
project-root/
├── 📄 README.md              # Hướng dẫn này
├── ⚙️ requirements.txt       # Python dependencies
├── 🧹 cleanup.sh            # Script dọn dẹp
├── 📝 .env                  # Cấu hình môi trường
├── 📋 API_USAGE_GUIDE.md    # Hướng dẫn sử dụng API
├── 📁 scripts/              # Scripts chính
│   ├── 🌐 api_demo_fast.py  # FastAPI server
│   ├── ⬇️ downloader.py     # Tải dữ liệu thủ công
│   ├── ⚡ auto_download.py   # Tải dữ liệu tự động
│   └── 🔄 data_processor.py # Xử lý dữ liệu
├── 📁 logs/                 # Log files
├── 📁 metadata/             # Database và metadata
│   ├── 🗃️ symbol_index.sqlite    # Index mã chứng khoán
│   └── 📄 ingest_manifest.json   # Thông tin file đã tải
├── 📁 parquet/              # Dữ liệu đã xử lý
│   ├── 📊 symbol=VNM/       # Dữ liệu theo mã CK
│   └── 📊 symbol=FPT/
└── 📁 staging/              # Dữ liệu tạm
    └── 📅 YYYYMMDD/         # Theo ngày
        ├── 📁 raw/          # CSV đã giải nén
        └── 🗜️ CafeF.*.zip   # File ZIP gốc
```

## 💻 Yêu cầu hệ thống

### Chung
- **Python**: 3.8+ (khuyến nghị 3.9+)
- **RAM**: Tối thiểu 4GB (khuyến nghị 8GB+)
- **Dung lượng**: 2GB+ trống cho dữ liệu
- **Internet**: Để tải dữ liệu từ CafeF

### macOS
- **Hệ điều hành**: macOS 10.14+ (Mojave trở lên)
- **Homebrew**: Để cài đặt Python và các công cụ
- **Xcode Command Line Tools**: `xcode-select --install`

### Windows
- **Hệ điều hành**: Windows 10+ (64-bit)
- **PowerShell**: 5.1+ hoặc PowerShell Core 7+
- **Visual Studio Build Tools**: Cho một số Python packages

## 🍎 Cài đặt trên macOS

### Bước 1: Cài đặt Anaconda (Khuyến nghị)

```bash
# Tải Anaconda từ https://www.anaconda.com/download
# Hoặc cài bằng Homebrew
brew install anaconda

# Khởi động lại terminal hoặc chạy:
source ~/.bash_profile  # hoặc ~/.zshrc
```

### Bước 2: Clone và setup dự án

```bash
# Di chuyển đến thư mục làm việc
cd ~/Documents

# Clone repository (nếu từ Git)
git clone <repository-url>
cd project-root

# Hoặc giải nén file ZIP vào thư mục project-root
```

### Bước 3: Tạo môi trường Python

```bash
# Tạo môi trường conda mới
conda create -n cafef-project python=3.9 -y

# Kích hoạt môi trường
conda activate cafef-project

# Cài đặt dependencies
pip install -r requirements.txt

# Kiểm tra cài đặt
python -c "import fastapi, pandas, duckdb; print('✅ All packages installed successfully!')"
```

### Bước 4: Thiết lập quyền thực thi

```bash
# Cho phép chạy scripts
chmod +x cleanup.sh
chmod +x scripts/*.py

# Tạo thư mục cần thiết
mkdir -p logs metadata staging parquet
```

## 🪟 Cài đặt trên Windows

### Bước 1: Cài đặt Anaconda

1. **Tải Anaconda**:
   - Truy cập https://www.anaconda.com/download
   - Tải phiên bản Windows 64-bit
   - Chạy file .exe và làm theo hướng dẫn

2. **Mở Anaconda Prompt**:
   - Tìm "Anaconda Prompt" trong Start Menu
   - Chạy với quyền Administrator

### Bước 2: Setup dự án

```powershell
# Di chuyển đến thư mục làm việc
cd C:\Users\%USERNAME%\Documents

# Clone repository hoặc giải nén file ZIP
# Giả sử đã có thư mục project-root
cd project-root
```

### Bước 3: Tạo môi trường Python

```powershell
# Tạo môi trường conda mới
conda create -n cafef-project python=3.9 -y

# Kích hoạt môi trường
conda activate cafef-project

# Cài đặt dependencies
pip install -r requirements.txt

# Kiểm tra cài đặt
python -c "import fastapi, pandas, duckdb; print('✅ All packages installed successfully!')"
```

### Bước 4: Tạo batch files để dễ sử dụng

Tạo file `run_api.bat`:
```batch
@echo off
echo 🚀 Starting CafeF API Server...
call conda activate cafef-project
cd /d "%~dp0"
python scripts/api_demo_fast.py
pause
```

Tạo file `download_data.bat`:
```batch
@echo off
echo 📥 Downloading CafeF data...
call conda activate cafef-project
cd /d "%~dp0"
python scripts/downloader.py
pause
```

## ⚙️ Cấu hình

### File .env

Chỉnh sửa file `.env` trong thư mục gốc:

```bash
# Đường dẫn đến dữ liệu CSV (có thể để trống nếu dùng staging)
DATA_SRC_DIR=

# Port cho API server
API_PORT=9999

# Thư mục lưu dữ liệu Parquet
PARQUET_ROOT=./parquet

# Database file
SQLITE_DB=./metadata/symbol_index.sqlite

# Manifest file
MANIFEST=./metadata/ingest_manifest.json
```

### Cài đặt múi giờ

**macOS:**
```bash
export TZ=Asia/Ho_Chi_Minh
```

**Windows:**
```powershell
tzutil /s "SE Asia Standard Time"
```

## 🚀 Cách sử dụng

### 1. Khởi động API Server

**macOS/Linux:**
```bash
# Kích hoạt môi trường
conda activate cafef-project

# Khởi động server
python scripts/api_demo_fast.py

# Hoặc với uvicorn (production mode)
uvicorn scripts.api_demo_fast:app --host 0.0.0.0 --port 9999 --reload
```

**Windows:**
```powershell
# Kích hoạt môi trường
conda activate cafef-project

# Khởi động server
python scripts/api_demo_fast.py

# Hoặc double-click file run_api.bat
```

🌐 **Truy cập API**: http://localhost:9999

### 2. Tải dữ liệu

#### Tải thủ công

**macOS/Linux:**
```bash
# Tải dữ liệu hôm qua
python scripts/downloader.py

# Tải dữ liệu ngày cụ thể
python scripts/downloader.py 20250925
```

**Windows:**
```powershell
# Tải dữ liệu hôm qua
python scripts/downloader.py

# Tải dữ liệu ngày cụ thể
python scripts/downloader.py 20250925

# Hoặc double-click file download_data.bat
```

#### Tải tự động

**macOS với cron:**
```bash
# Mở crontab
crontab -e

# Thêm dòng sau (tải lúc 8h sáng mỗi ngày)
0 8 * * * cd /path/to/project-root && /usr/local/anaconda3/envs/cafef-project/bin/python scripts/auto_download.py >> logs/auto_download.log 2>&1
```

**Windows với Task Scheduler:**
1. Mở Task Scheduler
2. Tạo Basic Task mới
3. Trigger: Daily, 8:00 AM
4. Action: Start a program
5. Program: `C:\Users\%USERNAME%\anaconda3\envs\cafef-project\python.exe`
6. Arguments: `scripts\auto_download.py`
7. Start in: `C:\path\to\project-root`

#### Chế độ daemon (chạy liên tục)

```bash
# macOS/Linux
nohup python scripts/auto_download.py --daemon --time 08:00 > logs/daemon.log 2>&1 &

# Windows (trong PowerShell)
Start-Process -NoNewWindow python -ArgumentList "scripts/auto_download.py --daemon --time 08:00"
```

### 3. Xử lý dữ liệu

```bash
# Xử lý dữ liệu mới nhất
python -m scripts.data_processor staging/20250926/raw parquet

# Xử lý với tùy chọn
python -m scripts.data_processor staging/20250926/raw parquet --indicators --cleanup
```

## 📚 API Documentation

### Endpoints chính

| Endpoint | Method | Mô tả |
|----------|---------|--------|
| `/` | GET | Thông tin API |
| `/docs` | GET | Swagger UI |
| `/symbols` | GET | Danh sách mã chứng khoán |
| `/search?q={keyword}` | GET | Tìm kiếm mã CK |
| `/exchanges` | GET | Danh sách sàn giao dịch |
| `/exchange/{exchange}` | GET | Mã CK theo sàn |
| `/symbol/{symbol}` | GET | Dữ liệu chi tiết mã CK |

### Ví dụ sử dụng

```bash
# Lấy danh sách mã chứng khoán
curl http://localhost:9999/symbols

# Tìm kiếm mã chứa "VN"
curl http://localhost:9999/search?q=VN

# Lấy dữ liệu VNM
curl http://localhost:9999/symbol/VNM

# Lấy dữ liệu VNM trong khoảng thời gian
curl "http://localhost:9999/symbol/VNM?start=2024-01-01&end=2024-12-31"
```

### Response format

```json
{
  "symbol": "VNM",
  "count": 252,
  "data": [
    {
      "date": "2024-01-02",
      "open": 116500,
      "high": 117600,
      "low": 116100,
      "close": 117400,
      "volume": 1234567,
      "MA20": 115700,
      "RSI14": 58.3
    }
  ]
}
```

## 🔧 Troubleshooting

### Lỗi thường gặp

#### 1. Port đã được sử dụng

**Lỗi:** `[Errno 48] Address already in use`

**Giải pháp:**
```bash
# Tìm tiến trình đang dùng port
lsof -i :9999  # macOS/Linux
netstat -ano | findstr :9999  # Windows

# Dừng tiến trình
kill -9 <PID>  # macOS/Linux
taskkill /PID <PID> /F  # Windows
```

#### 2. Không tìm thấy module

**Lỗi:** `ModuleNotFoundError: No module named 'scripts'`

**Giải pháp:**
```bash
# Đảm bảo đang ở thư mục gốc
pwd  # Phải là .../project-root

# Tạo __init__.py nếu chưa có
touch scripts/__init__.py

# Chạy với PYTHONPATH
PYTHONPATH=. python scripts/api_demo_fast.py
```

#### 3. Lỗi database

**Lỗi:** `sqlite3.DatabaseError: database is locked`

**Giải pháp:**
```bash
# Dừng tất cả tiến trình Python
pkill -f python  # macOS/Linux
taskkill /IM python.exe /F  # Windows

# Xóa file lock (nếu có)
rm -f metadata/*.sqlite-wal metadata/*.sqlite-shm
```

#### 4. Lỗi memory

**Lỗi:** `MemoryError` khi xử lý dữ liệu lớn

**Giải pháp:**
```python
# Trong data_processor.py, giảm chunk_size
chunk_size = 1000  # thay vì 5000

# Hoặc tăng RAM swap
# macOS: System Preferences > Memory
# Windows: Control Panel > System > Advanced > Virtual Memory
```

### Kiểm tra hệ thống

#### Kiểm tra Python environment

```bash
# Kiểm tra phiên bản Python
python --version

# Kiểm tra packages đã cài
pip list | grep -E "(fastapi|pandas|duckdb)"

# Kiểm tra môi trường conda
conda info --envs
```

#### Kiểm tra dịch vụ

```bash
# Kiểm tra API có chạy không
curl -I http://localhost:9999

# Kiểm tra database
sqlite3 metadata/symbol_index.sqlite ".tables"

# Kiểm tra log files
tail -f logs/auto_download_$(date +%Y%m%d).log
```

### Performance tuning

#### Tối ưu database

```sql
-- Chạy trong sqlite3 metadata/symbol_index.sqlite
VACUUM;
REINDEX;
ANALYZE;
```

#### Tối ưu Parquet files

```bash
# Nén lại parquet files
python -c "
import pandas as pd
import pyarrow.parquet as pq
# Code tối ưu parquet...
"
```

## 🧹 Bảo trì

### Dọn dẹp định kỳ

```bash
# Chạy script dọn dẹp
./cleanup.sh

# Hoặc thủ công
find . -name "__pycache__" -exec rm -rf {} +
find . -name "*.pyc" -delete
find . -name ".DS_Store" -delete  # macOS only
```

### Backup dữ liệu

```bash
# Backup metadata
cp -r metadata/ backup_metadata_$(date +%Y%m%d)/

# Backup parquet (chọn lọc)
cp -r parquet/symbol=VNM/ backup_parquet/

# Tạo script backup tự động
# backup.sh
#!/bin/bash
DATE=$(date +%Y%m%d)
tar -czf backup_$DATE.tar.gz metadata/ logs/ *.md *.txt *.env scripts/
```

### Update dependencies

```bash
# Kiểm tra packages lỗi thời
pip list --outdated

# Update cẩn thận
pip install --upgrade pandas pyarrow fastapi

# Test sau khi update
python -c "import fastapi, pandas, duckdb; print('OK')"
```

### Monitoring

#### Log rotation

**macOS/Linux:**
```bash
# Thêm vào crontab
0 0 * * 0 find logs/ -name "*.log" -mtime +30 -delete
```

**Windows Task Scheduler:**
```batch
forfiles /p logs /s /m *.log /d -30 /c "cmd /c del @path"
```

#### Disk space monitoring

```bash
# Kiểm tra dung lượng
du -sh parquet/ staging/ logs/

# Alert khi gần đầy (Linux/macOS)
df -h . | awk 'NR==2{if($5+0 > 80) print "Warning: Disk space > 80%"}'
```

## 📞 Hỗ trợ

### Thông tin debug

Khi gặp vấn đề, vui lòng cung cấp:

1. **Hệ điều hành**: macOS/Windows version
2. **Python version**: `python --version`
3. **Conda environment**: `conda info --envs`
4. **Error message**: Copy đầy đủ từ terminal
5. **Log files**: Từ thư mục `logs/`

### Liên hệ

- **GitHub Issues**: [Link to repository issues]
- **Email**: [your-email@example.com]

---

🎉 **Chúc bạn sử dụng dự án thành công!**

> 💡 **Tip**: Bookmark trang http://localhost:9999/docs để nhanh chóng truy cập Swagger UI

## 📄 License

[Chỉ định license của dự án - MIT, Apache, etc.]

## Sử dụng

### Tải thủ công theo ngày

```bash
# Tải dữ liệu của ngày hôm qua
python scripts/downloader.py

# Tải dữ liệu của ngày cụ thể (định dạng YYYYMMDD)
python scripts/downloader.py 20250925
```

### Tự động tải hằng ngày

Có hai cách để tự động tải dữ liệu:

1. **Sử dụng script auto_download.py với chế độ daemon:**

```bash
# Chạy liên tục và tải dữ liệu lúc 8 giờ sáng mỗi ngày
python scripts/auto_download.py --daemon

# Chạy liên tục và tải dữ liệu lúc 22 giờ mỗi ngày
python scripts/auto_download.py --daemon --time 22:00
```

2. **Sử dụng cron job (Linux/macOS):**

```bash
# Mở crontab editor
crontab -e

# Thêm dòng sau để chạy lúc 8 giờ sáng mỗi ngày
0 8 * * * cd /đường/dẫn/đến/project-root && python scripts/downloader.py

# Hoặc thêm dòng sau để chạy với log
0 8 * * * cd /đường/dẫn/đến/project-root && python scripts/downloader.py >> logs/cron_download.log 2>&1
```

3. **Sử dụng Task Scheduler (Windows):**

Tạo một batch file `download.bat`:

```batch
cd C:\đường\dẫn\đến\project-root
python scripts\downloader.py
```

Sau đó tạo một task trong Task Scheduler để chạy file batch này hằng ngày.

## Cấu hình môi trường

Script hỗ trợ các biến môi trường:

Ví dụ:

```bash
export DATA_SRC_DIR=/path/to/data
export API_PORT=9000
```

## API Demo

API demo cung cấp giao diện truy vấn dữ liệu:

```bash
# Chạy API server
python -m uvicorn scripts.api_demo_fast:app --reload --port 9000
```

API có sẵn tại địa chỉ: http://localhost:8000

## Xử lý dữ liệu

Để xử lý và chuyển đổi dữ liệu thô từ CSV sang Parquet với các chỉ báo kỹ thuật:

```bash
# Xử lý dữ liệu và tính toán chỉ báo kỹ thuật
python -m scripts.data_processor staging/20250926/raw parquet

# Hoặc sử dụng script ingest_cafef (phiên bản cũ)
python scripts/ingest_cafef.py
```

## API Endpoints

API có các endpoints sau:

- `GET /symbols` - Danh sách tất cả các mã chứng khoán
