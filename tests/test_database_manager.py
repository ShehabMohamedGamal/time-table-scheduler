import unittest
import tempfile
import sqlite3
from src.database.database_manager import DatabaseManager

class TestDatabaseManager(unittest.TestCase):
    def setUp(self):
        # Create temporary database
        self.db_file = tempfile.NamedTemporaryFile()
        self.conn = sqlite3.connect(self.db_file.name)
        self.cur = self.conn.cursor()
        
        # Create test table
        self.cur.execute('''
            CREATE TABLE test_table (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                value INTEGER
            )
        ''')
        self.conn.commit()
        self.conn.close()
        
        self.db_manager = DatabaseManager(self.db_file.name)

    def test_crud_operations(self):
        # Create
        result = self.db_manager.create_record(
            'test_table',
            {'name': 'test', 'value': 42}
        )
        self.assertTrue(result.success)
        
        # Read
        result = self.db_manager.read_records(
            'test_table',
            {'name': 'test'}
        )
        self.assertTrue(result.success)
        self.assertEqual(len(result.data), 1)
        self.assertEqual(result.data[0][1], 'test')
        
        # Update
        result = self.db_manager.update_record(
            'test_table',
            {'value': 43},
            {'name': 'test'}
        )
        self.assertTrue(result.success)
        
        # Verify update
        result = self.db_manager.read_records(
            'test_table',
            {'name': 'test'}
        )
        self.assertEqual(result.data[0][2], 43)
        
        # Delete
        result = self.db_manager.delete_record(
            'test_table',
            {'name': 'test'}
        )
        self.assertTrue(result.success)
        
        # Verify deletion
        result = self.db_manager.read_records('test_table')
        self.assertEqual(len(result.data), 0)

    def test_batch_operations(self):
        # Test batch insert
        data = [
            ('name1', 1),
            ('name2', 2),
            ('name3', 3)
        ]
        result = self.db_manager.execute_batch(
            "INSERT INTO test_table (name, value) VALUES (?, ?)",
            data
        )
        self.assertTrue(result.success)
        self.assertEqual(result.rows_affected, 3)

    def test_transaction(self):
        # Test successful transaction
        queries = [
            ("INSERT INTO test_table (name, value) VALUES (?, ?)", 
             ('trans1', 1)),
            ("INSERT INTO test_table (name, value) VALUES (?, ?)", 
             ('trans2', 2))
        ]
        result = self.db_manager.transaction(queries)
        self.assertTrue(result.success)
        
        # Verify transaction
        result = self.db_manager.read_records('test_table')
        self.assertEqual(len(result.data), 2)

    def tearDown(self):
        self.db_file.close()