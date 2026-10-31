from sqlalchemy import event
from sqlmodel import SQLModel, create_engine

from config import DB_PATH

engine = create_engine(f"sqlite:///{DB_PATH}")


@event.listens_for(engine, "connect")
def use_write_ahead_log(connection, _) -> None:
    # The runner, CLI and website may open the same file from different processes.
    connection.execute("PRAGMA journal_mode=WAL")


def create_tables() -> None:
    SQLModel.metadata.create_all(engine)
