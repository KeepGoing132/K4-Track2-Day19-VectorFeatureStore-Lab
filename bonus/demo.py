"""bonus/demo.py — 5-Query Demo Script for HybridMemoryAgent.

Demonstrates:
  1. Simple recall (vector / BM25 hit on technical term: Kubernetes)
  2. Profile-guided recall (relying on topic_affinity & reading speed)
  3. Fresh activity recall (relying on queries_last_hour & session fatigue)
  4. Paraphrased query recall (Vietnamese paraphrase without literal keyword)
  5. Mixed query recall (hybrid search + user profile combination)

Exits 0 and prints assembled context.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure repo root is on sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from bonus.agent import HybridMemoryAgent


def main() -> int:
    print("=" * 65)
    print("DEMO: HybridMemoryAgent (Episodic Memory + Feast Feature Store)")
    print("=" * 65)

    agent = HybridMemoryAgent()

    # Seed realistic episodic memory notes for user u_001
    sample_notes = [
        "Đã đọc tài liệu Kubernetes: Pod lifecycle, ReplicaSet và cấu hình Auto-scaling Horizontal Pod Autoscaler (HPA).",
        "Ghi chú về Cloud Security: Thực thi mô hình Zero-Trust, bảo mật API Gateway với OAuth2 và JWT token.",
        "Kiến trúc hệ thống: Giải pháp mở rộng hạ tầng tự động linh hoạt dựa trên lưu lượng truy cập thực tế của người dùng.",
        "Tối ưu chi phí đám mây AWS: Áp dụng Spot Instance và FinOps để cắt giảm 40% chi phí điện toán.",
        "Cơ sở dữ liệu: So sánh PostgreSQL replication và MongoDB sharding cho hệ thống giao dịch phân tán.",
    ]

    print("\n[Step 1] Ingesting initial episodic memories for user 'u_001'...")
    for note in sample_notes:
        agent.remember(text=note, user_id="u_001")
    print(f"  Ingested {len(sample_notes)} notes into Qdrant/BM25 index.")

    # 5 Demo queries matching BONUS-CHALLENGE.md specifications
    demo_queries = [
        ("Query 1 — Hỏi đơn giản (Vector/BM25 hit)", "Tôi đã đọc gì về Kubernetes?"),
        ("Query 2 — Hỏi cần profile context", "Recommend đọc gì tiếp"),
        ("Query 3 — Hỏi cần fresh activity", "Tôi đang quan tâm gì gần đây?"),
        ("Query 4 — Hỏi paraphrase (Vector wins)", "Tài liệu về tự động mở rộng hạ tầng?"),
        ("Query 5 — Hỏi mixed (Hybrid + Profile)", "Cho tôi summary cloud security"),
    ]

    print("\n[Step 2] Executing 5 benchmark queries:\n")
    for title, q in demo_queries:
        print(f"--- {title} ---")
        context = agent.recall(query=q, user_id="u_001")
        print(context)
        print()

    print("=" * 65)
    print("DEMO COMPLETED SUCCESSFULLY — All 5 query contexts assembled.")
    print("=" * 65)
    return 0


if __name__ == "__main__":
    sys.exit(main())
