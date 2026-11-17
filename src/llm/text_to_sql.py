
import sqlite3
import ollama
import re
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / "data" / "university.db"
MODEL = "qwen2.5:3b"
GROQ_MODEL = "openai/gpt-oss-20b"


# Get Groq API key from Streamlit secrets or environment
def get_groq_key():
    key = os.getenv("GROQ_API_KEY")

    if key:
        return key

    try:
        import streamlit as st
        return st.secrets.get("GROQ_API_KEY")
    except Exception:
        return None


# Generate response using Groq or local Ollama
def chat(messages):
    api_key = get_groq_key()

    if api_key:
        from groq import Groq

        client = Groq(api_key=api_key)

        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages
        )

        return response.choices[0].message.content or ""

    response = ollama.chat(
        model=MODEL,
        messages=messages,
        options={"temperature": 0}
    )

    return response["message"]["content"]


# Read actual database schema
def get_schema():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    tables = cursor.execute("""
        select name from sqlite_master
        where type = 'table' and name not like 'sqlite_%'
        order by name
    """).fetchall()

    schema = ""

    for (table,) in tables:
        columns = cursor.execute(
            f"pragma table_info('{table}')"
        ).fetchall()

        foreign_keys = cursor.execute(
            f"pragma foreign_key_list('{table}')"
        ).fetchall()

        schema += f"\nTable: {table}\n"

        for column in columns:
            schema += f"- {column[1]} ({column[2]})\n"

        for fk in foreign_keys:
            schema += (
                f"Foreign key: {table}.{fk[3]} -> "
                f"{fk[2]}.{fk[4]}\n"
            )

    conn.close()
    return schema


# Clean generated SQL
def clean_sql(response):
    sql = response.strip()

    sql = re.sub(r"^```(?:sql)?\s*", "", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\s*```$", "", sql)
    sql = re.sub(r"^sql\s*", "", sql, flags=re.IGNORECASE)

    sql = re.sub(
        r"^(?:here is the sql query|sql query|query)\s*:\s*",
        "",
        sql,
        flags=re.IGNORECASE
    )

    sql = sql.strip()

    while sql.startswith("(") and sql.endswith(")"):
        depth = 0
        balanced = True

        for i, char in enumerate(sql):
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1

            if depth == 0 and i != len(sql) - 1:
                balanced = False
                break

        if balanced and depth == 0:
            sql = sql[1:-1].strip()
        else:
            break

    return sql


# Validate read-only SQL
def validate_sql(sql):
    cleaned = sql.strip().rstrip(";").strip()

    if not cleaned:
        raise ValueError("The model returned an empty SQL query.")

    if not re.match(r"^(select|with)\b", cleaned, re.IGNORECASE):
        raise ValueError("Only SELECT queries are allowed.")

    if ";" in cleaned:
        raise ValueError("Only one SQL statement is allowed.")

    conn = None

    try:
        conn = sqlite3.connect(
            f"{DB_PATH.as_uri()}?mode=ro",
            uri=True
        )

        conn.execute("PRAGMA query_only = ON")

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
        conn.execute("EXPLAIN " + cleaned)

        return True

    finally:
        if conn:
            conn.close()


# Generate SQL using the available AI provider
def generate_sql(question):
    schema = get_schema()

    system_prompt = f"""
You are an expert SQLite Text-to-SQL assistant.

Your task is to convert natural language questions into SQL.

DATABASE SCHEMA:
{schema}

IMPORTANT SCHEMA RULES:
- roll_number belongs to students.
- student_id belongs to students and enrollments.
- course_code belongs to courses.
- course_id belongs to courses and enrollments.
- course_name belongs to courses.
- department_name belongs to departments.
- IT is stored as Information Technology.
- Never assign a column to a table that does not contain it.
- Use foreign keys for all JOIN operations.
- Do not invent columns, tables or relationships.

JOIN EXAMPLE:
To retrieve student roll numbers and course codes:

select s.roll_number, c.course_code
from students s
join enrollments e on s.student_id = e.student_id
join courses c on e.course_id = c.course_id;

SQL RULES:
- Generate exactly one SQLite SELECT query.
- WITH queries are allowed only when they end in SELECT.
- Use correct SQLite syntax.
- Use GROUP BY and HAVING correctly.
- Use LIMIT when a specific number of records is requested.
- Do not add unnecessary conditions or filters.
- Do not generate INSERT, UPDATE, DELETE, DROP or other
  write operations.
- Return SQL only.
- Do not use markdown or explanations.
"""

    user_prompt = (
        f"Question: {question}\n"
        "Generate one valid SQLite SELECT query."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    sql = clean_sql(chat(messages))
    last_error = None

    # Generate and validate, with one correction attempt
    for attempt in range(2):
        try:
            validate_sql(sql)
            return sql

        except (sqlite3.Error, ValueError) as error:
            last_error = error

            if attempt == 1:
                raise ValueError(
                    f"Could not generate valid SQL: {last_error}\n\n"
                    f"Generated SQL:\n{sql}"
                )

            correction_messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": (
                    f"Original question:\n{question}\n\n"
                    f"Previous SQL:\n{sql}\n\n"
                    f"Validation error:\n{error}\n\n"
                    "Correct the SQL query.\n"
                    "Check every selected column against the schema.\n"
                    "Use the correct tables and JOIN relationships.\n"
                    "Return exactly one read-only SELECT query.\n"
                    "Return SQL only, without markdown."
                )}
            ]

            sql = clean_sql(chat(correction_messages))

    raise ValueError(f"SQL generation failed: {last_error}")


if __name__ == "__main__":
    question = (
        "List roll numbers with the course codes "
        "they are enrolled in."
    )

    print("Question:", question)
    print("\nGenerated SQL:\n")
    print(generate_sql(question))
