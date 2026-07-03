"""
rag.knowledge_base — 知识库管理

提供 ChromaDB collection 的增删改查操作，
以及文档级别的 CRUD 能力。
"""

import logging
import uuid
from typing import Optional

import chromadb
from chromadb.config import Settings

from config import CHROMA_PERSIST_DIR

logger = logging.getLogger(__name__)

# 模块级别的全局 client 和 collection，用于跨模块共享
_client: Optional[chromadb.PersistentClient] = None
_collection: Optional[chromadb.Collection] = None


def get_chroma_client() -> chromadb.PersistentClient:
    """获取或创建全局 ChromaDB 持久化客户端"""
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(
            path=CHROMA_PERSIST_DIR,
            settings=Settings(anonymized_telemetry=False),
        )
        logger.info(f"ChromaDB 客户端已初始化，持久化路径: {CHROMA_PERSIST_DIR}")
    return _client


def get_collection(collection_name: str = "knowledge_base") -> chromadb.Collection:
    """获取或创建指定名称的 collection"""
    global _collection
    client = get_chroma_client()
    _collection = client.get_or_create_collection(name=collection_name)
    logger.info(f"ChromaDB collection '{collection_name}' 已就绪，文档数: {_collection.count()}")
    return _collection


class KnowledgeBase:
    """
    知识库管理器

    职责：
    - 管理 ChromaDB collection 生命周期
    - 文档的增删改查（通过 ID）
    - 知识库元信息查询（文档数量、模型信息等）

    接口契约：
        add_documents(
            texts: list[str],
            metadatas: Optional[list[dict]] = None,
            ids: Optional[list[str]] = None,
        ) -> list[str]
            - 添加文档到知识库，返回文档 ID 列表

        delete_documents(ids: list[str]) -> int
            - 按 ID 删除文档，返回删除数量

        get_document(doc_id: str) -> Optional[dict]
            - 按 ID 查询单个文档

        count() -> int
            - 返回知识库中文档总数

        clear() -> int
            - 清空知识库并返回删除数量
    """

    def __init__(self, collection_name: str = "knowledge_base") -> None:
        """
        Args:
            collection_name: ChromaDB collection 名称
        """
        self.collection_name: str = collection_name
        self._collection: chromadb.Collection = get_collection(collection_name)

    @property
    def collection(self) -> chromadb.Collection:
        """获取底层的 ChromaDB collection 实例"""
        return self._collection

    def add_documents(
        self,
        texts: list[str],
        metadatas: Optional[list[dict]] = None,
        ids: Optional[list[str]] = None,
    ) -> list[str]:
        """
        批量添加文档

        Args:
            texts: 文档文本列表
            metadatas: 元数据列表
            ids: 自定义 ID 列表，不提供则自动生成 UUID

        Returns:
            添加成功的文档 ID 列表
        """
        if not texts:
            return []

        if ids is None:
            ids = [str(uuid.uuid4()) for _ in range(len(texts))]
        if metadatas is None:
            metadatas = [{} for _ in range(len(texts))]

        try:
            self._collection.add(
                documents=texts,
                metadatas=metadatas,
                ids=ids,
            )
            logger.info(f"添加 {len(ids)} 条文档到知识库 '{self.collection_name}'")
            return ids
        except Exception as exc:
            logger.error(f"添加文档失败: {exc}")
            raise

    def delete_documents(self, ids: list[str]) -> int:
        """
        按 ID 批量删除文档

        Args:
            ids: 文档 ID 列表

        Returns:
            实际删除的文档数量
        """
        if not ids:
            return 0
        try:
            # 先获取集合中存在的 ID，避免删除不存在的 ID 导致报错
            existing = self._collection.get(ids=ids)
            existing_ids = existing.get("ids", [])
            if not existing_ids:
                logger.warning(f"要删除的 {len(ids)} 个文档均不存在")
                return 0
            self._collection.delete(ids=existing_ids)
            logger.info(f"从知识库删除 {len(existing_ids)} 条文档")
            return len(existing_ids)
        except Exception as exc:
            logger.error(f"删除文档失败: {exc}")
            raise

    def get_document(self, doc_id: str) -> Optional[dict]:
        """
        查询单个文档

        Args:
            doc_id: 文档 ID

        Returns:
            文档数据字典（含 id, text, metadata），不存在返回 None
        """
        try:
            result = self._collection.get(ids=[doc_id])
            ids = result.get("ids", [])
            if not ids:
                return None
            return {
                "id": ids[0],
                "text": result.get("documents", [None])[0],
                "metadata": result.get("metadatas", [{}])[0],
            }
        except Exception as exc:
            logger.error(f"查询文档 {doc_id} 失败: {exc}")
            return None

    def count(self) -> int:
        """返回知识库中文档总数"""
        try:
            return self._collection.count()
        except Exception as exc:
            logger.error(f"获取文档数量失败: {exc}")
            return 0

    def clear(self) -> int:
        """
        清空知识库中所有文档

        Returns:
            删除的文档数量
        """
        try:
            cnt = self._collection.count()
            if cnt > 0:
                # 获取所有 ID 后删除
                all_ids = self._collection.get()["ids"]
                if all_ids:
                    self._collection.delete(ids=all_ids)
            logger.info(f"知识库 '{self.collection_name}' 已清空，共删除 {cnt} 条文档")
            return cnt
        except Exception as exc:
            logger.error(f"清空知识库失败: {exc}")
            raise
