"""
FastAPI 应用入口

负责：
- 创建 FastAPI 实例并配置 CORS 中间件
- 注册各子模块路由
- 启动时初始化 ChromaDB collection
- 提供基础健康检查端点
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import API_HOST, API_PORT, CHROMA_PERSIST_DIR, CORS_ORIGINS


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理：
    - 启动时初始化 ChromaDB collection
    - 关闭时清理资源（预留）
    """
    # ========== 启动逻辑 ==========
    print(f"[Lifespan] 初始化 ChromaDB，持久化路径: {CHROMA_PERSIST_DIR}")
    import chromadb
    from chromadb.config import Settings

    try:
        client = chromadb.PersistentClient(
            path=CHROMA_PERSIST_DIR,
            settings=Settings(anonymized_telemetry=False),
        )
        collection = client.get_or_create_collection(name="knowledge_base")
        print(f"[Lifespan] ChromaDB collection 'knowledge_base' 就绪，文档数: {collection.count()}")
    except Exception as exc:
        print(f"[Lifespan] ChromaDB 初始化失败: {exc}")

    yield  # 应用运行期间

    # ========== 关闭逻辑 ==========
    print("[Lifespan] 应用关闭，清理资源")


# ---- FastAPI 实例 ----
app = FastAPI(
    title="电商 AI Agent 体系",
    description="集成 RAG、多 Agent 协作、客服对话的智能电商平台",
    version="0.1.0",
    lifespan=lifespan,
)

# ---- CORS 中间件 ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- 注册路由 ----
from api.chat import router as chat_router
from api.data import router as data_router

app.include_router(chat_router, prefix="/api", tags=["对话"])
app.include_router(data_router, prefix="/api", tags=["数据"])

# ---- 健康检查 ----
@app.get("/health", tags=["系统"])
async def health_check() -> dict[str, str]:
    """基础健康检查端点"""
    return {"status": "ok", "version": "0.1.0"}


# ---- 静态文件服务（必须放在最后） ----
app.mount("/", StaticFiles(directory="static", html=True), name="static")


# ---- 静态文件服务 ----
import os
_static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
app.mount("/", StaticFiles(directory=_static_dir, html=True), name="static")

# ---- 直接运行入口 ----
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=API_HOST,
        port=API_PORT,
        reload=True,
    )
