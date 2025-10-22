from typing import List, Dict, Any, Optional, Tuple, Union
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from .query_optimizer import QueryOptimizer, QueryStats  # Added QueryStats import

@dataclass
class QueryResult:
    """Wrapper for database query results"""
    success: bool
    data: Optional[List[Any]] = None
    error: Optional[str] = None
    rows_affected: int = 0

class DatabaseManager:
    """Manages database operations with optimization support"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.optimizer = QueryOptimizer(db_path)
    
    @contextmanager
    def connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def execute_query(self, 
                     query: str, 
                     params: Tuple = (), 
                     fetch: bool = True,
                     analyze: bool = False
                     ) -> Union[QueryResult, Tuple[QueryResult, QueryStats]]:
        """Execute a single query with optional performance analysis"""
        try:
            with self.connection() as conn:
                cur = conn.cursor()
                
                if analyze:
                    # Always get stats when analyze is True
                    stats = self.optimizer.analyze_query(query, params)
                    cur.execute(query, params)
                else:
                    cur.execute(query, params)
                    stats = None
                
                if fetch:
                    data = cur.fetchall()
                    result = QueryResult(True, data=data, rows_affected=cur.rowcount)
                else:
                    result = QueryResult(True, rows_affected=cur.rowcount)
                
                # Only return tuple with stats when analyze is True and stats exists
                if analyze and stats is not None:
                    return (result, stats)
                return result
                
        except sqlite3.Error as e:
            return QueryResult(False, error=str(e))

    def execute_batch(self, 
                     query: str, 
                     param_list: List[Tuple]
                     ) -> QueryResult:
        """Execute batch operation with multiple parameter sets"""
        try:
            with self.connection() as conn:
                cur = conn.cursor()
                cur.executemany(query, param_list)
                return QueryResult(True, rows_affected=cur.rowcount)
                
        except sqlite3.Error as e:
            return QueryResult(False, error=str(e))

    def transaction(self, queries: List[Tuple[str, Tuple]]) -> QueryResult:
        """Execute multiple queries in a single transaction"""
        try:
            with self.connection() as conn:
                cur = conn.cursor()
                results = []
                
                for query, params in queries:
                    # Always set analyze=False for transactions
                    query_result = self.execute_query(query, params, analyze=False)
                    
                    # We know it's QueryResult since analyze=False
                    if not isinstance(query_result, QueryResult):
                        return QueryResult(False, error="Unexpected query result type")
                    
                    if not query_result.success:
                        return query_result
                    
                    if query_result.data:
                        results.append(query_result.data)
                
                return QueryResult(True, data=results)
                
        except sqlite3.Error as e:
            return QueryResult(False, error=str(e))

    def create_record(self, table: str, data: Dict[str, Any]) -> QueryResult:
        """Insert a new record"""
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        result = self.execute_query(query, tuple(data.values()), fetch=False)
        return result if isinstance(result, QueryResult) else result[0]

    def read_records(self, 
                    table: str, 
                    conditions: Optional[Dict[str, Any]] = None
                    ) -> QueryResult:
        """Read records with optional conditions"""
        query = f"SELECT * FROM {table}"
        params = ()
        
        if conditions:
            where_clause = ' AND '.join([f"{k} = ?" for k in conditions.keys()])
            query += f" WHERE {where_clause}"
            params = tuple(conditions.values())
            
        result = self.execute_query(query, params)
        return result if isinstance(result, QueryResult) else result[0]

    def update_record(self, 
                     table: str, 
                     data: Dict[str, Any], 
                     conditions: Dict[str, Any]
                     ) -> QueryResult:
        """Update records matching conditions"""
        set_clause = ', '.join([f"{k} = ?" for k in data.keys()])
        where_clause = ' AND '.join([f"{k} = ?" for k in conditions.keys()])
        query = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"
        params = tuple(list(data.values()) + list(conditions.values()))
        result = self.execute_query(query, params, fetch=False)
        return result if isinstance(result, QueryResult) else result[0]

    def delete_record(self, 
                     table: str, 
                     conditions: Dict[str, Any]
                     ) -> QueryResult:
        """Delete records matching conditions"""
        where_clause = ' AND '.join([f"{k} = ?" for k in conditions.keys()])
        query = f"DELETE FROM {table} WHERE {where_clause}"
        result = self.execute_query(query, tuple(conditions.values()), fetch=False)
        return result if isinstance(result, QueryResult) else result[0]