
import sqlite3
import random
from pathlib import Path

# Use a fixed seed for reproducible data
random.seed(42)

BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / "data" / "university.db"

conn = sqlite3.connect(DB_PATH)
conn.execute("pragma foreign_keys = on")
cursor = conn.cursor()

# Clear existing records in dependency order
cursor.execute("delete from marks")
cursor.execute("delete from enrollments")
cursor.execute("delete from students")
cursor.execute("delete from courses")
cursor.execute("delete from departments")

# Insert departments
departments = [
    ("Computer Science", "Block A"),
    ("Information Technology", "Block B"),
    ("Electronics", "Block C"),
    ("Mechanical Engineering", "Block D"),
    ("Civil Engineering", "Block E")
]

cursor.executemany(
    "insert into departments (department_name, building) values (?, ?)",
    departments
)

# Insert 20 courses
courses = [
    ("Database Management", "IT301", 4, 2),
    ("Web Technologies", "IT302", 3, 2),
    ("Data Structures", "IT303", 4, 2),
    ("Operating Systems", "CS301", 4, 1),
    ("Computer Networks", "CS302", 3, 1),
    ("Artificial Intelligence", "CS303", 4, 1),
    ("Digital Electronics", "EC301", 3, 3),
    ("Microprocessors", "EC302", 4, 3),
    ("Thermodynamics", "ME301", 3, 4),
    ("Machine Design", "ME302", 4, 4),
    ("Fluid Mechanics", "ME303", 3, 4),
    ("Structural Analysis", "CE301", 4, 5),
    ("Surveying", "CE302", 3, 5),
    ("Software Engineering", "IT304", 3, 2),
    ("Computer Architecture", "CS304", 4, 1),
    ("Embedded Systems", "EC303", 4, 3),
    ("Manufacturing Processes", "ME304", 3, 4),
    ("Construction Materials", "CE303", 3, 5),
    ("Python Programming", "IT305", 3, 2),
    ("Algorithms", "CS305", 4, 1)
]

cursor.executemany(
    """insert into courses
    (course_name, course_code, credits, department_id)
    values (?, ?, ?, ?)""",
    courses
)

# Generate 100 students
first_names = [
    "Aarav", "Arjun", "Rohan", "Karan", "Kabir",
    "Simran", "Ananya", "Meera", "Ishita", "Priya",
    "Rahul", "Aditya", "Neha", "Aman", "Sanya"
]

last_names = [
    "Sharma", "Singh", "Kaur", "Verma", "Patel",
    "Gupta", "Malhotra", "Mehta", "Gill", "Kumar"
]

students = []

for i in range(1, 101):
    name = random.choice(first_names) + " " + random.choice(last_names)
    gender = random.choice(["Male", "Female"])
    admission_year = random.choice([2023, 2024, 2025])
    department_id = random.randint(1, 5)

    students.append((
        f"UNI{i:04d}",
        name,
        f"student{i}@university.edu",
        gender,
        admission_year,
        department_id
    ))

cursor.executemany(
    """insert into students
    (roll_number, name, email, gender, admission_year, department_id)
    values (?, ?, ?, ?, ?, ?)""",
    students
)

# Generate enrollments and marks
assessment_types = ["Midterm", "Assignment", "Final"]

for student_id in range(1, 101):
    course_ids = random.sample(range(1, 21), 3)

    for course_id in course_ids:
        semester = random.randint(1, 6)
        academic_year = f"2025-{2026}"
        enrollment_date = f"2025-{random.randint(1, 12):02d}-15"

        cursor.execute(
            """insert into enrollments
            (student_id, course_id, semester, academic_year, enrollment_date)
            values (?, ?, ?, ?, ?)""",
            (student_id, course_id, semester, academic_year, enrollment_date)
        )

        enrollment_id = cursor.lastrowid

        for assessment in assessment_types:
            max_marks = 100
            obtained = random.randint(35, 100)

            cursor.execute(
                """insert into marks
                (enrollment_id, assessment_type, marks_obtained, max_marks)
                values (?, ?, ?, ?)""",
                (enrollment_id, assessment, obtained, max_marks)
            )

# Save changes
conn.commit()

# Display record counts
print("University data generated successfully!\n")

for table in ["departments", "students", "courses", "enrollments", "marks"]:
    count = cursor.execute(
        f"select count(*) from {table}"
    ).fetchone()[0]

    print(f"{table}: {count} records")

conn.close()
