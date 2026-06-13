from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.model_base import Base


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="板块id")
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="板块名称")
    description: Mapped[str] = mapped_column(String(255), nullable=True, default="", comment="板块描述")
    icon: Mapped[str] = mapped_column(String(50), nullable=True, default="", comment="板块图标")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, comment="排序权重")

    posts: Mapped[list["Posts"]] = relationship("Posts", back_populates="category")
