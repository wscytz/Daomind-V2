# -*- coding: utf-8 -*-
"""二十四节气服务 — 计算当前节气、选取对应经典段落"""

from datetime import date
from typing import Optional, Dict, List

# 节气表：月 → [(日, 节气名, 关键词, 描述)]
# 日期取近似值（每年微调 1-2 天不影响主题匹配）
SOLAR_TERMS = {
    1:  [(6, "小寒", "蛰伏", "寒气渐盛，万物深藏。宜守静养精，待时而动。"),
         (20, "大寒", "坚冰", "寒至极处，坚冰将融。最冷之时，春已在望。")],
    2:  [(4, "立春", "新生", "东风解冻，万物始生。一年之计，从今日起。"),
         (19, "雨水", "润泽", "春雨润物，无声入夜。柔能克刚，水善利万物。")],
    3:  [(6, "惊蛰", "苏醒", "春雷乍动，蛰虫始振。沉寂之后的觉醒，力量涌现。"),
         (21, "春分", "平衡", "昼夜均分，阴阳相半。不偏不倚，中道而行。")],
    4:  [(5, "清明", "澄明", "天清地明，万物皆显。心若清明，则无蔽塞。"),
         (20, "谷雨", "生长", "雨生百谷，润物无声。厚积薄发，顺势而为。")],
    5:  [(6, "立夏", "繁茂", "万物至此皆长大。心宜安宁，勿急勿躁。"),
         (21, "小满", "知足", "麦粒渐满，未全满。小满即是圆满，知足常乐。")],
    6:  [(6, "芒种", "耕耘", "有芒之谷，此时可种。勤而不疲，劳而有节。"),
         (21, "夏至", "极盛", "阳气至极，阴气始生。盛极必衰，居安思危。")],
    7:  [(7, "小暑", "温热", "暑气渐升，宜静心。心静自然凉，躁动则热烦。"),
         (23, "大暑", "酷热", "一年最热之时。如能守心，酷暑亦是修行。")],
    8:  [(7, "立秋", "收敛", "凉风至，白露降。收敛心神，由动转静。"),
         (23, "处暑", "止热", "暑气止于此。进退有度，适时而止。")],
    9:  [(8, "白露", "凝练", "露凝而白，秋意渐浓。凝结精华，去芜存菁。"),
         (23, "秋分", "均衡", "再次平衡，阴阳各半。平和之道，过犹不及。")],
    10: [(8, "寒露", "清冷", "露气寒冷，将凝结为霜。清心寡欲，寡言慎行。"),
         (23, "霜降", "沉淀", "霜降杀百草，万物归藏。放下执念，回归本心。")],
    11: [(7, "立冬", "收藏", "水始冰，地始冻。收藏能量，为来年蓄力。"),
         (22, "小雪", "内省", "天地不通，闭塞成冬。向内观照，静待春来。")],
    12: [(7, "大雪", "深藏", "大雪纷飞，银装素裹。藏锋守拙，大道至简。"),
         (22, "冬至", "复始", "一阳复始，日影最长。否极泰来，光明将返。")],
}

# 节气对应的经典主题关键词
TERM_RAG_THEMES = {
    "小寒": "蛰伏守静", "大寒": "坚韧等待", "立春": "新的开始", "雨水": "柔顺包容",
    "惊蛰": "觉醒行动", "春分": "中庸平衡", "清明": "澄澈明心", "谷雨": "顺势生长",
    "立夏": "内心安宁", "小满": "知足常乐", "芒种": "勤勉有节", "夏至": "盛极思危",
    "小暑": "静心消烦", "大暑": "守心如一", "立秋": "收敛心神", "处暑": "适可而止",
    "白露": "去芜存菁", "秋分": "不偏不倚", "寒露": "清心寡欲", "霜降": "放下执念",
    "立冬": "蓄力收藏", "小雪": "向内观照", "大雪": "藏锋守拙", "冬至": "否极泰来",
}


def get_current_term(target_date: Optional[date] = None) -> Dict:
    """获取当前节气信息"""
    d = target_date or date.today()
    month_terms = SOLAR_TERMS.get(d.month, [])
    current = month_terms[0]  # 默认本月第一个
    for day, name, keyword, desc in month_terms:
        if d.day >= day:
            current = (day, name, keyword, desc)
    _, name, keyword, desc = current
    return {
        "name": name,
        "keyword": keyword,
        "description": desc,
        "date": f"{d.month}月{d.day}日",
        "theme": TERM_RAG_THEMES.get(name, keyword),
    }


def get_wisdom_card(rag_service, target_date: Optional[date] = None) -> Dict:
    """根据节气和日期选取每日智慧卡"""
    d = target_date or date.today()
    term = get_current_term(d)

    # 日期种子：同一天返回同一张卡
    day_seed = d.year * 10000 + d.month * 100 + d.day

    # 用节气主题搜索经典
    theme = term["theme"]
    results = []
    try:
        # 优先从道德经和庄子搜
        r1 = rag_service.search(theme, classic="daodejing", top_k=2)
        results.extend(r1.get("results", []))
        r2 = rag_service.search(theme, classic="zhuangzi", top_k=2)
        results.extend(r2.get("results", []))
        r3 = rag_service.search(theme, classic="daoist_therapy", top_k=1)
        results.extend(r3.get("results", []))
    except Exception:
        pass

    if not results:
        return {"term": term, "passage": None}

    # 用日期种子选一条（避免每次随机）
    idx = day_seed % len(results)
    chosen = results[idx]

    source = chosen.get("source", "")
    source_name = {
        "daodejing": "道德经", "zhuangzi": "庄子", "lunyu": "论语",
        "daoist_therapy": "道家认知疗法", "poem": "白居易", "poem_outer": "白居易",
    }.get(source, source)

    passage = {
        "source": source,
        "source_name": source_name,
        "chapter": chosen.get("chapter", ""),
        "original": chosen.get("original") or chosen.get("content", ""),
        "translation": chosen.get("translation") or chosen.get("modern_context") or chosen.get("interpretation", ""),
        "title": chosen.get("title", ""),
    }

    # 跳过内容为空的条目
    if not passage["original"] and not passage["title"]:
        # 尝试下一个
        for offset in range(1, len(results)):
            alt = results[(idx + offset) % len(results)]
            src2 = alt.get("source", "")
            orig = alt.get("original") or alt.get("content", "")
            if orig:
                src_name2 = {
                    "daodejing": "道德经", "zhuangzi": "庄子", "lunyu": "论语",
                    "daoist_therapy": "道家认知疗法", "poem": "白居易", "poem_outer": "白居易",
                }.get(src2, src2)
                passage = {
                    "source": src2,
                    "source_name": src_name2,
                    "chapter": alt.get("chapter", ""),
                    "original": orig,
                    "translation": alt.get("translation") or alt.get("modern_context") or alt.get("interpretation", ""),
                    "title": alt.get("title", ""),
                }
                break

    return {"term": term, "passage": passage}
