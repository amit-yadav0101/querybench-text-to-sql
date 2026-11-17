
import json
import csv
import re
import time
import sqlite3
from pathlib import Path
from collections import Counter, defaultdict

import ollama

from src.llm.text_to_sql import get_schema
from src.database.query_runner import execute_read_only


BASE_DIR = Path(__file__).resolve().parents[2]
QUESTIONS_FILE = BASE_DIR / "data" / "evaluation_questions.json"
EXPECTED_FILE = BASE_DIR / "data" / "expected_results.json"
OUTPUT_JSON = BASE_DIR / "data" / "llm_evaluation_results.json"
OUTPUT_CSV = BASE_DIR / "data" / "llm_evaluation_details.csv"
SUMMARY_CSV = BASE_DIR / "data" / "llm_evaluation_summary.csv"

MODEL = "qwen2.5:3b"


# Common instructions used in every experiment
BASE_PROMPT = """
You are an expert SQLite Text-to-SQL assistant.
Generate exactly one read-only SQL query.
Use only the supplied database schema.
Do not invent tables or columns.
Use correct SQL syntax.
Return SQL only, without markdown or explanations.
"""


# Additional schema hints for experiment B and C
SCHEMA_HINTS = """
SCHEMA HINTS:
- Course names belong to courses.course_name.
- Department names belong to departments.department_name.
- Students connect to departments through department_id.
- Students connect to courses through enrollments.
- Enrollments connect to marks through enrollment_id.
- The IT department is stored as Information Technology.
- Use exact database values when filtering text columns.
- Use correct foreign-key relationships for JOIN operations.
"""


# Worked examples used only in experiment C
FEW_SHOT_EXAMPLES = """
EXAMPLE 1

Question: Show each student's name and department name.

SQL:
SELECT s.name, d.department_name
FROM students s
JOIN departments d
ON s.department_id = d.department_id;


EXAMPLE 2

Question: Count students in each department.

SQL:
SELECT d.department_name, COUNT(s.student_id) AS total_students
FROM departments d
LEFT JOIN students s
ON d.department_id = s.department_id
GROUP BY d.department_id, d.department_name;


EXAMPLE 3

Question: List course names and their department names.

SQL:
SELECT c.course_name, d.department_name
FROM courses c
JOIN departments d
ON c.department_id = d.department_id;
"""


EXPERIMENTS = {
    "A_baseline": BASE_PROMPT,
    "B_schema_hints": BASE_PROMPT + SCHEMA_HINTS,
    "C_few_shot": BASE_PROMPT + SCHEMA_HINTS + FEW_SHOT_EXAMPLES
}


def load_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def clean_sql(sql):
    sql = sql.strip()
    sql = sql.replace("```sql", "").replace("```SQL", "")
    sql = sql.replace("```", "").strip()
    return sql


def normalize_value(value):
    if isinstance(value, float):
        return round(value, 8)
    if isinstance(value, list):
        return tuple(normalize_value(v) for v in value)
    if isinstance(value, dict):
        return tuple(sorted(
            (k, normalize_value(v)) for k, v in value.items()
        ))
    return value


def compare_results(actual, expected, ordered):
    actual_rows = [
        tuple(normalize_value(v) for v in row)
        for row in actual
    ]

    expected_rows = [
        tuple(normalize_value(v) for v in row)
        for row in expected
    ]

    if ordered:
        return actual_rows == expected_rows

    return Counter(actual_rows) == Counter(expected_rows)


def classify_error(success, result_match, error, category):
    message = str(error).lower()

    if success and result_match:
        return "correct"

    if not success:
        if any(word in message for word in [
            "not authorized", "readonly", "read-only",
            "not allowed", "multiple statements"
        ]):
            return "unsafe_or_blocked"

        if "syntax error" in message or "near" in message:
            return "syntax_error"

        if "no such table" in message or "no such column" in message:
            return "schema_linking_error"

        return "execution_error"

    if category == "join":
        return "possible_join_error"

    if category == "aggregation":
        return "possible_aggregation_error"

    if category == "nested":
        return "possible_nested_query_error"

    return "result_mismatch"


def generate_sql(question, schema, prompt):
    response = ollama.chat(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": prompt
            },
            {
                "role": "user",
                "content": (
                    f"Database schema:\n{schema}\n\n"
                    f"Question: {question}\n"
                    "Generate one SQLite query."
                )
            }
        ],
        options={"temperature": 0}
    )

    return clean_sql(response["message"]["content"])


