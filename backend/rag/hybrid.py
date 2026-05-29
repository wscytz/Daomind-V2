# -*- coding: utf-8 -*-
"""BM25 + 向量混合检索（RRF 融合）"""

import logging
import re
from collections import Counter
from typing import Dict, List, Tuple

import numpy as np

logger = logging.getLogger(__name__)


def tokenize_chinese(text: str) -> List[str]:
    """中英文混合分词：中文按字 bigram + 单字，英文按空格"""
    tokens = []
    # 提取英文单词
    en_words = re.findall(r'[a-zA-Z]+', text.lower())
    tokens.extend(en_words)
    # 中文 bigram + 单字
    cn_chars = re.findall(r'[一-鿿]', text)
    tokens.extend(cn_chars)
    for i in range(len(cn_chars) - 1):
        tokens.append(cn_chars[i] + cn_chars[i + 1])
    return tokens


class BM25Retriever:
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus = []
        self.doc_freqs = []
        self.idf = {}
        self.doc_len = []
        self.avgdl = 0.0

    def index(self, documents: List[str]):
        self.corpus = documents
        self.doc_len = [len(tokenize_chinese(doc)) for doc in documents]
        self.avgdl = sum(self.doc_len) / len(documents) if documents else 0
        self.doc_freqs = [Counter(tokenize_chinese(doc)) for doc in documents]

        N = len(documents)
        df = Counter()
        for freq in self.doc_freqs:
            df.update(freq.keys())
        import math
        self.idf = {t: math.log((N - f + 0.5) / (f + 0.5) + 1) for t, f in df.items()}

    def search(self, query: str, top_k: int = 5) -> List[Tuple[int, float]]:
        if not self.corpus:
            return []
        import math
        query_tokens = tokenize_chinese(query)
        scores = []
        for doc_id, doc_freq in enumerate(self.doc_freqs):
            score = 0
            dl = self.doc_len[doc_id]
            for token in query_tokens:
                if token not in doc_freq:
                    continue
                tf = doc_freq[token]
                idf = self.idf.get(token, 0)
                score += idf * (tf * (self.k1 + 1)) / (tf + self.k1 * (1 - self.b + self.b * dl / self.avgdl))
            if score > 0:
                scores.append((doc_id, score))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]


class HybridRetriever:
    """BM25 + 向量检索，RRF 融合"""

    def __init__(self, bm25: BM25Retriever, embeddings_normalized: np.ndarray,
                 data: list, alpha: float = 0.6):
        self.bm25 = bm25
        self.embeddings_normalized = embeddings_normalized
        self.data = data
        self.alpha = alpha

    def search(self, query_embedding: np.ndarray, query_text: str,
               top_k: int = 5, build_result_fn=None) -> List[Dict]:
        norm = np.linalg.norm(query_embedding)
        vector_scores = {}
        if norm > 0:
            q = query_embedding / norm
            sims = np.dot(self.embeddings_normalized, q)
            top_vec = np.argsort(sims)[::-1][:top_k * 2]
            vector_scores = {int(idx): float(sims[idx]) for idx in top_vec}

        keyword_scores = dict(self.bm25.search(query_text, top_k=top_k * 2))

        fused = {}
        w_v, w_k = self.alpha, 1 - self.alpha
        for rank, (doc_id, _) in enumerate(sorted(vector_scores.items(), key=lambda x: x[1], reverse=True), 1):
            fused[doc_id] = fused.get(doc_id, 0) + w_v / (60 + rank)
        for rank, (doc_id, _) in enumerate(sorted(keyword_scores.items(), key=lambda x: x[1], reverse=True), 1):
            fused[doc_id] = fused.get(doc_id, 0) + w_k / (60 + rank)

        ranked = sorted(fused.items(), key=lambda x: x[1], reverse=True)[:top_k]

        if build_result_fn:
            return [build_result_fn(doc_id, self.data[doc_id], vector_scores.get(doc_id, 0)) for doc_id, _ in ranked]
        return [{"id": doc_id, "score": score, "source": "hybrid"} for doc_id, score in ranked]
