# -*- coding: utf-8 -*-
"""关键词情绪检测 — 给 RAG 检索结果排序用"""

from collections import OrderedDict
from typing import Optional

EMOTION_KEYWORDS = OrderedDict([
    ("抑郁", ["活着没意思", "想死", "不想活", "抑郁", "沮丧", "绝望"]),
    ("恐惧", ["恐惧", "害怕", "可怕", "担心害怕"]),
    ("焦虑", ["焦虑", "紧张", "不安", "忧虑", "困扰", "失眠", "心慌"]),
    ("愤怒", ["愤怒", "生气", "恼火", "恨", "烦", "火大"]),
    ("悲伤", ["难过", "伤心", "悲伤", "痛苦", "失落", "郁闷", "孤独"]),
    ("孤独", ["孤独", "孤单", "寂寞", "一个人"]),
    ("迷茫", ["迷茫", "困惑", "不知道", "不确定"]),
    ("压力", ["压力", "累", "疲惫", "负担", "辛苦"]),
    ("开心", ["开心", "高兴", "快乐", "幸福", "满足"]),
])

PRINCIPLES = {
    "焦虑": "少私寡欲，知足知止",
    "愤怒": "利而不害，为而不争",
    "悲伤": "清静无为，顺其自然",
    "压力": "少私寡欲，知足知止",
    "迷茫": "见素抱朴，少私寡欲",
    "恐惧": "知和处下，以柔胜刚",
    "抑郁": "致虚极，守静笃",
    "孤独": "独与天地精神往来",
    "开心": "知足常乐，悠然自得",
}


def detect_emotion(text: str) -> Optional[str]:
    """检测情绪，无匹配时返回 None（让调用方决定是否使用默认值）"""
    if not text:
        return None
    for emotion, keywords in EMOTION_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return emotion
    return None


def get_principle(emotion: str) -> str:
    return PRINCIPLES.get(emotion, "少私寡欲，知足知止")
