from sqlalchemy import inspect, text
from sqlmodel import Session

from core import db
from core.db import create_tables
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
