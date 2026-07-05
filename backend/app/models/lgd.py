from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class LGDDistrict(Base):
    """LGD district master. PK is the LGD district code (from villageofSpecificState / districtofSpecificState)."""

    __tablename__ = "lgd_district"

    district_code: Mapped[int] = mapped_column(primary_key=True)
    district_name: Mapped[str] = mapped_column(String(128))
    census2001_code: Mapped[str | None] = mapped_column(String(16))
    census2011_code: Mapped[str | None] = mapped_column(String(16))


class LGDSubdistrict(Base):
    __tablename__ = "lgd_subdistrict"

    subdistrict_code: Mapped[int] = mapped_column(primary_key=True)
    subdistrict_name: Mapped[str] = mapped_column(String(128))
    district_code: Mapped[int] = mapped_column(ForeignKey("lgd_district.district_code"))
    census2001_code: Mapped[str | None] = mapped_column(String(16))
    census2011_code: Mapped[str | None] = mapped_column(String(16))


class LGDBlock(Base):
    """Blocks/talukas have no Census 2011 equivalent code — join via district_code + name only."""

    __tablename__ = "lgd_block"

    block_code: Mapped[int] = mapped_column(primary_key=True)
    block_name: Mapped[str] = mapped_column(String(128))
    district_code: Mapped[int] = mapped_column(ForeignKey("lgd_district.district_code"))


class LGDVillage(Base):
    """LGD village master (villageofSpecificState*.xls). ~30.7k rows for Karnataka.

    census2011_code is the join key into the Census Village Amenities table, which is keyed
    by Census 2011 codes rather than LGD codes.
    """

    __tablename__ = "lgd_village"

    village_code: Mapped[int] = mapped_column(primary_key=True)
    village_name: Mapped[str] = mapped_column(String(256))
    village_name_local: Mapped[str | None] = mapped_column(String(256))
    district_code: Mapped[int] = mapped_column(ForeignKey("lgd_district.district_code"))
    subdistrict_code: Mapped[int | None] = mapped_column(ForeignKey("lgd_subdistrict.subdistrict_code"))
    census2001_code: Mapped[str | None] = mapped_column(String(16))
    census2011_code: Mapped[str | None] = mapped_column(String(16), index=True)
    village_status: Mapped[str | None] = mapped_column(String(32))


class LGDLocalBody(Base):
    """PRI hierarchy (Zila/Taluk/Gram Panchayat), self-referencing via parent_localbody_code."""

    __tablename__ = "lgd_local_body"

    localbody_code: Mapped[int] = mapped_column(primary_key=True)
    localbody_type_name: Mapped[str] = mapped_column(String(64))
    localbody_name: Mapped[str] = mapped_column(String(256))
    parent_localbody_code: Mapped[int | None] = mapped_column(ForeignKey("lgd_local_body.localbody_code"))


class LGDVillageGPMapping(Base):
    __tablename__ = "lgd_village_gp_mapping"

    village_code: Mapped[int] = mapped_column(ForeignKey("lgd_village.village_code"), primary_key=True)
    local_body_code: Mapped[int] = mapped_column(ForeignKey("lgd_local_body.localbody_code"))
