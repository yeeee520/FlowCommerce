"""
api — HTTP API 路由模块

提供 RESTful API 和 SSE 流式接口，是前端与后端之间的桥梁。

对外暴露的核心路由：
    - chat.router   (APIRouter): /api/chat — 对话接口（含 SSE 流式）
    - data.router   (APIRouter): /api/data — 数据管理接口
"""

from api.chat import router as chat_router
from api.data import router as data_router

__all__ = [
    "chat_router",
    "data_router",
]
