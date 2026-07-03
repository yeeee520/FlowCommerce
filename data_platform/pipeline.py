"""
data_platform.pipeline — ETL 流水线编排器

将清洗、分块、向量化等步骤串联为完整的处理流水线。
支持断点续跑、进度上报和异常恢复。
"""

import json
import logging
from pathlib import Path
from typing import Callable, Optional

from data_platform.batch_embedder import BatchEmbedder
from data_platform.cleaner import DataCleaner
from rag.knowledge_base import get_collection

logger = logging.getLogger(__name__)


class DataPipeline:
    """
    ETL 数据流水线编排器

    职责：
    - 从数据源加载原始商品数据
    - 调用 DataCleaner 清洗
    - 调用 BatchEmbedder 向量化并入库
    - 全流程状态追踪与异常处理

    接口契约：
        run(
            source_path: str,
            on_progress: Optional[Callable[[int, int], None]] = None,
        ) -> dict[str, int]
            - 参数: source_path — 数据源文件路径（JSON/CSV）
            - 参数: on_progress — 可选进度回调 (current, total)
            - 返回: {"total": int, "cleaned": int, "embedded": int, "failed": int}
    """

    def __init__(self, cleaner: Optional[DataCleaner] = None) -> None:
        """
        Args:
            cleaner: 清洗器实例，不提供则使用默认实现
        """
        self.cleaner: DataCleaner = cleaner or DataCleaner()
        self._collection = get_collection()

    def run(
        self,
        source_path: str | Path,
        on_progress: Optional[Callable[[int, int], None]] = None,
    ) -> dict[str, int]:
        """
        执行完整 ETL 流水线

        流程：
        1. 从 source_path 读取 JSON 格式数据
        2. 提取每条数据的文本内容（dialogue user+assistant 拼接）
        3. 调用 DataCleaner 清洗
        4. 调用 BatchEmbedder 向量化并存入 ChromaDB
        5. 通过 on_progress 回调报告进度

        Args:
            source_path: 数据源文件路径
            on_progress: 进度回调 (当前索引, 总数)

        Returns:
            处理结果统计字典: {"total": N, "cleaned": N, "embedded": N, "failed": N}
        """
        source_path = Path(source_path)
        if not source_path.exists():
            raise FileNotFoundError(f"数据源文件不存在: {source_path}")

        logger.info(f"开始执行 ETL 流水线，数据源: {source_path}")

        # 1. 加载数据
        with open(source_path, "r", encoding="utf-8") as f:
            raw_data: list[dict] = json.load(f)

        # 2. 提取文本内容：从 sample_dialogues 结构中提取 dialogue
        texts: list[str] = []
        metadatas: list[dict] = []
        ids: list[str] = []

        for item in raw_data:
            item_id = item.get("id", "")
            product_name = item.get("product_name", "")
            category = item.get("category", "")
            attributes = item.get("attributes", {})
            dialogues = item.get("dialogues", [])

            # 将每个 dialogue 的 user+assistant 拼接为一条文档
            for di, dialogue in enumerate(dialogues):
                user_msg = dialogue.get("user", "")
                assistant_msg = dialogue.get("assistant", "")
                combined_text = f"Q: {user_msg}\nA: {assistant_msg}"
                texts.append(combined_text)
                metadatas.append({
                    "product_id": item_id,
                    "product_name": product_name,
                    "category": category,
                    "dialogue_index": di,
                    **attributes,
                })
                ids.append(f"{item_id}_dialogue_{di}")

        total = len(texts)
        logger.info(f"提取到 {total} 条待处理文本")

        # 3. 清洗
        cleaned_texts: list[str] = []
        cleaned_metadatas: list[dict] = []
        cleaned_ids: list[str] = []
        failed_count = 0

        for i, text in enumerate(texts):
            cleaned, log = self.cleaner.clean(text)
            if log.status == "success":
                cleaned_texts.append(cleaned)
                cleaned_metadatas.append(metadatas[i])
                cleaned_ids.append(ids[i])
            else:
                failed_count += 1
                logger.warning(f"文本 {i} ({ids[i]}) 清洗失败: {log.error_message}")

            if on_progress:
                on_progress(i + 1, total)

        cleaned_count = len(cleaned_texts)
        logger.info(f"清洗完成: {cleaned_count} 成功, {failed_count} 失败")

        # 4. 向量化入库
        embedded_count = 0
        if cleaned_texts:
            embedder = BatchEmbedder(collection=self._collection)
            stored_ids = embedder.embed_and_store(
                texts=cleaned_texts,
                metadatas=cleaned_metadatas,
                ids=cleaned_ids,
            )
            embedded_count = len(stored_ids)
            logger.info(f"向量化入库完成: {embedded_count} 条")

        result = {
            "total": total,
            "cleaned": cleaned_count,
            "embedded": embedded_count,
            "failed": failed_count,
        }
        logger.info(f"ETL 流水线完成: {result}")
        return result
