# Báo cáo Benchmark: Single-Agent Baseline vs Multi-Agent Research System

*Dự án: VinUni AI Lab - Multi-Agent Research Lab (Lab 20)*  
*Thời gian thực nghiệm: 2026-08-20*  
*Mô hình sử dụng: Groq (`qwen/qwen3.6-27b`)*

---

## 1. Bảng số liệu định lượng (Quantitative Benchmark Summary)

| Hệ thống / Kiến trúc | Độ trễ (Latency) | Chi phí ước tính (USD) | Điểm chất lượng (0-10) | Tỷ lệ trích dẫn (Citation) | Tỷ lệ lỗi (Failure) | Mô tả thực nghiệm |
|---|---:|---:|---:|---:|---:|---|
| **Single-Agent Baseline** | **5.43s** | $0.0000 | **9.0 / 10** | **0.0%** | 0.0% | 1 lần gọi LLM trực tiếp, không tra cứu ngoài |
| **Multi-Agent Workflow** | **47.30s** | $0.0000 | **10.0 / 10** | **100.0%** | 0.0% | Điều phối tuần tự qua 4 node (Supervisor $\rightarrow$ Researcher $\rightarrow$ Analyst $\rightarrow$ Writer) |

---

## 2. Phân tích so sánh chuyên sâu (Comparative Analysis)

### A. Tính chuẩn xác của dữ liệu & Trích dẫn nguồn (Grounding & Citation Rigor)
- **Single-Agent Baseline:**
  - Hoạt động hoàn toàn dựa vào tri thức đóng băng trong tham số mô hình (parametric memory).
  - Không có công cụ tìm kiếm bên ngoài, do đó **không thể trích dẫn nguồn thực tế** (Citation Coverage = 0%).
  - Dễ gặp ảo giác (hallucination) hoặc cung cấp thông tin lỗi thời đối với các chủ đề công nghệ mới (như *GraphRAG state-of-the-art*).
- **Multi-Agent Workflow:**
  - Tách biệt rõ ràng các nhiệm vụ chuyên biệt: `Researcher` tìm kiếm dữ liệu mới nhất $\rightarrow$ `Analyst` so sánh và đánh giá độ tin cậy của tài liệu $\rightarrow$ `Writer` tổng hợp nội dung.
  - Đạt **100% Citation Coverage**: Mọi luận điểm chính trong báo cáo đều được gắn mã số trích dẫn `[1]`, `[2]`, `[3]`, `[4]`, `[5]` tương ứng chính xác với danh mục *References* ở cuối bài.

### B. Cân bằng giữa Độ trễ và Độ sâu phân tích (Latency vs Depth Trade-off)
- **Single-Agent Baseline:** Tối ưu vượt trội về mặt thời gian phản hồi (~5.43 giây), phù hợp với các tác vụ hỏi đáp nhanh.
- **Multi-Agent Workflow:** Độ trễ cao hơn gấp ~8.7 lần (~47.30 giây) do phải thực thi tuần tự qua các node LLM và Search API. Tuy nhiên, nội dung đầu ra đạt độ sâu vượt trội: phân tích đa chiều về cơ chế kiến trúc, đánh giá ưu nhược điểm kỹ thuật, so sánh trade-off và trích xuất bằng chứng thực nghiệm rõ ràng.

---

## 3. Phân tích các dạng lỗi & Rủi ro hệ thống (Failure Mode & Risk Analysis)

Trong quá trình thiết kế và thực nghiệm hệ thống Multi-Agent, ba dạng rủi ro cốt lõi đã được nhận diện và kiểm soát:

1. **Rơi rụng ngữ cảnh qua các bước chuyển giao (Context Drift across Handoffs):**
   - *Biểu hiện:* Dữ liệu bị tóm tắt liên tục qua từng agent (từ raw document sang `research_notes` rồi sang `analysis_notes`) có nguy cơ làm rơi rụng các số liệu hoặc ngữ cảnh quan trọng.
   - *Giải pháp:* Thiết kế `ResearchState` dùng chung, giữ nguyên danh sách `sources` ban đầu để `WriterAgent` có thể đối chiếu trực tiếp khi tạo trích dẫn cuối cùng.

2. **Ảo giác dây chuyền (Cascading Hallucinations):**
   - *Biểu hiện:* Nếu `Researcher` thu thập tài liệu sai hoặc trích xuất nhầm sự thật, các agent phía sau (`Analyst`, `Writer`) sẽ lập luận trên tiền đề sai lệch đó.
   - *Giải pháp:* Tích hợp bộ lọc nguồn trong `SearchClient`, kiểm tra độ tin cậy trong `AnalystAgent` và dự phòng `CriticAgent` để hậu kiểm chéo.

3. **Giới hạn tốc độ gọi API & Chi phí điều phối (Rate Limits & Coordination Overhead):**
   - *Biểu hiện:* Các agent gửi request liên tục dễ chạm giới hạn RPM/TPM của LLM provider (lỗi `429 Too Many Requests`).
   - *Giải pháp:* Sử dụng thư viện `tenacity` với cơ chế retry tự động và exponential backoff (thời gian chờ tăng dần 2s $\rightarrow$ 4s $\rightarrow$ 8s) kết hợp `MAX_ITERATIONS = 6` để chặn vòng lặp vô hạn.

