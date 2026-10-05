# Ảnh minh chứng Lab 19

18 ảnh PNG được chụp trực tiếp từ giao diện JupyterLab bằng Microsoft Edge
headless và Playwright. Ảnh giữ nguyên nội dung notebook đã chạy; không vẽ lại
bảng, thay số liệu hoặc dùng ảnh AI. Code được thu gọn bằng menu View để nhìn
rõ kết quả. Hai ảnh bonus hiển thị log chạy thật trong trình soạn thảo Jupyter.

| Phần | Minh chứng | Ảnh |
|---|---|---|
| NB1 | 1.000 vectors, top-5 keyword và paraphrase | [Index](01_embeddings_index.png), [Paraphrase](01_paraphrase_top5.png) |
| NB2 | Precision@10 và bảng theo loại query | [Hybrid search](02_hybrid_search_rrf.png) |
| NB3 | API response và P50/P95/P99; hybrid P99 13,9 ms | [Latency](03_search_api_benchmark.png), [API response](03_api_response.png) |
| NB4 | Feast apply, materialize 3 views, online lookup và PIT 3 dòng | [Online + PIT](04_feast_feature_store.png), [Apply](04_feast_apply.png), [Apply hoàn tất](04_feast_apply_completed.png), [Materialize](04_feast_materialize.png) |
| NB5 | Recall của post-filter và filtered search | [Filtered search](05_filtered_search.png) |
| NB6 | Bảng single-shot và agentic retrieval | [Agent retrieval](06_agent_retrieval.png) |
| NB7 | Threshold sweep và cô lập tenant | [Cache sweep](07_semantic_cache.png), [Tenant isolation](07_cache_tenant_isolation.png) |
| NB8 | Target-encoding leakage, PIT join và on-demand features | [Encoding](08_feature_engineering.png), [PIT](08_point_in_time_join.png), [On-demand](08_on_demand_features.png) |
| Bonus | Context của 5 truy vấn và thông báo demo hoàn tất | [Demo](bonus_hybrid_memory_demo.png), [Hoàn tất](bonus_demo_completed.png) |

Nguồn đầy đủ: `.ipynb` trong `notebooks/` và `submission/bonus_demo.txt`.
[capture_manifest.json](capture_manifest.json) ghi phương pháp chụp, kích thước,
thời điểm và SHA-256 của file nguồn. Các ảnh là kết quả đã lưu trong notebook,
không khẳng định notebook được chạy lại khi chụp.

Chụp lại: chạy JupyterLab tại repo, cài Playwright trong `.venv`, rồi chạy
`python scripts/capture_jupyter.py` bằng Python của môi trường đó. Giữ output
notebook sau khi chạy. Script chỉ thay bộ ảnh sau khi tất cả lượt chụp thành công.
