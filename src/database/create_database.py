
import sqlite3
from pathlib import Path

# Set the database location
BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / "data" / "university.db"

# Create the data folder if needed
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# Connect to the SQLite database
conn = sqlite3.connect(DB_PATH)
conn.execute("pragma foreign_keys = on")
cursor = conn.cursor()

# Create departments table
cursor.execute("""
create table if not exists departments (
    department_id integer primary key,
    department_name text not null unique,
    building text not null
)
""")

# Create students table
cursor.execute("""
create table if not exists students (
    student_id integer primary key,
    roll_number text not null unique,
    name text not null,
    email text not null unique,
    gender text not null,
    admission_year integer not null,
    department_id integer not null,
    foreign key (department_id) references departments(department_id)
)
""")

# Create courses table
cursor.execute("""
create table if not exists courses (
    course_id integer primary key,
    course_name text not null,
    course_code text not null unique,
    credits integer not null check (credits > 0),
    department_id integer not null,
    foreign key (department_id) references departments(department_id)
)
""")

# Create enrollments table
cursor.execute("""
create table if not exists enrollments (
    enrollment_id integer primary key,
    student_id integer not null,
    course_id integer not null,
    semester integer not null check (semester between 1 and 8),
    academic_year text not null,
    enrollment_date text not null,
    foreign key (student_id) references students(student_id),
    foreign key (course_id) references courses(course_id),
    unique (student_id, course_id, semester, academic_year)
)
""")

# Create marks table
cursor.execute("""
create table if not exists marks (
    mark_id integer primary key,
    enrollment_id integer not null,
    assessment_type text not null,
    marks_obtained real not null check (marks_obtained >= 0),
    max_marks real not null check (max_marks > 0),
    foreign key (enrollment_id) references enrollments(enrollment_id),
    unique (enrollment_id, assessment_type),
    check (marks_obtained <= max_marks)
)
""")

# Save the database
conn.commit()

# Verify the tables
cursor.execute("""
select name from sqlite_master
where type = 'table'
order by name
""")

print("Database created successfully!")
print("Location:", DB_PATH)
print("\nTables:")

for table in cursor.fetchall():
    print("-", table[0])

conn.close()
