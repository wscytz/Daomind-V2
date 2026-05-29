import os
import sys
import json
import logging
import threading
from pathlib import Path
from dotenv import load_dotenv


def _get_base_dir() -> Path:
    """项目根目录，兼容 PyInstaller 打包"""
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent.parent


def _get_user_dir() -> Path:
    """用户可写目录（settings.json 等）"""
    if getattr(sys, 'frozen', False):
        # exe 所在目录
        return Path(sys.executable).parent
    return _get_base_dir()


_base = _get_base_dir()
_user = _get_user_dir()

# .env 加载：优先用户目录，其次项目目录
_env_file = _user / ".env"
if not _env_file.exists():
    _env_file = _base / ".env"
load_dotenv(_env_file)

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8001"))
_CORS_ENV = os.getenv("CORS_ORIGINS", "")
if _CORS_ENV == "*":
    CORS_ORIGINS = ["*"]
elif _CORS_ENV:
    CORS_ORIGINS = [o.strip() for o in _CORS_ENV.split(",")]
else:
    CORS_ORIGINS = ["http://localhost:8001", "http://127.0.0.1:8001", "http://localhost:5173"]
_RAG_RAW = os.getenv("RAG_DATA_DIR", "")
RAG_DATA_DIR = Path(_RAG_RAW) if _RAG_RAW else _base / "data" / "rag_databases"
SETTINGS_FILE = _user / "settings.json"
FRONTEND_DIR = _base / "frontend" / "dist"

_config_lock = threading.Lock()

# ═══════════════════════════════════════════════════════
# API Provider 配置
# ═══════════════════════════════════════════════════════

PROVIDERS = [
    {
        "name": "zhipu",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "api_key": os.getenv("ZHIPU_API_KEY", ""),
        "models": {
            "glm-4-flash": "glm-4-flash",
            "glm-4.7": "glm-4.7",
            "glm-5": "glm-5",
            "emohaa": "emohaa",
        },
    },
    {
        "name": "doubao",
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "api_key": os.getenv("DOUBAO_API_KEY", ""),
        "models": {
            "seed": "doubao-seed-2-0-pro-260215",
            "seed-lite": "doubao-seed-2-0-lite-260215",
        },
    },
]

EMBEDDING_PROVIDER = {
    "base_url": os.getenv("EMBEDDING_BASE_URL", "https://open.bigmodel.cn/api/paas/v4"),
    "api_key": os.getenv("EMBEDDING_API_KEY", os.getenv("ZHIPU_API_KEY", "")),
    "model": os.getenv("EMBEDDING_MODEL", "embedding-3"),
}


def _load_settings_file():
    """从 settings.json 加载用户保存的配置，覆盖 env 默认值"""
    if not SETTINGS_FILE.exists():
        return
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        global PROVIDERS, EMBEDDING_PROVIDER
        with _config_lock:
            if "providers" in data:
                for saved in data["providers"]:
                    for p in PROVIDERS:
                        if p["name"] == saved.get("name"):
                            if saved.get("base_url"):
                                p["base_url"] = saved["base_url"]
                            if saved.get("api_key"):
                                p["api_key"] = saved["api_key"]
            if "embedding" in data:
                emb = data["embedding"]
                if emb.get("base_url"):
                    EMBEDDING_PROVIDER["base_url"] = emb["base_url"]
                if emb.get("api_key"):
                    EMBEDDING_PROVIDER["api_key"] = emb["api_key"]
                if emb.get("model"):
                    EMBEDDING_PROVIDER["model"] = emb["model"]
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.warning(f"加载 settings.json 失败: {e}，使用 .env 默认配置")


def save_settings(providers_data: list, embedding_data: dict):
    """保存配置到 settings.json 并更新运行时"""
    global PROVIDERS, EMBEDDING_PROVIDER
    payload = {"providers": providers_data, "embedding": embedding_data}
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    with _config_lock:
        for saved in providers_data:
            for p in PROVIDERS:
                if p["name"] == saved.get("name"):
                    if saved.get("base_url"):
                        p["base_url"] = saved["base_url"]
                    if saved.get("api_key"):
                        p["api_key"] = saved["api_key"]
        if embedding_data.get("base_url"):
            EMBEDDING_PROVIDER["base_url"] = embedding_data["base_url"]
        if embedding_data.get("api_key"):
            EMBEDDING_PROVIDER["api_key"] = embedding_data["api_key"]
        if embedding_data.get("model"):
            EMBEDDING_PROVIDER["model"] = embedding_data["model"]


def get_settings_snapshot() -> dict:
    """返回当前配置的快照（脱敏）"""
    providers_safe = []
    for p in PROVIDERS:
        key = p.get("api_key", "")
        masked = key[:4] + "****" + key[-4:] if len(key) > 8 else ("****" if key else "")
        providers_safe.append({
            "name": p["name"],
            "base_url": p["base_url"],
            "api_key": key,
            "api_key_masked": masked,
            "models": p.get("models", {}),
        })
    emb_key = EMBEDDING_PROVIDER.get("api_key", "")
    emb_masked = emb_key[:4] + "****" + emb_key[-4:] if len(emb_key) > 8 else ("****" if emb_key else "")
    return {
        "providers": providers_safe,
        "embedding": {
            "base_url": EMBEDDING_PROVIDER["base_url"],
            "api_key": emb_key,
            "api_key_masked": emb_masked,
            "model": EMBEDDING_PROVIDER["model"],
        },
    }


# 启动时加载用户保存的配置
_load_settings_file()


def get_all_model_choices() -> dict:
    """返回所有可用模型: { '前端名': {'provider_name', 'api_model', 'base_url', 'api_key'} }"""
    choices = {}
    for p in PROVIDERS:
        if not p["api_key"]:
            continue
        for display_name, api_model in p["models"].items():
            choices[display_name] = {
                "provider": p["name"],
                "base_url": p["base_url"],
                "api_key": p["api_key"],
                "api_model": api_model,
            }
    return choices


def get_model_config(model_name: str) -> dict | None:
    """按前端名查找模型配置"""
    choices = get_all_model_choices()
    return choices.get(model_name)
