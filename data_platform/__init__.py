"""
data_platform — 数据平台模块

负责商品数据接入、清洗、加工与向量化入库。
提供从原始数据到可检索知识库的完整 ETL 流水线。

对外暴露的核心接口：
    - MaterialAssociation   (SQLAlchemy Model): 素材-商品关联表
    - CleaningLog           (SQLAlchemy Model): 清洗日志表
    - DataCleaner           (class): 数据清洗器
    - DataPipeline          (class): ETL 流水线编排器
    - BatchEmbedder         (class): 批量向量化与入库
"""

from data_platform.models import CleaningLog, MaterialAssociation
from data_platform.cleaner import DataCleaner
from data_platform.pipeline import DataPipeline
from data_platform.batch_embedder import BatchEmbedder

__all__ = [
    "CleaningLog",
    "MaterialAssociation",
    "DataCleaner",
    "DataPipeline",
    "BatchEmbedder",
]
