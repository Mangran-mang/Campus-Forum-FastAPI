from datetime import datetime

from sqlalchemy import Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.model_base import Base


class Image(Base):
    __tablename__ = "images"
    __table_args__ = (
        UniqueConstraint("target_type", "target_id", name="uq_image_target_type_target_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="图片ID")
    filename: Mapped[str] = mapped_column(String(255), nullable=False, comment="存储文件名")
    target_type: Mapped[str] = mapped_column(String(10), nullable=False, comment="关联类型(post/goods)")
    target_id: Mapped[str] = mapped_column(String(36), nullable=False, comment="关联目标ID")
    # ## 为什么加 ondelete="CASCADE"（2026-09-21）
    # 这条是最容易踩的：只要用户上传过【一张】配图，删用户就会 500。
    # 加了之后：删用户时，他的图片记录跟着删（磁盘上的文件不会自动删，
    # 需要业务代码处理——目前 upload_image/delete_image 只管库，不管用户注销场景）。
    author_uid: Mapped[str] = mapped_column(String(36), ForeignKey("user.uid", ondelete="CASCADE"), nullable=False, comment="上传者ID")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, comment="排序序号")
    created_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="上传时间")

    author: Mapped["User"] = relationship("User", back_populates="images")
