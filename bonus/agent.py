"""bonus/agent.py — Minimal POC of Hybrid Memory Agent for Vietnamese Personal Assistant.

Combines:
  1. Episodic Memory (Vector DB + BM25 Lexical with RRF fusion)
  2. Stable User Profile & Streaming Activity (Feature Store - Feast / Online Store)

Part of Day 19 Bonus Challenge.
"""
from __future__ import annotations

import math
import hashlib
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List

# Optional retrieval dependencies; tests can explicitly inject an offline profile store.
try:
    from fastembed import TextEmbedding
    _HAS_FASTEMBED = True
except ImportError:
    _HAS_FASTEMBED = False

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, PointStruct, VectorParams, Filter, FieldCondition, MatchValue
    _HAS_QDRANT = True
except ImportError:
    _HAS_QDRANT = False


@dataclass
class MemoryRecord:
    id: str
    user_id: str
    text: str
    vector: List[float] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


class StandaloneBM25:
    """Lightweight in-memory BM25 implementation for zero-dependency portability."""
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus: List[List[str]] = []
        self.doc_ids: List[str] = []
        self.doc_len: List[int] = []
        self.avg_dl: float = 0.0
        self.idf: Dict[str, float] = {}

    @staticmethod
    def tokenize(text: str) -> List[str]:
        return re.findall(r"\w+", text.lower())

    def fit(self, doc_ids: List[str], texts: List[str]) -> None:
        self.doc_ids = doc_ids
        self.corpus = [self.tokenize(t) for t in texts]
        self.doc_len = [len(c) for c in self.corpus]
        total_docs = len(self.corpus)
        if total_docs == 0:
            self.avg_dl = 0.0
            return
        self.avg_dl = sum(self.doc_len) / total_docs

        df: Dict[str, int] = {}
        for doc in self.corpus:
            for term in set(doc):
                df[term] = df.get(term, 0) + 1

        self.idf = {
            term: math.log((total_docs - n + 0.5) / (n + 0.5) + 1.0)
            for term, n in df.items()
        }

    def score(self, query: str) -> List[tuple[str, float]]:
        q_tokens = self.tokenize(query)
        scores: List[tuple[str, float]] = []
        for idx, (doc_id, doc_tokens) in enumerate(zip(self.doc_ids, self.corpus)):
            score = 0.0
            doc_len = self.doc_len[idx]
            token_counts: Dict[str, int] = {}
            for t in doc_tokens:
                token_counts[t] = token_counts.get(t, 0) + 1

            for q in q_tokens:
                if q not in token_counts:
                    continue
                tf = token_counts[q]
                denom = tf + self.k1 * (1.0 - self.b + self.b * (doc_len / (self.avg_dl or 1.0)))
                score += self.idf.get(q, 0.0) * ((tf * (self.k1 + 1.0)) / denom)
            scores.append((doc_id, score))
        scores.sort(key=lambda kv: kv[1], reverse=True)
        return scores


class FallbackEmbedder:
    """Deterministic hash-based dense embedder for lightweight environments (dim=64)."""
    dim: int = 64

    def embed(self, texts: List[str]) -> List[List[float]]:
        results = []
        for text in texts:
            vec = [0.0] * self.dim
            words = re.findall(r"\w+", text.lower())
            for i, w in enumerate(words):
                h = int.from_bytes(hashlib.blake2b(w.encode("utf-8"), digest_size=8).digest(), "big") % self.dim
                vec[h] += 1.0 / (1.0 + i * 0.05)
            norm = math.sqrt(sum(v * v for v in vec)) or 1.0
            results.append([v / norm for v in vec])
        return results


