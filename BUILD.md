# Dao-Mind v2 构建指南

## 项目结构

```
daomind/
├── backend/          # FastAPI 后端（Python 3.11+）
│   ├── main.py       # 入口
│   ├── config.py     # 配置（环境变量 + settings.json）
│   ├── api/          # REST 端点
│   ├── clients/      # OpenAI 兼容 API 客户端
│   ├── rag/          # NPZ RAG 检索管线
│   └── services/     # 咨询 + 情绪检测
├── frontend/         # Vue3 前端
│   └── src/
│       ├── App.vue   # 主布局
│       ├── components/
│       ├── stores/   # Pinia 状态管理
│       └── styles/   # CSS 设计系统
├── data/             # RAG 数据库（6 个 NPZ 知识库）
└── build.bat         # 一键打包脚本
```

## 开发环境

### 后端

```bash
cd backend
pip install -r ../requirements.txt
python -m uvicorn main:app --reload --port 8001
```

### 前端

```bash
cd frontend
npm install
npm run dev    # Vite 开发服务器 :5173，自动代理 /api 到 :8001
```

### 配置 API Key

- 复制 `.env.example` 为 `.env`，填入 API Key
- 或者在应用内「设置」页面直接配置（保存到 `settings.json`）

## 打包分发

### 便携版

```bash
build.bat
# 产出 dist/daomind/ — 含所有源码和依赖清单
# 复制到目标机器，pip install 后 python -m uvicorn 启动
```

### 单文件 exe

```bash
cd backend
pip install pyinstaller
python -m PyInstaller --onefile --console --name "DaoMind" ^
  --add-data "../frontend/dist;frontend/dist" ^
  --add-data "../data/rag_databases;data/rag_databases" ^
  --hidden-import uvicorn --hidden-import numpy ^
  --clean --noconfirm launcher.py
# 产出 dist/DaoMind.exe (~58MB)，双击即用
```

## 测试

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

## 兼容性

- 所有 API 兼容 OpenAI `/v1/chat/completions` 格式
- 新增云商只需在 `config.py` 的 PROVIDERS 列表加一条
- NPZ 双格式兼容（`data` 键 + `embedding_texts` 键）
- 支持 PyInstaller 打包后的 `sys._MEIPASS` 路径
