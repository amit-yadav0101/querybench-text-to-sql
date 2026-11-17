
import json
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

DB_PATH = BASE_DIR / "data" / "university.db"
EXPECTED_PATH = BASE_DIR / "data" / "expected_results.json"

with open(EXPECTED_PATH, "r") as file:
    expected_results = json.load(file)

conn = sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro", uri=True)
conn.execute("pragma query_only = on")

passed = 0

for item in expected_results:
    # Re-run the reference SQL using its question ID
    with open(BASE_DIR / "data" / "evaluation_questions.json") as file:
        questions = json.load(file)

    question = next(q for q in questions if q["id"] == item["id"])
    cursor = conn.execute(question["reference_sql"])

    actual = {
        "columns": [col[0] for col in cursor.description],
        "rows": [list(row) for row in cursor.fetchall()]
    }

    expected = {
        "columns": item["columns"],
        "rows": item["rows"]
    }

    if actual == expected:
        passed += 1
    else:
        print(f"FAIL: Question {item['id']}")

conn.close()

print(f"\nReference result comparison: {passed}/50 passed")
