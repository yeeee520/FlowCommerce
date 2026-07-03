"""
api.data — 数据管理 API 路由

提供知识库数据的上传、查询、删除等管理接口。
"""

import logging
import os
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from data_platform.pipeline import DataPipeline
from rag.knowledge_base import KnowledgeBase
from rag.retriever import Retriever

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/data")

# 模块级别单例
_kb: Optional[KnowledgeBase] = None
_retriever: Optional[Retriever] = None


def get_kb() -> KnowledgeBase:
    """获取 KnowledgeBase 单例"""
    global _kb
    if _kb is None:
        _kb = KnowledgeBase()
    return _kb


def get_retriever() -> Retriever:
    """获取 Retriever 单例"""
    global _retriever
    if _retriever is None:
        _retriever = Retriever(knowledge_base=get_kb())
    return _retriever


# ============================================================
# 请求/响应模型
# ============================================================

class DocumentQuery(BaseModel):
    """文档查询请求"""
    query: str = Field(..., description="搜索查询文本")
    top_k: Optional[int] = Field(default=5, description="返回数量", ge=1, le=50)


class DocumentItem(BaseModel):
    """单个文档条目"""
    id: str = Field(..., description="文档 ID")
    text: str = Field(..., description="文档内容")
    metadata: dict = Field(default_factory=dict, description="元数据")
    score: Optional[float] = Field(default=None, description="相关性分数")


class DocumentQueryResponse(BaseModel):
    """文档查询响应"""
    results: list[DocumentItem] = Field(default_factory=list, description="查询结果")
    total: int = Field(..., description="结果总数")


class DataUploadResponse(BaseModel):
    """数据上传响应"""
    status: str = Field(..., description="处理状态")
    total: int = Field(..., description="处理总数")
    success: int = Field(default=0, description="成功数")
    failed: int = Field(default=0, description="失败数")


class KnowledgeBaseStats(BaseModel):
    """知识库统计信息"""
    document_count: int = Field(..., description="文档总数")
    collection_name: str = Field(..., description="Collection 名称")


# ============================================================
# 路由
# ============================================================

@router.post("/upload", response_model=DataUploadResponse, summary="上传数据文件")
async def upload_data(file: UploadFile = File(...)) -> DataUploadResponse:
    """
    上传 JSON/CSV 数据文件，触发 ETL 流水线处理。

    支持的文件格式：.json
    """
    # 校验文件类型
    if not file.filename or not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="仅支持 JSON 格式文件")

    try:
        # 保存上传文件到临时目录
        content = await file.read()
        with tempfile.NamedTemporaryFile(
            mode="wb",
            suffix=".json",
            delete=False,
        ) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        logger.info(f"上传文件已保存到临时路径: {tmp_path}")

        # 执行 ETL 流水线
        pipeline = DataPipeline()
        result = pipeline.run(source_path=tmp_path)

        # 清理临时文件
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

        return DataUploadResponse(
            status="success",
            total=result["total"],
            success=result["embedded"],
            failed=result["failed"],
        )

    except Exception as exc:
        logger.error(f"上传处理失败: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"数据处理失败: {str(exc)}")


@router.post("/search", response_model=DocumentQueryResponse, summary="检索知识库")
async def search_documents(query: DocumentQuery) -> DocumentQueryResponse:
    """
    在知识库中检索相关文档。
    使用混合检索（向量 + BM25 + RRF 融合）。
    """
    try:
        retriever = get_retriever()
        docs = retriever.retrieve(query=query.query, top_k=query.top_k)

        results = [
            DocumentItem(
                id=doc["id"],
                text=doc["content"],
                metadata=doc.get("metadata", {}),
                score=doc.get("score"),
            )
            for doc in docs
        ]

        return DocumentQueryResponse(results=results, total=len(results))

    except Exception as exc:
        logger.error(f"检索失败: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"检索失败: {str(exc)}")


@router.get("/stats", response_model=KnowledgeBaseStats, summary="知识库统计")
async def get_stats() -> KnowledgeBaseStats:
    """
    获取知识库统计信息。
    """
    try:
        kb = get_kb()
        return KnowledgeBaseStats(
            document_count=kb.count(),
            collection_name=kb.collection_name,
        )
    except Exception as exc:
        logger.error(f"获取统计信息失败: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取统计失败: {str(exc)}")


@router.delete("/documents/{doc_id}", summary="删除文档")
async def delete_document(doc_id: str) -> dict[str, str]:
    """
    按 ID 删除指定文档。
    """
    try:
        kb = get_kb()
        deleted = kb.delete_documents([doc_id])
        if deleted == 0:
            raise HTTPException(status_code=404, detail=f"文档 {doc_id} 不存在")
        return {"status": "deleted", "doc_id": doc_id}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"删除文档失败: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除失败: {str(exc)}")


@router.get("/health", summary="数据服务健康检查")
async def data_health() -> dict[str, str]:
    """检查数据服务是否就绪"""
    return {"status": "ok", "service": "data"}
