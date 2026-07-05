from datetime import date

from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class MPLADsAllocatedLimit(Base):
    __tablename__ = "mplads_allocated_limit"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    constituency: Mapped[str] = mapped_column(String(128))
    mp_name: Mapped[str] = mapped_column(String(256))
    allocated_amount: Mapped[int] = mapped_column(BigInteger)
    lok_sabha_term: Mapped[str] = mapped_column(String(16))  # "17th" | "18th"


class MPLADsWork(Base):
    """One row per unique MPLADs work code (e.g. WS/MP618/2024-2025/156002), merged across
    the Works Recommended/Sanctioned/Completed source files — each file only fills in the
    columns for the stage(s) it covers. `work_code` is the natural key linking a work's
    lifecycle across the three CSVs.
    """

    __tablename__ = "mplads_work"

    work_code: Mapped[str] = mapped_column(String(128), primary_key=True)
    category: Mapped[str | None] = mapped_column(String(128))
    work_title: Mapped[str] = mapped_column(String(512))
    ida: Mapped[str | None] = mapped_column(String(256))
    mp_name: Mapped[str] = mapped_column(String(256))
    constituency: Mapped[str] = mapped_column(String(128))
    lok_sabha_term: Mapped[str] = mapped_column(String(16))

    recommended_date: Mapped[date | None]
    recommended_amount: Mapped[int | None] = mapped_column(BigInteger)

    sanction_date: Mapped[date | None]
    sanction_stage: Mapped[str | None] = mapped_column(String(64))
    sanction_amount: Mapped[int | None] = mapped_column(BigInteger)

    completed_date: Mapped[date | None]
    completed_rating: Mapped[str | None] = mapped_column(String(32))
    completed_amount: Mapped[int | None] = mapped_column(BigInteger)

    # Fuzzy-matched from work_title's embedded village/place mention (see app.ingestion.mplads).
    matched_lgd_village_code: Mapped[int | None]
    match_score: Mapped[float | None]


class MPLADsExpenditure(Base):
    """Per-disbursement transaction records — multiple rows can share the same work_id."""

    __tablename__ = "mplads_expenditure"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    work_id: Mapped[str] = mapped_column(String(128))
    work_title: Mapped[str] = mapped_column(String(512))
    vendor_name: Mapped[str | None] = mapped_column(String(256))
    ida: Mapped[str | None] = mapped_column(String(256))
    mp_name: Mapped[str] = mapped_column(String(256))
    constituency: Mapped[str] = mapped_column(String(128))
    lok_sabha_term: Mapped[str] = mapped_column(String(16))
    expenditure_date: Mapped[date | None]
    work_status: Mapped[str | None] = mapped_column(String(64))
    amount: Mapped[int | None] = mapped_column(BigInteger)
