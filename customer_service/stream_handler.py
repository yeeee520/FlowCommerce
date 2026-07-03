"""
customer_service.stream_handler — SSE 流式输出处理器

将 LLM 的流式生成转换为 Server-Sent Events (SSE) 格式，
供前端消费并实现打字机效果。
"""

import json
import logging
from typing import AsyncGenerator, Optional

logger = logging.getLogger(__name__)


class StreamHandler:
    """
    SSE 流式输出处理器

    职责：
    - 将 AsyncGenerator 转换为 SSE 事件流
    - 支持事件类型区分（token, error, done）
    - 处理流中断和异常

    接口契约：
        async to_sse(
            generator: AsyncGenerator[str, None],
            event_type: str = "token",
        ) -> AsyncGenerator[str, None]
            - 参数: generator — LLM token 生成器
            - 参数: event_type — SSE 事件类型
            - 返回: SSE 格式的事件流生成器

        async wrap_error(error_msg: str) -> AsyncGenerator[str, None]
            - 参数: error_msg — 错误信息
            - 返回: 包含错误事件的 SSE 流
    """

    async def to_sse(
        self,
        generator: AsyncGenerator[str, None],
        event_type: str = "token",
    ) -> AsyncGenerator[str, None]:
        """
        将 token 生成器转换为 SSE 事件流

        SSE 格式：
        - 每个 token: data: {"type":"token","content":"你"}\n\n
        - 流结束: data: [DONE]\n\n

        Args:
            generator: LLM 输出 token 的异步生成器
            event_type: SSE 事件类型标识

        Yields:
            SSE 格式字符串
        """
        try:
            async for token in generator:
                if token:
                    payload = json.dumps(
                        {"type": event_type, "content": token},
                        ensure_ascii=False,
                    )
                    yield f"data: {payload}\n\n"
            # 流正常结束，发送 [DONE] 信号
            yield "data: [DONE]\n\n"
            logger.debug("SSE 流正常结束")
        except Exception as exc:
            logger.error(f"SSE 流转换异常: {exc}")
            # 发送错误事件
            error_payload = json.dumps(
                {"type": "error", "content": f"流输出异常: {exc}"},
                ensure_ascii=False,
            )
            yield f"data: {error_payload}\n\n"
            yield "data: [DONE]\n\n"

    async def wrap_error(self, error_msg: str) -> AsyncGenerator[str, None]:
        """
        生成 SSE 格式的错误事件流

        发送一条错误事件后立即结束。

        Args:
            error_msg: 错误信息

        Yields:
            SSE 错误事件
        """
        error_payload = json.dumps(
            {"type": "error", "content": error_msg},
            ensure_ascii=False,
        )
        yield f"data: {error_payload}\n\n"
        yield "data: [DONE]\n\n"
        logger.warning(f"SSE 错误事件: {error_msg}")
