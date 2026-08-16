import uuid
from datetime import datetime
from typing import TYPE_CHECKING


from sqlalchemy import String, DateTime, Enum, DECIMAL, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.model_base import Base

if TYPE_CHECKING:
    from models.model_goods_classify import GoodsClassify
    from models.model_user import User
else:
    GoodsClassify = None
    User = None

class Goods(Base):
    __tablename__ = "goods"
    gid: Mapped[str] = mapped_column(String(36),primary_key=True, nullable= False,default=lambda :str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(30), nullable=False)
    classify: Mapped[int] = mapped_column(Integer, ForeignKey("goods_classify.id"), nullable=False)
    author_uid: Mapped[str] = mapped_column(String(36), ForeignKey("user.uid"), nullable=False, comment="发布者用户ID")
    status: Mapped[str] = mapped_column(Enum('在售','已售出'), nullable=False)
    price: Mapped[DECIMAL] = mapped_column(DECIMAL(10,2), nullable=False)
    update_time: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
        comment="更新时间"
    )

    classify_rel: Mapped["GoodsClassify"] = relationship(
        back_populates="goods"
        )
    author: Mapped["User"] = relationship(back_populates="goods")
