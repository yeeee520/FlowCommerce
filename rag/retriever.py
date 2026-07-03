"""
rag.retriever — 混合检索器

实现向量检索（语义）与 BM25 检索（关键词）的混合策略，
并进行重排序融合，返回最相关文档。
"""

import logging
from typing import Optional

import jieba
from rank_bm25 import BM25Okapi

from config import TOP_K
from rag.knowledge_base import KnowledgeBase

logger = logging.getLogger(__name__)

# RRF 融合参数
RRF_K: int = 60


class Retriever:
    """
    混合检索器

    策略：
    - 向量检索：通过 ChromaDB 语义相似度检索
    - BM25 检索：基于 jieba 分词的关键词匹配
    - 融合策略：RRF (Reciprocal Rank Fusion) 重排序

    接口契约：
        retrieve(
            query: str,
            top_k: Optional[int] = None,
            filters: Optional[dict] = None,
        ) -> list[dict]
            - 参数: query — 用户查询文本
            - 参数: top_k — 返回数量，默认使用配置中的 TOP_K
            - 参数: filters — ChromaDB 元数据过滤条件
            - 返回: 按相关性降序的文档列表 [{"id": str, "content": str, "metadata": dict, "score": float, "source_type": str}, ...]

        retrieve_with_bm25(
            query: str,
            top_k: Optional[int] = None,
        ) -> list[dict]
            - 纯 BM25 检索，用于调试和对比
    """

    def __init__(self, knowledge_base: Optional[KnowledgeBase] = None) -> None:
        """
        Args:
            knowledge_base: 知识库实例，不提供则使用默认 knowledge_base collection
        """
        self.kb: KnowledgeBase = knowledge_base or KnowledgeBase()

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        filters: Optional[dict] = None,
    ) -> list[dict]:
        """
        混合检索（向量 + BM25 + RRF 融合）

        流程：
        1. 向量语义检索：ChromaDB similarity_search
        2. BM25 关键词检索：jieba 分词 + BM25Okapi
        3. RRF 融合两路结果
        4. 返回 top_k 个结果

        Args:
            query: 查询文本
            top_k: 返回数量
            filters: 元数据过滤条件

        Returns:
            文档列表，每个文档含 id/content/metadata/score/source_type
        """
        k = top_k or TOP_K
        # 检索时取更多候选（2x），给 RRF 融合留空间
        candidate_k = max(k * 2, 20)

        # 1. 向量语义检索
        vector_results = self._vector_search(query, candidate_k, filters)
        logger.debug(f"向量检索返回 {len(vector_results)} 个候选")

        # 2. BM25 关键词检索
        bm25_results = self._bm25_search(query, candidate_k)
        logger.debug(f"BM25 检索返回 {len(bm25_results)} 个候选")

        # 3. RRF 融合
        fused = self._rrf_fusion(vector_results, bm25_results, k)
        logger.info(f"RRF 融合后返回 {len(fused)} 个结果 (query='{query[:50]}...')")
        return fused

    def retrieve_with_bm25(
        self,
        query: str,
        top_k: Optional[int] = None,
    ) -> list[dict]:
        """
        纯 BM25 关键词检索

        Args:
            query: 查询文本
            top_k: 返回数量

        Returns:
            文档列表
        """
        return self._bm25_search(query, top_k or TOP_K)

    # ---------- 内部方法 ----------

    def _vector_search(
        self,
        query: str,
        top_k: int,
        filters: Optional[dict] = None,
    ) -> list[dict]:
        """
        向量语义检索

        Args:
            query: 查询文本
            top_k: 返回数量
            filters: 元数据过滤条件

        Returns:
            文档列表 [{"id": str, "content": str, "metadata": dict, "score": float}, ...]
        """
        try:
            where_filter = filters if filters else None
            results = self.kb.collection.query(
                query_texts=[query],
                n_results=top_k,
                where=where_filter,
            )
            docs: list[dict] = []
            ids = results.get("ids", [[]])[0]
            documents = results.get("documents", [[]])[0]
            metadatas = results.get("metadatas", [[]])[0]
            distances = results.get("distances", [[]])[0]

            for i in range(len(ids)):
                # 将 ChromaDB 的 distance 转换为相似度分数 (1 - distance)
                # ChromaDB 默认使用余弦距离，距离越小越相似
                score = 1.0 - distances[i] if i < len(distances) else 0.0
                docs.append({
                    "id": ids[i],
                    "content": documents[i] if i < len(documents) else "",
                    "metadata": metadatas[i] if i < len(metadatas) else {},
                    "score": round(score, 4),
                })
            return docs
        except Exception as exc:
            logger.error(f"向量检索失败: {exc}")
            return []

    def _bm25_search(self, query: str, top_k: int) -> list[dict]:
        """
        BM25 关键词检索

        使用 jieba 分词构建 BM25 索引，对全量文档进行关键词匹配。

        Args:
            query: 查询文本
            top_k: 返回数量

        Returns:
            文档列表
        """
        try:
            # 获取全量文档构建 BM25 索引
            all_data = self.kb.collection.get()
            all_ids = all_data.get("ids", [])
            all_docs = all_data.get("documents", [])
            all_metadatas = all_data.get("metadatas", [])

            if not all_docs:
                logger.warning("BM25 检索: 知识库为空")
                return []

            # jieba 分词构建语料
            tokenized_corpus = [list(jieba.cut(doc)) for doc in all_docs]
            bm25 = BM25Okapi(tokenized_corpus)

            # 对查询分词并计算 BM25 分数
            tokenized_query = list(jieba.cut(query))
            scores = bm25.get_scores(tokenized_query)

            # 按分数降序排序，取 top_k
            ranked = sorted(
                enumerate(scores), key=lambda x: x[1], reverse=True
            )[:top_k]

            results: list[dict] = []
            for idx, score in ranked:
                results.append({
                    "id": all_ids[idx] if idx < len(all_ids) else "",
                    "content": all_docs[idx],
                    "metadata": all_metadatas[idx] if idx < len(all_metadatas) else {},
                    "score": round(float(score), 4),
                })
            return results
        except Exception as exc:
            logger.error(f"BM25 检索失败: {exc}")
            return []

    @staticmethod
    def _rrf_fusion(
        vector_results: list[dict],
        bm25_results: list[dict],
        top_k: int,
    ) -> list[dict]:
        """
        RRF (Reciprocal Rank Fusion) 融合两路检索结果

        公式: RRF_score(d) = sum( 1 / (k + rank_i(d)) )
        其中 k=60 为平滑参数

        Args:
            vector_results: 向量检索结果
            bm25_results: BM25 检索结果
            top_k: 最终返回数量

        Returns:
            融合排序后的文档列表
        """
        rrf_scores: dict[str, float] = {}
        doc_map: dict[str, dict] = {}

        # 处理向量检索结果
        for rank, doc in enumerate(vector_results, start=1):
            doc_id = doc["id"]
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + 1.0 / (RRF_K + rank)
            if doc_id not in doc_map:
                doc_map[doc_id] = {
                    "id": doc["id"],
                    "content": doc["content"],
                    "metadata": doc["metadata"],
                    "source_type": "vector",
                }

        # 处理 BM25 检索结果
        for rank, doc in enumerate(bm25_results, start=1):
            doc_id = doc["id"]
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + 1.0 / (RRF_K + rank)
            if doc_id not in doc_map:
                doc_map[doc_id] = {
                    "id": doc["id"],
                    "content": doc["content"],
                    "metadata": doc["metadata"],
                    "source_type": "bm25",
                }
            else:
                # 同时被两路检索到，标记为 hybrid
                doc_map[doc_id]["source_type"] = "hybrid"

        # 按 RRF 分数降序排序
        sorted_ids = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        top_ids = sorted_ids[:top_k]

        results: list[dict] = []
        for doc_id, rrf_score in top_ids:
            doc = doc_map[doc_id].copy()
            doc["score"] = round(rrf_score, 4)
            results.append(doc)

        return results
