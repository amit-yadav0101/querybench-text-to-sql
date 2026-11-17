
import json
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

DB_PATH = BASE_DIR / "data" / "university.db"
QUESTIONS_PATH = BASE_DIR / "data" / "evaluation_questions.json"
OUTPUT_PATH = BASE_DIR / "data" / "expected_results.json"

# Load the 50 evaluation questions
with open(QUESTIONS_PATH, "r") as file:
    questions = json.load(file)

# Open database in read-only mode
conn = sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro", uri=True)
conn.execute("pragma query_only = on")

results = []

for question in questions:
    cursor = conn.execute(question["reference_sql"])

    columns = [item[0] for item in cursor.description]
    rows = cursor.fetchall()

    results.append({
        "id": question["id"],
        "columns": columns,
        "rows": [list(row) for row in rows],
        "row_count": len(rows)
    })

conn.close()

# Save expected results
with open(OUTPUT_PATH, "w") as file:
    json.dump(results, file, indent=4)

print("Expected results generated successfully!")
print("Total questions:", len(results))
print("Total result rows:", sum(item["row_count"] for item in results))
print("Saved to:", OUTPUT_PATH)
