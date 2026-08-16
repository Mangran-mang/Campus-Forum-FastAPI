from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from models.model_base import Base


class LevelConfig(Base):
    """
    等级定义表（配置表，固定 10 行）
    存储每一级的等级编号、名称与升级所需的最小经验值。
    用户的实际等级永远由 experience 对照本表推导，本表只作为规则来源。
    """
    __tablename__ = "level_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键")
    level: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, comment="等级")
    name: Mapped[str] = mapped_column(String(50), nullable=False, comment="等级名称")
    min_experience: Mapped[int] = mapped_column(Integer, nullable=False, comment="升级到该等级所需的最小经验值")
