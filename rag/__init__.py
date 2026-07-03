"""
rag — 检索增强生成模块

负责知识库管理、文档检索、查询改写与重排序。
为客服 Agent 提供精确的商品信息检索能力。

对外暴露的核心接口：
    - KnowledgeBase      (class): 知识库管理（CRUD）
    - Retriever          (class): 混合检索器（向量 + BM25）
    - QueryRewriter      (class): 查询改写与扩展
"""

from rag.knowledge_base import KnowledgeBase
from rag.retriever import Retriever
from rag.query_rewriter import QueryRewriter

__all__ = [
    "KnowledgeBase",
    "Retriever",
    "QueryRewriter",
]
