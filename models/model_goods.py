import uuid
from datetime import datetime
from decimal import Decimal
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
    # ## 为什么加 ondelete="CASCADE"（2026-09-21）
    # 不加的话 MySQL 默认 NO ACTION → 发布过商品的用户删不掉（DELETE 会 500）。
    # 这里原本只写了 ForeignKey("user.uid")，连 onupdate 都没有——
    # user.uid 是 UUID 主键、永不变更，所以 onupdate 本来就没意义，不用补。
    author_uid: Mapped[str] = mapped_column(String(36), ForeignKey("user.uid", ondelete="CASCADE"), nullable=False, comment="发布者用户ID")
    status: Mapped[str] = mapped_column(Enum('在售','已售出'), nullable=False)
    price: Mapped[Decimal] = mapped_column(DECIMAL(10,2), nullable=False)
    # 这里原本写的是Mapped[DECIMAL],但python中的值类型是decimal.Decimal,
    # 因为mapped_column中显示声明了要是DECIMAL才没出错,所以还是用Mapped[Decimal]稳妥
    update_time: Mapped[datetime] = mapped_column(
        DateTime,
        index=True,
        default=datetime.now,
        onupdate=datetime.now,
        comment="更新时间"
    )

    classify_rel: Mapped["GoodsClassify"] = relationship(
        back_populates="goods"
        )
    author: Mapped["User"] = relationship(back_populates="goods")
