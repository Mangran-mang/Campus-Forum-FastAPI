from datetime import datetime

from sqlalchemy import Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.model_base import Base


class Image(Base):
    __tablename__ = "images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="图片ID")
    filename: Mapped[str] = mapped_column(String(255), nullable=False, comment="存储文件名")
    target_type: Mapped[str] = mapped_column(String(10), nullable=False, comment="关联类型(post/goods)")
    target_id: Mapped[str] = mapped_column(String(36), nullable=False, comment="关联目标ID")
    author_uid: Mapped[str] = mapped_column(String(36), ForeignKey("user.uid"), nullable=False, comment="上传者ID")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, comment="排序序号")
    created_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="上传时间")

    author: Mapped["User"] = relationship("User", back_populates="images")
