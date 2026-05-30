import os
import sys
import json
import base64
import logging
import threading
from pathlib import Path
from dotenv import load_dotenv


def _encrypt_key(key: str) -> str:
    """简单混淆：base64 编码（非密码学安全，防肉眼直接读取）"""
    if not key:
        return ""
    return base64.b64encode(key.encode("utf-8")).decode("ascii")


def _decrypt_key(enc: str) -> str:
    """解混淆"""
    if not enc:
        return ""
    try:
        return base64.b64decode(enc.encode("ascii")).decode("utf-8")
    except Exception:
        return enc  # 兼容旧版明文存储


def _get_base_dir() -> Path:
    """项目根目录，兼容 PyInstaller 打包"""
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent.parent


def _get_user_dir() -> Path:
    """用户可写目录（settings.json 等）"""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return _get_base_dir()


_base = _get_base_dir()
_user = _get_user_dir()

# .env 加载
_env_file = _user / ".env"
if not _env_file.exists():
    _env_file = _base / ".env"
load_dotenv(_env_file)

HOST = os.getenv("HOST", "127.0.0.1")
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

# 源名称映射（单一事实来源）
SOURCE_NAMES = {
    "daodejing": "道德经",
    "zhuangzi": "庄子",
    "lunyu": "论语",
    "daoist_therapy": "道家认知疗法",
    "poem": "白居易",
    "poem_outer": "白居易",
}

_config_lock = threading.Lock()

# ═══════════════════════════════════════════════════════
# API Provider 配置
# 结构：models 里每个 key 是前端用的 model id，value 含 api_model（实际发给 API 的名）、label（显示名）、tag（标签）
# ═══════════════════════════════════════════════════════

PROVIDERS = [
    {
        "name": "智谱 AI",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "api_key": os.getenv("ZHIPU_API_KEY", ""),
        "auth_type": "bearer",
        "models": {
            "glm-4-flash": {"api_model": "glm-4-flash", "label": "GLM-4 Flash", "tag": "快速"},
            "glm-4.7":     {"api_model": "glm-4.7", "label": "GLM-4.7", "tag": ""},
            "glm-5":       {"api_model": "glm-5", "label": "GLM-5", "tag": "旗舰"},
            "emohaa":      {"api_model": "emohaa", "label": "Emohaa", "tag": "情感"},
        },
    },
    {
        "name": "豆包",
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "api_key": os.getenv("DOUBAO_API_KEY", ""),
        "auth_type": "bearer",
        "models": {
            "seed":      {"api_model": "doubao-seed-2-0-pro-260215", "label": "Seed Pro", "tag": "推理"},
            "seed-lite": {"api_model": "doubao-seed-2-0-lite-260215", "label": "Seed Lite", "tag": "快速"},
        },
    },
    {
        "name": "Ollama（本地）",
        "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
        "api_key": os.getenv("OLLAMA_API_KEY", "ollama"),
        "auth_type": os.getenv("OLLAMA_AUTH_TYPE", "none"),
        "models": {
            "llama3":   {"api_model": "llama3", "label": "Llama 3", "tag": "本地"},
            "llama3.1": {"api_model": "llama3.1", "label": "Llama 3.1", "tag": "本地"},
            "qwen2.5":  {"api_model": "qwen2.5:7b", "label": "Qwen 2.5", "tag": "本地"},
            "deepseek-r1": {"api_model": "deepseek-r1:7b", "label": "DeepSeek R1", "tag": "推理·本地"},
            "bge-m3":   {"api_model": "bge-m3", "label": "BGE-M3 (Embedding)", "tag": "本地Embedding"},
        },
    },
]

EMBEDDING_PROVIDER = {
    "base_url": os.getenv("EMBEDDING_BASE_URL", "https://open.bigmodel.cn/api/paas/v4"),
    "api_key": os.getenv("EMBEDDING_API_KEY", os.getenv("ZHIPU_API_KEY", "")),
    "model": os.getenv("EMBEDDING_MODEL", "embedding-3"),
    "auth_type": "bearer",
}


