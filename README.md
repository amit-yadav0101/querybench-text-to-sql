# QueryBench – English-to-SQL Helper

QueryBench is an LLM-powered Text-to-SQL application that converts natural language questions into executable SQLite queries.

The project uses a locally hosted language model to generate SQL, dynamically reads database schemas, validates generated queries, and executes them in read-only mode. It also includes a custom benchmark to evaluate SQL generation performance.

## Features

- Convert natural language questions into SQL queries.
- Generate SQL using Ollama and Qwen 2.5 (3B).
- Dynamically extract database schema and relationships.
- Validate generated SQL before execution.
- Execute queries in read-only mode.
- Explore database tables, columns and relationships.
- View query results and download them as CSV.
- Maintain query history during a session.
- Evaluate generated SQL using a custom 50-question benchmark.

## Technology Stack

- Python
- SQLite
- Ollama
- Qwen 2.5 (3B)
- Streamlit
- Pandas

## Database Schema

The project uses a university database containing five tables:

1. Departments
2. Students
3. Courses
4. Enrollments
5. Marks

The database contains 1,325 records across these tables.

## Project Structure

```text
querybench-text-to-sql/
├── app.py
├── requirements.txt
├── README.md
├── data/
│   ├── university.db
│   ├── evaluation_questions.json
│   ├── expected_results.json
│   ├── llm_evaluation_results.json
│   ├── llm_evaluation_details.csv
│   └── llm_evaluation_summary.csv
├── src/
│   ├── database/
│   ├── evaluation/
│   └── llm/
└── prompts/
