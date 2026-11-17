
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / "data" / "university.db"

conn = sqlite3.connect(DB_PATH)
conn.execute("pragma foreign_keys = on")
cursor = conn.cursor()

# Check record counts
print("RECORD COUNTS")

tables = ["departments", "students", "courses", "enrollments", "marks"]

for table in tables:
    count = cursor.execute(
        f"select count(*) from {table}"
    ).fetchone()[0]

    print(f"{table}: {count}")

# Check foreign key violations
print("\nFOREIGN KEY CHECK")

violations = cursor.execute(
    "pragma foreign_key_check"
).fetchall()

print("No foreign key violations!" if not violations else violations)

# Check enrollment and mark relationships
print("\nDATA INTEGRITY CHECK")

missing_marks = cursor.execute("""
select count(*)
from enrollments e
left join marks m on e.enrollment_id = m.enrollment_id
where m.mark_id is null
""").fetchone()[0]

print("Enrollments without marks:", missing_marks)

# Test a multi-table join
print("\nJOIN QUERY TEST")

results = cursor.execute("""
select s.name, c.course_name, m.marks_obtained
from students s
join enrollments e on s.student_id = e.student_id
join courses c on e.course_id = c.course_id
join marks m on e.enrollment_id = m.enrollment_id
where m.assessment_type = 'Final'
limit 5
""").fetchall()

for row in results:
    print(row)

conn = sqlite3.connect("data/university.db")

print("\nDEPARTMENT RECORDS")
print(conn.execute("SELECT * FROM departments").fetchall())

print("\nSTUDENT DISTRIBUTION")
print(conn.execute("""
    SELECT d.department_name, COUNT(s.student_id)
    FROM departments d
    LEFT JOIN students s ON d.department_id = s.department_id
    GROUP BY d.department_name
""").fetchall())

print("\nDIRECT IT QUERY COUNT")
print(conn.execute("""
    SELECT COUNT(*)
    FROM students s
    JOIN departments d ON s.department_id = d.department_id
    WHERE d.department_name = 'IT'
""").fetchone())

conn.close()