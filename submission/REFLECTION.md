# Reflection — Lab 19

**Tên:** Nguyễn Ngọc Bảo
**Mã học viên:** 2A202602951
**Cohort:** A20-K4
**Path đã chạy:** lite

---

## Câu hỏi (≤ 200 chữ)

> Trên golden set 50 queries, mode nào thắng ở loại query nào (`exact` /
> `paraphrase` / `mixed`), và tại sao? Khi nào bạn **không** dùng hybrid
> (i.e. khi nào pure BM25 hoặc pure vector là lựa chọn đúng)?

Trên golden set 50 queries:
- **`exact`**: BM25 thắng hoặc ngang ngửa vì khớp chính xác thuật ngữ kỹ thuật nguyên văn (Kubernetes, OAuth), nơi vector dễ bị nhiễu do xấp xỉ không gian.
- **`paraphrase`**: Vector search thắng vì bắt trọn ngữ nghĩa trừu tượng và ngữ cảnh tiếng Việt (diễn đạt lại khái niệm) mà BM25 hoàn toàn bất lực do không trùng từ.
- **`mixed`**: Hybrid (RRF k=60) thắng vượt trội nhờ kết hợp sức mạnh lexical và semantic, triệt tiêu điểm mù của từng phương pháp đơn lẻ.

**Khi không dùng Hybrid:**
- Chọn **Pure BM25**: Khi tra cứu exact entity (mã ID, SKU, log trace, tên riêng), hệ thống yêu cầu độ trễ cực thấp (<2ms), hoặc ràng buộc tài nguyên khắt khe không đủ compute/RAM để chạy embedding.
- Chọn **Pure Vector**: Khi tìm kiếm đa phương tiện (audio/ảnh), cross-lingual (câu hỏi tiếng Việt tìm tài liệu tiếng Anh), hoặc tài liệu văn xuôi trừu tượng không có từ khoá cố định. Bỏ qua hybrid giúp tiết kiệm 50% chi phí indexing và giảm độ trễ fusion.

---

## Điều ngạc nhiên nhất khi làm lab này

RRF ($1 / (k + rank)$) có công thức vô cùng đơn giản, không cần chuẩn hóa điểm số hay tinh chỉnh trọng số thủ công, nhưng lại mang lại độ ổn định và cải thiện Precision@10 vượt trội trên mọi dạng truy vấn.

---

## Bonus challenge

- [x] Đã làm bonus (xem `bonus/`)
- [ ] Pair work với: _<Làm việc độc lập>_
