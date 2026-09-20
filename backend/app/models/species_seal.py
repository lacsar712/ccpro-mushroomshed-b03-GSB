from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SpeciesSeal(Base):
    """出菇室品种封印：进入 fruiting 时把当时的品种封存，解封前禁止改品种。"""

    __tablename__ = "species_seals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id"), nullable=False, index=True)
    species: Mapped[str] = mapped_column(String(64), nullable=False)
    sealed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    released_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    release_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    released_by: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    room: Mapped["Room"] = relationship("Room", back_populates="species_seals")
