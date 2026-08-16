from sqlalchemy import String, Integer
from sqlalchemy.orm import mapped_column, Mapped, relationship

from typing import TYPE_CHECKING, List

from models.model_base import Base

if TYPE_CHECKING:
    from models.model_goods import Goods

class GoodsClassify(Base):
    __tablename__ = "goods_classify"
    id: Mapped[int] = mapped_column(Integer,primary_key=True)
    name: Mapped[str] = mapped_column(String(30), nullable=False)

    goods: Mapped[List["Goods"]] = relationship(
        back_populates="classify_rel"
        )