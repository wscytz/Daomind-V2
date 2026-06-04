# -*- coding: utf-8 -*-
"""6个 RAG Provider 合一"""

import json
import logging
import re
from pathlib import Path
from typing import Dict
from .base import BaseNPZRAG

logger = logging.getLogger(__name__)


def _clean_original(text: str) -> str:
    """清洗原文：移除混入的场景/情绪标签"""
    if not text:
        return ""
    # 移除「场景：xxx」「情绪：xxx」等尾部标签
    text = re.sub(r'\n*(?:场景|情绪|标签)[：:].+', '', text)
    return text.strip()


class DaodejingProvider(BaseNPZRAG):
    @property
    def provider_name(self): return "道德经"

    def _build_result(self, idx, item, sim):
        return {
            "id": str(idx), "similarity": sim, "source": "daodejing",
            "chapter": item.get("chapter", idx),
            "original": _clean_original(item.get("original", "")),
            "translation": item.get("translation", ""),
            "interpretation": item.get("interpretation", ""),
            "scene_tags": item.get("scene_tags", []),
            "emotion_tags": item.get("emotion_tags", []),
            "taoist_principle": item.get("taoist_principle", ""),
            "key_metaphor": item.get("key_metaphor", ""),
            "modern_context": item.get("modern_context", ""),
        }


class LunyuProvider(BaseNPZRAG):
    @property
    def provider_name(self): return "论语"

    def _build_result(self, idx, item, sim):
        return {
            "id": str(idx), "similarity": sim, "source": "lunyu",
            "chapter": item.get("chapter", ""),
            "original": _clean_original(item.get("original", "")),
            "translation": item.get("translation", ""),
            "interpretation": item.get("interpretation", ""),
            "emotion_tags": item.get("emotion_tags", []),
            "scene_tags": item.get("scene_tags", []),
        }


class ZhuangziProvider(BaseNPZRAG):
    @property
    def provider_name(self): return "庄子"

    def _build_result(self, idx, item, sim):
        return {
            "id": str(idx), "similarity": sim, "source": "zhuangzi",
            "chapter": item.get("chapter", ""),
            "original": _clean_original(item.get("original", "")),
            "translation": item.get("translation", ""),
            "interpretation": item.get("interpretation", ""),
            "emotion_tags": item.get("emotion_tags", []),
            "scene_tags": item.get("scene_tags", []),
        }


class DaoistTherapyProvider(BaseNPZRAG):
    """道家治疗 — 数据从独立 JSON 加载（NPZ 只有 metadata）"""

    def __init__(self, npz_path: Path, json_path: Path):
        self._json_path = json_path
        super().__init__(npz_path)

    def _load_embeddings(self) -> bool:
        ok = super()._load_embeddings()
        if not ok and self.embeddings is None:
            return False
        # 从 JSON 加载治疗知识（NPZ 只有 metadata）
        try:
            with open(self._json_path, "r", encoding="utf-8") as f:
                self.data = json.load(f)
            logger.info(f"[道家治疗] 从JSON加载 {len(self.data)} 条知识")
            self.loaded = True
        except Exception as e:
            logger.error(f"[道家治疗] JSON加载失败: {e}")
            return False
        return True

    @property
    def provider_name(self): return "道家治疗"

    def _build_result(self, idx, item, sim):
        return {
            "id": str(idx), "similarity": sim, "source": "daoist_therapy",
            "title": item.get("title", ""),
            "content": item.get("content", ""),
            "emotion_tags": item.get("emotion_tags", []),
            "scene_tags": item.get("scene_tags", []),
            "wisdom": item.get("wisdom", ""),
            "modern_interpretation": item.get("modern_interpretation", ""),
        }


class BaijuyiProvider(BaseNPZRAG):
    """白居易核心诗歌 — 数据从独立 JSON 加载"""

    def __init__(self, npz_path: Path, json_path: Path):
        self._json_path = json_path
        super().__init__(npz_path)

    def _load_embeddings(self) -> bool:
        # 先让基类加载 NPZ（只取 embeddings，data 会被覆盖）
        ok = super()._load_embeddings()
        if not ok:
            return False
        # 从独立 JSON 加载诗歌元数据
        try:
            with open(self._json_path, "r", encoding="utf-8") as f:
                self.data = json.load(f)
            logger.info(f"[白居易] 从JSON加载 {len(self.data)} 首诗")
        except Exception as e:
            logger.error(f"[白居易] JSON加载失败: {e}")
            return False
        return True

    @property
    def provider_name(self): return "白居易"

    def _build_result(self, idx, item, sim):
        return {
            "id": str(item.get("id", idx)),
            "similarity": sim, "source": "poem",
            "title": item.get("title", ""),
            "content": item.get("content", ""),
            "theme": ", ".join(item.get("scenes", [])),
            "emotion_tags": item.get("emotions", []),
            "wisdom": item.get("usage_example", ""),
            "modern_interpretation": item.get("modern_interpretation", ""),
            "translation": item.get("translation", ""),
            "quality_level": item.get("quality_level", ""),
        }


class BaijuyiOuterProvider(BaseNPZRAG):
    """白居易外圈补充诗歌"""

    def __init__(self, npz_path: Path, json_path: Path):
        self._json_path = json_path
        super().__init__(npz_path)

    def _load_embeddings(self) -> bool:
        ok = super()._load_embeddings()
        if not ok:
            return False
        try:
            with open(self._json_path, "r", encoding="utf-8") as f:
                self.data = json.load(f)
            logger.info(f"[白居易外圈] 从JSON加载 {len(self.data)} 首诗")
        except Exception as e:
            logger.error(f"[白居易外圈] JSON加载失败: {e}")
            return False
        return True

    @property
    def provider_name(self): return "白居易外圈"

    def _build_result(self, idx, item, sim):
        return {
            "id": str(item.get("id", idx)),
            "similarity": sim, "source": "poem_outer",
            "title": item.get("title", ""),
            "content": item.get("content", ""),
            "theme": ", ".join(item.get("scenes", [])),
            "emotion_tags": item.get("emotions", []),
            "translation": item.get("translation", ""),
            "quality_level": item.get("quality_level", ""),
        }
