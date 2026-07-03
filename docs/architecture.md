# 电商 AI Agent 体系 — 架构设计文档

> **版本**：v0.1.0 | **日期**：2026年7月 | **状态**：Demo / 核心已实现，规划扩展中

---

## 1. 项目概述

### 1.1 项目背景

在电商场景中，传统人工客服面临效率低、响应慢、知识覆盖不全面等问题。同时，电商运营（宣传图、宣传视频、文案）依赖大量人工制作，成本高昂。AI Agent 体系的引入，旨在通过检索增强生成（RAG）、多 Agent 协作、多模态内容生成等技术，构建一个从数据清洗到智能服务、从内容生产到素材管理的全链路智能化平台。

本项目的核心命题是：**数据中台作为基础设施，驱动上层 AI 应用（智能客服、运营 Agent、素材中心等）的闭环运转**。

### 1.2 核心目标

| 目标 | 说明 |
|------|------|
| **智能客服替代人工** | 通过 RAG + LLM 实现商品咨询、订单查询、售后处理的自动化，降低客服人力成本 |
| **数据驱动的知识管理** | 构建完整 ETL 管道，将原始数据清洗后向量化注入知识库，形成持续迭代的数据闭环 |
| **运营自动化** | 通过运营 Agent 自动生成宣传素材（图片/视频/文案），经素材中心与商品关联后回流知识库 |
| **多模态支持** | 从纯文本扩展到图片、视频的多模态检索与生成能力 |
| **Agent 集群治理** | 随着 Agent 增多，通过 MCP 协议和编排器实现统一管理和边界控制 |

### 1.3 技术亮点

- **混合检索（RRF）**：向量语义检索 + BM25 关键词检索 + Reciprocal Rank Fusion 重排序，兼顾语义理解和精确匹配
- **查询改写**：基于多轮对话上下文，自动扩展同义词、提取关键词，提升检索召回率
- **SSE 流式输出**：Server-Sent Events 协议实现打字机效果的实时对话体验
- **Agent 编排**：Orchestrator 模式管理多 Agent 的注册、路由、并行执行与结果聚合
- **模块化设计**：各子系统独立可替换，数据中台、RAG、客服、Agent 集群边界清晰

---

## 2. 系统架构总览

### 2.1 整体架构图

