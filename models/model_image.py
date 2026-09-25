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
    # ## 为什么补 unique=True（2026-09-25）
    # 数据库里 images.filename 上【本来就有】唯一索引（`SHOW INDEX FROM images` 实测
    # Non_unique=0），而模型没写 —— 这是"库比模型严"的漂移。
    # 后果：autogenerate 每次都想去 `drop_index('filename')` 把它删掉，
    # 那是**功能回归**（filename 是 UUID，唯一性天然成立，这条索引是防重复的保护）。
    #
    # 漂移的修法有两种，判据是"这个约束是不是我们**想要**的"：
    #   想要 → 把模型补成和库一致（这里就是这种）
    #   不想要 → 写迁移把库改成和模型一致（例如 9/21 删掉的那条 target 唯一约束）
    # 无脑跟着 autogenerate 走会把两种漂移都往"模型"的方向拉，删掉不该删的东西。
    filename: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, comment="存储文件名")
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
