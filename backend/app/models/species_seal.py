from datetime import datetime
from typing import List, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SpeciesSeal(Base):
    """物种封印：出菇室进入 fruiting 时把当时的 species 抄一份封印。

    封印未解除（released_at 为空）期间，出菇室的 species 不允许修改。
    同一间出菇室同时只允许有一张 released_at 为空的封印。
    """

    __tablename__ = "species_seals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id"), nullable=False, index=True)
    species: Mapped[str] = mapped_column(String(64), nullable=False)
    sealed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    released_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    release_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    room: Mapped["Room"] = relationship("Room", back_populates="species_seals")
