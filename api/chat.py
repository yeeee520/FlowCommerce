"""
api.chat — 对话 API 路由

提供智能客服对话接口，支持普通模式和 SSE 流式模式。
"""

import logging
from typing import Optional

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from customer_service.agent import CustomerAgent
from customer_service.stream_handler import StreamHandler

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat")

# 模块级别单例（在实际生产环境中应使用依赖注入）
_agent: Optional[CustomerAgent] = None
_stream_handler: Optional[StreamHandler] = None


def get_agent() -> CustomerAgent:
    """获取 CustomerAgent 单例"""
    global _agent
    if _agent is None:
        _agent = CustomerAgent()
        logger.info("CustomerAgent 已初始化")
    return _agent


def get_stream_handler() -> StreamHandler:
    """获取 StreamHandler 单例"""
    global _stream_handler
    if _stream_handler is None:
        _stream_handler = StreamHandler()
    return _stream_handler


# ============================================================
# 请求/响应模型
# ============================================================

class ChatRequest(BaseModel):
    """对话请求体"""
    message: str = Field(..., description="用户消息内容", min_length=1, max_length=2000)
    history: Optional[list[dict[str, str]]] = Field(
        default=None,
        description="对话历史 [{\"role\": \"user\"|\"assistant\", \"content\": \"...\"}]",
    )
    stream: bool = Field(default=False, description="是否启用 SSE 流式输出")


class ChatResponse(BaseModel):
    """对话响应体（非流式）"""
    reply: str = Field(..., description="AI 回复内容")
    intent: Optional[str] = Field(default=None, description="识别到的意图标签")
    sources: Optional[list[dict]] = Field(
        default=None,
        description="检索到的参考文档 [{\"text\": str, \"score\": float}]",
    )


# ============================================================
# 路由
# ============================================================

@router.post("/send", summary="发送对话消息")
async def chat_send(request: ChatRequest):
    """
    发送对话消息并获取 AI 回复。

    - 当 stream=False 时，返回完整 ChatResponse
    - 当 stream=True 时，返回 SSE 事件流 (text/event-stream)
    """
    agent = get_agent()
    handler = get_stream_handler()

    if request.stream:
        # ---- SSE 流式模式 ----
        token_generator = await agent.chat(
            message=request.message,
            history=request.history,
            stream=True,
        )

        async def sse_stream():
            async for sse_event in handler.to_sse(token_generator, event_type="token"):
                yield sse_event

        return StreamingResponse(
            sse_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    else:
        # ---- 非流式模式 ----
        reply = await agent.chat(
            message=request.message,
            history=request.history,
            stream=False,
        )
        # 获取检索来源和意图
        sources = getattr(agent, "_last_sources", [])
        intent = getattr(agent, "_last_intent", None)

        # 构建简洁的来源列表返回前端
        source_items = []
        for doc in sources:
            source_items.append({
                "text": doc.get("content", "")[:200],  # 截取前 200 字
                "score": doc.get("score", 0),
                "product_name": doc.get("metadata", {}).get("product_name", ""),
                "source_type": doc.get("source_type", "unknown"),
            })

        return ChatResponse(
            reply=str(reply),
            intent=intent,
            sources=source_items if source_items else None,
        )


@router.get("/health", summary="对话服务健康检查")
async def chat_health() -> dict[str, str]:
    """检查对话服务是否就绪"""
    return {"status": "ok", "service": "chat"}
