from sqlalchemy import inspect, text
from sqlmodel import Session

from core import db
from core.db import create_tables
from evaluations.models import Evaluation  # noqa: F401  (registers the table)
from regression_tests.models import Test


def test_changed_table_is_rebuilt_keeping_its_rows():
    with db.engine.begin() as connection:
        connection.execute(text("DROP TABLE test"))
        connection.execute(
            text(
                "CREATE TABLE test (id VARCHAR PRIMARY KEY, lineage_id VARCHAR NOT NULL,"
                " name VARCHAR NOT NULL, version INTEGER NOT NULL,"
                " source_conversation_id VARCHAR NOT NULL, status VARCHAR NOT NULL,"
                " spec JSON, inferred JSON, created_at DATETIME NOT NULL)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO test VALUES ('t1', 't1', 'Old', 1, 's1', 'DRAFT', '{}',"
                " NULL, '2026-01-01 00:00:00')"
            )
        )

    create_tables()

    columns = {c["name"]: c for c in inspect(db.engine).get_columns("test")}
    assert columns["source_conversation_id"]["nullable"]
    with Session(db.engine) as session:
        assert session.get_one(Test, "t1").name == "Old"


def test_rebuild_keeps_indexes_working():
    with db.engine.begin() as connection:
        connection.execute(text("ALTER TABLE test ADD COLUMN obsolete VARCHAR"))

    create_tables()

    indexes = {index["name"] for index in inspect(db.engine).get_indexes("test")}
    assert "ix_test_swarm_id" in indexes


def test_rebuilding_a_table_keeps_foreign_keys_to_it():
    with db.engine.begin() as connection:
        connection.execute(text("ALTER TABLE simulation ADD COLUMN obsolete VARCHAR"))

    create_tables()

    [foreign_key] = inspect(db.engine).get_foreign_keys("evaluation")
    assert foreign_key["referred_table"] == "simulation"
