from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class KnowYourSchool(Base):
    """UDISE school directory (Know Your School JSON). No enrollment/facility fields exist
    in the source — despite the project brief's assumption, this only gives a school
    directory (location, management type, category, operational status), so the fact
    table's school signal is school-count-only, not enrollment-vs-capacity.
    """

    __tablename__ = "know_your_school"

    school_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    udise_code: Mapped[str] = mapped_column(String(16))
    school_name: Mapped[str] = mapped_column(String(256))
    district_name: Mapped[str] = mapped_column(String(128))
    block_name: Mapped[str | None] = mapped_column(String(128))
    village_name: Mapped[str | None] = mapped_column(String(256))
    village_cd: Mapped[str | None] = mapped_column(String(32))
    mgmt_desc: Mapped[str | None] = mapped_column(String(128))
    category_desc: Mapped[str | None] = mapped_column(String(128))
    is_operational: Mapped[bool] = mapped_column(Boolean)
    lgd_village_id: Mapped[int | None] = mapped_column(Integer)
    lgd_village_name: Mapped[str | None] = mapped_column(String(256))

    # Fuzzy-matched to lgd_village when lgd_village_id isn't populated in the source (common
    # for private/urban schools) — see app.ingestion.know_your_school.
    matched_lgd_village_code: Mapped[int | None] = mapped_column(Integer)
    match_score: Mapped[float | None]