```
┌──────────────────────────────────────────────────────────────────────┐
│                         前端展示层 (static/)                           │
│                  index.html + style.css + app.js                     │
│              原生 HTML/CSS/JS — 零框架依赖，轻量级部署                   │
└─────────────────────────────┬────────────────────────────────────────┘
                              │ HTTP REST / SSE (text/event-stream)
┌─────────────────────────────▼────────────────────────────────────────┐
│                       API 网关层 (api/)                               │
│                                                                       │
│   POST /api/chat/send  ─── 智能客服对话（支持 SSE 流式）               │
│   POST /api/data/upload ─── 数据文件上传，触发 ETL 流水线             │
│   POST /api/data/search ─── 知识库混合检索                            │
│   GET  /api/data/stats  ─── 知识库统计信息                            │
│   DELETE /api/data/documents/{id} ─── 删除文档                        │
│   GET  /health           ─── 全局健康检查                             │
└─────────────────────────────┬────────────────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         │                    │                    │
┌────────▼────────┐  ┌────────▼────────┐  ┌────────▼────────┐
│ 智能客服层       │  │ RAG 知识层       │  │ 数据中台层       │
│ customer_       │  │ rag/             │  │ data_platform/   │
│ service/        │  │                  │  │                  │
│                 │  │ ┌──────────────┐ │  │ ┌──────────────┐ │
│ ┌─────────────┐ │  │ │ KnowledgeBase│ │  │ │ DataCleaner  │ │
│ │CustomerAgent│ │  │ │ (ChromaDB)   │ │  │ │ (清洗+标准化) │ │
│ │ 意图识别     │ │  │ └──────┬───────┘ │  │ └──────┬───────┘ │
│ │ 对话编排     │ │  │        │         │  │        │         │
│ └──────┬──────┘ │  │ ┌──────▼───────┐ │  │ ┌──────▼───────┐ │
│        │        │  │ │  Retriever   │ │  │ │ DataPipeline │ │
│ ┌──────▼──────┐ │  │ │  混合检索+RRF │◄─┼──┤ │ (ETL编排)    │ │
│ │PromptManager│ │  │ └──────┬───────┘ │  │ └──────┬───────┘ │
│ │ 模板管理     │ │  │        │         │  │        │         │
│ └──────┬──────┘ │  │ ┌──────▼───────┐ │  │ ┌──────▼───────┐ │
│        │        │  │ │QueryRewriter │ │  │ │BatchEmbedder │ │
│ ┌──────▼──────┐ │  │ │ 查询改写+扩展 │ │  │ │ 批量向量化    │ │
│ │StreamHandler│ │  │ └──────────────┘ │  │ └──────────────┘ │
│ │ SSE流式输出  │ │  │                  │  │                  │
│ └─────────────┘ │  └──────────────────┘  └──────────────────┘
└────────┬────────┘
         │
┌────────▼────────────────────────────────────────────────────────────┐
│                      Agent 集群层 (agent_cluster/)                    │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    Orchestrator (编排器)                      │    │
│  │                                                              │    │
│  │  Agent 注册 ──► 意图路由 ──► 任务分发 ──► 并行执行 ──► 结果聚合 │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                              │                                       │
│     ┌──────────┬──────────┬──────────┬──────────┬──────────┐       │
│     │ 商品Agent │ 订单Agent │ 售后Agent │ 运营Agent │ 直播Agent │ ...  │
│     └──────────┴──────────┴──────────┴──────────┴──────────┘       │
└──────────────────────────────────────────────────────────────────────┘

                              ▼
┌──────────────────────────────────────────────────────────────────────┐
│                         数据存储层                                    │
│                                                                       │
│  ┌──────────────────┐    ┌──────────────────┐                        │
│  │    ChromaDB      │    │     SQLite       │                        │
│  │  (向量数据库)     │    │  (关系型数据库)   │                        │
│  │                  │    │                  │                        │
│  │  文本嵌入向量     │    │  CleaningLog     │                        │
│  │  元数据存储       │    │  MaterialAssoc   │                        │
│  └──────────────────┘    └──────────────────┘                        │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.2 三层架构设计

本系统采用清晰的三层架构，各层职责分明、依赖方向自上而下：

```
┌──────────────────────────────────────────────────┐
│                 Agent 应用层                       │
│  customer_service / agent_cluster / (规划中模块)   │
│  业务逻辑编排、意图识别、多Agent协作、流式输出      │
├──────────────────────────────────────────────────┤
│                 RAG 知识层                         │
│  rag / (AI素材中心)                               │
│  知识库管理、混合检索、查询改写、向量化存储         │
├──────────────────────────────────────────────────┤
│                 数据中台层                          │
│  data_platform                                    │
│  数据接入、清洗、ETL管道、批量向量化                │
└──────────────────────────────────────────────────┘
```

**设计理念**：数据中台是整个体系的核心基础设施。所有上层应用（客服、运营、素材管理）的数据都经由数据中台的清洗和向量化管道注入知识库，形成"数据生产 → 清洗加工 → 向量化入库 → 检索消费"的闭环。

### 2.3 技术栈选型说明

| 层级 | 技术选型 | 选型理由 |
|------|---------|---------|
| **Web 框架** | FastAPI + Uvicorn | 原生异步支持（async/await），自动生成 OpenAPI 文档，性能优于 Flask/Django |
| **向量数据库** | ChromaDB | 轻量级、嵌入式部署，无需独立服务；原生支持元数据过滤；适合 Demo 阶段快速验证 |
| **关系数据库** | SQLite + SQLAlchemy | 零配置、文件级部署；SQLAlchemy ORM 提供数据库无关的抽象层，未来可平滑迁移至 PostgreSQL |
| **LLM 框架** | LangChain + LangChain-OpenAI | 业界标准的 LLM 应用框架，提供 Chain/Agent/Tool 抽象；社区活跃，生态丰富 |
| **嵌入模型** | text-embedding-3-small | OpenAI 最新一代嵌入模型，1536 维向量，性价比高（$0.02/1M tokens） |
| **对话模型** | gpt-4o-mini | 推理能力强、成本低（$0.15/1M input tokens），适合客服场景的高频调用 |
| **关键词检索** | BM25 (rank-bm25 + jieba) | BM25 是信息检索领域经典算法，jieba 分词对中文友好；组合语义检索互补 |
| **流式输出** | SSE (sse-starlette) | 比 WebSocket 更轻量，单向推送足够；浏览器原生 EventSource 支持 |
| **前端** | 原生 HTML/CSS/JS | 零构建工具、零框架依赖；适合 Demo 快速交付；生产环境可替换为 React/Vue |

**关键权衡**：

- **ChromaDB vs Milvus/Qdrant**：ChromaDB 嵌入式部署降低运维复杂度，适合 Demo。生产环境建议迁移至 Milvus（分布式、十亿级规模）或 Qdrant（高性能、丰富过滤）。
- **SQLite vs PostgreSQL**：SQLite 无需独立服务，但并发写入能力有限。数据量增长后应迁移至 PostgreSQL。
- **SSE vs WebSocket**：客服对话场景是单向推送（服务端→客户端），SSE 足够且更简单。若未来需要双向实时通信（如语音对话），再升级为 WebSocket。

---

## 3. 七大模块详细设计

### 3.1 数据中台（已实现）— `data_platform/`

数据中台是整个体系的核心基础设施，负责原始数据的接入、清洗、加工和向量化入库。

#### 3.1.1 模块架构

```
data_platform/
├── __init__.py          # 模块导出
├── models.py            # SQLAlchemy 数据模型
├── cleaner.py           # DataCleaner 数据清洗器
├── pipeline.py          # DataPipeline ETL 编排器
└── batch_embedder.py    # BatchEmbedder 批量向量化
```

#### 3.1.2 数据模型（models.py）

**CleaningLog（数据清洗日志表）**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer (PK) | 自增主键 |
| raw_text | Text | 清洗前的原始文本 |
| cleaned_text | Text | 清洗后的文本 |
| status | String(20) | 清洗状态：pending / processing / success / failed |
| error_message | Text | 失败时的错误信息 |
| created_at | DateTime | 记录创建时间 |

**MaterialAssociation（素材-商品关联表）**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer (PK) | 自增主键 |
| material_id | String(255) | 素材唯一标识 |
| product_id | String(255) | 关联商品标识 |
| material_type | String(50) | 素材类型：image / video / audio |
| created_at | DateTime | 记录创建时间 |

#### 3.1.3 DataCleaner 数据清洗器

清洗管道包含 5 个步骤：

```
原始文本
  │
  ├── 1. HTML 标签去除    regex: <[^>]*>
  ├── 2. 表情符号去除      Unicode 范围过滤（Emoji + Symbols）
  ├── 3. 标点统一化       中文标点 → 英文标点（如 "，→", "。"→"."）
  ├── 4. 空白规范化       多个空白合并为一个空格
  └── 5. 首尾空白去除     .strip()
  │
  ▼
清洗后文本 + CleaningLog
```

**关键设计决策**：

- **标点统一化**：将中文标点映射为英文标点，原因是 LLM 对英文标点的 token 化更高效，且向量嵌入模型训练语料以英文标点为主
- **表情符号去除**：Emoji 在嵌入模型中缺乏语义表示，保留会引入噪声
- **容错设计**：单条清洗失败不阻塞批量处理，每条独立重试 MAX_RETRIES 次（默认 3 次）

**核心代码逻辑**：

```python
def clean(self, raw_text: str) -> tuple[str, CleaningLog]:
    log_entry = CleaningLog(raw_text=raw_text, status="pending")
    try:
        text = raw_text
        text = self._HTML_TAG_PATTERN.sub("", text)       # 1. 去HTML
        text = self._EMOJI_PATTERN.sub("", text)           # 2. 去Emoji
        text = text.translate(self._PUNCTUATION_MAP)       # 3. 统一标点
        text = self._MULTI_SPACE_PATTERN.sub(" ", text)    # 4. 规范化空白
        text = text.strip()                                # 5. 去首尾空白
        log_entry.cleaned_text = text
        log_entry.status = "success"
        return text, log_entry
    except Exception as exc:
        log_entry.status = "failed"
        log_entry.error_message = str(exc)
        return raw_text, log_entry
