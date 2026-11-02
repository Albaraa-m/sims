from sqlalchemy import Connection, event, inspect, text
from sqlmodel import Session, SQLModel, create_engine

from core.config import DB_PATH

engine = create_engine(f"sqlite:///{DB_PATH}")


@event.listens_for(engine, "connect")
def use_write_ahead_log(connection, _) -> None:
    # The runner, CLI and website may open the same file from different processes.
    connection.execute("PRAGMA journal_mode=WAL")


def table_matches_model(connection: Connection, table_name: str) -> bool:
    model_columns = {
        column.name: column.nullable
        for column in SQLModel.metadata.tables[table_name].columns
    }
    stored_columns = {
        column["name"]: column["nullable"]
        for column in inspect(connection).get_columns(table_name)
    }
    return model_columns == stored_columns


def rebuild_table_from_model(connection: Connection, table_name: str) -> None:
    """SQLite can't change a column in place, so copy the rows into a new table.

    Columns the model no longer has are dropped with their data.
    """
    old_table = f"{table_name}_before_migration"
    connection.execute(text(f"ALTER TABLE {table_name} RENAME TO {old_table}"))
    SQLModel.metadata.tables[table_name].create(connection)
    stored = {column["name"] for column in inspect(connection).get_columns(old_table)}
    shared = ", ".join(
        column.name
        for column in SQLModel.metadata.tables[table_name].columns
        if column.name in stored
    )
    connection.execute(
        text(f"INSERT INTO {table_name} ({shared}) SELECT {shared} FROM {old_table}")
    )
    connection.execute(text(f"DROP TABLE {old_table}"))


def create_tables() -> None:
    """Creates missing tables and rebuilds any whose columns changed."""
    with engine.begin() as connection:
        existing_tables = inspect(connection).get_table_names()
        for table_name in SQLModel.metadata.tables:
            if table_name in existing_tables and not table_matches_model(
                connection, table_name
            ):
                rebuild_table_from_model(connection, table_name)
        SQLModel.metadata.create_all(connection)


def save[Row: SQLModel](row: Row) -> Row:
    with Session(engine) as session:
        session.add(row)
        session.commit()
        session.refresh(row)
        return row


def get_row[Row: SQLModel](model: type[Row], row_id: str) -> Row:
    with Session(engine) as session:
        return session.get_one(model, row_id)
