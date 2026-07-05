import enum
from datetime import datetime

from sqlalchemy import ARRAY, Enum, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base

EMBEDDING_DIM = 384  # all-MiniLM-L6-v2. Stored as a plain float array (not pgvector — that
# Postgres extension isn't installed and adding it would need another admin-elevated
# install cycle like PostGIS did; dedup clustering is done in Python/numpy instead of
# in-SQL vector search, which is plenty for this dataset's scale).


class Channel(str, enum.Enum):
    voice = "voice"
    text = "text"
    photo = "photo"


class Theme(str, enum.Enum):
    water = "water"
    road = "road"
    school = "school"
    health = "health"
    electricity = "electricity"
    sanitation = "sanitation"
    other = "other"


class Submission(Base):
    """A single raw citizen development request (Phase 2)."""

    __tablename__ = "submission"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    channel: Mapped[Channel] = mapped_column(Enum(Channel, name="channel_enum"))
    raw_text: Mapped[str] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(16))  # ISO code, e.g. "kn" | "en"
    translated_text: Mapped[str | None] = mapped_column(Text)
    theme: Mapped[Theme] = mapped_column(Enum(Theme, name="theme_enum"))
    place_text: Mapped[str | None] = mapped_column(String(256))  # raw place mention extracted from text
    resolved_lgd_code: Mapped[int | None] = mapped_column(ForeignKey("lgd_village.village_code"))
    place_match_score: Mapped[float | None] = mapped_column(Float)
    lat: Mapped[float | None] = mapped_column(Float)
    lng: Mapped[float | None] = mapped_column(Float)
    urgency_score: Mapped[float | None] = mapped_column(Float)
    embedding: Mapped[list[float] | None] = mapped_column(ARRAY(Float))
    issue_id: Mapped[int | None] = mapped_column(ForeignKey("issue.id"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class Issue(Base):
    """A clustered/deduplicated issue — one row per group of near-duplicate submissions
    describing the same underlying problem (Phase 2 step 4)."""

    __tablename__ = "issue"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    theme: Mapped[Theme] = mapped_column(Enum(Theme, name="theme_enum"))
    village_code: Mapped[int | None] = mapped_column(ForeignKey("lgd_village.village_code"))
    representative_text: Mapped[str] = mapped_column(Text)
    corroboration_count: Mapped[int] = mapped_column(default=1)
    first_seen_at: Mapped[datetime] = mapped_column(server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(server_default=func.now())
