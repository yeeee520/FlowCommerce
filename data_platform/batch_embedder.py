"""
data_platform.batch_embedder — 批量向量化与入库

将清洗后的文本批量生成嵌入向量并存入 ChromaDB。
"""

import logging
import time
import uuid
from typing import Optional

import chromadb

from config import BATCH_SIZE, MAX_RETRIES

logger = logging.getLogger(__name__)


class BatchEmbedder:
    """
    批量嵌入生成与入库器

    职责：
    - 使用 ChromaDB 内置本地嵌入模型（all-MiniLM-L6-v2）生成向量
    - 批量写入 ChromaDB collection
    - 支持增量更新和幂等写入
    - 失败重试与速率限制

    注意：嵌入由 ChromaDB collection 内置的 ONNX 模型本地完成，
    无需外部 API，兼容 DeepSeek 等不提供嵌入接口的 LLM 服务。

    接口契约：
        embed_and_store(
            texts: list[str],
            metadatas: Optional[list[dict]] = None,
            ids: Optional[list[str]] = None,
        ) -> list[str]
            - 参数: texts — 待嵌入的文本列表
            - 参数: metadatas — 每条文本的元数据（可选）
            - 参数: ids — 自定义文档 ID（可选，默认自动生成）
            - 返回: 成功写入的文档 ID 列表
    """

    def __init__(
        self,
        collection: chromadb.Collection,
    ) -> None:
        """
        Args:
            collection: ChromaDB collection 实例（需已配置默认嵌入函数）
        """
        self.collection: chromadb.Collection = collection

    def embed_and_store(
        self,
        texts: list[str],
        metadatas: Optional[list[dict]] = None,
        ids: Optional[list[str]] = None,
    ) -> list[str]:
        """
        批量生成嵌入并存入向量库

        支持分批处理，每批大小由 BATCH_SIZE 配置控制。
        带重试机制，失败时最多重试 MAX_RETRIES 次。

        Args:
            texts: 文本列表
            metadatas: 元数据列表，与 texts 一一对应
            ids: 自定义 ID 列表，不提供则自动生成 UUID

        Returns:
            成功写入的文档 ID 列表
        """
        if not texts:
            logger.warning("embed_and_store: 文本列表为空，跳过")
            return []

        # 如果没有提供 ids，自动生成
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in range(len(texts))]
        if metadatas is None:
            metadatas = [{} for _ in range(len(texts))]

        if len(texts) != len(ids) or len(texts) != len(metadatas):
            raise ValueError(
                f"texts({len(texts)}), ids({len(ids)}), metadatas({len(metadatas)}) 长度不一致"
            )

        all_stored_ids: list[str] = []
        total = len(texts)

        for batch_start in range(0, total, BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE, total)
            batch_texts = texts[batch_start:batch_end]
            batch_metadatas = metadatas[batch_start:batch_end]
            batch_ids = ids[batch_start:batch_end]

            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    self.collection.add(
                        documents=batch_texts,
                        metadatas=batch_metadatas,
                        ids=batch_ids,
                    )
                    all_stored_ids.extend(batch_ids)
                    logger.debug(
                        f"批次 [{batch_start}:{batch_end}] 写入成功 "
                        f"({len(batch_ids)} 条), 第 {attempt} 次尝试"
                    )
                    break
                except Exception as exc:
                    logger.error(
                        f"批次 [{batch_start}:{batch_end}] 第 {attempt}/{MAX_RETRIES} 次写入失败: {exc}"
                    )
                    if attempt < MAX_RETRIES:
                        time.sleep(2 ** attempt)  # 指数退避
                    else:
                        logger.critical(
                            f"批次 [{batch_start}:{batch_end}] 重试 {MAX_RETRIES} 次后仍失败，跳过该批次"
                        )

        logger.info(f"embed_and_store 完成: {len(all_stored_ids)}/{total} 条成功写入")
        return all_stored_ids
