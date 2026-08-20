# Lab Guide: Multi-Agent Research System

## Scenario

Bạn cần xây dựng một research assistant có thể nhận câu hỏi dài, tìm thông tin, phân tích và viết câu trả lời cuối cùng. Lab yêu cầu so sánh hai cách làm:

1. **Single-agent baseline**: một agent làm toàn bộ.
2. **Multi-agent workflow**: Supervisor điều phối Researcher, Analyst, Writer.

## Quy tắc quan trọng

- Không thêm agent nếu không có lý do rõ ràng.
- Mỗi agent phải có responsibility riêng.
- Shared state phải đủ rõ để debug.
- Phải có trace hoặc log cho từng bước.
- Phải benchmark, không chỉ nhìn output bằng cảm tính.

## Milestone 1: Baseline

File gợi ý:

- `src/multi_agent_research_lab/cli.py`
- `src/multi_agent_research_lab/services/llm_client.py`

TODO(student): thay baseline placeholder bằng một call LLM thật.

## Milestone 2: Supervisor

File gợi ý:

- `src/multi_agent_research_lab/agents/supervisor.py`
- `src/multi_agent_research_lab/graph/workflow.py`

TODO(student): implement routing policy.

Gợi ý câu hỏi thiết kế:

- Khi nào gọi Researcher?
- Khi nào gọi Analyst?
- Khi nào gọi Writer?
- Khi nào stop?
- Nếu agent fail thì retry hay fallback?

## Milestone 3: Worker agents

File gợi ý:

- `src/multi_agent_research_lab/agents/researcher.py`
- `src/multi_agent_research_lab/agents/analyst.py`
- `src/multi_agent_research_lab/agents/writer.py`

TODO(student): implement từng worker.

## Milestone 4: Trace và benchmark

File gợi ý:

- `src/multi_agent_research_lab/observability/tracing.py`
- `src/multi_agent_research_lab/evaluation/benchmark.py`
- `src/multi_agent_research_lab/evaluation/report.py`

Benchmark tối thiểu:

| Metric | Cách đo gợi ý |
|---|---|
| Latency | wall-clock time |
| Cost | token usage hoặc provider usage |
| Quality | rubric 0-10 do peer review |
| Citation coverage | số claims có source / tổng claims chính |
| Failure rate | số query fail / tổng query |

## Troubleshooting

### macOS: lỗi SSL certificate khi gọi API qua HTTPS (Tavily, OpenAI, ...)

Triệu chứng: khi implement `SearchClient` (hoặc bất kỳ HTTPS call nào) trên macOS, bạn có thể gặp lỗi kiểu:

```
ssl.SSLCertVerificationError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed:
unable to get local issuer certificate
```

Nguyên nhân: Python cài từ python.org trên macOS **không dùng** certificate store của hệ điều hành, nên không tìm thấy CA bundle hợp lệ. Đây là lỗi môi trường, **không phải** do API key sai.

Cách khắc phục (chọn 1 trong 3):

1. **Chạy script cài certificate đi kèm Python** (nhanh nhất):

   ```bash
   /Applications/Python\ 3.12/Install\ Certificates.command
   ```

   (thay `3.12` bằng version Python của bạn)

2. **Dùng `certifi` trong code** — thêm `certifi` vào dependencies, rồi tạo SSL context khi gọi HTTPS:

   ```python
   import certifi
   import ssl
   from urllib.request import urlopen

   ssl_context = ssl.create_default_context(cafile=certifi.where())
   urlopen(request, timeout=timeout, context=ssl_context)
   ```

3. **Set biến môi trường** trỏ tới CA bundle của certifi (không cần đổi code):

   ```bash
   export SSL_CERT_FILE=$(python -m certifi)
   ```

## Exit ticket

Mỗi nhóm trả lời 2 câu:

1. **Case nào nên dùng multi-agent? Vì sao?**
   - **Nghiên cứu chuyên sâu & tổng hợp đa nguồn:** Cần phân rã nhiệm vụ thành các khâu độc lập (thu thập dữ liệu mới nhất $\rightarrow$ đánh giá độ tin cậy bằng chứng $\rightarrow$ tổng hợp bài viết học thuật có trích dẫn), giúp tránh quá tải context window và loại bỏ ảo giác (hallucination).
   - **Quy trình đòi hỏi kiểm chứng độc lập (Independent Verification):** Tách rời vai trò tạo nội dung và phản biện/kiểm tra chéo nhằm loại bỏ thiên kiến tự xác nhận (confirmation bias).
   - **Hệ thống điều phối nhiều công cụ chuyên biệt (Multi-tool Orchestration):** Mỗi agent quản lý một tập tool riêng giúp prompt tinh gọn và tăng độ chính xác khi gọi công cụ.

2. **Case nào không nên dùng multi-agent? Vì sao?**
   - **Tác vụ đơn giản, một bước:** Tóm tắt ngắn, dịch thuật cơ bản, giải thích hàm code. Single-Agent đã giải quyết tốt trong vài giây với chi phí rẻ hơn nhiều.
   - **Ứng dụng yêu cầu phản hồi thời gian thực (<2 giây):** Multi-agent có độ trễ cao (do handoff qua nhiều bước LLM tuần tự), không phù hợp cho Voice Assistant hay Auto-complete code.
   - **Ngân sách token và tài nguyên hạn chế:** Chi phí token và rủi ro chạm Rate Limit tăng theo số lượng agent trong vòng lặp.
