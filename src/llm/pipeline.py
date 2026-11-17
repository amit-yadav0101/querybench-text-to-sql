
from src.llm.text_to_sql import generate_sql
from src.database.query_runner import execute_read_only


def ask_database(question):
    # Generate SQL
    sql = generate_sql(question)

    # Execute SQL safely
    result = execute_read_only(sql)

    return {
        "question": question,
        "sql": sql,
        "result": result
    }


if __name__ == "__main__":
    question = "Find the names of students enrolled in Database Management."

    response = ask_database(question)

    print("\nQuestion:", response["question"])
    print("\nGenerated SQL:\n", response["sql"])

    if response["result"]["success"]:
        print("\nResults:")
        for row in response["result"]["rows"][:10]:
            print(row)

        print("\nTotal rows:", response["result"]["row_count"])
    else:
        print("\nError:", response["result"]["error"])