---

## 4. Khuyến nghị kiến trúc (Architectural Recommendations)

| Tình huống bài toán thực tế | Kiến trúc khuyến nghị | Lý do kỹ thuật |
|---|---|---|
| Câu hỏi thông thường, tóm tắt nhanh, tra cứu cơ bản | **Single-Agent Baseline** | Tiết kiệm chi phí, độ trễ thấp (<5s), không tốn chi phí điều phối |
| Nghiên cứu chuyên sâu, tổng hợp đa nguồn, báo cáo kỹ thuật | **Multi-Agent Workflow** | Bắt buộc kiểm chứng nguồn, phân tích đa chiều và loại trừ hallucination |

---

## 5. Observability & Tracing Links

- **Nền tảng Tracing:** LangSmith
- **Dự án Tracing:** `multi-agent-research-lab`
- **Trace ID:**
  > 01a01e8b-c997-71e0-93a1-91df6b18d5aa
- **Lịch sử các bước thực thi ghi nhận trên trace (`route_history`):**
  1. `supervisor.routed` (Iteration 1 $\rightarrow$ `researcher`)
  2. `researcher.done` (Thu thập 5 tài liệu nguồn)
  3. `supervisor.routed` (Iteration 2 $\rightarrow$ `analyst`)
  4. `analyst.done` (Phân tích đối sánh & đánh giá bằng chứng)
  5. `supervisor.routed` (Iteration 3 $\rightarrow$ `writer`)
  6. `writer.done` (Tổng hợp báo cáo kèm trích dẫn)
  7. `supervisor.routed` (Iteration 4 $\rightarrow$ `done` $\rightarrow$ `END`)

---

## 6. Exit Ticket (Trả lời câu hỏi tổng kết)

### Câu 1: Case nào NÊN dùng Multi-Agent? Vì sao?
1. **Nghiên cứu học thuật và báo cáo kỹ thuật chuyên sâu:** Đòi hỏi tách biệt các bước độc lập (thu thập dữ liệu mới nhất $\rightarrow$ đánh giá độ tin cậy nguồn $\rightarrow$ tổng hợp bài viết học thuật có trích dẫn), giúp tránh quá tải context window và giảm thiểu hallucination.
2. **Quy trình bắt buộc có kiểm chứng và kiểm toán độc lập (Verification & Audit):** Tách rời agent tạo nội dung và agent phản biện/kiểm tra giúp loại bỏ hiện tượng thiên kiến tự xác nhận (confirmation bias).
3. **Hệ thống điều phối nhiều công cụ phức tạp (Multi-tool Orchestration):** Mỗi agent quản lý một tập công cụ chuyên biệt (Web Search, SQL Database, Code Interpreter) giúp prompt ngắn gọn và gọi tool chính xác hơn.

### Câu 2: Case nào KHÔNG NÊN dùng Multi-Agent? Vì sao?
1. **Tác vụ đơn giản, một bước (Single-turn Tasks):** Tóm tắt văn bản ngắn, dịch thuật cơ bản, giải thích cú pháp code. Single-Agent đã đạt chất lượng 9/10 trong vài giây với chi phí rẻ hơn nhiều lần.
2. **Ứng dụng tương tác thời gian thực / độ trễ cực thấp (Ultra-Low Latency):** Multi-agent mất 30–50 giây do handoff qua nhiều bước LLM, không phù hợp cho Voice Assistant hoặc inline code completion.
3. **Môi trường hạn chế tài nguyên và giới hạn API nghiêm ngặt:** Việc gọi LLM nhiều vòng lặp làm tăng chi phí token và dễ chạm Rate Limit nếu không có hạ tầng tài nguyên lớn.

---

## 7. Đánh giá Peer Review Rubric (Self-Assessment)

| Tiêu chí | Điểm | Giải trình chi tiết |
|---|:---:|---|
| **Role clarity** | 2 / 2 | Phân tách rõ ràng trách nhiệm của 4 agent: Supervisor (router), Researcher (gather), Analyst (evaluate), Writer (synthesize). |
| **State design** | 2 / 2 | `ResearchState` lưu giữ toàn bộ dữ liệu trung gian (`sources`, `research_notes`, `analysis_notes`, `final_answer`, `agent_results`, `trace`, `errors`). |
| **Failure guard** | 2 / 2 | Thiết lập đầy đủ `max_iterations`, `timeout_seconds`, retry exponential backoff (`tenacity`), và offline fallback search. |
| **Benchmark** | 2 / 2 | Đo lường định lượng 5 metrics: Latency, Cost, Quality, Citation Coverage, Failure Rate. |
| **Trace explanation** | 2 / 2 | Ghi nhận chi tiết từng span hành động, tích hợp sẵn với LangSmith / Langfuse. |
| **Tổng điểm** | **10 / 10** | **Đạt mức Xuất sắc theo chuẩn Rubric của bài Lab** |
