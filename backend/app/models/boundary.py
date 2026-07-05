from geoalchemy2 import Geometry
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class PCBoundary(Base):
    """Parliamentary Constituency boundaries (2024 KML). Scoped to Karnataka's 28 PCs on ingest."""

    __tablename__ = "pc_boundary"

    pc_id: Mapped[int] = mapped_column(primary_key=True)
    st_name: Mapped[str] = mapped_column(String(64))
    pc_no: Mapped[int]
    pc_name: Mapped[str] = mapped_column(String(128))
    geom: Mapped[str] = mapped_column(Geometry(geometry_type="GEOMETRY", srid=4326))
