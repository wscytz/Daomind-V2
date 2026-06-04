# -*- coding: utf-8 -*-
"""GET /api/about — 应用署名与版本信息"""

from fastapi import APIRouter

router = APIRouter()

APP_ABOUT = {
    "name": "Dao-Mind",
    "title": "道心",
    "version": "2.0",
    "author": "金许诺",
    "alias": "jxn/wscytz",
    "copyright": "Copyright (c) 2026 金许诺 (jxn/wscytz)",
}


@router.get("/about")
async def about():
    return APP_ABOUT
