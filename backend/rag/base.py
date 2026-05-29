# -*- coding: utf-8 -*-
"""NPZ向量检索基类 — Embedding 走 HTTP，不依赖任何 SDK"""

import json
import logging
import numpy as np
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Optional

import requests

logger = logging.getLogger(__name__)


class BaseNPZRAG(ABC):
    def __init__(self, npz_path: Path):
        self.npz_path = npz_path
        self.embeddings = None
        self.embeddings_normalized = None
        self.data = []
        self.loaded = False

        if not npz_path.exists():
            logger.error(f"[{self.provider_name}] 向量文件不存在: {npz_path}")
            return
        self._load_embeddings()

    def _load_embeddings(self) -> bool:
        try:
            npz_data = np.load(self.npz_path, allow_pickle=True)
            self.embeddings = npz_data['embeddings']
            if 'data' in npz_data:
                self.data = json.loads(str(npz_data['data']))
            elif 'embedding_texts' in npz_data:
                self.data = list(npz_data['embedding_texts'])

            norms = np.linalg.norm(self.embeddings, axis=1, keepdims=True)
            norms[norms == 0] = 1
            self.embeddings_normalized = self.embeddings / norms
            self.loaded = True
            logger.info(f"[{self.provider_name}] 加载成功: {len(self.data)}条, 维度{self.embeddings.shape}")
            return True
        except Exception as e:
            logger.error(f"[{self.provider_name}] 加载失败: {e}")
            return False

    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @abstractmethod
    def _build_result(self, idx: int, item: Dict, similarity: float) -> Dict: ...

    def get_query_embedding(self, query: str, base_url: str, api_key: str,
                            model: str = "embedding-3", auth_type: str = "bearer") -> Optional[np.ndarray]:
        """调 Embedding API（OpenAI 兼容格式）获取查询向量"""
        try:
            headers = {"Content-Type": "application/json"}
            if api_key:
                if auth_type == "api-key":
                    headers["X-API-Key"] = api_key
                else:
                    headers["Authorization"] = f"Bearer {api_key}"
            resp = requests.post(
                f"{base_url}/embeddings",
                headers=headers, json={"model": model, "input": [query]},
                timeout=30,
            )
            if resp.status_code != 200:
                logger.error(f"[{self.provider_name}] Embedding API {resp.status_code}: {resp.text[:200]}")
                return None
            data = resp.json()
            return np.array(data["data"][0]["embedding"], dtype=np.float32)
        except Exception as e:
            logger.error(f"[{self.provider_name}] Embedding失败: {e}")
            return None

    def search_with_vector(self, query_embedding: np.ndarray, top_k: int = 3) -> List[Dict]:
        if not self.loaded or self.embeddings_normalized is None:
            return []
        norm = np.linalg.norm(query_embedding)
        if norm == 0:
            return []
        query_norm = query_embedding / norm
        similarities = np.dot(self.embeddings_normalized, query_norm)
        top_indices = np.argsort(similarities)[::-1][:top_k]
        return [
            self._build_result(idx, self.data[idx], float(similarities[idx]))
            for idx in top_indices
        ]

    def retrieve(self, query: str, base_url: str, api_key: str,
                 model: str = "embedding-3", auth_type: str = "bearer", top_k: int = 3) -> List[Dict]:
        embedding = self.get_query_embedding(query, base_url, api_key, model, auth_type)
        if embedding is None:
            return []
        return self.search_with_vector(embedding, top_k)
