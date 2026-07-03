"""
data_platform.models — 数据平台 SQLAlchemy 数据模型

定义关系型数据库中存储的数据结构。
使用 SQLAlchemy ORM，由 SQLite 持久化。
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """声明性基类"""
    pass


class CleaningLog(Base):
    """
    数据清洗日志表

    记录每一次数据清洗操作的输入、输出和状态。
    """
    __tablename__ = "cleaning_logs"

    id: int = Column(Integer, primary_key=True, autoincrement=True)  # type: ignore[assignment]
    """主键，自增 ID"""

    raw_text: str = Column(Text, nullable=False)  # type: ignore[assignment]
    """清洗前的原始文本"""

    cleaned_text: str = Column(Text, nullable=True)  # type: ignore[assignment]
    """清洗后的文本，失败时可为空"""

    status: str = Column(String(20), nullable=False, default="pending")  # type: ignore[assignment]
    """清洗状态: pending | processing | success | failed"""

    error_message: str = Column(Text, nullable=True)  # type: ignore[assignment]
    """失败时的错误信息"""

    created_at: datetime = Column(DateTime, default=datetime.utcnow, nullable=False)  # type: ignore[assignment]
    """记录创建时间"""

    def __repr__(self) -> str:
        return f"<CleaningLog(id={self.id}, status={self.status})>"


class MaterialAssociation(Base):
    """
    素材-商品关联表

    记录图片/视频等素材与商品的对应关系，支持多对多。
    """
    __tablename__ = "material_associations"

    id: int = Column(Integer, primary_key=True, autoincrement=True)  # type: ignore[assignment]
    """主键，自增 ID"""

    material_id: str = Column(String(255), nullable=False, index=True)  # type: ignore[assignment]
    """素材唯一标识（如文件路径、URL 哈希）"""

    product_id: str = Column(String(255), nullable=False, index=True)  # type: ignore[assignment]
    """关联的商品唯一标识"""

    material_type: str = Column(String(50), nullable=False)  # type: ignore[assignment]
    """素材类型: image | video | audio"""

    created_at: datetime = Column(DateTime, default=datetime.utcnow, nullable=False)  # type: ignore[assignment]
    """记录创建时间"""

    def __repr__(self) -> str:
        return (
            f"<MaterialAssociation("
            f"material_id={self.material_id}, "
            f"product_id={self.product_id})>"
        )
