
import json
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

DB_PATH = BASE_DIR / "data" / "university.db"
QUESTIONS_PATH = BASE_DIR / "data" / "evaluation_questions.json"

with open(QUESTIONS_PATH, "r") as file:
    questions = json.load(file)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

passed = 0

for question in questions:
    try:
        cursor.execute(question["reference_sql"])
        cursor.fetchall()
        print(f"PASS: Question {question['id']}")
        passed += 1

    except sqlite3.Error as error:
        print(f"FAIL: Question {question['id']} - {error}")

print(f"\nValidation: {passed}/{len(questions)} passed")

conn.close()