```

#### 3.1.4 DataPipeline ETL 编排器

ETL 流水线串联清洗 → 分块 → 向量化三个步骤：

```
数据源 (JSON/CSV)
    │
    ▼
[加载] → 读取文件，解析为文本列表
    │
    ▼
[清洗] → DataCleaner.batch_clean() → 每条文本独立清洗+重试
    │
    ▼
[分块] → 按 CHUNK_SIZE(512) 切分，CHUNK_OVERLAP(64) 重叠
    │
    ▼
[向量化] → BatchEmbedder.embed_and_store() → 写入 ChromaDB
    │
    ▼
结果: {"total": N, "success": M, "failed": K, "skipped": J}
```

**设计要点**：

- **进度回调**：`on_progress(current, total)` 参数支持实时进度上报，便于前端展示处理进度条
- **断点续跑**：预留接口支持跳过已处理的记录，避免重复计算嵌入成本
- **批量处理**：每批 BATCH_SIZE(100) 条调用嵌入 API，平衡吞吐量与 API 速率限制

#### 3.1.5 BatchEmbedder 批量向量化

- 调用嵌入模型（text-embedding-3-small）生成 1536 维向量
- 批量写入 ChromaDB collection
- 支持增量更新和幂等写入（相同 ID 覆盖更新）
- 失败重试 + 速率限制

---

### 3.2 AI 客服系统 + RAG（已实现）

#### 3.2.1 模块架构

```
┌─────────────────────────────────────────────────┐
│              customer_service/                    │
│                                                   │
│  CustomerAgent ──► 对话编排（意图→检索→生成）      │
│  PromptManager ──► Prompt 模板管理（按场景选择）   │
│  StreamHandler ──► SSE 流式输出处理               │
└──────────────────────┬──────────────────────────┘
                       │ 依赖
┌──────────────────────▼──────────────────────────┐
│                   rag/                            │
│                                                   │
│  KnowledgeBase ──► ChromaDB CRUD 管理             │
│  Retriever     ──► 混合检索（向量 + BM25 + RRF）  │
│  QueryRewriter ──► 查询改写、同义词扩展            │
└─────────────────────────────────────────────────┘
```

#### 3.2.2 CustomerAgent 对话编排

对话流水线分为 5 个阶段：

```
用户消息 → CustomerAgent.chat()
           │
           ├── 1. identify_intent()     意图识别
           │      ├── "product_inquiry"  商品咨询
           │      ├── "order_status"     订单查询
           │      └── "after_sales"      售后处理
           │
           ├── 2. QueryRewriter.rewrite()  查询改写
           │      ├── 同义词扩展（"便宜" → "性价比"）
           │      ├── 关键词提取（从长句中提取核心检索词）
           │      └── 上下文融合（将历史对话信息融入查询）
           │
           ├── 3. Retriever.retrieve()    混合检索
           │      ├── 向量语义检索（ChromaDB）
           │      ├── BM25 关键词检索（jieba 分词）
           │      └── RRF 融合排序
           │
           ├── 4. PromptManager.build()   构建 Prompt
           │      ├── 根据意图选择 System Prompt
           │      ├── 注入检索到的上下文文档
           │      └── 拼接对话历史
           │
           └── 5. LLM 生成 → StreamHandler → SSE → 前端
```

**接口设计**：

```python
class CustomerAgent:
    async def chat(
        self,
        message: str,
        history: Optional[list[dict[str, str]]] = None,
        stream: bool = False,
    ) -> str | AsyncGenerator[str, None]: ...
```

返回值类型取决于 `stream` 参数：`False` 返回完整字符串，`True` 返回异步生成器（逐 token 产出）。这种多态返回设计让调用方可以灵活选择模式。

#### 3.2.3 PromptManager 模板管理

按意图类型提供不同的 System Prompt：

| 意图标签 | 场景 | Prompt 特点 |
|---------|------|------------|
| `product_inquiry` | 商品咨询 | 强调准确性、引用商品规格参数 |
| `order_status` | 订单查询 | 引导用户提供订单号，结构化输出状态 |
| `after_sales` | 售后处理 | 温和共情的语气，引导退换货流程 |
| `general` | 通用对话 | 友好专业的客服语气 |

#### 3.2.4 StreamHandler SSE 流式输出

```python
class StreamHandler:
    async def to_sse(
        self,
        generator: AsyncGenerator[str, None],
        event_type: str = "message",
    ) -> AsyncGenerator[str, None]:
        """
        将 LLM token 流转换为 SSE 格式:
        data: {"type": "message", "content": "token_text"}\n\n
        ...
        data: {"type": "done"}\n\n
        """
```

SSE 协议细节：
- Content-Type: `text/event-stream`
- 每个事件以 `data: ` 开头，以 `\n\n` 结尾
- 事件类型：`message`（文本 token）、`error`（错误信息）、`done`（流结束）
- 前端通过 `EventSource` 或 `fetch` + `ReadableStream` 消费

---

### 3.3 运营 Agent（规划中）

**业务场景**：传统电商运营需要设计师制作宣传图、剪辑师制作视频、文案撰写推广文案，人力成本高、产出周期长。

**设计方案**：

```
运营需求（商品ID + 推广目标）
        │
        ▼
