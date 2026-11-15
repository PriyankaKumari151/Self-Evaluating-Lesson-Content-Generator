import sqlite3

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from content_agent.config import settings


@contextmanager
def get_connection(
    db_path: str | Path | None = None
) -> Iterator[sqlite3.Connection]:
    """
    Provides a managed SQLite connection.

    Features:
    - Enables foreign key enforcement.
    - Automatically commits successful transactions.
    - Rolls back transactions on exceptions.
    - Closes the connection after use.

    An optional database path is supported for testing.
    """

    database_path = (
        Path(db_path)
        if db_path is not None
        else settings.database_path
    )

    # Create the parent directory if it doesn't exist.
    database_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    connection = sqlite3.connect(
        str(database_path),
        timeout=30
    )

    connection.row_factory = sqlite3.Row

    try:

        # SQLite does not enforce foreign keys by default.
        connection.execute(
            "PRAGMA foreign_keys = ON"
        )

        yield connection

        connection.commit()

    except Exception:

        connection.rollback()

        raise

    finally:

        connection.close()


def initialize_database(
    db_path: str | Path | None = None
) -> None:
    """
    Creates all database tables using schema.sql.
    """

    schema_path = Path(__file__).with_name(
        "schema.sql"
    )

    if not schema_path.exists():
        raise FileNotFoundError(
            f"Database schema not found: {schema_path}"
        )

    schema = schema_path.read_text(
        encoding="utf-8"
    )

    with get_connection(db_path) as connection:

        connection.executescript(schema)

        connection.execute(
            "PRAGMA user_version = 1"
        )