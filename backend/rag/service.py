# -*- coding: utf-8 -*-
"""统一 RAG 服务 — 无 SDK 依赖，Embedding 走 HTTP"""

import logging
from pathlib import Path
from typing import List, Dict, Optional
from threading import RLock
from cachetools import TTLCache

from .base import BaseNPZRAG
from .providers import (
    DaodejingProvider, LunyuProvider, ZhuangziProvider,
    DaoistTherapyProvider, BaijuyiProvider, BaijuyiOuterProvider,
)
from .hybrid import BM25Retriever, HybridRetriever

logger = logging.getLogger(__name__)

CLASSIC_ROUTES = {
    "daodejing": ["daodejing", "daoist_therapy"],
    "lunyu": ["lunyu", "daoist_therapy"],
    "zhuangzi": ["zhuangzi", "daoist_therapy"],
    "baijuyi": ["baijuyi", "baijuyi_outer", "daoist_therapy"],
    "daoist_therapy": ["daoist_therapy"],
}


class RAGService:
    def __init__(self, data_dir: Path, embedding_base_url: str,
                 embedding_api_key: str, embedding_model: str = "embedding-3"):
        self.data_dir = data_dir
        self.emb_base_url = embedding_base_url
        self.emb_api_key = embedding_api_key
        self.emb_model = embedding_model
        self.providers: Dict[str, BaseNPZRAG] = {}
        self.hybrids: Dict[str, HybridRetriever] = {}
        self._cache = TTLCache(maxsize=1000, ttl=300)
        self._lock = RLock()
        self._init_providers()

    def _init_providers(self):
        d = self.data_dir
        poems = d / "baijuyi_poems"

        configs = {
            "daodejing": DaodejingProvider(d / "daodejing_embeddings.npz"),
            "lunyu": LunyuProvider(d / "lunyu_embeddings.npz"),
            "zhuangzi": ZhuangziProvider(d / "zhuangzi_embeddings.npz"),
            "daoist_therapy": DaoistTherapyProvider(d / "daoist_therapy_embeddings.npz", d / "daoist_therapy_kb.json"),
            "baijuyi": BaijuyiProvider(poems / "baijuyi_embeddings.npz", poems / "baijuyi_poems.json"),
            "baijuyi_outer": BaijuyiOuterProvider(poems / "baijuyi_outer_embeddings.npz", poems / "baijuyi_poems_outer.json"),
        }

        for name, provider in configs.items():
            if provider.loaded:
                self.providers[name] = provider
                docs = [self._doc_text(item) for item in provider.data]
                if docs:
                    bm25 = BM25Retriever()
                    bm25.index(docs)
                    self.hybrids[name] = HybridRetriever(bm25, provider.embeddings_normalized, provider.data, alpha=0.6)

        logger.info(f"RAG服务就绪，已加载: {list(self.providers.keys())}")

    @property
    def loaded_providers(self) -> List[str]:
        return list(self.providers.keys())

    @staticmethod
    def _doc_text(item) -> str:
        if not isinstance(item, dict):
            return str(item)
        parts = [item.get("original", ""), item.get("translation", ""),
                 item.get("content", ""), item.get("title", ""),
                 item.get("interpretation", ""), item.get("modern_context", "")]
        tags = item.get("scene_tags", []) + item.get("emotion_tags", [])
        return " ".join(p for p in parts if p) + " " + " ".join(tags)

    def _get_embedding(self, query: str):
        """调一次 Embedding API，返回向量"""
        if not self.providers:
            return None
        first = next(iter(self.providers.values()))
        return first.get_query_embedding(query, self.emb_base_url, self.emb_api_key, self.emb_model)

    def search(self, query: str, classic: str = "daodejing", top_k: int = 3) -> Dict:
        cache_key = f"{query}::{classic}::{top_k}"
        with self._lock:
            cached = self._cache.get(cache_key)
            if cached:
                return cached

        route = CLASSIC_ROUTES.get(classic, CLASSIC_ROUTES["daodejing"])
        query_embedding = self._get_embedding(query)
        if query_embedding is None:
            return {"results": [], "error": "Embedding API 调用失败"}

        all_results = []
        for name in route:
            provider = self.providers.get(name)
            if not provider or not provider.loaded:
                continue
            hybrid = self.hybrids.get(name)
            if hybrid:
                results = hybrid.search(
                    query_embedding, query, top_k=top_k,
                    build_result_fn=lambda idx, item, sim, p=provider: p._build_result(idx, item, sim),
                )
            else:
                results = provider.search_with_vector(query_embedding, top_k)
            all_results.extend(results)

        all_results.sort(key=lambda x: x.get("similarity", 0), reverse=True)
        all_results = all_results[:top_k]

        result = {
            "results": all_results,
            "sources": list(set(r.get("source", "") for r in all_results)),
        }
        with self._lock:
            self._cache[cache_key] = result
        return result

    def format_context(self, results: List[Dict]) -> str:
        if not results:
            return ""
        parts = ["【参考知识】"]
        for i, r in enumerate(results[:5], 1):
            src = r.get("source", "")
            if src in ("poem", "poem_outer"):
                parts.append(f"\n{i}. 《{r.get('title', '')}》")
                if r.get("content"): parts.append(f"   原文：{r['content'][:200]}")
                if r.get("translation"): parts.append(f"   译文：{r['translation'][:200]}")
            elif src == "daodejing":
                parts.append(f"\n{i}. 道德经 第{r.get('chapter', '')}章")
                if r.get("original"): parts.append(f"   原文：{r['original']}")
                if r.get("translation"): parts.append(f"   译文：{r['translation']}")
            elif src in ("lunyu", "zhuangzi"):
                label = "论语" if src == "lunyu" else "庄子"
                parts.append(f"\n{i}. {label}·{r.get('chapter', '')}")
                if r.get("original"): parts.append(f"   原文：{r['original']}")
                if r.get("translation"): parts.append(f"   译文：{r['translation']}")
            elif src == "daoist_therapy":
                if r.get("title"): parts.append(f"\n{i}. {r['title']}")
                if r.get("content"): parts.append(f"   {r['content'][:200]}")
        return "\n".join(parts)