┌───────────────────────────────────┐
│          运营 Agent                │
│                                   │
│  ┌─────────┐ ┌─────────┐ ┌──────┐│
│  │ 文生图   │ │ 文生视频 │ │ 文案 ││
│  │ DALL-E/ │ │ Sora/   │ │ LLM  ││
│  │ SD      │ │ Runway  │ │ 生成 ││
│  └────┬────┘ └────┬────┘ └──┬───┘│
│       │          │         │     │
│       ▼          ▼         ▼     │
│  ┌─────────────────────────────┐ │
│  │        生成结果              │ │
│  │  (图片/视频/文案文件)        │ │
│  └─────────────┬───────────────┘ │
└────────────────┼─────────────────┘
                 │
                 ▼
        ┌────────────────┐
        │  AI 素材中心     │  ← 自动注入素材中心
        │  (素材-商品关联)  │
        └────────────────┘
```

**技术选型建议**：

| 能力 | 推荐方案 | 备选方案 |
|------|---------|---------|
| 文生图 | DALL-E 3 API | Stable Diffusion (自部署) |
| 图生视频 | Runway Gen-3 | Stable Video Diffusion |
| 文案生成 | gpt-4o / Claude 3.5 Sonnet | 微调的领域模型 |

**关键设计考虑**：

- **Prompt 模板化**：不同商品类目（服装、3C、食品）应有不同的生成 Prompt 模板
- **品牌一致性**：生成的素材需符合品牌视觉规范（色调、Logo位置、字体），可通过 ControlNet 等条件控制技术实现
- **人工审核环节**：生成内容需要人工审核后才能发布，避免 AI 幻觉导致的不合规内容

---

### 3.4 AI 素材中心（规划中）

**业务场景**：运营 Agent 生成的素材、直播切片 Agent 提取的视频片段，需要统一管理和与商品关联，才能被客服系统和知识库消费。

**设计方案**：

```
AI 素材中心
├── 素材存储层
│   ├── 对象存储 (OSS/S3) — 图片、视频、音频文件
│   └── 元数据库 — 素材标签、商品关联、使用记录
│
├── 向量化层
│   ├── CLIP 模型 — 图片/视频的语义向量化
│   └── 文本嵌入 — 素材描述文本的向量化
│
└── 检索层
    ├── 多模态检索 — 以图搜图、以文搜图
    └── 商品关联检索 — 按商品ID检索所有关联素材
```

**数据流**：

```
运营Agent/直播Agent → 生成素材
        │
        ▼
  [素材上传] → 对象存储
        │
        ▼
  [商品关联] → MaterialAssociation 表
        │
        ▼
  [向量化] → CLIP + text-embedding
        │
        ▼
  [注入数据中台] → 清洗 → 向量化 → ChromaDB
        │
        ▼
  [AI客服可检索] → 多模态知识库
```

**技术选型建议**：

| 组件 | 推荐方案 | 说明 |
|------|---------|------|
| 对象存储 | MinIO (自部署) / 阿里云 OSS | 兼容 S3 API，便于迁移 |
| 图像向量化 | OpenAI CLIP / Chinese-CLIP | 中文电商场景建议 Chinese-CLIP |
| 元数据库 | PostgreSQL + pgvector | 支持向量检索的关系型数据库 |

---

### 3.5 直播切片 Agent（规划中）

**业务场景**：电商直播中，主播会在不同时段介绍不同产品。将直播内容自动识别并切片为多个带标签的短视频，可作为商品详情页的素材。

**设计方案**：

```
直播视频流
    │
    ▼
┌─────────────────────────────────┐
│       直播切片 Agent             │
│                                 │
│  1. ASR 语音转文字               │
│     └── Whisper / 阿里云ASR     │
│                                 │
│  2. 内容理解                     │
│     ├── 产品名称识别 (NER)       │
│     ├── 产品特点提取             │
│     └── 时段标记                 │
│                                 │
│  3. 精彩片段提取                 │
│     ├── 产品介绍时段定位         │
│     ├── 高潮/亮点检测            │
│     └── 视频裁剪 (FFmpeg)       │
│                                 │
│  4. 标签生成                     │
│     ├── 产品标签                 │
│     ├── 场景标签                 │
│     └── 情绪标签                 │
└─────────────┬───────────────────┘
              │
              ▼
     切片视频 + 标签 → AI素材中心
```

**技术选型建议**：

| 组件 | 推荐方案 | 说明 |
|------|---------|------|
| ASR | Whisper large-v3 | 开源、多语言支持、中文识别准确率高 |
| NER | 微调的 BERT-CRF | 针对电商产品名称的命名实体识别 |
| 视频处理 | FFmpeg | 业界标准的视频处理工具 |
| 亮点检测 | 音频能量分析 + 语义变化检测 | 结合声学和语义特征 |

---

### 3.6 模型微调（规划中）

**业务场景**：通用大模型在电商客服场景下可能存在回复不够"像真人客服"的问题，需要通过领域数据微调来提升回复的自然度和专业度。

**设计方案**：

```
数据中台
    │
    ▼
┌─────────────────────────────────┐
│        微调数据准备               │
│                                 │
│  1. 数据筛选                     │
│     └── 从CleaningLog中筛选      │
│         高质量人工客服对话         │
│                                 │
│  2. 数据格式化                   │
│     └── 转换为指令微调格式        │
│         {"instruction": ...,     │
│          "input": ...,           │
│          "output": ...}          │
│                                 │
│  3. 质量审核                     │
│     └── 人工抽样 + 自动评分       │
└─────────────┬───────────────────┘
              │
              ▼
┌─────────────────────────────────┐
│        微调执行                   │
│                                 │
│  ┌───────────────────────────┐  │
│  │ LoRA / QLoRA 微调          │  │
│  │ - 基座模型: Qwen2-7B       │  │
│  │ - 微调框架: LLaMA-Factory  │  │
│  │ - 参数量: ~0.1% 新增参数   │  │
│  └───────────────────────────┘  │
└─────────────┬───────────────────┘
              │
              ▼
      微调模型 → 替换通用LLM
