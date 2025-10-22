# Usage Guide

## Basic Usage

1. Generate a timetable:

```bash
python -m timetable_generator generate --levels levels.json
```

2. Validate an existing timetable:

```bash
python -m timetable_generator validate --input timetable.json
```

3. Export results:

```bash
python -m timetable_generator export --format csv --output schedule.csv
```

## Advanced Features

### Custom Constraints

Add custom constraints in your configuration:

```json
{
  "constraints": {
    "max_daily_hours": 6,
    "preferred_start_time": "09:00",
    "lunch_break": true
  }
}
```

### Resource Management

Specify resource requirements:

```json
{
  "course_requirements": {
    "CSC111": {
      "room_type": "Lecture",
      "min_capacity": 30,
      "requires_projector": true
    }
  }
}
```

### Performance Optimization

For large datasets:

```bash
python -m timetable_generator generate \
    --optimize-memory \
    --parallel \
    --max-attempts 5
```
