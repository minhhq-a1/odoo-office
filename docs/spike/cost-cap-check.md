# Xác minh chặn chi phí trước pilot

Quy tắc đã duyệt: trần model 300 USD; cảnh báo ở 80% (240 USD); ngừng mở lượt chạy mới ở 90% (270 USD).

## Trạng thái 2026-10-27

- Môi trường cloud của thread này **không có** `ANTHROPIC_API_KEY` hay `ANTHROPIC_AUTH_TOKEN`. Biến môi trường mới chỉ vào được session tạo sau khi lưu.
- Chưa biết anh Max dùng Anthropic trực tiếp hay custom provider (endpoint tương thích Anthropic qua `ANTHROPIC_BASE_URL`).

## Ba lớp chặn, kiểm tra từng lớp

| Lớp | Cách đặt | Cách kiểm tra | Ai làm |
|---|---|---|---|
| 1. Provider (chặn cứng) | Tạo workspace riêng cho pilot trên Claude Console, đặt spend limit của workspace 300 USD; API key pilot tạo trong workspace đó. Custom provider: dùng tính năng hạn mức tương đương của provider. | Chụp màn hình trang limit; ghi rõ provider có chặn request khi chạm hạn mức hay chỉ cảnh báo. | Anh Max (cần quyền admin Console) |
| 2. Điều phối (Paperclip) | Budget company = 270 USD, agent budget nhỏ hơn. | Vòng 2 của spike: đặt budget vài cent, xem agent có auto-pause, lượt đang chạy có bị cắt không, vượt bao nhiêu. | Em |
| 3. Đối soát | So chi phí Paperclip ghi nhận với usage/cost của provider sau mỗi ngày chạy. | Đo độ trễ ghi nhận chi phí của provider; nếu trễ lớn thì hạ ngưỡng dừng của lớp 2. | Em, cần quyền đọc usage |

Pilot chỉ bắt đầu khi lớp 1 đã đặt và lớp 2 đã thử đạt.
