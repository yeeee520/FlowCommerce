"""
customer_service.agent — 智能客服 Agent

编排从用户输入到最终回复的完整对话流水线：
意图识别 -> 查询改写 -> RAG检索 -> 上下文构建 -> LLM生成
"""

import logging
from typing import AsyncGenerator, Optional

from langchain_openai import ChatOpenAI

from config import LLM_MODEL, OPENAI_API_BASE, OPENAI_API_KEY, TOP_K
from customer_service.prompts import PromptManager
from rag.query_rewriter import QueryRewriter
from rag.retriever import Retriever

logger = logging.getLogger(__name__)

# 意图识别系统提示词
INTENT_SYSTEM_PROMPT = """你是一个电商客服意图识别专家。请判断用户消息属于以下哪个意图类别，只输出类别名称，不要输出任何其他内容。

意图类别：
- 商品咨询：询问商品信息、规格、价格、功能、对比、推荐等
- 订单查询：查询订单状态、物流进度、配送信息等
- 售后问题：退换货、退款、投诉、质量问题等
- 物流查询：询问物流进度、配送时效、配送范围等
- 通用问答：其他无法归类的问题

用户消息："""


class CustomerAgent:
    """
    智能客服 Agent

    职责：
    - 接收用户消息和对话历史
    - 识别意图（商品咨询、订单查询、售后投诉等）
    - 调用 RAG 检索相关商品信息
    - 构建 Prompt 并调用 LLM 生成回复
    - 支持流式输出

    接口契约：
        async chat(
            message: str,
            history: Optional[list[dict[str, str]]] = None,
            stream: bool = False,
        ) -> str | AsyncGenerator[str, None]
            - 参数: message — 用户消息
            - 参数: history — 对话历史 [{"role": "user"|"assistant", "content": "..."}]
            - 参数: stream — 是否流式输出
            - 返回: 完整回复文本 (stream=False) 或 异步生成器 (stream=True)

        async identify_intent(message: str) -> str
            - 参数: message — 用户消息
            - 返回: 意图类别标签
    """

    def __init__(
        self,
        retriever: Optional[Retriever] = None,
        rewriter: Optional[QueryRewriter] = None,
        prompt_manager: Optional[PromptManager] = None,
        llm: Optional[ChatOpenAI] = None,
    ) -> None:
        """
        Args:
            retriever: 检索器实例
            rewriter: 查询改写器实例
            prompt_manager: Prompt 管理器实例
            llm: 大语言模型实例
        """
        self.retriever: Retriever = retriever or Retriever()
        self.rewriter: QueryRewriter = rewriter or QueryRewriter()
        self.prompt_manager: PromptManager = prompt_manager or PromptManager()
        self.llm: ChatOpenAI = llm or ChatOpenAI(
            model=LLM_MODEL,
            openai_api_key=OPENAI_API_KEY,
            openai_api_base=OPENAI_API_BASE,
            temperature=0.7,
        )
        # 意图识别用低温度的独立 LLM 实例，保证输出稳定
        self._intent_llm: ChatOpenAI = ChatOpenAI(
            model=LLM_MODEL,
            openai_api_key=OPENAI_API_KEY,
            openai_api_base=OPENAI_API_BASE,
            temperature=0.0,
        )

    async def chat(
        self,
        message: str,
        history: Optional[list[dict[str, str]]] = None,
        stream: bool = False,
    ) -> str | AsyncGenerator[str, None]:
        """
        处理用户对话

        完整流水线：
        1. 查询改写（结合历史）
        2. 意图识别
        3. RAG 检索
        4. 构建消息
        5. LLM 生成回复

        Args:
            message: 用户消息
            history: 对话历史
            stream: 是否流式返回

        Returns:
            回复文本 或 异步生成器
        """
        logger.info(f"CustomerAgent.chat: message='{message[:50]}...', stream={stream}")

        try:
            # 1. 查询改写
            rewritten_query = self.rewriter.rewrite(message, history)
            logger.debug(f"改写后查询: '{rewritten_query[:50]}...'")

            # 2. 意图识别
            intent = await self.identify_intent(message)
            logger.debug(f"识别意图: {intent}")

            # 3. RAG 检索
            docs = self.retriever.retrieve(rewritten_query, top_k=TOP_K)
            self._last_sources = docs  # 保存供 API 层获取
            self._last_intent = intent  # 保存意图
            logger.debug(f"检索到 {len(docs)} 个相关文档")

            # 构建上下文文本
            context_parts: list[str] = []
            for i, doc in enumerate(docs, 1):
                context_parts.append(
                    f"[文档{i}] 商品: {doc['metadata'].get('product_name', '未知')}\n{doc['content']}"
                )
            context = "\n\n---\n\n".join(context_parts) if context_parts else None

            # 4. 构建消息
            messages = self.prompt_manager.build_messages(
                intent=intent,
                user_message=message,
                context=context,
                history=history,
            )

            # 5. LLM 生成
            if stream:
                return self._stream_response(messages, intent, docs)
            else:
                response = self.llm.invoke(messages)
                reply = response.content if hasattr(response, "content") else str(response)
                logger.info(f"生成回复完成，长度: {len(reply)}")
                # 将检索来源附加到返回（通过 _reply_with_sources 包装）
                # 非流式直接返回文本，sources 由上层 API 单独返回
                return reply

        except Exception as exc:
            logger.error(f"CustomerAgent.chat 异常: {exc}", exc_info=True)
            if stream:
                async def error_gen() -> AsyncGenerator[str, None]:
                    yield "抱歉，系统暂时无法处理您的请求，请稍后再试。"
                return error_gen()
            return "抱歉，系统暂时无法处理您的请求，请稍后再试。"

    async def identify_intent(self, message: str) -> str:
        """
        识别用户意图

        调用 LLM 对用户消息进行分类，返回中文意图标签。
        中文标签可直接用于 PromptManager。

        Args:
            message: 用户消息

        Returns:
            意图标签，如 "商品咨询", "订单查询", "售后问题", "物流查询", "通用问答"
        """
        try:
            response = self._intent_llm.invoke([
                {"role": "system", "content": INTENT_SYSTEM_PROMPT},
                {"role": "user", "content": message},
            ])
            intent = response.content.strip() if hasattr(response, "content") else str(response).strip()

            # 验证返回的意图是否在已知类别中
            valid_intents = {"商品咨询", "订单查询", "售后问题", "物流查询", "通用问答"}
            if intent not in valid_intents:
                logger.warning(f"LLM 返回未知意图 '{intent}'，回退为'通用问答'")
                intent = "通用问答"

            logger.debug(f"意图识别: '{message[:50]}...' -> {intent}")
            return intent

        except Exception as exc:
            logger.error(f"意图识别失败: {exc}")
            return "通用问答"

    async def _stream_response(
        self,
        messages: list[dict[str, str]],
        intent: str,
        docs: list[dict],
    ) -> AsyncGenerator[str, None]:
        """
        流式生成回复

        Args:
            messages: 完整的消息列表
            intent: 意图标签
            docs: 检索到的文档列表（供上层使用）

        Yields:
            逐个 token
        """
        try:
            async for chunk in self.llm.astream(messages):
                if hasattr(chunk, "content") and chunk.content:
                    yield chunk.content
        except Exception as exc:
            logger.error(f"流式生成异常: {exc}")
            yield "\n[回复生成中断，请重试]"

    def get_last_sources(self) -> list[dict]:
        """获取最近一次检索的文档来源（由 chat 方法设置）"""
        return getattr(self, "_last_sources", [])
