# Spike Paperclip: kết quả vòng 2 (chạy thật, agent giả lập)

- Ngày: 2026-10-27, Paperclip commit `0cb3fc7` (MIT), chạy trong container cloud dùng một lần.
- Môi trường: Node 24.11.1, pnpm 9.15.4 (`pnpm install --no-frozen-lockfile` vì lockfile lệch cấu hình `patchedDependencies`), PostgreSQL 16 ngoài (`DATABASE_URL`), chế độ `local_trusted`, tắt telemetry (`PAPERCLIP_TELEMETRY_DISABLED=1`). Lệnh khởi động: [`round2/run.sh`](round2/run.sh).
- Agent giả lập: adapter `process` chạy [`round2/fake_agent.py`](round2/fake_agent.py). Script tự chọn ticket trong inbox, checkout, báo cost event 3 cent, ghi một dòng "side effect" ra file, rồi chuyển ticket sang `done` kèm comment.
- Log đầy đủ (lệnh curl và phản hồi): [`round2/evidence.log`](round2/evidence.log).
- **Agent thật `claude_local` chưa chạy**: container không có `ANTHROPIC_API_KEY`/`ANTHROPIC_AUTH_TOKEN` (chỉ có `ANTHROPIC_BASE_URL` mặc định `https://api.anthropic.com`).

## Bảng kết quả

| Tiêu chí | Luồng bình thường | Tình huống lỗi | Ghi chú |
|---|---|---|---|
| Tích hợp agent | **Đạt** (giả lập) | **Đạt có điều kiện** | Xem mục "Restart/kill". Adapter `process` không tự cấp `PAPERCLIP_TASK_ID`, agent phải tự lấy từ inbox. Agent thật chưa chạy được. |
| Phê duyệt | **Đạt** | **Đạt** | Stage `approval` do runtime cưỡng chế; phê duyệt thiếu comment bị từ chối. |
| Giới hạn chi phí | **Đạt** | **Đạt**, có rủi ro vận hành | Hard stop cắt cả lượt đang chạy; `reservationCents` chặn trước khi chạy. Sau khi server bị kill cứng, agent kẹt ở trạng thái pause, không mở lại được qua API. |
| Lưu vết | **Đạt** | **Đạt có điều kiện** | Activity log nối được ticket, run, output, người duyệt. Cost event chỉ gắn với run khi body có `heartbeatRunId`; header `X-Paperclip-Run-Id` không đủ. |
| Đối chiếu chi phí với provider | Chưa chạy | Chưa chạy | Cần API key. Paperclip có sẵn `POST /companies/{id}/accounting/provider-costs/import` (provider `anthropic`/`openai`, theo ngày UTC) để nhập chi phí từ provider, cần secret riêng. |

## Chi tiết từng phép thử

### A. Budget fail-closed với usage chưa định giá
- Agent có budget 10 cent. Lượt chạy đầu (cost event bị lỗi validate vì thiếu `occurredAt`) để lại 1 event `unpriced`.
- Kết quả: agent bị **hard stop ngay**, tuy chi phí ghi nhận là 0. Mặc định `unpricedUsagePolicy = "block"`. Hệ thống tự mở incident và một approval.
- Muốn resume phải đặt `unpricedUsagePolicy: "allow"` qua `POST /companies/{id}/budgets/policies`. Nếu không, API trả về `Resolve unpriced usage or explicitly allow it in the budget policy before resuming`.
- Lưu ý: `PATCH /agents/{id}/budgets` chỉ nhận `budgetMonthlyCents`. Policy đầy đủ (reservation, unpriced, warnPercent) phải đặt qua `/budgets/policies`.

### B. Budget có giá: cảnh báo, hard stop, reservation
Budget agent 10 cent, mỗi lượt 3 cent, các ticket chạy tuần tự:

| Ticket | Chi phí ghi nhận | Trạng thái budget | Ticket |
|---|---|---|---|
| T2 | 6 | ok | done |
| T3 | 9 | warning (vượt 80%) | done |
| T4 | 12 | hard_stop, agent pause | blocked |
| T5 | 12 | hard_stop | không chạy |

- Hard stop xảy ra ngay khi cost event đẩy tổng chi phí vượt ngưỡng. Lượt T4 đang chạy bị huỷ (`Agent lifecycle stop requested`) trước bước `PATCH done`. Tuy vậy side effect của T4 đã xảy ra trước đó, nên **vượt 2 cent (20%)**.
- B2: đặt `reservationCents = 3` và budget 14 khi chi phí đã ghi nhận là 12. Lượt T6 **bị từ chối trước khi chạy** (`Available budget is reserved by unfinished runs`), không có side effect.
- Kết luận cho pilot: đặt `reservationCents` ≥ chi phí tối đa của một lượt, cộng budget company = 270 USD, thì không vượt ngưỡng 90%.

