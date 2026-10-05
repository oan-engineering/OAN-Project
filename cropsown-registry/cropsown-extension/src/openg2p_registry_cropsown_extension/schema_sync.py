"""Keep existing database tables in step with the ORM models.

`create_migrate()` (openg2p-fastapi-common) runs `metadata.create_all`, which
creates tables that do not exist and never touches tables that do. A column
added to a model therefore reaches a fresh database but silently never appears
on an existing one, and queries against it then fail at runtime.

`sync_schema()` closes that gap for the changes that are safe to automate:

* a column in the model but not in the table is ADDED (``ALTER TABLE ... ADD
  COLUMN``). A NOT NULL column is added NOT NULL only when it has a server
  default; otherwise it is added nullable, because existing rows have no value
  for it, and that is reported.
* a column in the table but not in the model (a rename or a removal) is only
  REPORTED. Dropping or renaming loses data, so that stays a reviewed, manual
  migration.
* a column whose type differs is only REPORTED, for the same reason.

It runs after `create_migrate()` in the extension's `migrate` command, so a PR
that adds a column is applied on the next deploy with no manual step.

The same module checks without changing anything, for a post-deploy gate:

    python -m openg2p_registry_cropsown_extension.schema_sync --check

exits 1 if any model column is missing from the database.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from dataclasses import dataclass, field
from typing import Iterable, List

from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.schema import CreateColumn

_logger = logging.getLogger(__name__)


class SchemaDriftError(RuntimeError):
    """Raised by a check when model columns are missing from the database."""


@dataclass
class SchemaReport:
    added: List[str] = field(default_factory=list)
    missing: List[str] = field(default_factory=list)
    added_nullable: List[str] = field(default_factory=list)
    extra: List[str] = field(default_factory=list)
    type_mismatch: List[str] = field(default_factory=list)

    def lines(self) -> List[str]:
        out = []
        out += [f"ADDED column {c}" for c in self.added]
        out += [f"MISSING column {c}" for c in self.missing]
        out += [
            f"NOTE {c} is NOT NULL in the model but was added nullable "
            "(existing rows have no value); backfill it, then add the constraint"
            for c in self.added_nullable
        ]
        out += [
            f"EXTRA column {c} is in the database but not the model "
            "(renamed or removed?) - not dropped"
            for c in self.extra
        ]
        out += [f"TYPE differs {c} - not changed" for c in self.type_mismatch]
        return out


def _tables(models: Iterable[type]):
    seen = set()
    for model in models:
        table = model.__table__
        if table.fullname not in seen:
            seen.add(table.fullname)
            yield table


def _sync(conn, tables, apply: bool) -> SchemaReport:
    report = SchemaReport()
    inspector = inspect(conn)
    dialect = conn.dialect
    preparer = dialect.identifier_preparer

    for table in tables:
        if not inspector.has_table(table.name, schema=table.schema):
            # create_migrate() creates whole tables; nothing to add here.
            if not apply:
                report.missing.append(f"{table.fullname} (whole table)")
            continue

        db_columns = {c["name"]: c for c in inspector.get_columns(table.name, schema=table.schema)}
        model_names = {c.name for c in table.columns}

        for column in table.columns:
            qualified = f"{table.fullname}.{column.name}"
            if column.name in db_columns:
                db_type = db_columns[column.name]["type"]
                model_type = column.type.compile(dialect=dialect)
                if db_type.compile(dialect=dialect) != model_type:
                    report.type_mismatch.append(
                        f"{qualified} (database {db_type.compile(dialect=dialect)}, model {model_type})"
                    )
                continue

            if not apply:
                report.missing.append(qualified)
                continue

            # create_all() makes a native enum type only with its table; a new
            # enum column on an existing table needs the type created first.
            if hasattr(column.type, "create"):
                column.type.create(conn, checkfirst=True)
            # Compile the model's own column (a detached copy has no table, which
            # the PostgreSQL compiler needs).
            ddl = str(CreateColumn(column).compile(dialect=dialect))
            if not column.nullable and column.server_default is None:
                # Existing rows would violate NOT NULL; add it nullable instead.
                ddl = ddl.replace(" NOT NULL", "", 1)
                report.added_nullable.append(qualified)
            table_name = preparer.format_table(table)
            # Several API pods run migrate at once on a deploy; IF NOT EXISTS
            # keeps the one that loses the race from failing.
            if_not_exists = "IF NOT EXISTS " if dialect.name == "postgresql" else ""
            conn.exec_driver_sql(f"ALTER TABLE {table_name} ADD COLUMN {if_not_exists}{ddl}")
            report.added.append(qualified)

        for name in db_columns:
            if name not in model_names:
                report.extra.append(f"{table.fullname}.{name}")

    return report


async def sync_schema(engine: AsyncEngine, models: Iterable[type], apply: bool = True) -> SchemaReport:
    """Add missing columns (apply=True) or only report them (apply=False)."""
    tables = list(_tables(models))
    async with engine.begin() as conn:
        report = await conn.run_sync(_sync, tables, apply)
    for line in report.lines():
        (_logger.warning if not line.startswith("ADDED") else _logger.info)("schema: %s", line)
    if not apply and report.missing:
        raise SchemaDriftError(
            "database is missing model columns:\n  " + "\n  ".join(report.missing)
        )
    return report


_ENV_PREFIXES = (
    "REGISTRY_STAFF_PORTAL_API_",
    "REGISTRY_PARTNER_API_",
    "REGISTRY_EXTENSIONS_",
    "REGISTRY_CORE_",
)


def _datasource_from_env(environ) -> str:
    """The DB URL of the service this runs inside.

    The extension is loaded by an API whose settings carry that API's own prefix
    (REGISTRY_STAFF_PORTAL_API_DB_HOSTNAME, ...), not the extension's, so read
    whichever prefix the pod has.
    """
    for prefix in _ENV_PREFIXES:
        if environ.get(f"{prefix}DB_DATASOURCE"):
            return environ[f"{prefix}DB_DATASOURCE"]
        if environ.get(f"{prefix}DB_DBNAME"):
            get = lambda key, default=None: environ.get(f"{prefix}DB_{key}", default)  # noqa: E731
            from sqlalchemy.engine import URL

            return URL.create(
                get("DRIVER", "postgresql+asyncpg"),
                username=get("USERNAME"),
                password=get("PASSWORD"),
                host=get("HOSTNAME", "localhost"),
                port=int(get("PORT", 5432)),
                database=get("DBNAME"),
            ).render_as_string(hide_password=False)
    raise SystemExit("no <PREFIX>DB_DBNAME or <PREFIX>DB_DATASOURCE in the environment; tried " + ", ".join(_ENV_PREFIXES))


def _main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check", action="store_true", help="report drift and exit 1; change nothing")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    # Imported here so importing this module stays free of app configuration.
    import os

    from sqlalchemy.ext.asyncio import create_async_engine

    from .app import MIGRATED_MODELS

    engine = create_async_engine(_datasource_from_env(os.environ))

    async def run():
        try:
            report = await sync_schema(engine, MIGRATED_MODELS, apply=not args.check)
        finally:
            await engine.dispose()
        return report

    try:
        report = asyncio.run(run())
    except SchemaDriftError as err:
        print(f"SCHEMA DRIFT: {err}", file=sys.stderr)
        return 1
    print(f"schema OK: {len(list(_tables(MIGRATED_MODELS)))} tables checked"
          + (f", {len(report.added)} columns added" if report.added else ""))
    return 0


if __name__ == "__main__":
    sys.exit(_main())
