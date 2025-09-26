# Hướng dẫn tra cứu mã chứng khoán qua API

API hiện đã được nâng cấp với nhiều chức năng để tra cứu mã chứng khoán một cách dễ dàng. Dưới đây là các cách bạn có thể sử dụng:

## 1. Truy cập API

API hiện đang chạy tại địa chỉ: http://localhost:9001

## 2. Các chức năng tra cứu mã

### 2.1. Xem tất cả mã chứng khoán

```
GET /symbols
```

Truy cập: http://localhost:9001/symbols

Kết quả trả về danh sách tất cả mã chứng khoán trong hệ thống.

### 2.2. Tìm kiếm mã chứng khoán theo từ khóa

```
GET /search?q={từ_khóa}
```

Ví dụ: http://localhost:9001/search?q=VN

Kết quả trả về tất cả mã chứng khoán có chứa "VN" (như VNM, VND, v.v.)

### 2.3. Xem mã theo sàn giao dịch

```
GET /exchanges
```

Truy cập: http://localhost:9001/exchanges

Kết quả trả về danh sách các sàn giao dịch có trong hệ thống.

```
GET /exchange/{tên_sàn}
```

Ví dụ: http://localhost:9001/exchange/HOSE

Kết quả trả về danh sách mã chứng khoán trên sàn HOSE.

### 2.4. Xem dữ liệu chi tiết của một mã

```
GET /symbol/{mã}
```

Ví dụ: http://localhost:9001/symbol/VNM

Kết quả trả về dữ liệu giao dịch của mã VNM. Bạn có thể thêm tham số lọc:

```
GET /symbol/{mã}?start={ngày_bắt_đầu}&end={ngày_kết_thúc}
```

Ví dụ: http://localhost:9001/symbol/VNM?start=2020-01-01&end=2020-12-31

## 3. Tài liệu API đầy đủ

Để xem tài liệu API đầy đủ với các tham số và mô tả, truy cập:

```
GET /docs
```

Truy cập: http://localhost:9001/docs

Đây là trang tài liệu tự động được tạo bởi Swagger UI, giúp bạn hiểu rõ hơn về API và có thể thử nghiệm các endpoint trực tiếp trên trình duyệt.

## 4. Các mã chứng khoán phổ biến

- **HOSE**: VNM, FPT, VIC, BVH, MSN, HPG, VCB, TCB
- **HNX**: ACB, SHS, PVS
- **UPCOM**: ACV, VGC

## 5. Ví dụ về dữ liệu trả về

Khi truy vấn một mã cụ thể, bạn sẽ nhận được dữ liệu bao gồm:

```json
{
  "symbol": "VNM",
  "count": 252,
  "data": [
    {
      "date": "2020-01-02",
      "open": 116.5,
      "high": 117.6,
      "low": 116.1,
      "close": 117.4,
      "volume": 1234567,
      "MA20": 115.7,
      "RSI14": 58.3
    },
    ...
  ]
}
```
