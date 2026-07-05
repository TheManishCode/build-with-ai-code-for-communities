from geoalchemy2 import Geometry
from sqlalchemy import BigInteger, Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class VillageFact(Base):
    """The single materialized village-level fact table every ranking/scoring feature
    reads from. Built by app.ingestion.build_village_fact by joining:
      - lgd_village (spine)
      - census_village_amenities (population, schools, health, water, roads, electricity,
        banking — joined by census2011_code == village_code, a direct integer join)
      - census_pca_village (literacy, workforce — joined by fuzzy name match, see
        app.ingestion.census_pca; match_score preserved so low-confidence joins are visible)
      - know_your_school (school count — aggregated by matched_lgd_village_code)
      - pmgsy_habitation + pmgsy_road_drrp/proposal (pmgsy_connected — spatial join, see
        app.ingestion.build_village_fact)
      - mplads_work (historical/current MPLADs spend — aggregated by matched_lgd_village_code)

    NOTE on JJM: none of the JJM Reports files resolve to village granularity (confirmed
    state-level-only across every CSV and WQ .xls file inspected) — there is no FHTC%
    signal here. `has_treated_tap_water`/`has_hand_pump`/etc. from the Census Village
    Amenities table are used as the water-infrastructure gap proxy instead.
    """

    __tablename__ = "village_fact"

    village_code: Mapped[int] = mapped_column(ForeignKey("lgd_village.village_code"), primary_key=True)
    village_name: Mapped[str] = mapped_column(String(256))
    subdistrict_name: Mapped[str | None] = mapped_column(String(128))
    gram_panchayat_name: Mapped[str | None] = mapped_column(String(128))
    district_name: Mapped[str] = mapped_column(String(128))

    # Population / demographics (census_village_amenities; census2011_code join)
    total_population: Mapped[int | None] = mapped_column(Integer)
    total_households: Mapped[int | None] = mapped_column(Integer)
    sc_population: Mapped[int | None] = mapped_column(Integer)
    st_population: Mapped[int | None] = mapped_column(Integer)

    # Literacy / workforce (census_pca_village; fuzzy-name join — see match_score)
    literate_population: Mapped[int | None] = mapped_column(Integer)
    illiterate_population: Mapped[int | None] = mapped_column(Integer)
    literacy_rate: Mapped[float | None] = mapped_column(Float)
    pca_match_score: Mapped[float | None] = mapped_column(Float)

    # Schools (census_village_amenities counts + know_your_school directory count)
    census_school_count: Mapped[int | None] = mapped_column(Integer)
    kys_school_count: Mapped[int | None] = mapped_column(Integer)

    # Health
    health_facility_count: Mapped[int | None] = mapped_column(Integer)

    # Sanitation (census_village_amenities drainage status flags)
    has_closed_drainage: Mapped[bool | None] = mapped_column(Boolean)
    has_no_drainage: Mapped[bool | None] = mapped_column(Boolean)

    # Water (census_village_amenities status flags — proxy for the unavailable JJM FHTC%)
    has_treated_tap_water: Mapped[bool | None] = mapped_column(Boolean)
    has_safe_water_source: Mapped[bool | None] = mapped_column(Boolean)  # tap/hand-pump/tube-well/covered-well

    # Roads
    has_pucca_road: Mapped[bool | None] = mapped_column(Boolean)
    has_all_weather_road: Mapped[bool | None] = mapped_column(Boolean)
    pmgsy_connected: Mapped[bool | None] = mapped_column(Boolean)  # spatial join, see build_village_fact

    # Electricity
    domestic_power_hours_summer: Mapped[float | None] = mapped_column(Float)
    domestic_power_hours_winter: Mapped[float | None] = mapped_column(Float)

    # MPLADs history (aggregated across both Lok Sabha terms, matched_lgd_village_code join)
    mplads_completed_amount_total: Mapped[int | None] = mapped_column(BigInteger)
    mplads_completed_work_count: Mapped[int | None] = mapped_column(Integer)
    mplads_recommended_amount_total: Mapped[int | None] = mapped_column(BigInteger)

    # Approximate point location for map display — nearest matched PMGSY habitation point,
    # or null if no confident match exists (report the real coverage rate, don't fabricate).
    geom: Mapped[str | None] = mapped_column(Geometry(geometry_type="POINT", srid=4326))
    geom_source: Mapped[str | None] = mapped_column(String(32))  # "pmgsy_habitation" | None
