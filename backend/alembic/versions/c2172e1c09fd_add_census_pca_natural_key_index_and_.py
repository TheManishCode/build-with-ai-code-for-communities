"""add census_pca natural key index and pmgsy geography indexes

Revision ID: c2172e1c09fd
Revises: b293414ba8cc
Create Date: 2026-07-05 15:29:12.937483

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import geoalchemy2


# revision identifiers, used by Alembic.
revision: str = 'c2172e1c09fd'
down_revision: Union[str, Sequence[str], None] = 'b293414ba8cc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # census_pca_village only has an autoincrement `id` PK in the ORM model -- this natural-key
    # unique index lets ingestion upsert idempotently (COALESCE sentinels since subdistt_serial/
    # town_vill_code are legitimately NULL for DISTRICT/TALUK-level rows, and a unique index
    # never treats two NULLs as conflicting).
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_census_pca_village_natural_key
        ON census_pca_village (
            level,
            district_serial,
            COALESCE(subdistt_serial, -1),
            COALESCE(town_vill_code, -1),
            tru
        )
        """
    )
    # A plain GIST index on a geometry column can't be used by ST_DWithin(geom::geography, ...)
    # -- the cast changes the expression, so Postgres falls back to a Seq Scan (measured: ~90ms
    # per habitation row against 7676 DRRP roads, i.e. minutes for a full village_fact build).
    # These functional GIST indexes on the geography-cast expression fix that.
    op.execute("CREATE INDEX IF NOT EXISTS idx_pmgsy_road_drrp_geog ON pmgsy_road_drrp USING GIST ((geom::geography))")
    op.execute("CREATE INDEX IF NOT EXISTS idx_pmgsy_habitation_geog ON pmgsy_habitation USING GIST ((geom::geography))")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP INDEX IF EXISTS idx_pmgsy_habitation_geog")
    op.execute("DROP INDEX IF EXISTS idx_pmgsy_road_drrp_geog")
    op.execute("DROP INDEX IF EXISTS ux_census_pca_village_natural_key")
