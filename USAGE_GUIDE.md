# Timetable Scheduler - Complete Usage Guide

## 🚀 Quick Start

### 1. Installation & Setup

```bash
# Install dependencies
pip install -r requirements_file.txt

# Start the server
python main_entry.py
```

The server will start on `http://localhost:8000` with interactive API documentation at `http://localhost:8000/docs`.

### 2. CSV Upload

Your timetable scheduler now supports CSV uploads! Here's how to use it:

#### Supported CSV Formats

The system is flexible and supports various CSV formats. Here are the key requirements:

**Required Columns:**
- `course_id` (or `Course`) - Course identifier
- `day` (or `Day`) - Day of the week
- `start_time` (or `Start`) - Start time in HH:MM format
- `end_time` (or `End`) - End time in HH:MM format  
- `room_id` (or `Room`) - Room identifier

**Optional Columns:**
- `section_id` (or `Section`) - Section identifier (defaults to 'S1')
- `lecture_number` (or `Lecture`) - Lecture number (auto-extracted from course_id if missing)
- `instructor_id` (or `Instructor`) - Instructor identifier (defaults to 'UNKNOWN')

#### Example CSV Format

```csv
course_id,section_id,lecture_number,day,start_time,end_time,room_id,instructor_id
CS101,S1,1,Monday,09:00,10:30,F1.01,PROF01
MATH201,S2,1,Tuesday,10:45,12:15,F1.02,PROF02
PHYS101,S1,1,Wednesday,14:00,15:30,F1.20,PROF03
```

#### Upload via API

```bash
# Upload CSV file
curl -X POST "http://localhost:8000/upload-csv" \
     -H "Content-Type: text/csv" \
     --data-binary @your_timetable.csv
```

#### Upload via Web Interface

1. Go to `http://localhost:8000/docs`
2. Find the `/upload-csv` endpoint
3. Click "Try it out"
4. Upload your CSV file
5. Click "Execute"

## 📊 API Endpoints

### Core Schedule Management

#### Get All Slots
```bash
GET /slots
```
Returns all schedule slots in the system.

#### Get Specific Slot
```bash
GET /slots/{schedule_id}
```
Returns details of a specific schedule slot.

#### Create New Slot
```bash
POST /slots
Content-Type: application/json

{
  "course_id": "CS101",
  "section_id": "S1",
  "lecture_number": 1,
  "day": "Monday",
  "start_time": "09:00",
  "end_time": "10:30",
  "room_id": "F1.01",
  "instructor_id": "PROF01"
}
```

#### Update Slot
```bash
PUT /slots/{schedule_id}
Content-Type: application/json

{
  "day": "Tuesday",
  "start_time": "10:00",
  "end_time": "11:30"
}
```

#### Delete Slot
```bash
DELETE /slots/{schedule_id}
```

### Validation & Analytics

#### Validate Schedule
```bash
POST /validate
```
Checks for conflicts and validates the entire schedule.

#### Get Efficiency Metrics
```bash
GET /efficiency
```
Returns utilization metrics and efficiency statistics.

#### Health Check
```bash
GET /health
```
Returns system health status.

## 🔧 Configuration

### Time Format
- Use 24-hour format: `HH:MM` (e.g., `09:00`, `14:30`)
- Supported time slots: `09:00-09:45`, `09:45-10:30`, `10:45-11:30`, etc.

### Days of Week
Supported days: `Monday`, `Tuesday`, `Wednesday`, `Thursday`, `Friday`, `Saturday`, `Sunday`

### Room IDs
Use consistent room identifiers (e.g., `F1.01`, `G.02`, `Lab1`)

## 📝 CSV Processing Features

### Automatic Data Cleaning
The system automatically handles common CSV issues:

- **Time Format Fixes**: `0:15` → `12:15`, `0:29` → `12:29`
- **BOM Handling**: Automatically removes Byte Order Mark from UTF-8 files
- **Field Mapping**: Supports various column name variations
- **Missing Data**: Provides sensible defaults for optional fields

### Data Validation
- Validates time format and ranges
- Checks for scheduling conflicts
- Ensures required fields are present
- Validates day names and room assignments

### Error Handling
- Detailed error messages for invalid data
- Skips invalid rows while processing valid ones
- Returns comprehensive failure reports

## 🎯 Usage Examples

### Example 1: Basic Course Schedule

```csv
course_id,day,start_time,end_time,room_id,instructor_id
CS101,Monday,09:00,10:30,F1.01,PROF01
CS101,Wednesday,09:00,10:30,F1.01,PROF01
MATH201,Tuesday,10:45,12:15,G.02,PROF02
PHYS101,Thursday,14:00,15:30,Lab1,PROF03
```

### Example 2: Multiple Sections

```csv
course_id,section_id,lecture_number,day,start_time,end_time,room_id,instructor_id
CS101,S1,1,Monday,09:00,10:30,F1.01,PROF01
CS101,S2,1,Monday,11:00,12:30,F1.02,PROF01
CS101,S1,2,Wednesday,09:00,10:30,F1.01,PROF01
CS101,S2,2,Wednesday,11:00,12:30,F1.02,PROF01
```

### Example 3: Complex Schedule

```csv
Course,Day,Start,End,Room,Instructor
LRA401,Sunday,9:00,10:30,F1.01,PROF01
LRA402,Sunday,10:45,12:15,F1.02,PROF02
LRA403,Sunday,12:29,13:59,F1.20,PROF03
LRA404,Sunday,14:15,15:45,F1.21,PROF04
```

## 🔍 Troubleshooting

### Common Issues

#### 1. CSV Upload Fails
- **Check column names**: Ensure required columns are present
- **Verify time format**: Use HH:MM format (e.g., 09:00, not 9:00)
- **Check file encoding**: Save as UTF-8 without BOM

#### 2. Time Format Errors
- Use 24-hour format: `09:00` not `9:00`
- Ensure times are in HH:MM format
- Check for invalid times like `25:00` or `12:70`

#### 3. Missing Data
- Provide course_id, day, start_time, end_time, room_id
- Optional fields will use defaults if missing

#### 4. Duplicate Entries
- Each combination of course_id, section_id, lecture_number must be unique
- Check for existing entries before uploading

### Debug Mode

Enable detailed logging by setting the log level:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📈 Performance Tips

1. **Batch Uploads**: Use CSV upload for multiple entries
2. **Validation**: Run validation after major changes
3. **Efficiency**: Check efficiency metrics regularly
4. **Cleanup**: Remove unused slots to improve performance

## 🔒 Security Notes

- The API runs on localhost by default
- No authentication is implemented (suitable for local use)
- Database is stored locally in `timetable.db`
- CSV uploads are processed in memory

## 📚 Advanced Usage

### Custom Field Mapping

The parser supports flexible field mapping. You can use any of these column names:

- **Course ID**: `course_id`, `courseid`, `course`, `Course`
- **Day**: `day`, `Day`, `DAY`
- **Time**: `start_time`, `starttime`, `start`, `Start`
- **Room**: `room_id`, `roomid`, `room`, `Room`

### Bulk Operations

For large datasets, consider:
1. Splitting large CSV files into smaller chunks
2. Using the bulk create API for programmatic uploads
3. Running validation after each batch

### Integration

The system can be integrated with other applications via:
- REST API endpoints
- Direct database access
- CSV import/export functionality

## 🆘 Support

For issues or questions:
1. Check the API documentation at `/docs`
2. Review error messages in the response
3. Validate your CSV format against the examples
4. Check the system logs for detailed error information

---

**Happy Scheduling! 🎓📅**
