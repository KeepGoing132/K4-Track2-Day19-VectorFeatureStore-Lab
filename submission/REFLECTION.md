# Reflection — Lab 19

**Tên:** Nguyễn Ngọc Bảo

**Mã học viên:** 2A202602951

**Cohort:** A20-K4

**Path:** lite

Trên 50 truy vấn, Precision@10: BM25 **77,8%**, vector **73,2%**, hybrid **78,6%**.

- `exact`: BM25 và hybrid cùng **96,7%**, vector **88,7%**. Từ khóa kỹ thuật chính xác giúp BM25.
- `paraphrase`: BM25 **33,3%**, vector **24,0%**, hybrid **32,0%**. Model bge-small tiếng Anh còn yếu với diễn đạt tiếng Việt; vector không thắng trong lần đo này.
- `mixed`: hybrid **100%**, BM25 **97,0%**, vector **98,5%**. RRF tận dụng hai danh sách xếp hạng bổ sung nhau.

Tôi chọn BM25 khi tra mã định danh hoặc cần độ trễ thấp; chọn vector khi kiểm chứng được chất lượng truy vấn ngữ nghĩa. Hybrid không luôn thắng mọi loại truy vấn.

NB3 đo P99 hybrid **13,9 ms** sau warm-up. Giới hạn ONNX ở 4 luồng giảm độ trễ trên máy này. Bonus dùng Feast thật và lọc ký ức theo người dùng. Bộ đếm hoạt động chỉ giữ cửa sổ một giờ trong tiến trình; khởi động lại sẽ mất lịch sử.

Kết quả: `submission/benchmark.txt`, output notebook và `bonus/`.
