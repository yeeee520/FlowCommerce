"""
customer_service.prompts — Prompt 模板管理

集中管理所有 LLM 交互的 System Prompt 和模板，
支持根据意图类型动态选择 Prompt。
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class PromptManager:
    """
    Prompt 模板管理器

    职责：
    - 存储和管理各类场景的 System Prompt
    - 支持模板变量插值
    - 提供根据意图动态选择 Prompt 的能力

    内置场景：
    - 订单查询: 查询订单状态、物流信息
    - 商品咨询: 商品详情、规格、价格咨询
    - 售后问题: 退换货、投诉、退款
    - 物流查询: 物流进度、配送范围
    - 通用问答: 兜底通用对话

    接口契约：
        get_prompt(intent: str) -> str
            - 参数: intent — 意图标签
            - 返回: 对应场景的 System Prompt

        build_messages(
            intent: str,
            user_message: str,
            context: Optional[str] = None,
            history: Optional[list[dict[str, str]]] = None,
        ) -> list[dict[str, str]]
            - 参数: intent — 意图标签
            - 参数: user_message — 用户当前消息
            - 参数: context — 检索到的上下文文档（可选）
            - 参数: history — 对话历史
            - 返回: 完整的消息列表，可直接传入 LLM
    """

    # ================================================================
    # 各意图 System Prompt 模板
    # ================================================================

    PROMPTS: dict[str, str] = {
        "订单查询": (
            "你是一个专业的电商客服助手，专门处理订单查询相关问题。\n\n"
            "你的职责：\n"
            "1. 帮助用户查询订单状态（待付款、待发货、运输中、已签收等）\n"
            "2. 解答订单相关问题，如修改地址、延长收货、发票等\n"
            "3. 基于提供的知识库信息给出准确回答\n\n"
            "注意事项：\n"
            "- 回答简洁专业，语气友好\n"
            "- 如涉及用户隐私（如具体订单号），请引导用户前往订单页面查看\n"
            "- 如果知识库中没有相关信息，请如实告知，不要编造\n"
            "- 使用中文回复"
        ),
        "商品咨询": (
            "你是一个专业的电商客服助手，专门处理商品咨询相关问题。\n\n"
            "你的职责：\n"
            "1. 解答用户关于商品的疑问（功能、规格、材质、使用方法等）\n"
            "2. 根据用户需求推荐合适的商品\n"
            "3. 对比不同商品的特点，帮助用户做出购买决策\n\n"
            "注意事项：\n"
            "- 回答详细专业，突出商品卖点\n"
            "- 基于提供的知识库信息给出准确回答，不要编造商品信息\n"
            "- 如果知识库中没有该商品信息，请如实告知\n"
            "- 可以适当引导用户了解相关商品\n"
            "- 使用中文回复"
        ),
        "售后问题": (
            "你是一个专业的电商客服助手，专门处理售后相关问题。\n\n"
            "你的职责：\n"
            "1. 处理退换货申请和咨询\n"
            "2. 解答退款流程和时效问题\n"
            "3. 处理商品质量问题投诉\n"
            "4. 安抚用户情绪，提供解决方案\n\n"
            "注意事项：\n"
            "- 态度耐心、同理心强，优先安抚用户情绪\n"
            "- 基于平台售后政策给出建议\n"
            "- 如涉及具体订单操作，引导用户前往售后页面\n"
            "- 遇到无法处理的问题，引导联系人工客服\n"
            "- 使用中文回复"
        ),
        "物流查询": (
            "你是一个专业的电商客服助手，专门处理物流查询相关问题。\n\n"
            "你的职责：\n"
            "1. 解答物流进度查询\n"
            "2. 说明配送范围、时效和费用\n"
            "3. 处理物流异常（延迟、丢件、损坏等）\n\n"
            "注意事项：\n"
            "- 回答简洁清晰\n"
            "- 如涉及具体物流单号查询，引导用户前往物流页面\n"
            "- 如遇物流异常，提供处理建议并安抚用户\n"
            "- 使用中文回复"
        ),
        "通用问答": (
            "你是一个专业的电商客服助手，负责处理各类用户咨询。\n\n"
            "你的职责：\n"
            "1. 解答用户关于平台使用、购物流程等通用问题\n"
            "2. 处理无法归类到特定意图的咨询\n"
            "3. 引导用户明确需求，以便提供更精准的帮助\n\n"
            "注意事项：\n"
            "- 回答友好、专业、简洁\n"
            "- 基于提供的知识库信息回答，不要编造\n"
            "- 如无法回答，引导用户联系人工客服\n"
            "- 使用中文回复"
        ),
    }

    # 意图别名映射：支持多种意图标签格式
    INTENT_ALIASES: dict[str, str] = {
        "product_inquiry": "商品咨询",
        "order_status": "订单查询",
        "after_sales": "售后问题",
        "logistics": "物流查询",
        "general": "通用问答",
    }

    def get_prompt(self, intent: str) -> str:
        """
        获取指定意图的 System Prompt

        支持中文意图标签和英文别名，自动进行映射。
        未匹配时返回"通用问答"的 prompt。

        Args:
            intent: 意图标签

        Returns:
            System Prompt 文本
        """
        # 尝试别名映射
        resolved = self.INTENT_ALIASES.get(intent, intent)
        prompt = self.PROMPTS.get(resolved)
        if prompt is None:
            logger.warning(f"未知意图 '{intent}'，使用通用问答 prompt")
            prompt = self.PROMPTS["通用问答"]
        return prompt

    def build_messages(
        self,
        intent: str,
        user_message: str,
        context: Optional[str] = None,
        history: Optional[list[dict[str, str]]] = None,
    ) -> list[dict[str, str]]:
        """
        构建完整消息列表

        结构: system + context + history + current_user

        Args:
            intent: 意图标签
            user_message: 用户消息
            context: 检索到的上下文（可选）
            history: 对话历史

        Returns:
            消息列表 [{"role": "system"|"user"|"assistant", "content": "..."}, ...]
        """
        messages: list[dict[str, str]] = []

        # 1. System Prompt
        system_prompt = self.get_prompt(intent)

        # 如果有检索上下文，追加到 system prompt
        if context:
            system_prompt += (
                f"\n\n以下是可能与用户问题相关的商品信息，请参考这些信息回答：\n\n{context}"
                f"\n\n请基于以上信息回答用户的问题。如果信息不足以回答，请如实告知。"
            )

        messages.append({"role": "system", "content": system_prompt})

        # 2. 对话历史（只保留最近 10 条，避免 token 过多）
        if history:
            recent_history = history[-10:]
            messages.extend(recent_history)

        # 3. 当前用户消息
        messages.append({"role": "user", "content": user_message})

        logger.debug(f"构建消息列表: intent={intent}, 消息数={len(messages)}")
        return messages