def _load_settings_file():
    """从 settings.json 加载用户保存的配置（key 解混淆），完全替换 PROVIDERS"""
    global PROVIDERS, EMBEDDING_PROVIDER
    if not SETTINGS_FILE.exists():
        return
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        with _config_lock:
            if "providers" in data and isinstance(data["providers"], list):
                PROVIDERS.clear()
                for p in data["providers"]:
                    if p.get("base_url") and isinstance(p.get("models"), dict):
                        PROVIDERS.append({
                            "name": p.get("name", "自定义"),
                            "base_url": p["base_url"],
                            "api_key": _decrypt_key(p.get("api_key", "")),
                            "auth_type": p.get("auth_type", "bearer"),
                            "models": p["models"],
                        })
            if "embedding" in data:
                emb = data["embedding"]
                if emb.get("base_url"):
                    EMBEDDING_PROVIDER["base_url"] = emb["base_url"]
                if emb.get("api_key"):
                    EMBEDDING_PROVIDER["api_key"] = _decrypt_key(emb["api_key"])
                if emb.get("model"):
                    EMBEDDING_PROVIDER["model"] = emb["model"]
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.warning(f"加载 settings.json 失败: {e}，使用 .env 默认配置")


def save_settings(providers_data: list, embedding_data: dict):
    """保存配置到 settings.json（key 混淆存储），运行时保持明文"""
    global PROVIDERS, EMBEDDING_PROVIDER
    new_providers = []
    old_key_map = {p["name"]: p.get("api_key", "") for p in PROVIDERS}
    for p in providers_data:
        if not p.get("base_url") or not isinstance(p.get("models"), dict):
            continue
        key = p.get("api_key") or old_key_map.get(p.get("name", ""), "")
        new_providers.append({
            "name": p.get("name", "自定义"),
            "base_url": p["base_url"],
            "api_key": key,
            "auth_type": p.get("auth_type", "bearer"),
            "models": p["models"],
        })
    # 写文件时 key 做混淆
    file_providers = []
    for p in new_providers:
        file_providers.append({
            "name": p["name"],
            "base_url": p["base_url"],
            "api_key": _encrypt_key(p["api_key"]),
            "auth_type": p["auth_type"],
            "models": p["models"],
        })
    emb_key = embedding_data.get("api_key") or EMBEDDING_PROVIDER.get("api_key", "")
    payload = {"providers": file_providers, "embedding": {
        "base_url": embedding_data.get("base_url", EMBEDDING_PROVIDER["base_url"]),
        "api_key": _encrypt_key(emb_key),
        "model": embedding_data.get("model", EMBEDDING_PROVIDER["model"]),
    }}
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    with _config_lock:
        PROVIDERS.clear()
        PROVIDERS.extend(new_providers)
        EMBEDDING_PROVIDER["base_url"] = payload["embedding"]["base_url"]
        EMBEDDING_PROVIDER["api_key"] = emb_key
        EMBEDDING_PROVIDER["model"] = payload["embedding"]["model"]


def get_settings_snapshot() -> dict:
    """返回当前配置的快照（key 脱敏，不暴露明文）"""
    providers_safe = []
    for p in PROVIDERS:
        key = p.get("api_key", "")
        masked = key[:4] + "****" + key[-4:] if len(key) > 8 else ("****" if key else "")
        providers_safe.append({
            "name": p["name"],
            "base_url": p["base_url"],
            "api_key_masked": masked,
            "auth_type": p.get("auth_type", "bearer"),
            "models": p.get("models", {}),
        })
    emb_key = EMBEDDING_PROVIDER.get("api_key", "")
    emb_masked = emb_key[:4] + "****" + emb_key[-4:] if len(emb_key) > 8 else ("****" if emb_key else "")
    return {
        "providers": providers_safe,
        "embedding": {
            "base_url": EMBEDDING_PROVIDER["base_url"],
            "api_key_masked": emb_masked,
            "model": EMBEDDING_PROVIDER["model"],
        },
    }


# 启动时加载用户保存的配置
_load_settings_file()


def get_all_model_choices() -> dict:
    """返回所有可用模型（只返回有 api_key 的 provider）
    格式: { 'model_id': {'provider', 'base_url', 'api_key', 'api_model', 'label', 'tag'} }
    """
    choices = {}
    for p in PROVIDERS:
        if not p["api_key"]:
            continue
        for model_id, model_info in p.get("models", {}).items():
            # 兼容旧格式（纯字符串）和新格式（字典）
            if isinstance(model_info, str):
                api_model, label, tag = model_info, model_id, ""
            else:
                api_model = model_info.get("api_model", model_id)
                label = model_info.get("label", model_id)
                tag = model_info.get("tag", "")
            choices[model_id] = {
                "provider": p["name"],
                "base_url": p["base_url"],
                "api_key": p["api_key"],
                "api_model": api_model,
                "label": label,
                "tag": tag,
                "auth_type": p.get("auth_type", "bearer"),
            }
    return choices


def get_model_config(model_name: str) -> dict | None:
    """按前端 model_id 查找模型配置"""
    return get_all_model_choices().get(model_name)
