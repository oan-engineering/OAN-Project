"""schema_sync adds model columns that an existing table lacks.

The failure it prevents: a PR adds a column to a model, create_all() leaves the
existing table alone, the API's queries on that column fail, and the page is
blank with only a SQL error in the pod log. Runs against SQLite (aiosqlite), so
it needs no database server:

    pip install "sqlalchemy[asyncio]>=2" aiosqlite pytest
    python -m pytest test/test_schema_sync.py -q
"""

import asyncio
import importlib.util
import pathlib
import sys

import pytest
from sqlalchemy import Integer, String, inspect, text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Load the module by path: importing the package would pull in the registry
# platform and its configuration, which this test does not need.
_SRC = (
    pathlib.Path(__file__).resolve().parent.parent
    / "cropsown-extension/src/openg2p_registry_cropsown_extension/schema_sync.py"
)
_spec = importlib.util.spec_from_file_location("schema_sync", _SRC)
schema_sync = importlib.util.module_from_spec(_spec)
sys.modules["schema_sync"] = schema_sync  # dataclasses look the module up here
_spec.loader.exec_module(schema_sync)


class Base(DeclarativeBase):
    pass


class Sowing(Base):
    """The model as the new code has it: two columns newer than the table."""

    __tablename__ = "g2p_register_sowings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    crop: Mapped[str] = mapped_column(String(64))
    sowing_method: Mapped[str] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)


def _run(coro):
    return asyncio.run(coro)


async def _engine_with_old_table(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'db.sqlite'}")
    async with engine.begin() as conn:
        # The table as an older deploy created it, with a row and a column the
        # model no longer has.
        await conn.exec_driver_sql(
            "CREATE TABLE g2p_register_sowings (id INTEGER PRIMARY KEY, crop VARCHAR(64), legacy_note TEXT)"
        )
        await conn.exec_driver_sql("INSERT INTO g2p_register_sowings (id, crop) VALUES (1, 'teff')")
    return engine


async def _columns(engine):
    async with engine.connect() as conn:
        return await conn.run_sync(
            lambda c: {col["name"]: col for col in inspect(c).get_columns("g2p_register_sowings")}
        )


def test_check_mode_reports_missing_columns_and_changes_nothing(tmp_path):
    async def go():
        engine = await _engine_with_old_table(tmp_path)
        with pytest.raises(schema_sync.SchemaDriftError) as err:
            await schema_sync.sync_schema(engine, [Sowing], apply=False)
        cols = await _columns(engine)
        await engine.dispose()
        return str(err.value), cols

    message, cols = _run(go())
    assert "g2p_register_sowings.sowing_method" in message
    assert "g2p_register_sowings.status" in message
    assert "sowing_method" not in cols and "status" not in cols


def test_apply_adds_missing_columns_and_keeps_rows(tmp_path):
    async def go():
        engine = await _engine_with_old_table(tmp_path)
        report = await schema_sync.sync_schema(engine, [Sowing])
        cols = await _columns(engine)
        async with engine.connect() as conn:
            rows = (await conn.execute(text("SELECT id, crop, sowing_method, status FROM g2p_register_sowings"))).all()
        # A second run finds nothing left to do.
        again = await schema_sync.sync_schema(engine, [Sowing], apply=False)
        await engine.dispose()
        return report, cols, rows, again

    report, cols, rows, again = _run(go())
    assert sorted(report.added) == ["g2p_register_sowings.sowing_method", "g2p_register_sowings.status"]
    assert "sowing_method" in cols and "status" in cols
    assert rows == [(1, "teff", None, None)]
    assert again.missing == []


def test_not_null_without_default_is_added_nullable_and_reported(tmp_path):
    async def go():
        engine = await _engine_with_old_table(tmp_path)
        report = await schema_sync.sync_schema(engine, [Sowing])
        cols = await _columns(engine)
        await engine.dispose()
        return report, cols

    report, cols = _run(go())
    assert report.added_nullable == ["g2p_register_sowings.status"]
    assert cols["status"]["nullable"] is True


def test_datasource_is_read_from_the_api_prefix():
    url = schema_sync._datasource_from_env(
        {
            "REGISTRY_STAFF_PORTAL_API_DB_HOSTNAME": "commons-postgresql",
            "REGISTRY_STAFF_PORTAL_API_DB_DBNAME": "cropsown_registry",
            "REGISTRY_STAFF_PORTAL_API_DB_USERNAME": "cropsown_registry_user",
            "REGISTRY_STAFF_PORTAL_API_DB_PASSWORD": "p@ss:word",
        }
    )
    assert url == "postgresql+asyncpg://cropsown_registry_user:p%40ss%3Aword@commons-postgresql:5432/cropsown_registry"


def test_extra_database_columns_are_reported_not_dropped(tmp_path):
    async def go():
        engine = await _engine_with_old_table(tmp_path)
        report = await schema_sync.sync_schema(engine, [Sowing])
        cols = await _columns(engine)
        await engine.dispose()
        return report, cols

    report, cols = _run(go())
    assert report.extra == ["g2p_register_sowings.legacy_note"]
    assert "legacy_note" in cols
