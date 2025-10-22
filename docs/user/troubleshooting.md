# Troubleshooting Guide

## Common Issues

### No Valid Solution Found

**Problem**: Generator cannot find a valid timetable.

**Solutions**:

1. Check constraint conflicts:

```bash
python -m timetable_generator validate --constraints
```

2. Increase maximum attempts:

```bash
python -m timetable_generator generate --max-attempts 10
```

3. Review resource availability:

```bash
python -m timetable_generator analyze-resources
```

### Database Errors

**Problem**: Database connection or query errors.

**Solutions**:

1. Verify database exists:

```bash
ls data/timetable.db
```

2. Check schema:

```bash
python -m timetable_generator validate-schema
```

3. Reset database:

```bash
python scripts/reset_db.py
```

## Error Messages

| Error Code | Description          | Solution                           |
| ---------- | -------------------- | ---------------------------------- |
| E001       | Invalid level format | Check levels.json syntax           |
| E002       | Course not found     | Verify course exists in database   |
| E003       | Resource conflict    | Check room/instructor availability |

## Performance Issues

If generation is slow:

1. Enable indexing:

```bash
python -m timetable_generator optimize-db
```

2. Use batch processing:

```bash
python -m timetable_generator generate --batch-size 100
```

3. Monitor resource usage:

```bash
python -m timetable_generator stats --monitor
```
