<<<<<<< HEAD
# PROJECT-PYTHON
=======
# CafeF Data Downloader & Stock Analysis

Hệ thống tải dữ liệu giao dịch từ CafeF, xử lý, tính toán các chỉ báo kỹ thuật, và cung cấp API để truy vấn dữ liệu chứng khoán.

## Cấu trúc dự án

```
project-root/
├── logs/                 # Log files khi chạy tự động
├── metadata/             # Theo dõi trạng thái và lưu metadata
│   ├── downloaded_files.sqlite   # Database lưu thông tin files đã tải
│   └── ingest_manifest.json      # Thông tin các file đã tải dạng JSON
├── parquet/              # Data sau khi chuyển đổi sang Parquet
├── scripts/
│   ├── api_demo_fast.py  # API FastAPI để truy xuất dữ liệu
│   ├── downloader.py     # Script tải dữ liệu theo ngày
│   ├── auto_download.py  # Script tự động tải hằng ngày và xử lý dữ liệu
│   ├── data_processor.py # Xử lý dữ liệu thô và tính toán chỉ báo kỹ thuật
│   └── ingest_cafef.py   # Xử lý dữ liệu đã tải
└── staging/              # Thư mục chứa dữ liệu tạm
    └── YYYYMMDD/         # Thư mục theo ngày
        ├── raw/          # Dữ liệu CSV đã giải nén
        └── CafeF.SolieuGD.UptoYYYYMMDD.zip  # File zip gốc
```

## Cài đặt

Yêu cầu:


```bash
pip install -r requirements.txt
```

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
