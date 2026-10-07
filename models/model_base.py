from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    created_time: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        comment="创建时间",
        index=True,
    )