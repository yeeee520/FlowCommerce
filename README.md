<p align="center">
  <img src="static/icons/A_kawaii_whale_app_icon_design_2026-07-03T08-25-11.png" alt="FlowCommerce" width="120" height="120">
</p>

<h1 align="center">FlowCommerce</h1>

<p align="center">
  <b>电商 AI Agent 体系</b> &#x2014; 融合 RAG 知识检索、多 Agent 编排、智能客服与数据中台的端到端解决方案
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.110+-green.svg" alt="FastAPI">
  <img src="https://img.shields.io/badge/chromadb-0.5+-orange.svg" alt="ChromaDB">
  <img src="https://img.shields.io/badge/license-MIT-yellow.svg" alt="License">
</p>

&#x2014;

## 目录

- [项目概览](#项目概览)
- [系统架构](#系统架构)
- [模块介绍](#模块介绍)
- [快速开始](#快速开始)
- [技术栈](#技术栈)

&#x2014;

## 项目概览

**FlowCommerce** 是一个面向电商场景的 AI Agent 体系，将大语言模型、RAG 检索增强生成、多 Agent 编排和数据工程串联为完整的智能服务链路。

核心能力：

- **智能客服** &#x2014; 意图识别 / 查询改写 / 混合检索 / LLM 生成，完整对话流水线
- **多 Agent 编排** &#x2014; 注册专业 Agent，按意图路由、并行调度、结果聚合
- **混合检索** &#x2014; 向量语义检索 + BM25 关键词检索 + RRF 融合排序
- **数据中台** &#x2014; ETL 流水线：数据清洗 / 分块 / 批量向量化 / 入库
- **流式对话** &#x2014; SSE 流式输出，实时逐 token 响应
- **多主题前端** &#x2014; 4 套设计风格，适配不同品牌调性
- **桌面应用** &#x2014; PyWebView + PyInstaller 一键打包分发

&#x2014;

## 系统架构

`
                        Web 前端 (static/)
       极简苹果风 暗色科技风 专业商务风 Material Design
                            |
                        HTTP / SSE
                            |
                     FastAPI 后端 (api/)
              /api/chat  |  /api/data  |  /health
                            |
         +------------------+------------------+
         |                  |                  |
   Agent 编排器     智能客服 Agent       数据中台 API
  orchestator.py    CustomerAgent      DataPipeline
         |                  |                  |
         +--------+---------+---------+--------+
                  |                   |
           RAG 混合检索层 (rag/)
     向量检索 (ChromaDB) + BM25 (jieba+rank_bm25)
                RRF 融合排序
                  |
           数据中台 (data_platform/)
    数据清洗 / 文本分块 / 批量向量化 / ChromaDB 入库
`

&#x2014;

## 模块介绍

### Agent 编排器 (agent_cluster)

编排器负责管理多个专业 Agent 的生命周期。支持中文意图别名映射、单发分发和并行分发。

`python
from agent_cluster.orchestrator import Orchestrator

orchestrator = Orchestrator()
orchestrator.register_agent("customer_service", handler, ["product_inquiry"])
result = await orchestrator.dispatch("product_inquiry", {"message": "..."})
`

### 智能客服 Agent (customer_service)

完整对话流水线：查询改写 - 意图识别 - RAG 检索 - Prompt 构建 - LLM 生成

| 文件 | 职责 |
|------|------|
| agent.py | 主 Agent 类，编排流水线各环节 |
| prompts.py | Prompt 模板管理，按意图定制 |
| stream_handler.py | SSE 流式事件处理器 |

### RAG 知识库 (rag)

混合检索三阶段：

| 阶段 | 方法 | 优势 |
|------|------|------|
| 向量检索 | ChromaDB 语义相似度 | 理解语义关联 |
| BM25 检索 | jieba 分词 + rank_bm25 | 精确关键词匹配 |
| RRF 融合 | Reciprocal Rank Fusion | 兼顾语义与关键词 |

### 数据中台 (data_platform)

ETL 流水线：JSON 数据 / DataCleaner（去 HTML、去表情、标准化）/ BatchEmbedder（向量化）/ ChromaDB 入库

### API 服务 (api)

| 端点 | 方法 | 说明 |
|------|------|------|
| /api/chat/send | POST | 对话消息，支持 SSE 流式 |
| /api/data/upload | POST | 上传数据触发 ETL |
| /api/data/search | POST | 混合检索知识库 |
| /api/data/stats | GET | 知识库统计 |
| /health | GET | 健康检查 |

### Web 前端 (static)

4 套独立设计主题：极简苹果风 / 暗色科技风 / 专业商务风 / Material Design

&#x2014;

## 快速开始

### 1. 安装

`ash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
`

### 2. 配置

`ash
cp .env.example .env
`

编辑 .env 填入 API Key：

`ini
OPENAI_API_KEY=sk-your-key-here
OPENAI_API_BASE=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
`

### 3. 启动

`ash
python start.py
`

访问 http://localhost:8000 或 API 文档 http://localhost:8000/docs

### 4. 对话

`ash
curl http://localhost:8000/api/chat/send \
  -H "Content-Type: application/json" \
  -d '{"message": "这款防晒霜适合敏感肌吗？", "stream": false}'
`

### 5. 桌面应用

`ash
pip install pyinstaller
build_desktop.bat
`

构建产物位于 dist/EcomAIAgent.exe

&#x2014;

## 技术栈

| 组件 | 技术 |
|------|------|
| 运行时 | Python 3.11+ |
| 后端框架 | FastAPI + Uvicorn |
| RAG 向量库 | ChromaDB |
| 混合检索 | rank-bm25 + jieba |
| LLM 集成 | LangChain + OpenAI 兼容 API |
| 流式传输 | SSE |
| 前端 | 原生 HTML/CSS/JS |
| 桌面应用 | PyWebView |
| 打包分发 | PyInstaller |

&#x2014;

MIT License

<p align="center">Built with love for e-commerce AI</p>