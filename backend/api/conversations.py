# -*- coding: utf-8 -*-
"""本机对话记录备份。

前端仍优先使用 WebView/localStorage；这里提供一份按系统用户保存的备份，
避免 pywebview 或端口变化导致 localStorage 读不到历史记录。
"""

import json
import time
from pathlib import Path
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

import config

router = APIRouter()


class ConversationBackup(BaseModel):
    data: str = ""
    active_id: Optional[str] = None


def _read_payload() -> dict:
    path = config.CONVERSATIONS_FILE
    if not path.exists():
        return {"data": "", "active_id": None}
    try:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except Exception:
        return {"data": "", "active_id": None}
    if not isinstance(payload, dict):
        return {"data": "", "active_id": None}
    return {
        "data": payload.get("data", "") if isinstance(payload.get("data", ""), str) else "",
        "active_id": payload.get("active_id"),
        "updated_at": payload.get("updated_at"),
    }


def _write_payload(payload: dict) -> None:
    path = config.CONVERSATIONS_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(path) + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


@router.get("/conversations")
async def get_conversations():
    return _read_payload()


@router.post("/conversations")
async def save_conversations(body: ConversationBackup):
    payload = {
        "data": body.data,
        "active_id": body.active_id,
        "updated_at": time.time(),
    }
    _write_payload(payload)
    return {"status": "ok"}


@router.delete("/conversations")
async def clear_conversations():
    try:
        config.CONVERSATIONS_FILE.unlink(missing_ok=True)
    except Exception:
        _write_payload({"data": "", "active_id": None, "updated_at": time.time()})
    return {"status": "ok"}
