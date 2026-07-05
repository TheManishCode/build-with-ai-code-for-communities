from geoalchemy2 import Geometry
from sqlalchemy import Boolean, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class PMGSYHabitation(Base):
    """PMGSY habitation points. No LGD code and no connectivity attribute — see
    PMGSYRoadProposal/PMGSYRoadDRRP; connectivity must be derived via spatial join.
    59 of 61,990 statewide points have corrupt coordinates (bbox-filtered on ingest).
    """

    __tablename__ = "pmgsy_habitation"

    hab_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    district_id: Mapped[int] = mapped_column(Integer)
    block_id: Mapped[int] = mapped_column(Integer)
    hab_name: Mapped[str] = mapped_column(String(256))
    population: Mapped[int | None] = mapped_column(Integer)
    is_coord_valid: Mapped[bool] = mapped_column(Boolean, default=True)
    geom: Mapped[str] = mapped_column(Geometry(geometry_type="POINT", srid=4326))


class PMGSYRoadProposal(Base):
    """Proposed-road lines from the 5 Proposal_* zips (PM-JANMAN, PMGSY-I/II/III/IV)."""

    __tablename__ = "pmgsy_road_proposal"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    mrl_id: Mapped[int | None] = mapped_column(Integer)
    phase: Mapped[str] = mapped_column(String(16))  # PM-JANMAN | PMGSY-I | ... | PMGSY-IV
    lgd_district_code: Mapped[int | None] = mapped_column(Integer)
    block_id: Mapped[int | None] = mapped_column(Integer)
    cn_code: Mapped[float | None] = mapped_column(Float)
    proposed_length_km: Mapped[float | None] = mapped_column(Float)
    work_name: Mapped[str | None] = mapped_column(String(512))
    ims_year: Mapped[str | None] = mapped_column(String(32))
    proposal_type: Mapped[str | None] = mapped_column(String(8))
    geom: Mapped[str] = mapped_column(Geometry(geometry_type="LINESTRING", srid=4326))


class PMGSYRoadDRRP(Base):
    """The master District Rural Road Plan network — the only PMGSY layer with a road
    category field (RoadCatego), including RR(VR) = Village Road."""

    __tablename__ = "pmgsy_road_drrp"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    er_id: Mapped[int] = mapped_column(Integer)
    district_id: Mapped[int] = mapped_column(Integer)
    block_id: Mapped[int | None] = mapped_column(Integer)
    road_code: Mapped[str | None] = mapped_column(String(64))
    road_category: Mapped[str | None] = mapped_column(String(16))
    road_name: Mapped[str | None] = mapped_column(String(256))
    road_owner: Mapped[str | None] = mapped_column(String(32))
    geom: Mapped[str] = mapped_column(Geometry(geometry_type="LINESTRING", srid=4326))
