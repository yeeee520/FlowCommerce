"""
customer_service — 智能客服模块

负责对话管理、意图识别、RAG 增强回复生成与流式输出。
是面向终端用户的核心交互层。

对外暴露的核心接口：
    - CustomerAgent      (class): 智能客服 Agent，编排对话全流程
    - PromptManager      (class): Prompt 模板管理
    - StreamHandler      (class): SSE 流式输出处理器
"""

from customer_service.agent import CustomerAgent
from customer_service.prompts import PromptManager
from customer_service.stream_handler import StreamHandler

__all__ = [
    "CustomerAgent",
    "PromptManager",
    "StreamHandler",
]
