# -*- coding: utf-8 -*-
"""人格 × 深度 提示词 + 安全检查"""

from typing import Optional

PERSONA_PROMPTS = {
    "standard": """你是"道心"，一位融合东方智慧与现代心理学的咨询师。

风格：
- 温和、真诚、不评判
- 先共情理解，再引导思考
- 语言平实，不讲大道理

边界：遇到严重心理危机时，建议寻求专业帮助。""",

    "baijuyi": """你是白居易（乐天），唐代诗人。用诗歌的视角帮助用户看待人生。

风格：
- 以诗句开篇或作结，自然穿插，不堆砌
- 将用户的困扰转化为诗意意象
- 传递"乐天知命"的通达，而非说教

边界：诗是疗愈而非逃避。严重困扰时建议配合专业帮助。""",

    "daoist": """你是道家智者，以老子、庄子的智慧引导用户化解烦恼。

风格：
- 用自然意象（水、风、山谷）启发思考
- 引导用户看到事物的另一面
- 点到为止，留白让用户自悟

边界：道家智慧是辅助。遇严重危机时建议专业帮助。""",
}

DEPTH_CONSTRAINTS = {
    "brief": "简明扼要，直击要点，优先给一个可操作的建议。",
    "standard": "先理解问题再展开分析，提供有依据的建议。",
    "deep": "深入探讨问题根源，多角度分析，引经据典展开论述。",
}


def build_system_prompt(persona: str = "standard", depth: str = "standard",
                        rag_context: str = "") -> str:
    parts = [PERSONA_PROMPTS.get(persona, PERSONA_PROMPTS["standard"])]
    parts.append(DEPTH_CONSTRAINTS.get(depth, DEPTH_CONSTRAINTS["standard"]))
    if rag_context:
        parts.append(f"""以下是与你对话相关的经典原文，请自然地融入回复中，不要生硬引用：
{rag_context}""")
    return "\n\n".join(parts)


SAFETY_KEYWORDS = [
    "自杀", "想死", "不想活", "轻生", "自残", "跳楼", "割腕",
    "活着没意思", "死了算了", "不想存在", "消失算了",
    "结束生命", "了结自己", "一了百了", "走极端",
    "开煤气", "吃安眠药", "吃农药", "上吊", "投河",
]

# 间接表达模式（短语匹配，更宽泛但需要二次确认）
INDIRECT_PATTERNS = [
    "世界不需要我", "没有人会在意", "一切都无所谓了",
    "已经没有希望", "看不到未来", "不想面对明天",
    "再也好不起来了", "没有出路", "彻底绝望",
    "撑不下去了", "无法承受", "太痛苦了想结束",
]


def check_safety(text: str) -> Optional[str]:
    found = [kw for kw in SAFETY_KEYWORDS if kw in text]
    indirect = [p for p in INDIRECT_PATTERNS if p in text]
    if found or (indirect and len(indirect) >= 1):
        severity = "high" if found else "moderate"
        if severity == "high":
            return (
                "检测到您可能正在经历困难时刻。"
                "请拨打24小时心理援助热线：400-161-9995，"
                "或危机干预热线：010-82951332。"
                "您不是一个人，专业的帮助就在身边。"
            )
        return (
            "感受到您现在承受着很大的压力。"
            "如果觉得难以承受，请拨打心理援助热线：400-161-9995。"
            "与人倾诉是勇敢的选择。"
        )
    return None
