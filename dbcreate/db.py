import sqlite3
import pandas as pd
from typing import Optional

DB_PATH = 'timetable.db'

def create_database(path: str = DB_PATH) -> sqlite3.Connection:
    """Create database and required tables; returns a connection."""
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS courses (
        course_id TEXT PRIMARY KEY,
        course_name TEXT NOT NULL,
        credits REAL NOT NULL,
        course_type TEXT NOT NULL
    )''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS timetable (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        day TEXT NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        level INTEGER,
        room_id TEXT,
        course_id TEXT,
        instructor_id TEXT,
        FOREIGN KEY (room_id) REFERENCES rooms (room_id),
        FOREIGN KEY (course_id) REFERENCES courses (course_id),
        FOREIGN KEY (instructor_id) REFERENCES instructors (instructor_id)
    )''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS rooms (
        room_id TEXT PRIMARY KEY,
        room_type TEXT NOT NULL,
        room_capacity INTEGER
    )''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS instructors (
        instructor_id TEXT PRIMARY KEY,
        instructor_name TEXT NOT NULL,
        preferred_slots TEXT
    )''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS qualified_courses (
        instructor_id TEXT,
        course_id TEXT,
        PRIMARY KEY (instructor_id, course_id)
    )''')
    conn.commit()
    return conn

def load_data(csv_file: str, db_path: str = DB_PATH) -> None:
    """Load data from a CSV into the database. Expects columns used in parser."""
    df = pd.read_csv(csv_file)
    conn = create_database(db_path)
    cur = conn.cursor()
    try:
        # courses
        for _, row in df.iterrows():
            cid = row.get('course_id')
            if pd.notna(cid):
                cur.execute('''
                    INSERT OR REPLACE INTO courses (course_id, course_name, credits, course_type)
                    VALUES (?, ?, ?, ?)
                ''', (cid, row.get('course_name', ''), row.get('credits', 0), row.get('course_type', 'Lecture')))
        # rooms
        for _, row in df.iterrows():
            room_id = row.get('Space')
            if pd.isna(room_id):
                continue
            room_type = row.get('Type')
            cap_raw = row.get('Capacity')
            room_capacity = None
            if pd.notna(cap_raw):
                try:
                    room_capacity = int(cap_raw)
                except Exception:
                    room_capacity = None
            cur.execute('''
                INSERT OR REPLACE INTO rooms (room_id, room_type, room_capacity)
                VALUES (?, ?, ?)
            ''', (room_id, room_type, room_capacity))
        # instructors
        for _, row in df.iterrows():
            iid = row.get('instructor_id')
            if pd.notna(iid):
                name = row.get('instructor_name') or row.get('name') or ''
                prefs = row.get('preferred_slots') if 'preferred_slots' in df.columns else None
                cur.execute('''
                    INSERT OR REPLACE INTO instructors (instructor_id, instructor_name, preferred_slots)
                    VALUES (?, ?, ?)
                ''', (iid, name, prefs))
        # timetable rows
        for level in range(1, 5):
            for _, row in df.iterrows():
                if pd.notna(row.get('Day')):
                    cur.execute('''
                        INSERT INTO timetable (day, start_time, end_time, level)
                        VALUES (?, ?, ?, ?)
                    ''', (row.get('Day'), row.get('start_time'), row.get('end_time'), level))
        # qualified courses (comma-separated like "MTH111,MTH212")
        if 'qualified_courses' in df.columns:
            instr_cols = ['instructor_id', 'Instructor', 'instructor']
            for _, row in df.iterrows():
                # try common instructor id column names
                iid = next((row.get(c) for c in instr_cols if c in df.columns), None)
                if pd.isna(iid) or iid is None:
                    continue
                q = row.get('qualified_courses')
                if pd.isna(q):
                    continue
                for token in str(q).split(','):
                    course_code = token.strip()
                    if not course_code:
                        continue
                    cur.execute('''
                        INSERT OR IGNORE INTO qualified_courses (instructor_id, course_id)
                        VALUES (?, ?)
                    ''', (iid, course_code))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise
    finally:
        conn.close()

def main():
    try:
        load_data('aapl-adham.csv')
        print("Loaded data.")
    except Exception as e:
        print(f"Error loading data: {e}")

if __name__ == "__main__":
    main()
