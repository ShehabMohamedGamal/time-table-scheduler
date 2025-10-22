import unittest
import tempfile
import sqlite3
import os
from src.database.query_optimizer import QueryOptimizer
from src.database.database_manager import DatabaseManager

class TestQueryOptimizer(unittest.TestCase):
    def setUp(self):
        self.db_file = tempfile.NamedTemporaryFile(delete=False)
        self.conn = sqlite3.connect(self.db_file.name)
        self.cur = self.conn.cursor()
        
        # Create test tables with sample data
        self.cur.execute('''
            CREATE TABLE timetable (
                id INTEGER PRIMARY KEY,
                day TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                room_id TEXT,
                course_id TEXT,
                instructor_id TEXT
            )
        ''')
        
        # Insert sample data
        self.cur.executemany(
            "INSERT INTO timetable (day, start_time, end_time, room_id) VALUES (?, ?, ?, ?)",
            [
                ("Monday", "09:00", "10:30", "R101"),
                ("Monday", "11:00", "12:30", "R102"),
                ("Tuesday", "09:00", "10:30", "R101")
            ]
        )
        self.conn.commit()
        self.conn.close()
        
        self.optimizer = QueryOptimizer(self.db_file.name)
        self.db_manager = DatabaseManager(self.db_file.name)

    def test_index_creation(self):
        with sqlite3.connect(self.db_file.name) as conn:
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='index'")
            indices = [row[0] for row in cur.fetchall()]
            
            self.assertTrue(any('idx_timetable_room' in idx for idx in indices))
            self.assertTrue(any('idx_timetable_day_time' in idx for idx in indices))

    def test_query_analysis(self):
        query = "SELECT * FROM timetable WHERE room_id = ?"
        stats = self.optimizer.analyze_query(query, ("R101",))
        
        self.assertTrue(stats.uses_index)
        self.assertEqual(stats.rows_affected, 2)
        self.assertTrue(len(stats.plan) > 0)

    def test_optimized_query_execution(self):
        result, stats = self.db_manager.execute_query(
            "SELECT * FROM timetable WHERE day = ? AND start_time = ?",
            ("Monday", "09:00"),
            analyze=True
        )
        
        self.assertTrue(result.success)
        self.assertTrue(stats.uses_index)
        self.assertEqual(stats.rows_affected, 1)

    def tearDown(self):
        os.unlink(self.db_file.name)