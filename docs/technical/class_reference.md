# Class Reference

## Data Layer

### LevelParser

```python
class LevelParser:
    """Parses and validates course level configuration"""

    def load_levels(self) -> Dict[str, List]:
        """Load level configuration from file"""

    def validate_against_db(self) -> List[str]:
        """Validate courses against database"""
```

### DatabaseManager

```python
class DatabaseManager:
    """Manages database operations with transaction support"""

    def execute_query(self, query: str, params: Tuple = ()) -> QueryResult:
        """Execute single query with parameters"""

    def transaction(self, queries: List[Tuple[str, Tuple]]) -> QueryResult:
        """Execute multiple queries in transaction"""
```

## CSP Engine

### Variable

```python
class Variable:
    """Represents a schedulable unit in the timetable"""

    def assign(self, time_slot: TimeSlot, room_id: str, instructor_id: str):
        """Assign values to variable"""

    def conflicts_with(self, other: 'Variable') -> bool:
        """Check for conflicts with another variable"""
```

### Solver

```python
class Solver:
    """CSP solver with optimization"""

    def solve(self, variables: List[Variable], max_solutions: int = 1) -> List[List[Variable]]:
        """Find solutions using backtracking with forward checking"""
```

## Core Services

### TimetableGenerator

```python
class TimetableGenerator:
    """Generates complete timetables using CSP solver"""

    def generate(self, max_attempts: int = 3) -> GeneratorResult:
        """Generate complete timetable for all levels"""
```

### SolutionValidator

```python
class SolutionValidator:
    """Validates and analyzes timetable solutions"""

    def validate_solution(self, timetable: Dict[int, List[Variable]]) -> ValidationMetrics:
        """Validate complete timetable solution"""
```
