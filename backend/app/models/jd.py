"""Job Description analysis model."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class JDAnalysis(Base):
    __tablename__ = "jd_analysis"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    raw_text: Mapped[str] = mapped_column(Text, nullable=True)
    structured_data: Mapped[str] = mapped_column(Text)  # JSONB → Text/JSON for SQLite
    embedding: Mapped[str] = mapped_column(Text, nullable=True)  # JSON array
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
