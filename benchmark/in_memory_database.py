from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, create_engine

from core import db


def use_in_memory_database() -> None:
    """Benchmark rows never reach sims.db."""
    db.engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(db.engine)
