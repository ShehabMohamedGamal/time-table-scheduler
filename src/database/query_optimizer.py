from typing import List, Dict, Optional, Tuple
import sqlite3
import time
from dataclasses import dataclass
import logging

@dataclass
class QueryStats:
    """Statistics for query execution"""
    query: str
    execution_time: float
    rows_affected: int
    uses_index: bool
    plan: List[Dict]

class QueryOptimizer:
    """Handles query optimization and performance monitoring"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self._setup_logging()
        self._create_indices()

    def _setup_logging(self):
        """Configure performance logging"""
        handler = logging.FileHandler('query_performance.log')
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def _create_indices(self):
        """Create necessary indices for common queries"""
        indices = [
            ('idx_timetable_course', 'timetable(course_id)'),
            ('idx_timetable_room', 'timetable(room_id)'),
            ('idx_timetable_instructor', 'timetable(instructor_id)'),
            ('idx_timetable_day_time', 'timetable(day, start_time, end_time)')
        ]
        
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            for index_name, index_cols in indices:
                try:
                    cur.execute(f"CREATE INDEX IF NOT EXISTS {index_name} ON {index_cols}")
                except sqlite3.Error as e:
                    self.logger.error(f"Failed to create index {index_name}: {e}")

    def analyze_query(self, query: str, params: Tuple = ()) -> QueryStats:
        """Analyze query execution plan and performance"""
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            
            # Get execution plan
            cur.execute(f"EXPLAIN QUERY PLAN {query}", params)
            plan = [dict(zip(['id', 'parent', 'notused', 'detail'], row)) 
                   for row in cur.fetchall()]
            
            # Check index usage
            uses_index = any('USING INDEX' in row['detail'] 
                           for row in plan)
            
            # Execute and time the query
            start_time = time.time()
            cur.execute(query, params)
            execution_time = time.time() - start_time
            
            # Get results if any
            try:
                results = cur.fetchall()
                rows_affected = len(results)
            except sqlite3.Error:
                rows_affected = cur.rowcount
            
            stats = QueryStats(
                query=query,
                execution_time=execution_time,
                rows_affected=rows_affected,
                uses_index=uses_index,
                plan=plan
            )
            
            # Log performance data
            self._log_performance(stats)
            
            return stats

    def _log_performance(self, stats: QueryStats):
        """Log query performance statistics"""
        self.logger.info(
            f"Query: {stats.query[:100]}... "
            f"Time: {stats.execution_time:.4f}s "
            f"Rows: {stats.rows_affected} "
            f"Index: {stats.uses_index}"
        )