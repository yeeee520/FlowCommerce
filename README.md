<p align="center">
  <img src="static/icons/A_kawaii_whale_app_icon_design_2026-07-03T08-25-11.png" alt="FlowCommerce" width="120" height="120">
</p>

<h1 align="center">FlowCommerce</h1>

<p align="center">
  <b>电商 AI Agent 体系</b> &mdash; 融合 RAG 知识检索、多 Agent 编排、智能客服与数据中台
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.110+-green.svg" alt="FastAPI">
  <img src="https://img.shields.io/badge/chromadb-0.5+-orange.svg" alt="ChromaDB">
  <img src="https://img.shields.io/badge/license-MIT-yellow.svg" alt="License">
</p>

---

## 目录

- [项目概览](#项目概览)
- [系统架构](#系统架构)
- [模块介绍](#模块介绍)
- [快速开始](#快速开始)
- [技术栈](#技术栈)

---

## 项目概览

**FlowCommerce** 是一个面向电商场景的 AI Agent 服务体系，将大语言模型、RAG 检索增强生成、多 Agent 编排和数据工程串联为完整的智能服务链路。

核心能力：

- **智能客服** &mdash; 意图识别、查询改写、混合检索、LLM 生成完整对话流水线
- **多 Agent 编排** &mdash; 注册专业 Agent，按意图路由、并行调度、结果聚合
- **混合检索** &mdash; 向量语义检索 + BM25 关键词检索 + RRF 融合排序
- **数据中台** &mdash; ETL 流水线：数据清洗、分块、批量向量化、入库
- **流式对话** &mdash; SSE 流式输出，实时逐 token 响应
- **桌面应用** &mdash; PyWebView + PyInstaller 打包

---

## 系统架构

### 分层说明

| 层 | 组件 | 职责 |
|---|---|---|
| 前端 | HTML / CSS / JS | Web 界面，含多套设计主题 |
| API 层 | FastAPI + Uvicorn | 对话接口 (`/api/chat`)、数据管理接口 (`/api/data`) |
| Agent 层 | 编排器 / 客服 Agent | 意图路由、多 Agent 调度、对话流水线编排 |
| 检索层 | ChromaDB + BM25 + RRF | 混合向量检索与关键词检索 |
| 数据层 | 数据清洗 / 批量嵌入 | ETL 数据预处理与入库 |

### 调用链路

```
用户输入
  |
  v
[查询改写] --> 补全指代、扩展术语
  |
  v
[意图识别] --> 商品咨询 / 订单查询 / 售后问题 / 物流查询 / 通用问答
  |
  v
[混合检索] --> ChromaDB 向量检索 + BM25 关键词检索 + RRF 融合排序
  |
  v
[LLM 生成] --> 上下文注入 + Prompt 构建 + 流式/非流式输出
  |
  v
用户回复
```

### 数据流

```
原始 JSON 数据 --> 数据清洗 (去 HTML、去表情、标点统一)
  --> 文本分块 --> 批量向量化 --> ChromaDB 入库
  --> RAG 检索层读取 --> 客服 Agent 调用 --> 用户
```

---

## 模块介绍

### Agent 编排器 (agent_cluster)

编排器管理多个专业 Agent 的生命周期，支持中文意图别名映射与并行分发。

```python
from agent_cluster.orchestrator import Orchestrator

orchestrator = Orchestrator()
orchestrator.register_agent("customer_service", handler, ["product_inquiry"])
result = await orchestrator.dispatch("product_inquiry", {"message": "..."})
```

### 智能客服 Agent (customer_service)

| 文件 | 职责 |
|------|------|
| agent.py | 主 Agent，编排查询改写、意图识别、检索、生成的完整流水线 |
| prompts.py | Prompt 模板管理，按意图类别定制 system prompt |
| stream_handler.py | SSE 流式事件处理器 |

### RAG 知识库 (rag)

| 组件 | 文件 | 说明 |
|------|------|------|
| 知识库管理 | knowledge_base.py | ChromaDB collection 封装，增删改查 |
| 混合检索器 | retriever.py | 向量检索 + BM25 + RRF 三阶段融合 |
| 查询改写 | query_rewriter.py | LLM 驱动的查询改写，补全指代、优化措辞 |

### 数据中台 (data_platform)

| 组件 | 文件 | 说明 |
|------|------|------|
| ETL 流水线 | pipeline.py | 串联清洗、分块、向量化、入库 |
| 数据清洗 | cleaner.py | HTML 去除、Emoji 过滤、标点统一、空白规范化 |
| 批量嵌入 | batch_embedder.py | 批量向量化并写入 ChromaDB |

### API 服务 (api)

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/chat/send` | POST | 对话消息，支持 `stream=true` 开启 SSE 流式 |
| `/api/data/upload` | POST | 上传 JSON 数据文件触发 ETL |
| `/api/data/search` | POST | 混合检索知识库 |
| `/api/data/stats` | GET | 知识库统计信息 |
| `/api/data/documents/{id}` | DELETE | 删除指定文档 |
| `/health` | GET | 系统健康检查 |

---

## 快速开始

### 1. 安装

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. 配置

```bash
cp .env.example .env
```

编辑 `.env` 填入 API Key：

```ini
OPENAI_API_KEY=sk-your-key-here
OPENAI_API_BASE=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
```

### 3. 启动

```bash
python start.py
```

访问 [http://localhost:8000](http://localhost:8000) 或 API 文档 [http://localhost:8000/docs](http://localhost:8000/docs)

### 4. 对话

```bash
curl http://localhost:8000/api/chat/send \
  -H "Content-Type: application/json" \
  -d '{"message": "这款防晒霜适合敏感肌吗？", "stream": false}'
```

### 5. 桌面应用

```bash
pip install pyinstaller
build_desktop.bat
```

构建产物位于 `dist/EcomAIAgent.exe`

---

## 技术栈

| 组件 | 技术 |
|------|------|
| 运行时 | Python 3.11+ |
| 后端框架 | FastAPI + Uvicorn |
| RAG 向量库 | ChromaDB |
| 混合检索 | rank-bm25 + jieba 中文分词 |
| LLM 集成 | LangChain + OpenAI 兼容 API |
| 流式传输 | SSE (Server-Sent Events) |
| 前端 | 原生 HTML / CSS / JS |
| 桌面应用 | PyWebView |
| 打包分发 | PyInstaller |

---

MIT License

<p align="center">Built with love for e-commerce AI</p>
