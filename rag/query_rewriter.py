"""
rag.query_rewriter — 查询改写器

将用户的自然语言查询改写为更利于检索的形式，
包括同义词扩展、关键词提取、多轮对话上下文融合等。
"""

import logging
from typing import Optional

import jieba
from langchain_openai import ChatOpenAI

from config import LLM_MODEL, OPENAI_API_BASE, OPENAI_API_KEY

logger = logging.getLogger(__name__)

# 查询改写系统提示词
REWRITE_SYSTEM_PROMPT = """你是一个电商搜索查询优化专家。你的任务是将用户的自然语言查询改写为更适合检索的形式。

改写规则：
1. 补全指代：如果查询中有"它"、"这个"、"那个"等指代词，根据对话历史补全为具体对象
2. 扩展缩写：将口语化表达扩展为完整术语（如"包邮" -> "包邮 免运费"）
3. 优化措辞：去除无关的语气词，保留核心检索意图
4. 如果对话历史为空或无指代需要补全，直接返回原始查询即可

请只输出改写后的查询文本，不要输出任何解释、前缀或额外内容。"""


class QueryRewriter:
    """
    查询改写器

    策略：
    - 同义词扩展：将口语化表达映射为电商专业术语
    - 关键词提取：从长句中提取核心检索词
    - 上下文融合：将多轮对话历史融入当前查询

    接口契约：
        rewrite(
            query: str,
            history: Optional[list[dict[str, str]]] = None,
        ) -> str
            - 参数: query — 原始用户查询
            - 参数: history — 对话历史 [{"role": "user"|"assistant", "content": "..."}, ...]
            - 返回: 改写后的检索查询

        extract_keywords(query: str) -> list[str]
            - 参数: query — 查询文本
            - 返回: 提取的关键词列表
    """

    # jieba 词性标注中属于有效关键词的词性
    _VALID_POS: set[str] = {"n", "nr", "ns", "nt", "nz", "v", "vn", "a", "an", "eng"}

    def __init__(self, llm: Optional[ChatOpenAI] = None) -> None:
        """
        Args:
            llm: 语言模型实例，不提供则使用默认配置
        """
        self.llm: ChatOpenAI = llm or ChatOpenAI(
            model=LLM_MODEL,
            openai_api_key=OPENAI_API_KEY,
            openai_api_base=OPENAI_API_BASE,
            temperature=0.0,
        )

    def rewrite(
        self,
        query: str,
        history: Optional[list[dict[str, str]]] = None,
    ) -> str:
        """
        改写用户查询以优化检索效果

        当存在对话历史时，调用 LLM 补全指代和优化措辞。
        无历史时直接返回原始查询（避免不必要的 LLM 调用）。

        Args:
            query: 原始查询
            history: 对话历史（可选）

        Returns:
            改写后的查询文本
        """
        if not history:
            logger.debug(f"无对话历史，直接返回原始查询: '{query[:50]}...'")
            return query

        try:
            # 构建上下文：将历史转为可读文本
            history_text_parts: list[str] = []
            for msg in history[-6:]:  # 只取最近 6 条
                role = "用户" if msg.get("role") == "user" else "客服"
                content = msg.get("content", "")
                history_text_parts.append(f"{role}: {content}")
            history_text = "\n".join(history_text_parts)

            messages = [
                {"role": "system", "content": REWRITE_SYSTEM_PROMPT},
                {"role": "user", "content": f"对话历史：\n{history_text}\n\n当前查询：{query}\n\n改写后的查询："},
            ]

            response = self.llm.invoke(messages)
            rewritten = response.content.strip() if hasattr(response, "content") else str(response).strip()
            logger.info(f"查询改写: '{query[:50]}...' -> '{rewritten[:50]}...'")
            return rewritten if rewritten else query

        except Exception as exc:
            logger.warning(f"查询改写失败，使用原始查询: {exc}")
            return query

    def extract_keywords(self, query: str) -> list[str]:
        """
        提取查询中的核心关键词

        使用 jieba 分词 + 词性标注，过滤停用词和虚词，
        保留名词、动词、形容词等实义词。

        Args:
            query: 查询文本

        Returns:
            关键词列表
        """
        try:
            words = jieba.posseg.cut(query)
            # 停用词集合
            stop_pos = {"r", "u", "d", "p", "c", "m", "q", "x", "w", "y", "o", "e"}
            keywords: list[str] = []
            for word, flag in words:
                # 过滤单字、停用词性、纯标点
                if len(word) >= 2 and flag not in stop_pos:
                    keywords.append(word)
            logger.debug(f"关键词提取: '{query[:50]}...' -> {keywords}")
            return keywords
        except Exception as exc:
            logger.warning(f"关键词提取失败: {exc}")
            # 降级：基础分词
            return [w for w in jieba.cut(query) if len(w) >= 2]
