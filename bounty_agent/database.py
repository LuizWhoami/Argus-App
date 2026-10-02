import os
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()
engine = None
SessionLocal = None

DEFAULT_DB = os.getenv("BOUNTY_DB", "sqlite:///bounty.db")

# Colunas adicionadas após a v0.1 — migração idempotente para SQLite.
SQLITE_MIGRATIONS = {
    "http_probes": [
        ("content_type", "VARCHAR"),
        ("location", "VARCHAR"),
    ],
}


def _apply_sqlite_migrations(engine):
    if engine.dialect.name != "sqlite":
        return
    insp = inspect(engine)
    with engine.begin() as conn:
        for table, cols in SQLITE_MIGRATIONS.items():
            if not insp.has_table(table):
                continue
            existing = {c["name"] for c in insp.get_columns(table)}
            for name, ddl in cols:
                if name in existing:
                    continue
                conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {name} {ddl}'))


def init_db(db_url: str = DEFAULT_DB):
    global engine, SessionLocal
    engine = create_engine(db_url, echo=False)
    Base.metadata.create_all(engine)
    _apply_sqlite_migrations(engine)
    SessionLocal = sessionmaker(bind=engine)


def get_session():
    if SessionLocal is None:
        raise RuntimeError("init_db() precisa ser chamado antes de get_session()")
    return SessionLocal()
