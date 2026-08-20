# Tài liệu thiết kế hệ thống (Design Document)

*Hệ thống: Multi-Agent Research Assistant*  
*Lab: Lab 20 - Multi-Agent Systems*

---

## 1. Problem
Xây dựng một trợ lý nghiên cứu tự động (Research Assistant) có khả năng tiếp nhận các câu hỏi nghiên cứu kỹ thuật phức tạp, tự động tìm kiếm thông tin đa nguồn (online qua Tavily và offline qua local knowledge corpus), phân tích đối sánh bằng chứng và tổng hợp thành báo cáo khoa học hoàn chỉnh có trích dẫn nguồn xác thực.

---

## 2. Why multi-agent?
- **Hạn chế của Single-Agent:** Một LLM đơn lẻ chỉ dựa vào tri thức nội tại (dễ gây ảo giác/hallucination đối với chủ đề mới), không có khả năng tự kiểm chứng chéo và dễ bị quá tải ngữ cảnh (context overload) khi vừa tìm kiếm, vừa lọc dữ liệu, vừa viết bài.
- **Lợi ích của Multi-Agent:** Phân rã bài toán thành các vai trò chuyên biệt hóa (`Supervisor`, `Researcher`, `Analyst`, `Writer`), tạo cơ chế bàn giao trạng thái (`ResearchState`) rõ ràng, giúp tăng tỷ lệ trích dẫn xác thực lên 100% và nâng cao độ sâu phân tích.

---

## 3. Agent roles

| Agent | Responsibility | Input | Output | Failure mode & Mitigation |
|---|---|---|---|---|
| **Supervisor** | Điều phối luồng làm việc, quyết định agent tiếp theo và điểm dừng | `ResearchState` | Cập nhật `route_history`, chuyển giao quyền thực thi | *Vòng lặp vô hạn:* Khắc phục bằng guardrail `max_iterations = 6`. |
| **Researcher** | Tra cứu tài liệu đa nguồn (Tavily Search / Offline Corpus) và trích xuất sự thật | `state.request.query` | `state.sources`, `state.research_notes` | *Lỗi tìm kiếm / Mất mạng:* Fallback sang local offline corpus. |
| **Analyst** | Phân tích đối sánh các quan điểm, đánh giá độ tin cậy của bằng chứng | `state.research_notes`, `state.sources` | `state.analysis_notes` | *Ảo giác phân tích:* Bắt buộc trỏ về danh sách `sources` gốc. |
| **Writer** | Tổng hợp báo cáo kỹ thuật hoàn chỉnh kèm trích dẫn số `[1]`, `[2]` | `state.analysis_notes`, `state.sources` | `state.final_answer` | *Thiếu trích dẫn:* Kiểm tra format strict và danh mục References. |

---

## 4. Shared state (`ResearchState`)

- `request`: Chứa câu hỏi nghiên cứu (`query`), số lượng nguồn tối đa (`max_sources`) và đối tượng độc giả (`audience`).
- `iteration`: Bộ đếm vòng lặp thực thi để ngăn chặn chạy vô hạn.
- `route_history`: Lưu vết chuỗi quyết định định tuyến của Supervisor (phục vụ audit và debug).
- `sources`: Danh sách tài liệu thực tế thu thập được (`title`, `url`, `snippet`, `metadata`).
- `research_notes`: Ghi chú tóm tắt các luận điểm cốt lõi từ Researcher.
- `analysis_notes`: Bảng phân tích đối sánh và đánh giá độ tin cậy từ Analyst.
- `final_answer`: Báo cáo khoa học tổng hợp cuối cùng từ Writer.
- `agent_results`: Lưu trữ chi tiết nội dung và token usage của từng agent step.
- `trace`: Lịch sử các span sự kiện phục vụ tracing.
- `errors`: Danh sách các lỗi phát sinh trong quá trình chạy.

---

## 5. Routing policy
- Đồ thị điều phối sử dụng **LangGraph**:
  - `START` $\rightarrow$ `supervisor`
  - `supervisor` $\xrightarrow{\text{chưa có sources}}$ `researcher` $\rightarrow$ `supervisor`
  - `supervisor` $\xrightarrow{\text{chưa có analysis}}$ `analyst` $\rightarrow$ `supervisor`
  - `supervisor` $\xrightarrow{\text{chưa có final answer}}$ `writer` $\rightarrow$ `supervisor`
  - `supervisor` $\xrightarrow{\text{đã có final answer hoặc đạt max_iterations}}$ `END`

---

## 6. Guardrails
- **Max iterations:** Giới hạn tối đa 6 vòng lặp điều phối.
- **Timeout:** 60 giây cho mỗi lượt gọi API.
- **Retry:** Tự động thử lại 3 lần với exponential backoff (`tenacity`) khi gặp Rate Limit hoặc lỗi mạng.
- **Fallback:** Tự động chuyển sang tra cứu offline corpus nếu không có API key tìm kiếm.
- **Validation:** Kiểm định kiểu dữ liệu nghiêm ngặt qua Pydantic schema.

---

## 7. Benchmark plan
- **Tập truy vấn:** Các câu hỏi so sánh kiến trúc AI phức tạp (ví dụ: *GraphRAG state-of-the-art*, *RAG vs Fine-tuning*).
- **Chỉ số đo lường:** Latency (s), Cost (USD), Quality Score (0-10), Citation Coverage (0-100%), Failure Rate (%).
- **Kết quả kỳ vọng:** Multi-Agent vượt trội về Citation Coverage (100% vs 0%) và Quality (10/10 vs 9/10), chấp nhận độ trễ cao hơn do quy trình kiểm chứng sâu.
