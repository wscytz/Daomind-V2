# 道心 · Dao-Mind

> **以古人之智，解今人之忧**
> AI-powered mental health companion, grounded in Eastern philosophy.

[English](#english) | [中文](#中文)

---

## English

### What is Dao-Mind?

Dao-Mind is an open-source AI mental health counseling assistant that combines classical Chinese wisdom with modern psychology. It offers three **persona modes**:

| Mode | Description | Knowledge Base |
|------|------------|---------------|
| **Standard** | General psychological counseling | — |
| **Poetry Therapy (诗疗)** | Bai Juyi poetry-guided emotional healing | 100+ Bai Juyi poems |
| **Daoist Therapy (道疗)** | Dao De Jing + Zhuangzi + Lunyu guided practice | 道德经, 庄子, 论语, 道家认知疗法 |

### Features

- **Local-first**: All wisdom knowledge is stored locally (NPZ vector database)
- **Privacy-first**: Conversations encrypted with AES-GCM in localStorage
- **RAG-powered**: BM25 + vector hybrid search with RRF fusion — no third-party RAG SDK
- **Extensible**: Add any OpenAI-compatible API provider (Zhipu, Doubao, Ollama, DeepSeek...)
- **Cross-platform**: Desktop (Windows/macOS/Linux) + mobile-ready architecture

### Quick Start

#### Option A: Pre-built Executable (Recommended)

Download the latest `.exe` from [Releases](https://github.com/wscytz/dao-mind/releases).

#### Option B: Run from Source

```bash
# 1. Clone
git clone https://github.com/wscytz/dao-mind.git
cd dao-mind

# 2. Install backend dependencies
pip install -r requirements.txt

# 3. Install frontend dependencies
cd frontend && npm install && npm run build && cd ..

# 4. Copy frontend to backend static
cp -r frontend/dist backend/static/

# 5. Configure API keys
cp .env.example .env
# Edit .env and add your API key

# 6. Run
cd backend && python -m uvicorn main:app --reload
```

Open `http://localhost:8001` in your browser.

#### Option C: Fully Local with Ollama

```bash
# 1. Install Ollama (https://ollama.com)
ollama pull qwen2.5:7b
ollama pull bge-m3

# 2. Set environment variables
echo "OLLAMA_BASE_URL=http://localhost:11434/v1" >> .env
echo "OLLAMA_API_KEY=ollama" >> .env
echo "OLLAMA_AUTH_TYPE=none" >> .env

# 3. Select "Ollama (本地)" provider in the Settings page
```

### Architecture

```
dao-mind/
├── backend/
│   ├── main.py              # FastAPI entry point
│   ├── config.py            # Provider & settings management
│   ├── prompts.py           # System prompts per persona
│   ├── api/                 # API routes
│   │   ├── chat.py          # Non-streaming chat
│   │   ├── stream.py        # SSE streaming chat
│   │   ├── rag_counseling.py # RAG-enhanced counseling
│   │   └── wisdom.py         # 24 solar terms + daily wisdom card
│   ├── clients/             # API client layer
│   │   ├── unified.py       # Provider router
│   │   └── openai_compat.py # OpenAI-compatible client
│   ├── rag/                # RAG pipeline (zero-dependency)
│   │   ├── base.py         # NPZ vector retrieval
│   │   ├── hybrid.py        # BM25 + vector RRF fusion
│   │   ├── providers.py     # 6 knowledge providers
│   │   └── service.py       # Unified RAG service
│   └── services/
│       ├── counseling.py     # Persona-driven counseling
│       ├── emotion.py        # Keyword-based emotion detection
│       └── solar_term.py    # 24 solar terms
├── frontend/
│   ├── src/
│   │   ├── App.vue          # Main layout
│   │   ├── stores/chat.js  # Pinia store (AES-GCM encrypted)
│   │   └── components/      # Vue components
│   └── dist/               # Built frontend
├── data/rag_databases/      # Local NPZ vector databases
│   ├── daodejing_embeddings.npz
│   ├── zhuangzi_embeddings.npz
│   └── baijuyi_poems/      # Bai Juyi poetry collection
└── tests/                   # pytest test suite
```

### Technology Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Vue 3, Pinia, Vite 5, Axios |
| Backend | FastAPI, uvicorn, Python 3.11+ |
| Vector DB | NPZ (local), custom BM25 + cosine |
| LLM | OpenAI-compatible (Zhipu, Doubao, Ollama...) |
| Embedding | OpenAI-compatible (Zhipu, Ollama bge-m3...) |
| Packaging | PyInstaller (desktop exe) |
| Testing | pytest, httpx |

### Configuration

#### Environment Variables (.env)

```env
# LLM Provider
ZHIPU_API_KEY=your_key_here

# Embedding Provider (defaults to Zhipu)
EMBEDDING_API_KEY=your_key_here
EMBEDDING_MODEL=embedding-3

# Optional: Use Ollama (fully local)
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_API_KEY=ollama
OLLAMA_AUTH_TYPE=none

# Server
HOST=127.0.0.1
PORT=8001
```

#### API Provider Settings (in-app)

After starting, open **Settings** and add any OpenAI-compatible provider:

| Provider | base_url | auth_type |
|----------|----------|-----------|
| Ollama | `http://localhost:11434/v1` | none |
| DeepSeek | `https://api.deepseek.com/v1` | bearer |
| Groq | `https://api.groq.com/openai/v1` | bearer |
| Together | `https://api.together.xyz/v1` | bearer |

### Developing

```bash
# Backend development
cd backend
python -m uvicorn main:app --reload

# Frontend development (proxies /api to backend)
cd frontend
npm run dev

# Run tests
pytest tests/ -v
```

### License

MIT License — free for personal and commercial use.

---

## 中文

### 什么是道心？

道心是一款开源 AI 心理健康陪伴助手，以中华古典哲学为底蕴，提供三种**人格模式**：

| 模式 | 说明 | 知识库 |
|------|------|--------|
| **心理咨询** | 通用对话，情感支持 | 无 |
| **诗疗** | 白居易诗歌引导情绪疗愈 | 白居易诗集（核心+扩展）|
| **道疗** | 道德经·庄子·论语·道家认知疗法 | 道德经, 庄子, 论语, 道家认知疗法 |

### 核心特性

- **本地优先**：6个知识库全部本地存储（NPZ 向量库）
- **隐私保护**：对话用 AES-GCM 加密存储在本地
- **零第三方依赖**：RAG 管道自研，BM25 + 向量混合检索，RRF 融合
- **全开放接入**：支持任意 OpenAI 兼容 API（智谱/豆包/Ollama/DeepSeek...）
- **开箱即用**：下载 exe 双击运行

### 一分钟上手（完全本地）

```bash
# 1. 安装 Ollama
winget install Ollama.Ollama

# 2. 下载模型
ollama pull qwen2.5:7b
ollama pull bge-m3

# 3. 下载道心
# https://github.com/wscytz/dao-mind/releases

# 4. 启动后，在「设置」中选择「Ollama（本地）」
# 填写 http://localhost:11434/v1
```

### 立即开始

[下载Releases](https://github.com/wscytz/dao-mind/releases) | [查看文档](https://github.com/wscytz/dao-mind/wiki) | [提交Issue](https://github.com/wscytz/dao-mind/issues)

[![Build](https://github.com/wscytz/dao-mind/actions/workflows/build.yml/badge.svg)](https://github.com/wscytz/dao-mind/actions)