class MockFeastOnlineStore:
    """Explicitly injected offline profile store for tests, separate from Feast."""
    def __init__(self):
        self._profiles: Dict[str, Dict[str, Any]] = {
            "u_001": {
                "user_id": "u_001",
                "topic_affinity": "cloud_architecture",
                "reading_speed_wpm": 260,
                "preferred_lang": "vi-VN",
                "queries_last_hour": 14,
                "night_fatigue_index": 0.72,
                "preferred_topics": ["Kubernetes", "Microservices", "Cloud Security"],
            },
            "u_002": {
                "user_id": "u_002",
                "topic_affinity": "ai_machine_learning",
                "reading_speed_wpm": 180,
                "preferred_lang": "vi-VN",
                "queries_last_hour": 3,
                "night_fatigue_index": 0.15,
                "preferred_topics": ["PyTorch", "LLM Fine-tuning", "RAG"],
            }
        }

    def get_online_features(self, entity_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        user_id = entity_rows[0].get("user_id", "u_001")
        return dict(self._profiles.get(user_id, {
            "user_id": user_id, "topic_affinity": "unknown",
            "reading_speed_wpm": 0, "preferred_lang": "unknown",
            "queries_last_hour": 0, "distinct_topics_24h": 0,
        }))

    def record_query(self, user_id: str) -> None:
        if user_id in self._profiles:
            self._profiles[user_id]["queries_last_hour"] += 1


class HybridMemoryAgent:
    """Agent combining Episodic Memory (Vector + BM25 RRF) with Feast Feature Store."""

    def __init__(self, collection_name: str = "user_memories", feature_store=None):
        self.collection_name = collection_name
        if feature_store is None:
            from bonus.feature_store import FeastOnlineStore
            feature_store = FeastOnlineStore()
        self.feast = feature_store
        self.memories: Dict[str, MemoryRecord] = {}
        self.bm25 = StandaloneBM25()
        self._memory_counter = 0

        # Try to use FastEmbed and Qdrant if available
        if _HAS_FASTEMBED:
            from app.embeddings import Embedder
            self.embedder = Embedder()
            self.embedder._load()
            self.embed_dim = self.embedder.dim
        else:
            self.embedder = FallbackEmbedder()
            self.embed_dim = 64

        if _HAS_QDRANT:
            try:
                self.qdrant = QdrantClient(":memory:")
                self.qdrant.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=self.embed_dim, distance=Distance.COSINE),
                )
            except Exception:
                self.qdrant = None
        else:
            self.qdrant = None

    def _get_embedding(self, text: str) -> List[float]:
        if hasattr(self.embedder, "embed"):
            res = list(self.embedder.embed([text]))
            if isinstance(res[0], list):
                return res[0]
            return res[0].tolist()
        return [0.0] * self.embed_dim

    def remember(self, text: str, user_id: str = "u_001") -> None:
        """Add a new piece of episodic memory for this user."""
        self._memory_counter += 1
        mem_id = f"mem_{self._memory_counter:04d}"
        vector = self._get_embedding(text)

        rec = MemoryRecord(id=mem_id, user_id=user_id, text=text, vector=vector)
        self.memories[mem_id] = rec

        # Upsert into Qdrant if available
        if self.qdrant is not None:
            self.qdrant.upsert(
                collection_name=self.collection_name,
                points=[
                    PointStruct(
                        id=self._memory_counter,
                        vector=vector,
                        payload={"mem_id": mem_id, "user_id": user_id, "text": text},
                    )
                ],
            )

        # Refresh BM25 index on user's corpus
        user_mems = [m for m in self.memories.values() if m.user_id == user_id]
        self.bm25.fit(
            doc_ids=[m.id for m in user_mems],
            texts=[m.text for m in user_mems],
        )

    def _cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        dot = sum(a * b for a, b in zip(v1, v2))
        n1 = math.sqrt(sum(a * a for a in v1)) or 1.0
        n2 = math.sqrt(sum(b * b for b in v2)) or 1.0
        return dot / (n1 * n2)

    def _search_vector(self, query: str, user_id: str, top_k: int = 10) -> List[str]:
        q_vec = self._get_embedding(query)
        if self.qdrant is not None:
            try:
                res = self.qdrant.query_points(
                    collection_name=self.collection_name,
                    query=q_vec,
                    query_filter=Filter(must=[FieldCondition(
                        key="user_id", match=MatchValue(value=user_id),
                    )]),
                    limit=top_k,
                )
                return [p.payload["mem_id"] for p in res.points if p.payload.get("user_id") == user_id]
            except Exception:
                pass

        # Standalone vector search
        user_mems = [m for m in self.memories.values() if m.user_id == user_id]
        scored = [(m.id, self._cosine_similarity(q_vec, m.vector)) for m in user_mems]
        scored.sort(key=lambda kv: kv[1], reverse=True)
        return [mem_id for mem_id, _ in scored[:top_k]]

    def _search_bm25(self, query: str, user_id: str, top_k: int = 10) -> List[str]:
        # Rebuild for the requested user, rather than whoever last wrote a note.
        user_mems = [m for m in self.memories.values() if m.user_id == user_id]
        self.bm25.fit([m.id for m in user_mems], [m.text for m in user_mems])
        scored = self.bm25.score(query)
        return [mem_id for mem_id, score in scored if score > 0.0][:top_k]

    def _search_hybrid(self, query: str, user_id: str, top_k: int = 3, rrf_k: int = 60) -> List[str]:
        depth = max(top_k * 3, 10)
        sem_ids = self._search_vector(query, user_id, depth)
        kw_ids = self._search_bm25(query, user_id, depth)

        rrf_scores: Dict[str, float] = {}
        for rank, mem_id in enumerate(kw_ids, start=1):
            rrf_scores[mem_id] = rrf_scores.get(mem_id, 0.0) + 1.0 / (rrf_k + rank)
        for rank, mem_id in enumerate(sem_ids, start=1):
            rrf_scores[mem_id] = rrf_scores.get(mem_id, 0.0) + 1.0 / (rrf_k + rank)

        ranked = sorted(rrf_scores.items(), key=lambda kv: kv[1], reverse=True)
        return [mem_id for mem_id, _ in ranked[:top_k]]

    def recall(self, query: str, user_id: str = "u_001") -> str:
        """Retrieve top-K memories + user profile features -> return assembled context."""
        # 1. Get user profile + recent activity from Feast online store
        self.feast.record_query(user_id)
        profile = self.feast.get_online_features([{"user_id": user_id}])

        # 2. Hybrid search Qdrant / episodic memory filtered by user_id
        top_mem_ids = self._search_hybrid(query, user_id, top_k=3)
        retrieved_texts = [f"- {self.memories[mid].text}" for mid in top_mem_ids
                           if mid in self.memories and self.memories[mid].user_id == user_id]
        memories_str = "\n".join(retrieved_texts) if retrieved_texts else "- (Chưa có ký ức tương đồng trực tiếp)"

        # 3. Assemble context string
        context = (
            f"=== [AGENT RECALL CONTEXT] ===\n"
            f"User profile: likes <{profile['topic_affinity']}> reading at <{profile['reading_speed_wpm']}>wpm. "
            f"Preferred lang: <{profile['preferred_lang']}>.\n"
            f"Recent activity: <{profile['queries_last_hour']}> queries last hour. "
            f"Distinct topics (24h): <{profile.get('distinct_topics_24h', 'unknown')}>.\n"
            f"Top episodic memories retrieved:\n{memories_str}\n"
            f"Target Query: \"{query}\"\n"
            f"=============================="
        )
        return context
