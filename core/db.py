from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine

from core.config import DB_PATH

engine = create_engine(f"sqlite:///{DB_PATH}")


@event.listens_for(engine, "connect")
def use_write_ahead_log(connection, _) -> None:
    # The runner, CLI and website may open the same file from different processes.
    connection.execute("PRAGMA journal_mode=WAL")


def create_tables() -> None:
    SQLModel.metadata.create_all(engine)


def save[Row: SQLModel](row: Row) -> Row:
    with Session(engine) as session:
        session.add(row)
        session.commit()
        session.refresh(row)
        return row


def get_row[Row: SQLModel](model: type[Row], row_id: str) -> Row:
    with Session(engine) as session:
        return session.get_one(model, row_id)
