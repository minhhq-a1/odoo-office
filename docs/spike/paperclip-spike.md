# Spike Paperclip — kết quả vòng 1 (đọc mã nguồn, chưa chạy)

- Ngày: 2026-10-27
- Repo thử: https://github.com/paperclipai/paperclip, commit `0cb3fc7db591ba23e21fbbc70042bc44ec7d6f20` (2026-10-26), giấy phép MIT.
- Tiêu chí: theo báo cáo khảo sát đã duyệt (https://claude.ai/artifact/UT6eqiLaDV2v5KWXQB2sGA), mục "Spike Paperclip".
- Mức bằng chứng vòng này: **tài liệu + mã nguồn trong repo**. Chưa chạy Paperclip, nên chưa ô nào được tính là "đạt".

## Trạng thái từng ô

| Tiêu chí | Luồng bình thường | Tình huống lỗi | Bằng chứng hiện có |
|---|---|---|---|
| Tích hợp agent | Chưa chạy | Chưa chạy | Adapter `claude_local` đọc `ANTHROPIC_BASE_URL` (`packages/adapters/claude-local/src/server/models.ts`), nên về lý thuyết dùng được provider tương thích Anthropic API. Adapter `process` chạy lệnh tuỳ ý (`docs/adapters/process.md`). Rủi ro trùng lặp: restart server hard-kill lượt đang chạy, đánh dấu `process_lost` và tự retry 1 lần (`docs/deploy/dev-plane-restart-hygiene.md`); nếu agent đã có side effect trước khi bị kill thì retry có thể làm lại. Phải thử. |
| Phê duyệt | Chưa chạy | Chưa chạy | Execution policy có stage `review`/`approval` do runtime cưỡng chế, quyết định ghi vào `issue_execution_decisions` (`docs/guides/execution-policy.md`). `approvalsNeeded` chỉ hỗ trợ 1. Approval API riêng (`docs/api/approvals.md`) chỉ cho hire/strategy, không phải cho hành động tuỳ ý của agent. |
| Giới hạn chi phí | Chưa chạy | Chưa chạy | Budget theo tháng ở mức company/agent/project; 80% cảnh báo, 100% auto-pause (`docs/api/costs.md`). README tự nhận: cưỡng chế dựa trên chi phí đã ghi nhận, báo cáo usage và lượt đang chạy có thể làm chậm việc dừng. Không có ngưỡng 90%: muốn dừng ở 90% của 300 USD thì đặt budget Paperclip = 270 USD. Chi phí do adapter tự báo (`POST /cost-events`), không đối soát với hoá đơn provider. |
| Lưu vết | Chưa chạy | Chưa chạy | Activity log append-only qua `GET /api/companies/{id}/activity`; cost event có `agentId`; decision có `createdByRunId` (`docs/api/activity.md`, `docs/api/costs.md`). Chưa xác nhận nối được đủ chuỗi ticket → run → output → người duyệt → chi phí bằng một truy vấn. |

## Vòng 2 (cần chạy thật)

Chạy Paperclip từ commit trên trong container cloud, dùng 2 loại agent:

1. Agent giả lập (adapter `process`, script tự báo cost event) — thử approval, budget, lưu vết, restart/retry mà **không tốn tiền model**.
2. Agent Claude Code thật (`claude_local`) với 1–2 ticket nhỏ — thử tích hợp và đối chiếu chi phí Paperclip ghi nhận với chi phí provider. Cần API key trong môi trường.

Mỗi ô trong bảng trên được điền: đạt / không đạt, kèm lệnh đã chạy và log.
