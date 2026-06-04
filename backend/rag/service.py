# -*- coding: utf-8 -*-
"""统一 RAG 服务 — 无 SDK 依赖，Embedding 走 HTTP"""

import hashlib
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
    "baijuyi": ["baijuyi"],
    "baijuyi_outer": ["baijuyi_outer"],
    "daoist_therapy": ["daoist_therapy"],
}


class RAGService:
    def __init__(self, data_dir: Path, embedding_base_url: str,
                 embedding_api_key: str, embedding_model: str = "embedding-3",
                 auth_type: str = "bearer"):
        self.data_dir = data_dir
        self.emb_base_url = embedding_base_url
        self.emb_api_key = embedding_api_key
        self.emb_model = embedding_model
        self.emb_auth_type = auth_type
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

    @staticmethod
    def _is_usable_result(result: Dict) -> bool:
        """过滤明显脏的检索结果，避免截断诗句在前端反复曝光。"""
        if result.get("source") not in ("poem", "poem_outer"):
            return True

        content = (result.get("content") or result.get("original") or "").strip()
        if not content:
            return False

        # 外圈诗库有少量截断/低质样本，如《逢旧》末尾残留单字“知”。
        if content.endswith(("知", "。知", "，知")):
            return False

        return True

    @staticmethod
    def _rank_score(result: Dict) -> float:
        score = result.get("score")
        if score is None:
            score = result.get("similarity", 0)

        # 外圈低质量诗仍可作为兜底，但不应压过核心诗库和高质量外圈诗。
        if result.get("source") == "poem_outer" and result.get("quality_level") == "low":
            score *= 0.72

        return score

    @staticmethod
    def _filter_and_rank_results(results: List[Dict], top_k: int) -> List[Dict]:
        filtered = [r for r in results if RAGService._is_usable_result(r)]
        filtered.sort(key=RAGService._rank_score, reverse=True)
        return filtered[:top_k]

    def _get_embedding(self, query: str):
        """调一次 Embedding API，返回向量"""
        if not self.providers:
            return None
        first = next(iter(self.providers.values()))
        return first.get_query_embedding(query, self.emb_base_url, self.emb_api_key, self.emb_model, self.emb_auth_type)

    def _cache_key(self, query: str, classic: str, top_k: int) -> str:
        return f"{hashlib.md5(query.encode()).hexdigest()[:12]}::{classic}::{top_k}"

    def search(self, query: str, classic: str = "daodejing", top_k: int = 3) -> Dict:
        cache_key = self._cache_key(query, classic, top_k)
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
                    query_embedding, query, top_k=top_k * 4,
                    build_result_fn=lambda idx, item, sim, p=provider: p._build_result(idx, item, sim),
                )
            else:
                results = provider.search_with_vector(query_embedding, top_k * 4)
            all_results.extend(results)

        all_results = self._filter_and_rank_results(all_results, top_k)

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

    def search_multi(self, query: str, classics: List[str], top_k: int = 3) -> Dict:
        """多库综合检索：合并多个经典库的结果（embedding 只调一次）"""
        if not classics:
            return {"results": [], "sources": []}

        # 复用 embedding，一次调完
        query_embedding = self._get_embedding(query)
        if query_embedding is None:
            return {"results": [], "error": "Embedding API 调用失败"}

        all_results = []
        per_classic_k = max(top_k * 4, 8)

        for classic in classics:
            r = self._search_with_embedding(query_embedding, query, classic=classic, top_k=per_classic_k)
            all_results.extend(r.get("results", []))

        # 过滤脏样本并按相似度截断
        all_results = self._filter_and_rank_results(all_results, top_k)

        return {
            "results": all_results,
            "sources": list(set(r.get("source", "") for r in all_results)),
        }

    def _search_with_embedding(self, query_embedding: List[float], query: str, classic: str = "daodejing", top_k: int = 3) -> Dict:
        """复用已有 embedding 结果的检索（不重复调 API）"""
        cache_key = self._cache_key(query, classic, top_k)
        with self._lock:
            cached = self._cache.get(cache_key)
            if cached:
                return cached

        route = CLASSIC_ROUTES.get(classic, CLASSIC_ROUTES["daodejing"])

        all_results = []
        for name in route:
            provider = self.providers.get(name)
            if not provider or not provider.loaded:
                continue
            hybrid = self.hybrids.get(name)
            if hybrid:
                results = hybrid.search(
                    query_embedding, query, top_k=top_k * 4,
                    build_result_fn=lambda idx, item, sim, p=provider: p._build_result(idx, item, sim),
                )
            else:
                results = provider.search_with_vector(query_embedding, top_k * 4)
            all_results.extend(results)

        all_results = self._filter_and_rank_results(all_results, top_k)

        result = {
            "results": all_results,
            "sources": list(set(r.get("source", "") for r in all_results)),
        }
        with self._lock:
            self._cache[cache_key] = result
        return result
