# CSV Upload - Quick Reference

## 🚀 Quick Start

```bash
# Start server
python main_entry.py

# Upload CSV
curl -X POST "http://localhost:8000/upload-csv" \
     -H "Content-Type: text/csv" \
     --data-binary @your_file.csv
```

## 📋 Required CSV Format

### Minimum Required Columns
```csv
course_id,day,start_time,end_time,room_id
CS101,Monday,09:00,10:30,F1.01
MATH201,Tuesday,10:45,12:15,F1.02
```

### Complete Format
```csv
course_id,section_id,lecture_number,day,start_time,end_time,room_id,instructor_id
CS101,S1,1,Monday,09:00,10:30,F1.01,PROF01
MATH201,S2,1,Tuesday,10:45,12:15,F1.02,PROF02
```

## 🔧 Supported Column Names

| Field | Supported Names |
|-------|----------------|
| Course ID | `course_id`, `courseid`, `course`, `Course` |
| Day | `day`, `Day`, `DAY` |
| Start Time | `start_time`, `starttime`, `start`, `Start` |
| End Time | `end_time`, `endtime`, `end`, `End` |
| Room | `room_id`, `roomid`, `room`, `Room` |
| Section | `section_id`, `sectionid`, `section`, `Section` |
| Lecture | `lecture_number`, `lecturenumber`, `lecture`, `Lecture` |
| Instructor | `instructor_id`, `instructorid`, `instructor`, `Instructor` |

## ⏰ Time Format

- **Format**: `HH:MM` (24-hour)
- **Examples**: `09:00`, `14:30`, `16:45`
- **Auto-fixes**: `0:15` → `12:15`, `0:29` → `12:29`

## 📅 Days

- **Valid**: `Monday`, `Tuesday`, `Wednesday`, `Thursday`, `Friday`, `Saturday`, `Sunday`
- **Case**: Any case accepted (auto-converted to title case)

## 🏢 Rooms

- **Format**: Any string identifier
- **Examples**: `F1.01`, `G.02`, `Lab1`, `Hall-A`

## 🎯 Defaults

| Field | Default Value |
|-------|---------------|
| section_id | `S1` |
| lecture_number | Auto-extracted from course_id |
| instructor_id | `UNKNOWN` |

## ✅ Success Response

```json
{
  "message": "CSV processed successfully",
  "filename": "uploaded_file.csv",
  "total": 14,
  "created": 14,
  "failed": 0,
  "created_ids": [1, 2, 3, ...],
  "failures": []
}
```

## ❌ Error Response

```json
{
  "detail": "Missing required CSV columns: course_id, day"
}
```

## 🔍 Common Issues

| Issue | Solution |
|-------|----------|
| Missing columns | Add required columns: course_id, day, start_time, end_time, room_id |
| Invalid time format | Use HH:MM format (e.g., 09:00, not 9:00) |
| Invalid day | Use full day names (Monday, not Mon) |
| Duplicate entries | Each course+section+lecture combination must be unique |
| BOM issues | Save CSV as UTF-8 without BOM |

## 📊 Validation

After upload, validate your schedule:

```bash
# Check for conflicts
curl -X POST "http://localhost:8000/validate"

# Get efficiency metrics
curl -X GET "http://localhost:8000/efficiency"
```

## 📚 Full Documentation

For complete usage instructions, see [USAGE_GUIDE.md](USAGE_GUIDE.md).
