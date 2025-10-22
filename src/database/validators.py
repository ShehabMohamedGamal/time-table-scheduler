from typing import Dict, List, Optional
from dataclasses import dataclass
import sqlite3

@dataclass
class ValidationResult:
    """Results of a validation check"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]

class SchemaValidator:
    """Validates database schema and data integrity"""
    
    EXPECTED_TABLES = {
        'courses': {
            'course_id': 'TEXT PRIMARY KEY',
            'course_name': 'TEXT NOT NULL',
            'credits': 'REAL NOT NULL',
            'course_type': 'TEXT NOT NULL'
        },
        'timetable': {
            'id': 'INTEGER PRIMARY KEY',
            'day': 'TEXT NOT NULL',
            'start_time': 'TEXT NOT NULL',
            'end_time': 'TEXT NOT NULL',
            'level': 'INTEGER',
            'room_id': 'TEXT',
            'course_id': 'TEXT',
            'instructor_id': 'TEXT'
        },
        'rooms': {
            'room_id': 'TEXT PRIMARY KEY',
            'room_type': 'TEXT NOT NULL',
            'room_capacity': 'INTEGER'
        },
        'instructors': {
            'instructor_id': 'TEXT PRIMARY KEY',
            'instructor_name': 'TEXT NOT NULL',
            'preferred_slots': 'TEXT'
        }
    }

    def __init__(self, db_path: str):
        self.db_path = db_path

    def validate_schema(self) -> ValidationResult:
        """Validate database schema against expected structure"""
        errors = []
        warnings = []
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.cursor()
                
                # Get existing tables
                cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
                existing_tables = {row[0] for row in cur.fetchall()}
                
                # Check for missing tables
                for table in self.EXPECTED_TABLES:
                    if table not in existing_tables:
                        errors.append(f"Missing required table: {table}")
                        continue
                    
                    # Check table schema
                    cur.execute(f"PRAGMA table_info({table})")
                    columns = {row[1]: row[2] for row in cur.fetchall()}
                    
                    for col, type_ in self.EXPECTED_TABLES[table].items():
                        if col not in columns:
                            errors.append(
                                f"Missing column {col} in table {table}"
                            )
                        elif columns[col] != type_:
                            warnings.append(
                                f"Column {col} in {table} has type {columns[col]}, "
                                f"expected {type_}"
                            )
                
                return ValidationResult(
                    is_valid=len(errors) == 0,
                    errors=errors,
                    warnings=warnings
                )
                
        except sqlite3.Error as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Database error: {str(e)}"],
                warnings=[]
            )

class RelationshipValidator:
    """Validates referential integrity and relationships"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path

    def validate_relationships(self) -> ValidationResult:
        """Check referential integrity across tables"""
        errors = []
        warnings = []
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.cursor()
                
                # Check timetable foreign keys
                self._check_foreign_key(
                    cur, 'timetable', 'room_id', 'rooms', errors
                )
                self._check_foreign_key(
                    cur, 'timetable', 'course_id', 'courses', errors
                )
                self._check_foreign_key(
                    cur, 'timetable', 'instructor_id', 'instructors', errors
                )
                
                # Check for orphaned records
                self._check_orphaned_records(cur, warnings)
                
                return ValidationResult(
                    is_valid=len(errors) == 0,
                    errors=errors,
                    warnings=warnings
                )
                
        except sqlite3.Error as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Database error: {str(e)}"],
                warnings=[]
            )

    def _check_foreign_key(self, 
                          cur: sqlite3.Cursor, 
                          table: str, 
                          fk_column: str, 
                          ref_table: str, 
                          errors: List[str]) -> None:
        """Check foreign key references"""
        cur.execute(f"""
            SELECT DISTINCT t.{fk_column}
            FROM {table} t
            LEFT JOIN {ref_table} r ON t.{fk_column} = r.{fk_column}
            WHERE t.{fk_column} IS NOT NULL
            AND r.{fk_column} IS NULL
        """)
        invalid_refs = cur.fetchall()
        if invalid_refs:
            refs = ', '.join(str(ref[0]) for ref in invalid_refs)
            errors.append(
                f"Invalid {fk_column} references in {table}: {refs}"
            )

    def _check_orphaned_records(self, 
                              cur: sqlite3.Cursor, 
                              warnings: List[str]) -> None:
        """Check for unused records in reference tables"""
        for ref_table, fk_col in [
            ('rooms', 'room_id'),
            ('courses', 'course_id'),
            ('instructors', 'instructor_id')
        ]:
            cur.execute(f"""
                SELECT COUNT(*)
                FROM {ref_table} r
                LEFT JOIN timetable t ON r.{fk_col} = t.{fk_col}
                WHERE t.{fk_col} IS NULL
            """)
            count = cur.fetchone()[0]
            if count > 0:
                warnings.append(
                    f"Found {count} unused records in {ref_table}"
                )