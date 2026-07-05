from sqlalchemy import JSON, Boolean, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class CensusVillageAmenities(Base):
    """Census 2011 District Census Handbook 'Village Amenities' table (sheet Village_Data_2900).

    Scoped to Bagalkot district on ingest, even though the source file covers all 30
    Karnataka districts (confirmed 29,340 rows / 396 cols statewide).

    `village_code` here is the Census-2011 village code, which is the SAME numbering
    scheme as `lgd_village.census2011_code` (both are the PC01 village code) — a direct
    integer join, not a fuzzy match. Only ~35 of the 396 source columns are promoted to
    typed columns below (the rest are repetitive "nearest facility distance-band" filler
    columns); `raw` preserves the full original row for provenance/traceability.
    """

    __tablename__ = "census_village_amenities"

    village_code: Mapped[int] = mapped_column(Integer, primary_key=True)
    district_name: Mapped[str] = mapped_column(String(128))
    subdistrict_name: Mapped[str | None] = mapped_column(String(128))
    village_name: Mapped[str] = mapped_column(String(256))
    cd_block_name: Mapped[str | None] = mapped_column(String(128))
    gram_panchayat_name: Mapped[str | None] = mapped_column(String(128))

    total_geographical_area_ha: Mapped[float | None] = mapped_column(Float)
    total_households: Mapped[int | None] = mapped_column(Integer)
    total_population: Mapped[int | None] = mapped_column(Integer)
    male_population: Mapped[int | None] = mapped_column(Integer)
    female_population: Mapped[int | None] = mapped_column(Integer)
    sc_population: Mapped[int | None] = mapped_column(Integer)
    st_population: Mapped[int | None] = mapped_column(Integer)

    govt_primary_schools: Mapped[int | None] = mapped_column(Integer)
    pvt_primary_schools: Mapped[int | None] = mapped_column(Integer)
    govt_middle_schools: Mapped[int | None] = mapped_column(Integer)
    pvt_middle_schools: Mapped[int | None] = mapped_column(Integer)
    govt_secondary_schools: Mapped[int | None] = mapped_column(Integer)
    pvt_secondary_schools: Mapped[int | None] = mapped_column(Integer)
    govt_sr_secondary_schools: Mapped[int | None] = mapped_column(Integer)
    pvt_sr_secondary_schools: Mapped[int | None] = mapped_column(Integer)

    primary_health_centre_count: Mapped[int | None] = mapped_column(Integer)
    primary_health_subcentre_count: Mapped[int | None] = mapped_column(Integer)
    community_health_centre_count: Mapped[int | None] = mapped_column(Integer)

    has_treated_tap_water: Mapped[bool | None] = mapped_column(Boolean)
    has_hand_pump: Mapped[bool | None] = mapped_column(Boolean)
    has_tube_well: Mapped[bool | None] = mapped_column(Boolean)
    has_covered_well: Mapped[bool | None] = mapped_column(Boolean)

    has_closed_drainage: Mapped[bool | None] = mapped_column(Boolean)
    has_open_drainage: Mapped[bool | None] = mapped_column(Boolean)
    has_no_drainage: Mapped[bool | None] = mapped_column(Boolean)

    has_pucca_road: Mapped[bool | None] = mapped_column(Boolean)
    has_all_weather_road: Mapped[bool | None] = mapped_column(Boolean)
    has_kuchha_road: Mapped[bool | None] = mapped_column(Boolean)
    has_national_highway: Mapped[bool | None] = mapped_column(Boolean)
    has_state_highway: Mapped[bool | None] = mapped_column(Boolean)

    domestic_power_supply: Mapped[bool | None] = mapped_column(Boolean)
    domestic_power_hours_summer: Mapped[float | None] = mapped_column(Float)
    domestic_power_hours_winter: Mapped[float | None] = mapped_column(Float)

    has_commercial_bank: Mapped[bool | None] = mapped_column(Boolean)
    has_cooperative_bank: Mapped[bool | None] = mapped_column(Boolean)
    has_atm: Mapped[bool | None] = mapped_column(Boolean)
    has_shg: Mapped[bool | None] = mapped_column(Boolean)

    nearest_town_name: Mapped[str | None] = mapped_column(String(256))
    nearest_town_distance_km: Mapped[float | None] = mapped_column(Float)

    raw: Mapped[dict] = mapped_column(JSON)


class CensusPCAVillage(Base):
    """Primary Census Abstract Total (PCA-TOT), Bagalkot district file, all LEVEL rows
    (DISTRICT/TALUK/VILLAGE — TOWN/WARD skipped, urban wards out of scope for this MVP).

    `town_vill_code` is a PCA-internal serial code (e.g. 127100) — NOT the same scheme as
    census2011_code/LGD village_code. VILLAGE-level rows are joined to `lgd_village` by
    fuzzy name match within the same sub-district (see app.ingestion.census_pca); the
    match quality is recorded in `lgd_village_code`/`match_score` rather than assumed.
    """

    __tablename__ = "census_pca_village"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    level: Mapped[str] = mapped_column(String(16))  # DISTRICT | TALUK | VILLAGE
    district_serial: Mapped[int] = mapped_column(Integer)
    subdistt_serial: Mapped[int | None] = mapped_column(Integer)
    town_vill_code: Mapped[int | None] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(256))
    tru: Mapped[str] = mapped_column(String(16))  # Total | Rural | Urban

    total_households: Mapped[int | None] = mapped_column(Integer)
    total_population: Mapped[int | None] = mapped_column(Integer)
    male_population: Mapped[int | None] = mapped_column(Integer)
    female_population: Mapped[int | None] = mapped_column(Integer)
    literate_population: Mapped[int | None] = mapped_column(Integer)
    illiterate_population: Mapped[int | None] = mapped_column(Integer)
    total_workers: Mapped[int | None] = mapped_column(Integer)
    main_workers: Mapped[int | None] = mapped_column(Integer)
    marginal_workers: Mapped[int | None] = mapped_column(Integer)
    non_workers: Mapped[int | None] = mapped_column(Integer)

    lgd_village_code: Mapped[int | None] = mapped_column(Integer)
    match_score: Mapped[float | None] = mapped_column(Float)
