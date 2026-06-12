"""The analytics database the SQL agent queries.

A small, self-contained star schema (regions, products, sales) with seeded
sample data, deliberately separate from the application database.
:func:`create_analytics_database` builds and seeds it (writable);
:func:`read_only_engine` opens it with ``PRAGMA query_only = ON`` so the agent
can never modify it — the driver-level half of the SQL agent's defence in depth.
"""

from sqlalchemy import (
    Column,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    event,
    insert,
    select,
)
from sqlalchemy.engine import Engine

metadata = MetaData()

regions = Table(
    "regions",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String, nullable=False),
)

products = Table(
    "products",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String, nullable=False),
    Column("category", String, nullable=False),
    Column("unit_price", Float, nullable=False),
)

sales = Table(
    "sales",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("product_id", Integer, ForeignKey("products.id"), nullable=False),
    Column("region_id", Integer, ForeignKey("regions.id"), nullable=False),
    Column("quarter", String, nullable=False),
    Column("units", Integer, nullable=False),
    Column("revenue", Float, nullable=False),
)

#: The set of tables the SQL guard will permit a query to reference.
ALLOWED_TABLES = {"regions", "products", "sales"}

_REGIONS = [
    {"id": 1, "name": "North America"},
    {"id": 2, "name": "Europe"},
    {"id": 3, "name": "Asia Pacific"},
]
_PRODUCTS = [
    {"id": 1, "name": "Copilot Pro", "category": "subscription", "unit_price": 30.0},
    {"id": 2, "name": "Copilot Team", "category": "subscription", "unit_price": 25.0},
    {"id": 3, "name": "Storage Add-on", "category": "addon", "unit_price": 10.0},
]
_SALES = [
    {
        "id": 1,
        "product_id": 1,
        "region_id": 1,
        "quarter": "2025-Q1",
        "units": 1200,
        "revenue": 36000.0,
    },  # noqa: E501
    {
        "id": 2,
        "product_id": 1,
        "region_id": 2,
        "quarter": "2025-Q1",
        "units": 800,
        "revenue": 24000.0,
    },  # noqa: E501
    {
        "id": 3,
        "product_id": 2,
        "region_id": 1,
        "quarter": "2025-Q1",
        "units": 1500,
        "revenue": 37500.0,
    },  # noqa: E501
    {
        "id": 4,
        "product_id": 3,
        "region_id": 3,
        "quarter": "2025-Q1",
        "units": 500,
        "revenue": 5000.0,
    },  # noqa: E501
    {
        "id": 5,
        "product_id": 1,
        "region_id": 1,
        "quarter": "2025-Q2",
        "units": 1400,
        "revenue": 42000.0,
    },  # noqa: E501
    {
        "id": 6,
        "product_id": 2,
        "region_id": 2,
        "quarter": "2025-Q2",
        "units": 1700,
        "revenue": 42500.0,
    },  # noqa: E501
]


def create_analytics_database(url: str) -> None:
    """Create the schema and seed sample rows if the database is empty."""
    engine = create_engine(url, future=True)
    metadata.create_all(engine)
    with engine.begin() as conn:
        already_seeded = conn.execute(select(sales.c.id).limit(1)).first()
        if already_seeded is None:
            conn.execute(insert(regions), _REGIONS)
            conn.execute(insert(products), _PRODUCTS)
            conn.execute(insert(sales), _SALES)
    engine.dispose()


def read_only_engine(url: str) -> Engine:
    """Open the analytics DB read-only.

    For SQLite, every connection runs ``PRAGMA query_only = ON`` so any write is
    rejected by the driver regardless of what SQL slips through the guard.
    """
    engine = create_engine(url, future=True)
    if engine.dialect.name == "sqlite":

        @event.listens_for(engine, "connect")
        def _enforce_read_only(dbapi_conn, _record):  # pragma: no cover - trivial
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA query_only = ON;")
            cur.close()

    return engine


def schema_description(metadata_obj: MetaData = metadata) -> str:
    """A compact text schema (``table(col type, ...)`` per line) for prompting."""
    lines = []
    for table in metadata_obj.sorted_tables:
        cols = ", ".join(f"{c.name} {c.type}" for c in table.columns)
        lines.append(f"{table.name}({cols})")
    return "\n".join(lines)
