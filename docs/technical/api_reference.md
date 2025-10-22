# API Reference

## Database Operations

### Query Execution

```python
# Execute single query
result = db_manager.execute_query(
    "SELECT * FROM courses WHERE course_type = ?",
    ("Lecture",)
)

# Execute transaction
result = db_manager.transaction([
    ("INSERT INTO courses VALUES (?, ?, ?)", ("CSC101", "Intro CS", "Lecture")),
    ("UPDATE rooms SET capacity = ? WHERE room_id = ?", (30, "R101"))
])
```

## Timetable Generation

### Basic Generation

```python
generator = TimetableGenerator(db_path, levels_path)
result = generator.generate()

if result.success:
    timetable = result.timetable
    stats = result.stats
else:
    print(f"Generation failed: {result.error}")
```

### With Custom Constraints

```python
generator.constraint_manager.add_constraint(custom_constraint)
result = generator.generate(max_attempts=5)
```

## Solution Validation

### Validation

```python
validator = SolutionValidator(constraint_manager)
metrics = validator.validate_solution(timetable)

if metrics.is_valid:
    print(f"Quality score: {metrics.quality_score}")
else:
    print("Violations:", metrics.constraint_violations)
```

### Report Generation

```python
reporter = ReportGenerator("reports")
report = reporter.generate_report(metrics, variables, stats)
reporter.save_report(report, format='json')
```
