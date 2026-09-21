from datetime import datetime

from sqlalchemy import Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.model_base import Base


class Image(Base):
    __tablename__ = "images"
    # ## 这里原本有一条 UniqueConstraint，2026-09-21 已删除（连同上面的 import）
    #     UniqueConstraint("target_type", "target_id", name="uq_image_target_type_target_id")
    #
    # 它的语义是"一个目标只能有一张图"，和业务直接冲突：
    # 帖子和商品都要支持多图（crud/image.py 有 MAX_IMAGES_PER_TARGET=5 的数量上限，
    # 本表还有 sort_order 排序），加上它之后传第二张图就会 IntegrityError。
    #
    # 为什么之前一直没炸：这条约束只写在模型里、从没进过任何迁移，
    # 所以数据库里根本没有它（information_schema 实测确认）。
    # 但它是个定时炸弹 —— 哪天跑 alembic autogenerate 就会被加进迁移。
    #
    # 注意：删掉它【不需要】迁移 —— 数据库本来就没有，删完模型和库反而一致了。
    # 验证方法：alembic check（不再报这条即可）。

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
