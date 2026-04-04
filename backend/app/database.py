from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker, declarative_base
from .config import settings

_is_sqlite = settings.database_url.startswith("sqlite:")

_engine_kwargs: dict = {}
if _is_sqlite:
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # PostgreSQL: enable connection health checks
    _engine_kwargs["pool_pre_ping"] = True

engine = create_engine(settings.database_url, **_engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ---------------------------------------------------------------------------
# Lightweight SQLite schema patch — runs on every startup.
# Detects missing columns on analysis_history and adds them automatically.
# Old SQLite DBs created before these fields existed will be patched in-place.
# ---------------------------------------------------------------------------
_MISSING_COLUMNS = {
    "analysis_history": [
        ("source_entry_count", "INTEGER DEFAULT 0"),
        ("latest_entry_id", "INTEGER"),
        ("latest_entry_created_at", "DATETIME"),
        ("total_entries_at_time", "INTEGER DEFAULT 0"),
    ],
}


def run_schema_patch():
    """
    Check analysis_history for missing columns and ALTER TABLE if needed.
    Logs clearly so startup output confirms the patch was (or wasn't) needed.
    """
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    if "analysis_history" not in existing_tables:
        print("[SCHEMA_PATCH] analysis_history table does not exist yet — will be created by create_all()")
        return

    try:
        existing_columns = {col["name"] for col in inspector.get_columns("analysis_history")}
    except Exception as e:
        print(f"[SCHEMA_PATCH] could not inspect analysis_history columns: {e}")
        return

    added = []
    with engine.connect() as conn:
        for col_name, col_def in _MISSING_COLUMNS.get("analysis_history", []):
            if col_name not in existing_columns:
                try:
                    stmt = f'ALTER TABLE analysis_history ADD COLUMN {col_name} {col_def}'
                    conn.exec_driver_sql(stmt)
                    conn.commit()
                    added.append(col_name)
                    print(f"[SCHEMA_PATCH] ADDED column: analysis_history.{col_name}")
                except Exception as e:
                    print(f"[SCHEMA_PATCH] FAILED to add column {col_name}: {e}")
            else:
                print(f"[SCHEMA_PATCH] column already exists: analysis_history.{col_name}")

    if added:
        print(f"[SCHEMA_PATCH] analysis_history schema patch complete — {len(added)} column(s) added: {added}")
    else:
        print("[SCHEMA_PATCH] analysis_history schema is up-to-date — no changes needed")