### C. Phê duyệt
- T1 có `executionPolicy` gồm một stage `approval`, người duyệt là `local-board`. Agent chuyển sang `done` thì runtime đổi thành `in_review` và giao cho người duyệt (`executionState.currentStageType = approval`).
- Phê duyệt không kèm comment bị từ chối: `Approving a review or approval stage requires a comment`. Phê duyệt có comment thì ticket chuyển `done`, quyết định ghi vào `issue_execution_decisions` (outcome `approved`, actor `local-board`).
- Chưa thử: agent tự phê duyệt bằng token của chính nó. Tài liệu ghi là bị chặn bằng 422.

### D. Lưu vết
- `GET /companies/{id}/activity` cho T1 trả về đủ chuỗi: `issue.created` (board) → `issue.checked_out` (agent, run `0b284976`) → `issue.updated` sang in_review (agent, cùng run) → `issue.comment_added` (output) → `issue.updated` sang done + comment của người duyệt (board).
- Một truy vấn SQL nối được ticket, chi phí và quyết định (xem cuối `evidence.log`). Cost event do agent tự báo **không có `heartbeat_run_id`**, vì script chỉ gửi header `X-Paperclip-Run-Id` mà không gửi field `heartbeatRunId` trong body. Agent tự viết phải gửi field này.

### E. Restart và kill giữa lượt chạy (rủi ro chạy trùng)
| Phép thử | Kết quả |
|---|---|
| E1: `SIGTERM` server khi agent đang chạy (T7) | Server drain, gửi SIGTERM cho process con. Run → `failed` (`signal: SIGTERM`), **không tự retry**, ticket → `blocked`. Không có side effect, không trùng. |
| E2: `SIGKILL` server (T8) | Process con **sống sót** (mồ côi) và gửi được cost event lên server mới bằng JWT cũ (201). Sau đó nó chết vì stdout đã đóng. Khoảng 60 giây sau khi restart, server đánh dấu run `interrupted` (`orphaned_running_run`), ticket → `blocked`, **không retry**. Run kẹt ở `waiting_for_receipt`, agent bị pause vì `pendingRunCount > 0`, và **không resume được qua API** (`Completed runs must finish accounting before resuming`; `accounting/repair` báo `repairable: false`; `accounting/retry` trả về `accounted: false`). |
| E3: `SIGKILL` server, agent bỏ qua lỗi stdout (T10, agent 2) | Process mồ côi **làm xong việc sau khi server đã restart**: báo chi phí, side effect 1 lần, comment và `done` đều được chấp nhận. Server không chạy lại. Nhưng run vẫn hiện `running` sau hơn 5 phút và agent kẹt ở trạng thái `running`. |

- Kết luận: trong 3 phép thử **không thấy chạy trùng**. Bản này không tự retry sau restart như tài liệu vòng 1 dự đoán; thay vào đó ticket bị `blocked` chờ người xử lý. Rủi ro thật nằm ở chỗ khác: (1) process mồ côi sau `SIGKILL` vẫn tiếp tục ghi vào hệ thống, nên nếu người vận hành mở lại ticket bị `blocked` trong lúc process cũ còn sống thì sẽ chạy trùng; (2) trạng thái run và budget bị kẹt, cần can thiệp DB hoặc tạo agent mới.
- Biện pháp cho pilot: chạy server dưới process manager dừng bằng SIGTERM (không kill -9), giết cả process group của agent khi restart, và trước khi mở lại ticket `blocked` phải kiểm tra không còn process agent nào đang chạy.

## Quan sát khác
- Lượt chạy T1 làm xong việc nhưng heartbeat run hiển thị `cancelled` ("Cancelled before issue reassignment"), vì runtime chuyển ticket sang người duyệt. Trạng thái run không phản ánh đúng kết quả, nên báo cáo phải đọc theo ticket.
- Lượt chạy đầu tiên không tìm được ticket nên ticket bị recovery chuyển sang `blocked`. Agent tự viết phải tự checkout ticket.

## Việc còn lại
1. Chạy 1–2 ticket với `claude_local` khi container có API key, rồi đối chiếu `costs/by-agent` với Usage/Cost trên Console (hoặc import qua `accounting/provider-costs/import`, cần Admin API key).
2. Thử agent tự phê duyệt (cần tạo agent key) và luồng `changes_requested`.