```

**为什么选择 LoRA 而非全量微调**：

- **成本**：LoRA 仅训练 0.1%-1% 的参数量，显存需求从 4×A100 降至单张 A100
- **效率**：训练时间从天级降至小时级
- **可迭代**：可以针对不同场景（商品咨询、售后等）训练多个 LoRA 权重，动态切换
- **数据需求**：LoRA 在 1000-5000 条高质量数据上即可见效

---

### 3.7 MCP 与 Agent 集群（规划中）

**业务场景**：当 Agent 数量增多（客服 Agent、运营 Agent、直播 Agent 等），需要统一的治理框架来管理 Agent 的注册、发现、通信和边界控制。

**设计方案**：

```
┌─────────────────────────────────────────────────────────┐
│                   MCP 协议层                             │
│                                                         │
│  Model Context Protocol — 标准化 Agent 间通信             │
│                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │ Tools 暴露   │  │ Resources   │  │ Prompts     │     │
│  │ (可调用能力)  │  │ (数据资源)   │  │ (提示模板)   │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
└─────────────────────────┬───────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────┐
│                Agent 集群管理层                           │
│                                                         │
│  ┌───────────────────────────────────────────────────┐  │
│  │              Orchestrator (编排器)                  │  │
│  │                                                    │  │
│  │  register_agent()  ──► 注册 Agent 及能力标签        │  │
│  │  dispatch()        ──► 意图路由 → 单Agent执行       │  │
│  │  dispatch_parallel()──► 多Agent并行 → 结果聚合      │  │
│  └───────────────────────────────────────────────────┘  │
│                          │                              │
│  ┌──────────┬──────────┬──────────┬──────────┐         │
│  │ 客服Agent │ 运营Agent │ 直播Agent │ 数据Agent │  ...   │
│  └──────────┴──────────┴──────────┴──────────┘         │
└─────────────────────────────────────────────────────────┘
```

**Orchestrator 核心设计**：

```python
class Orchestrator:
    def __init__(self):
        self._agents: dict[str, Callable] = {}      # name → handler
        self._intent_map: dict[str, str] = {}       # intent → agent_name

    def register_agent(self, name: str, handler: Callable, intent_tags: list[str]):
        """注册 Agent，将意图标签映射到处理函数"""
        self._agents[name] = handler
        for tag in intent_tags:
            self._intent_map[tag] = name

    async def dispatch(self, intent: str, payload: dict) -> dict:
        """单任务分发"""
        agent_name = self._intent_map.get(intent)
        handler = self._agents.get(agent_name)
        return await handler(**payload)

    async def dispatch_parallel(self, tasks: list[dict]) -> list[dict]:
        """多任务并行执行（asyncio.gather）"""
        coros = [self.dispatch(t["intent"], t["payload"]) for t in tasks]
        return await asyncio.gather(*coros)
```

**为什么引入 MCP 协议**：

- **标准化**：MCP（Model Context Protocol）是 Anthropic 提出的 Agent 间通信标准，定义了 Tools、Resources、Prompts 三类原语
- **互操作性**：不同供应商的 Agent 可以通过 MCP 互操作
- **安全边界**：通过 MCP 的权限模型，控制每个 Agent 能访问的资源和工具

---

## 4. 核心实现原理

### 4.1 混合检索（向量 + BM25 + RRF 融合）

混合检索是本系统最核心的技术创新点，解决了纯向量检索的"语义漂移"问题和纯关键词检索的"词汇不匹配"问题。

#### 4.1.1 向量语义检索

```
用户查询 "这件衣服保暖效果怎么样"
        │
        ▼
  text-embedding-3-small → 1536维向量 q
        │
        ▼
  ChromaDB 余弦相似度检索
  score(q, d_i) = (q · d_i) / (|q| × |d_i|)
        │
        ▼
  返回 Top-K 语义最相似的文档
```

**优势**：能理解"保暖"和"御寒"的语义相似性，即使文档中没有"保暖"这个词。

**局限**：对于精确的产品型号、规格参数等关键词匹配较弱。

#### 4.1.2 BM25 关键词检索

```
用户查询 "这件衣服保暖效果怎么样"
        │
        ▼
  jieba 分词 → ["这件", "衣服", "保暖", "效果", "怎么样"]
        │
        ▼
  BM25 算法计算每个文档的得分
  score(d, q) = Σ IDF(q_i) × (f(q_i, d) × (k1 + 1)) / (f(q_i, d) + k1 × (1 - b + b × |d|/avgdl))
        │
        ▼
  返回 Top-K 关键词匹配最多的文档
```

其中：
- **IDF(q_i)**：逆文档频率，衡量词 q_i 的稀有程度
- **f(q_i, d)**：词 q_i 在文档 d 中的词频
- **|d|**：文档长度
- **avgdl**：平均文档长度
- **k1, b**：调节参数（通常 k1=1.5, b=0.75）

**优势**：精确匹配产品型号、品牌名、规格参数等。

**局限**：无法理解同义词和语义变体。

#### 4.1.3 RRF（Reciprocal Rank Fusion）融合

RRF 是两种检索结果的无监督融合算法：

```
给定:
  - 向量检索结果: R_vec = [(doc_A, score=0.95), (doc_B, score=0.88), (doc_C, score=0.76), ...]
  - BM25 检索结果: R_bm25 = [(doc_C, score=12.5), (doc_B, score=10.2), (doc_D, score=8.1), ...]

计算每个文档的 RRF 得分:

  RRF_score(d) = Σ (1 / (k + rank_r(d)))

  其中:
    r ∈ {vec, bm25}   — 检索器
    rank_r(d)         — 文档 d 在检索器 r 的结果中的排名（从1开始）
    k                 — 平滑常数（通常 k=60）

示例:
  doc_A: RRF = 1/(60+1) + 1/(60+∞) = 0.0164  (仅在向量结果中)
  doc_B: RRF = 1/(60+2) + 1/(60+2) = 0.0323  (在两个结果中都排名第2)
  doc_C: RRF = 1/(60+3) + 1/(60+1) = 0.0323  (向量第3，BM25第1)
  doc_D: RRF = 1/(60+∞) + 1/(60+3) = 0.0159  (仅在BM25结果中)