def evaluate_one(item, expected, schema, experiment, prompt):
    question_id = item["id"]
    question = item["question"]
    category = item["category"]

    sql = ""
    result = {}
    error = ""
    generation_time = 0
    execution_time = 0

    try:
        start = time.perf_counter()
        sql = generate_sql(question, schema, prompt)
        generation_time = time.perf_counter() - start

        start = time.perf_counter()
        result = execute_read_only(sql)
        execution_time = time.perf_counter() - start

        success = result.get("success", False)

        if success:
            actual_rows = result.get("rows", [])
            expected_rows = expected.get("rows", [])
            expected_columns = expected.get("columns", [])
            actual_columns = result.get("columns", [])

            columns_match = len(actual_columns) == len(expected_columns)

            ordered = bool(
                re.search(
                    r"\border\s+by\b",
                    item["reference_sql"],
                    re.IGNORECASE
                )
            )

            result_match = (
                columns_match
                and compare_results(
                    actual_rows,
                    expected_rows,
                    ordered
                )
            )

            error_type = classify_error(
                True, result_match, "", category
            )

        else:
            result_match = False
            columns_match = False
            error = result.get("error", "Unknown execution error")

            error_type = classify_error(
                False, False, error, category
            )

    except Exception as exception:
        success = False
        result_match = False
        columns_match = False
        error = str(exception)

        error_type = classify_error(
            False, False, error, category
        )

    return {
        "experiment": experiment,
        "id": question_id,
        "category": category,
        "difficulty": item["difficulty"],
        "question": question,
        "generated_sql": sql,
        "execution_success": success,
        "columns_match": columns_match,
        "result_match": result_match,
        "error_type": error_type,
        "error": error,
        "generation_seconds": round(generation_time, 3),
        "execution_seconds": round(execution_time, 3)
    }


def build_summary(records):
    grouped = defaultdict(list)

    for record in records:
        grouped[record["experiment"]].append(record)

    summaries = []

    for experiment, items in grouped.items():
        total = len(items)
        executed = sum(
            item["execution_success"] for item in items
        )
        correct = sum(
            item["result_match"] for item in items
        )

        avg_generation = sum(
            item["generation_seconds"] for item in items
        ) / total if total else 0

        avg_execution = sum(
            item["execution_seconds"] for item in items
        ) / total if total else 0

        summaries.append({
            "experiment": experiment,
            "total_questions": total,
            "execution_success": executed,
            "execution_success_percent": round(
                executed / total * 100, 2
            ) if total else 0,
            "correct_results": correct,
            "execution_accuracy_percent": round(
                correct / total * 100, 2
            ) if total else 0,
            "average_generation_seconds": round(
                avg_generation, 3
            ),
            "average_execution_seconds": round(
                avg_execution, 3
            )
        })

    return summaries


def save_csv(path, records):
    if not records:
        return

    with open(path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=list(records[0].keys())
        )
        writer.writeheader()
        writer.writerows(records)


def main():
    questions = load_json(QUESTIONS_FILE)
    expected_results = load_json(EXPECTED_FILE)

    expected_by_id = {
        item["id"]: item for item in expected_results
    }

    if len(questions) != 50:
        raise ValueError(
            f"Expected 50 questions, found {len(questions)}"
        )

    if len(expected_by_id) != len(expected_results):
        raise ValueError("Duplicate IDs in expected results.")

    for question in questions:
        if question["id"] not in expected_by_id:
            raise ValueError(
                f"Missing expected result for question {question['id']}"
            )

    schema = get_schema()
    all_records = []

    print("TEXT-TO-SQL EVALUATION")
    print("Model:", MODEL)
    print("Questions:", len(questions))
    print("Experiments:", len(EXPERIMENTS))
    print("Total model runs:", len(questions) * len(EXPERIMENTS))
    print("=" * 55)

    for experiment, prompt in EXPERIMENTS.items():
        print(f"\nStarting {experiment}")

        for index, item in enumerate(questions, start=1):
            record = evaluate_one(
                item,
                expected_by_id[item["id"]],
                schema,
                experiment,
                prompt
            )

            all_records.append(record)

            status = (
                "CORRECT" if record["result_match"]
                else "WRONG"
            )

            print(
                f"{experiment} | "
                f"{index}/{len(questions)} | "
                f"Question {item['id']} | {status}"
            )

            # Save progress after every question
            with open(OUTPUT_JSON, "w", encoding="utf-8") as file:
                json.dump(all_records, file, indent=2)

            save_csv(OUTPUT_CSV, all_records)

    summaries = build_summary(all_records)

    with open(OUTPUT_JSON, "w", encoding="utf-8") as file:
        json.dump(all_records, file, indent=2)

    save_csv(OUTPUT_CSV, all_records)
    save_csv(SUMMARY_CSV, summaries)

    print("\n" + "=" * 55)
    print("FINAL EXPERIMENT SUMMARY")

    for summary in summaries:
        print("\n", summary["experiment"])
        print(
            "Execution success:",
            f'{summary["execution_success_percent"]}%'
        )
        print(
            "Execution accuracy:",
            f'{summary["execution_accuracy_percent"]}%'
        )
        print(
            "Average generation time:",
            summary["average_generation_seconds"],
            "seconds"
        )

    print("\nFiles saved:")
    print(OUTPUT_JSON)
    print(OUTPUT_CSV)
    print(SUMMARY_CSV)


if __name__ == "__main__":
    main()
