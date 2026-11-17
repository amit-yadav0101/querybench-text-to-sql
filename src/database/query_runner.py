
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / "data" / "university.db"


def execute_read_only(sql):
    if not isinstance(sql, str) or not sql.strip():
        return {"success": False, "error": "Empty SQL query."}

    try:
        # Open database in read-only mode
        conn = sqlite3.connect(
            f"file:{DB_PATH.as_posix()}?mode=ro",
            uri=True
        )

        conn.execute("pragma query_only = on")

        # Block database modifications
        allowed_actions = {
            sqlite3.SQLITE_SELECT,
            sqlite3.SQLITE_READ,
            sqlite3.SQLITE_FUNCTION,
            sqlite3.SQLITE_RECURSIVE
        }

        def authorize(action, arg1, arg2, database, trigger):
            if action in allowed_actions:
                return sqlite3.SQLITE_OK
            return sqlite3.SQLITE_DENY

        conn.set_authorizer(authorize)

        # Execute exactly one statement
        cursor = conn.execute(sql)

        if cursor.description is None:
            raise ValueError("Only SELECT queries are allowed.")

        columns = [item[0] for item in cursor.description]
        rows = cursor.fetchall()

        conn.close()

        return {
            "success": True,
            "columns": columns,
            "rows": [list(row) for row in rows],
            "row_count": len(rows)
        }

    except (sqlite3.Error, ValueError) as error:
        try:
            conn.close()
        except (NameError, sqlite3.Error):
            pass

        return {
            "success": False,
            "error": str(error)
        }


if __name__ == "__main__":
    query = "select name, roll_number from students limit 5"

    result = execute_read_only(query)

    print(result)