最终排序: doc_B, doc_C > doc_A > doc_D
```

**为什么选择 RRF 而非加权求和**：

1. **无需归一化**：向量相似度(0~1)和 BM25 得分(无上界)的量纲不同，加权求和需要复杂的归一化
2. **对异常值鲁棒**：排名比原始得分更稳定，某个检索器的极端高分不会主导融合结果
3. **超参数少**：仅需调节 k 值（通常 60 即可），无需为不同检索器设置权重

**核心代码逻辑**：

```python
def rrf_fusion(
    vector_results: list[dict],  # [{"id": str, "score": float}, ...]
    bm25_results: list[dict],
    k: int = 60,
    top_k: int = 5,
) -> list[dict]:
    """RRF 融合排序"""
    scores: dict[str, float] = {}

    # 向量检索结果贡献
    for rank, doc in enumerate(vector_results, start=1):
        scores[doc["id"]] = scores.get(doc["id"], 0) + 1 / (k + rank)

    # BM25 检索结果贡献
    for rank, doc in enumerate(bm25_results, start=1):
        scores[doc["id"]] = scores.get(doc["id"], 0) + 1 / (k + rank)

    # 按 RRF 得分降序排列
    sorted_ids = sorted(scores, key=scores.get, reverse=True)[:top_k]
    return [{"id": id_, "score": scores[id_]} for id_ in sorted_ids]
```

### 4.2 查询改写

查询改写是提升检索召回率的关键环节。用户的口语化表达（"这玩意儿质量行不行"）与知识库中的正式描述（"产品经过ISO9001质量认证"）之间存在巨大的语义鸿沟。

**改写流程**：

```
用户原始查询: "这玩意儿质量行不行"
        │
        ▼
┌─────────────────────────────┐
│  1. 指代消解                  │
│     "这玩意儿" → 结合历史对话  │
│     推断指代 "iPhone 15"     │
├─────────────────────────────┤
│  2. 同义词扩展                │
│     "行不行" → "质量" "可靠"  │
│     "这玩意儿" → "这个产品"    │
├─────────────────────────────┤
│  3. 关键词提取                │
│     → ["iPhone 15", "质量",  │
│         "可靠性", "评价"]     │
├─────────────────────────────┤
│  4. 结构化查询生成             │
│     → "iPhone 15 产品质量    │
│        可靠性评价"            │
└─────────────────────────────┘
        │
        ▼
改写后查询: "iPhone 15 产品质量 可靠性 评价"
```

**关键设计**：

- **多轮上下文融合**：将历史对话中的实体信息融入当前查询。例如用户先问"iPhone 15 多少钱"，再问"那续航呢"，改写后为"iPhone 15 续航"
- **同义词映射表**：维护电商领域的同义词映射，如 {"便宜":"性价比", "好用":"用户体验", "快不快":"性能"}
- **LLM 辅助改写**：复杂场景下调用轻量级 LLM 进行查询改写

### 4.3 SSE 流式输出

SSE（Server-Sent Events）是一种基于 HTTP 的服务器推送技术，比 WebSocket 更轻量，适合单向数据流场景。

**协议格式**：

```
HTTP/1.1 200 OK
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive

data: {"type":"message","content":"您好"}

data: {"type":"message","content":"，我"}

data: {"type":"message","content":"是AI"}

data: {"type":"message","content":"客服"}

data: {"type":"done"}

```

**实现要点**：

```python
# 服务端 (FastAPI)
from sse_starlette.sse import EventSourceResponse

@router.post("/chat/send")
async def chat_send(request: ChatRequest):
    if request.stream:
        async def event_generator():
            async for token in agent.chat(message, history, stream=True):
                yield {"event": "message", "data": token}
            yield {"event": "done", "data": ""}
        return EventSourceResponse(event_generator())
    else:
        reply = await agent.chat(message, history, stream=False)
        return ChatResponse(reply=reply)
```

**前端消费**：

```javascript
// 使用 fetch + ReadableStream（比 EventSource 更灵活，支持 POST）
const response = await fetch("/api/chat/send", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, stream: true }),
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    const text = decoder.decode(value);
    // 解析 SSE 格式，更新 UI
    parseSSEAndRender(text);
}
```

### 4.4 ETL 管道数据流设计

```
                    ┌──────────────┐
                    │  数据源       │
                    │ JSON / CSV   │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │  加载解析     │
                    │  逐条读取     │
                    └──────┬───────┘
                           │
              ┌────────────▼────────────┐
              │     DataCleaner         │
              │                         │
              │  每条独立清洗 + 重试3次   │
              │  HTML→Emoji→标点→空白   │
              └────────────┬────────────┘
                           │
                    ┌──────▼───────┐
                    │   文本分块    │
                    │  512字符/块   │
                    │  64字符重叠   │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │  BatchEmbedder│
                    │  批量向量化   │
                    │  100条/批     │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │   ChromaDB   │
                    │   向量存储    │
                    └──────────────┘
