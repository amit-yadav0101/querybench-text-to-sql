
import streamlit as st
import pandas as pd
import sqlite3
from pathlib import Path
from src.llm.pipeline import ask_database

# PAGE CONFIGURATION
st.set_page_config(
    page_title="QueryBench | Text-to-SQL",
    page_icon="",
    layout="wide"
)

DB_PATH = Path("data/university.db")

# SESSION STATE
if "history" not in st.session_state:
    st.session_state.history = []

if "last_response" not in st.session_state:
    st.session_state.last_response = None

# DATABASE INFORMATION
def get_database_info():
    conn = sqlite3.connect(f"file:{DB_PATH.resolve()}?mode=ro", uri=True)
    cursor = conn.cursor()

    tables = cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()

    schema = {}
    relationships = []

    for table in tables:
        name = table[0]

        columns = cursor.execute(
            f'PRAGMA table_info("{name}")'
        ).fetchall()

        schema[name] = columns

        foreign_keys = cursor.execute(
            f'PRAGMA foreign_key_list("{name}")'
        ).fetchall()

        for fk in foreign_keys:
            relationships.append(
                f"{name}.{fk[3]} → {fk[2]}.{fk[4]}"
            )

    counts = {}
    for table in tables:
        counts[table[0]] = cursor.execute(
            f'SELECT COUNT(*) FROM "{table[0]}"'
        ).fetchone()[0]

    conn.close()
    return schema, relationships, counts


# HEADER
st.markdown("""
<style>
.block-container {
    padding-top: 2rem;
    padding-bottom: 3rem;
}
.main-title {
    font-size: 2rem;
    font-weight: 700;
    color: #17365D;
}
.subtitle {
    color: #64748b;
    margin-bottom: 25px;
}
div.stButton > button {
    border-radius: 8px;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">QueryBench</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">Ask questions in English. Get SQL queries and database results.</div>',
    unsafe_allow_html=True
)

# SIDEBAR
with st.sidebar:
    st.title("QueryBench")
    st.caption("AI-powered database assistant")
    st.divider()

    page = st.radio(
        "Navigation",
        ["Query Workspace", "Schema Explorer", "Query History", "About Project"]
    )

    st.divider()
    st.markdown("**Active database**")
    st.info("University Database")
    st.caption("SQLite | 5 tables")

    st.divider()
    st.caption("Powered by Ollama and Qwen 2.5 3B")

# LOAD SCHEMA
try:
    schema, relationships, counts = get_database_info()
except Exception as error:
    st.error(f"Could not load database: {error}")
    st.stop()

# QUERY WORKSPACE
if page == "Query Workspace":

    st.subheader("Query Workspace")
    st.caption("Write your question in natural language.")

    total_records = sum(counts.values())

    c1, c2, c3 = st.columns(3)
    c1.metric("Database Tables", len(schema))
    c2.metric("Total Records", total_records)
    c3.metric("Relationships", len(relationships))

    st.divider()

    st.markdown("**Suggested questions**")

    examples = [
        "Find all students admitted after 2024.",
        "Count the number of students in each department.",
        "Find students enrolled in Database Management.",
        "Find the average marks obtained in each course."
    ]

    cols = st.columns(2)

    for i, example in enumerate(examples):
        if cols[i % 2].button(example, key=f"example_{i}", use_container_width=True):
            st.session_state.selected_question = example

    question = st.text_area(
        "Ask your database",
        value=st.session_state.get("selected_question", ""),
        placeholder="Example: Find the top 5 students based on their average marks.",
        height=110
    )

    if st.button("Generate SQL", type="primary", use_container_width=True):
        if not question.strip():
            st.warning("Please enter a question.")
        else:
            with st.spinner("Generating SQL and executing query..."):
                try:
                    response = ask_database(question)
                    st.session_state.last_response = response

                    st.session_state.history.insert(0, {
                        "question": question,
                        "sql": response["sql"],
                        "success": response["result"]["success"]
                    })

                except Exception as error:
                    st.error(f"Application error: {error}")

    response = st.session_state.last_response

    if response:
        st.divider()
        st.subheader("Generated SQL")

        st.code(response["sql"], language="sql")

        if response["result"]["success"]:
            st.success("Query executed successfully.")

            result = response["result"]

            df = pd.DataFrame(
                result["rows"],
                columns=result["columns"]
            )

            st.subheader("Query Results")

            a, b = st.columns(2)
            a.metric("Rows returned", result["row_count"])
            b.metric("Columns returned", len(result["columns"]))

            st.dataframe(df, use_container_width=True)

            st.download_button(
                "Download results as CSV",
                data=df.to_csv(index=False).encode("utf-8"),
                file_name="query_results.csv",
                mime="text/csv"
            )

        else:
            st.error(response["result"]["error"])

# SCHEMA EXPLORER
elif page == "Schema Explorer":

    st.subheader("Schema Explorer")
    st.caption("Explore the structure of the university database.")

    for table, columns in schema.items():

        with st.expander(f"{table}  |  {counts[table]} records"):
            df = pd.DataFrame(
                columns,
                columns=["Position", "Column Name", "Data Type", "Not Null", "Default", "Primary Key"]
            )

            st.dataframe(
                df[["Column Name", "Data Type", "Not Null", "Primary Key"]],
                hide_index=True,
                use_container_width=True
            )

    st.divider()
    st.subheader("Foreign Key Relationships")

    if relationships:
        for relationship in relationships:
            st.write(f"- {relationship}")
    else:
        st.info("No foreign-key relationships found.")

# QUERY HISTORY
elif page == "Query History":

    st.subheader("Query History")
    st.caption("Questions asked during this session.")

    if st.session_state.history:
        for i, item in enumerate(st.session_state.history):
            with st.expander(item["question"]):
                st.code(item["sql"], language="sql")
                st.write(
                    "Status:",
                    "Successful" if item["success"] else "Failed"
                )

        if st.button("Clear History"):
            st.session_state.history = []
            st.rerun()
    else:
        st.info("No queries have been executed yet.")

# ABOUT
elif page == "About Project":

    st.subheader("About QueryBench")

    st.write("""
    QueryBench is an English-to-SQL application that allows users
    to interact with relational databases using natural language.

    The application uses a locally running language model to
    generate SQL queries and SQLite to execute them.
    """)

    st.markdown("**Technology Stack**")

    st.write("""
    - Python
    - Streamlit
    - SQLite
    - Ollama
    - Qwen 2.5 3B
    - Pandas
    """)

    st.markdown("**Main Features**")

    st.write("""
    - Natural-language to SQL generation
    - Database schema exploration
    - Read-only query execution
    - Query result visualisation
    - CSV export
    - Query history
    """)