```

**设计决策**：

- **分块重叠**：64 字符的重叠确保上下文不丢失，避免关键信息被截断在两个块的边界
- **批量大小**：100 条/批是经过权衡的值——太大会触发 API 速率限制，太小则增加 HTTP 请求开销
- **重试机制**：3 次重试覆盖了大多数瞬时故障（网络抖动、API 限流），超过 3 次通常意味着需要人工介入

---

## 5. 数据流图

### 5.1 用户对话数据流

```
┌──────────┐     ┌──────────────┐     ┌──────────────┐
│  用户输入  │────►│ API 网关      │────►│ CustomerAgent │
│  "iPhone  │     │ POST /api/   │     │ .chat()      │
│   15 价格" │     │ chat/send    │     │              │
└──────────┘     └──────────────┘     └──────┬───────┘
                                             │
                    ┌────────────────────────┼──────────────────────┐
                    │                        │                      │
                    ▼                        ▼                      ▼
           ┌──────────────┐        ┌──────────────┐       ┌──────────────┐
           │ identify_intent│       │QueryRewriter │       │  Retriever   │
           │ "product_     │        │ .rewrite()   │       │ .retrieve()  │
           │  inquiry"     │        │              │       │              │
           └──────────────┘        │ "iPhone 15   │       │ 向量+BM25    │
                                   │  价格 售价    │       │ +RRF融合     │
                                   │  多少钱"      │       │              │
                                   └──────┬───────┘       └──────┬───────┘
                                          │                      │
                                          │       ┌──────────────┘
                                          │       │
                                          ▼       ▼
                                   ┌──────────────────┐
                                   │  PromptManager   │
                                   │  .build()        │
                                   │                  │
                                   │ System: 你是电商  │
                                   │   客服...        │
                                   │ Context: [检索    │
                                   │   到的文档...]    │
                                   │ User: iPhone 15  │
                                   │   价格           │
                                   └────────┬─────────┘
                                            │
                                            ▼
                                   ┌──────────────────┐
                                   │   LLM 生成       │
                                   │  gpt-4o-mini    │
                                   └────────┬─────────┘
                                            │
                              ┌─────────────┴─────────────┐
                              │                           │
                              ▼                           ▼
                     ┌──────────────┐            ┌──────────────┐
                     │ 非流式返回    │            │ SSE 流式返回  │
                     │ ChatResponse │            │ StreamHandler │
                     └──────┬───────┘            └──────┬───────┘
                            │                           │
                            └──────────┬────────────────┘
                                       │
                                       ▼
                              ┌──────────────┐
                              │   前端渲染    │
                              │  打字机效果   │
                              └──────────────┘
```

### 5.2 数据导入数据流

```
┌──────────┐     ┌──────────────┐     ┌──────────────┐
│  文件上传  │────►│ API 网关      │────►│ DataPipeline │
│  .json/   │     │ POST /api/   │     │ .run()       │
│  .csv     │     │ data/upload  │     │              │
└──────────┘     └──────────────┘     └──────┬───────┘
                                             │
              ┌──────────────────────────────┼──────────────────────┐
              │                              │                      │
              ▼                              ▼                      ▼
     ┌──────────────┐              ┌──────────────┐       ┌──────────────┐
     │ 加载原始数据   │              │ DataCleaner  │       │ 文本分块      │
     │ JSON/CSV解析  │              │ .batch_clean │       │ 512字/块     │
     │ 提取文本字段   │              │              │       │ 64字重叠     │
     └──────────────┘              │ 5步清洗管道   │       └──────┬───────┘
                                   └──────┬───────┘              │
                                          │                      │
                                          └──────────┬───────────┘
                                                     │
                                                     ▼
                                            ┌──────────────┐
                                            │BatchEmbedder │
                                            │.embed_and_   │
                                            │store()       │
                                            │              │
                                            │text-embedding│
                                            │-3-small      │
                                            │→ 1536维向量  │
                                            └──────┬───────┘
                                                   │
                                                   ▼
                                            ┌──────────────┐
                                            │  ChromaDB    │
                                            │  向量入库     │
                                            └──────────────┘
```

---

## 6. 接口文档

### 6.1 对话接口

**POST /api/chat/send**

发送对话消息并获取 AI 回复。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| message | string | 是 | 用户消息内容，1-2000 字符 |
| history | array | 否 | 对话历史，格式 `[{"role":"user"\|"assistant","content":"..."}]` |
| stream | boolean | 否 | 是否启用 SSE 流式输出，默认 false |

**非流式响应示例**：

```json
{
    "reply": "您好！iPhone 15 目前的价格是 5999 元起...",
    "intent": "product_inquiry",
    "sources": [
        {"text": "iPhone 15 128GB 版本售价 5999 元...", "score": 0.95},
        {"text": "iPhone 15 Pro 256GB 版本售价 8999 元...", "score": 0.82}
    ]
}
```

**流式响应**：Content-Type 为 `text/event-stream`，事件格式：

```
data: {"type":"message","content":"您好"}

data: {"type":"message","content":"！"}

data: {"type":"done"}
```

### 6.2 数据管理接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/data/upload | 上传 JSON/CSV 文件，触发 ETL 流水线 |
| POST | /api/data/search | 知识库混合检索 |
| GET | /api/data/stats | 获取知识库统计信息 |
| DELETE | /api/data/documents/{doc_id} | 删除指定文档 |

**POST /api/data/upload 请求**：

```
Content-Type: multipart/form-data
Body: file=<JSON/CSV 文件>
```

**响应**：

```json
{
    "status": "completed",
    "total": 150,
    "success": 148,
    "failed": 2
}
```

**POST /api/data/search 请求**：

```json
{
    "query": "iPhone 15 价格",
    "top_k": 5
}
```

**响应**：

```json
{
    "results": [
        {
            "id": "doc_001",
            "text": "iPhone 15 128GB 版本售价 5999 元...",
            "metadata": {"product_id": "P001", "category": "手机"},
            "score": 0.95
        }
    ],
    "total": 1
}
```

**GET /api/data/stats 响应**：

```json
{
    "document_count": 1250,
    "collection_name": "knowledge_base"
}
```

### 6.3 系统接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /health | 全局健康检查 |
| GET | /api/chat/health | 对话服务健康检查 |
| GET | /api/data/health | 数据服务健康检查 |

---

## 7. 部署方案

### 7.1 Docker 部署配置

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 暴露端口
EXPOSE 8000

# 启动服务
CMD ["python", "main.py"]
```

**docker-compose.yml（推荐配置）**：

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - OPENAI_API_BASE=${OPENAI_API_BASE:-https://api.openai.com/v1}
      - EMBEDDING_MODEL=text-embedding-3-small
      - LLM_MODEL=gpt-4o-mini
      - CHROMA_PERSIST_DIR=/app/data/chroma_db
      - SQLITE_DB_PATH=/app/data/ecommerce.db
    volumes:
      - ./data:/app/data          # 持久化向量库和SQLite数据
      - ./chroma_db:/app/chroma_db
    restart: unless-stopped
```

### 7.2 环境变量配置说明

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `OPENAI_API_KEY` | (空) | **必填**。OpenAI 兼容 API 的密钥 |
| `OPENAI_API_BASE` | `https://api.openai.com/v1` | API 基础地址，支持自定义代理 |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | 嵌入模型名称 |
| `LLM_MODEL` | `gpt-4o-mini` | 对话模型名称 |
| `CHROMA_PERSIST_DIR` | `./chroma_db` | ChromaDB 向量库持久化目录 |
| `SQLITE_DB_PATH` | `./data/ecommerce.db` | SQLite 数据库文件路径 |
| `CHUNK_SIZE` | `512` | 文本分块大小（字符数） |
| `CHUNK_OVERLAP` | `64` | 相邻文本块之间的重叠字符数 |
| `TOP_K` | `5` | 向量检索返回的候选文档数量 |
| `BATCH_SIZE` | `100` | 批量处理时每批的数据量 |
| `MAX_RETRIES` | `3` | 外部 API 调用失败时的最大重试次数 |
| `API_HOST` | `0.0.0.0` | FastAPI 监听地址 |
| `API_PORT` | `8000` | FastAPI 监听端口 |
| `CORS_ORIGINS` | `*` | 允许的跨域来源，逗号分隔 |

### 7.3 快速启动

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 填入 OPENAI_API_KEY

# 3. 导入种子数据
python scripts/seed_data.py

# 4. 启动服务
python main.py
# 访问 http://localhost:8000
```

---

## 8. 扩展规划

### 8.1 从 Demo 到生产环境的演进路径

```
Phase 1 (当前)              Phase 2 (3个月)            Phase 3 (6个月)           Phase 4 (12个月)
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Demo 单机部署    │───►│ 容器化微服务     │───►│ 分布式 + 高可用   │───►│ 全链路 AI 平台   │
│                 │    │                 │    │                 │    │                 │
│ FastAPI 单进程   │    │ Docker Compose  │    │ K8s 集群部署     │    │ 多租户 SaaS     │
│ ChromaDB 嵌入式  │    │ Nginx 反向代理   │    │ Milvus 分布式    │    │ 模型市场        │
│ SQLite 本地文件  │    │ PostgreSQL 替换  │    │ Redis 缓存层     │    │ Agent 编排平台  │
│ 单知识库        │    │ 多知识库隔离     │    │ 消息队列(Kafka)  │    │ 低代码Agent构建 │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 8.2 各规划模块技术选型总结

| 模块 | 当前状态 | 推荐技术栈 | 优先级 | 预估工作量 |
|------|---------|-----------|--------|-----------|
| 数据中台 | **已实现** | Python + SQLAlchemy + ChromaDB | — | — |
| AI客服 + RAG | **已实现** | LangChain + gpt-4o-mini + BM25 | — | — |
| 运营 Agent | 规划中 | DALL-E 3 / Runway Gen-3 / LLM | 高 | 4 周 |
| AI素材中心 | 规划中 | MinIO + Chinese-CLIP + PostgreSQL | 高 | 6 周 |
| 直播切片 | 规划中 | Whisper + FFmpeg + BERT-CRF | 中 | 8 周 |
| 模型微调 | 规划中 | Qwen2-7B + LoRA + LLaMA-Factory | 中 | 4 周 |
| MCP + Agent集群 | 规划中 | MCP Protocol + asyncio | 低 | 6 周 |

### 8.3 关键里程碑

```
Month 1-2:  运营Agent + 素材中心 MVP
            → 实现文生图和文案自动生成
            → 素材-商品关联存储和检索

Month 3-4:  直播切片Agent + 多模态RAG
            → ASR转写 + 内容切片
            → 图片/视频向量化检索

Month 5-6:  模型微调 + Agent集群
            → 基于真实客服数据的LoRA微调
            → MCP协议集成 + Agent编排

Month 7-12: 生产化改造
            → K8s部署 + 监控告警
            → 多租户 + 权限管理
            → 性能优化 + 压测
```

---

## 附录：项目目录结构

```
AIagent/
├── main.py                     # FastAPI 应用入口
├── config.py                   # 全局配置（环境变量、模型参数）
├── requirements.txt            # Python 依赖
│
├── api/                        # API 路由层
│   ├── __init__.py
│   ├── chat.py                 # 对话接口 (POST /api/chat/send)
│   └── data.py                 # 数据管理接口 (CRUD)
│
├── customer_service/           # 智能客服模块
│   ├── __init__.py
│   ├── agent.py                # CustomerAgent 对话编排
│   ├── prompts.py              # PromptManager 模板管理
│   └── stream_handler.py       # StreamHandler SSE 流式输出
│
├── rag/                        # RAG 知识检索模块
│   ├── __init__.py
│   ├── knowledge_base.py       # KnowledgeBase ChromaDB CRUD
│   ├── retriever.py            # Retriever 混合检索（向量+BM25+RRF）
│   └── query_rewriter.py       # QueryRewriter 查询改写
│
├── data_platform/              # 数据中台模块
│   ├── __init__.py
│   ├── models.py               # SQLAlchemy 数据模型
│   ├── cleaner.py              # DataCleaner 数据清洗器
│   ├── pipeline.py             # DataPipeline ETL 编排器
│   └── batch_embedder.py       # BatchEmbedder 批量向量化
│
├── agent_cluster/              # Agent 集群模块
│   ├── __init__.py
│   └── orchestrator.py         # Orchestrator Agent 编排器
│
├── static/                     # 前端静态资源
│   ├── index.html              # 主页面
│   ├── style.css               # 样式表
│   └── app.js                  # 交互逻辑
│
├── data/                       # 数据文件
│   └── sample_dialogues.json   # 种子对话数据
│
├── scripts/                    # 工具脚本
│   └── seed_data.py            # 种子数据导入脚本
│
└── docs/                       # 文档
    └── architecture.md         # 架构设计文档（本文件）
```
