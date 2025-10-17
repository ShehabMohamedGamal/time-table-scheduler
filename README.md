# Intelligent Timetable Management System

A modular, object-oriented university timetable management system with automated conflict detection, efficiency analysis, and RESTful API.

## 📁 Project Structure

```
timetable-system/
│
├── main.py                 # Application entry point
├── config.py               # Centralized configuration
├── requirements.txt        # Python dependencies
├── README.md              # This file
│
├── src/                   # Source modules
│   ├── __init__.py
│   ├── database.py        # DatabaseManager - SQLite operations
│   ├── parser.py          # DataParser - CSV parsing
│   ├── validator.py       # ScheduleValidator - Conflict detection
│   ├── manager.py         # SlotManager - Slot CRUD operations
│   └── api.py             # APIHandler - FastAPI endpoints
│
├── timetable.db           # SQLite database (auto-created)
└── timetable.log          # Application logs (auto-created)
```

## 🏗️ Architecture

### Design Principles

The system follows **SOLID principles** and clean architecture:

1. **Single Responsibility**: Each class has one clear purpose
2. **Dependency Injection**: Components receive dependencies via constructor
3. **Separation of Concerns**: Clear boundaries between layers
4. **Modularity**: Easy to extend and maintain

### Component Diagram

```
┌─────────────────────────────────────────────────┐
│              FastAPI Application                 │
│                  (api.py)                        │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│             SlotManager                          │
│  • Coordinates operations                        │
│  • Transaction management                        │
│              (manager.py)                        │
└────────┬────────────────────────────────┬───────┘
         │                                 │
         ▼                                 ▼
┌────────────────────┐          ┌─────────────────┐
│ DatabaseManager    │          │ScheduleValidator│
│ • CRUD operations  │◄─────────│ • Conflict check│
│ • Schema mgmt      │          │ • Efficiency    │
│   (database.py)    │          │   (validator.py)│
└────────────────────┘          └─────────────────┘
         ▲
         │
┌────────┴───────────┐
│    DataParser      │
│ • CSV parsing      │
│ • Data validation  │
│    (parser.py)     │
└────────────────────┘
```

## 🚀 Installation

### Prerequisites

- Python 3.8+
- pip

### Setup

```bash
# Clone or extract project
cd timetable-system

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

The API will be available at:
- **API Base**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 📊 Database Schema

### Tables

1. **courses**: Course information
   - course_id (PK), course_name, credits, course_type

2. **instructors**: Faculty members
   - instructor_id (PK), name, preferred_slots, qualified_courses

3. **rooms**: Available rooms
   - room_id (PK), room_type, capacity

4. **sections**: Student sections
   - section_id (PK), semester, student_count

5. **schedule**: Main timetable
   - schedule_id (PK), course_id (FK), section_id (FK), lecture_number
   - day, start_time, end_time, room_id (FK), instructor_id (FK)
   - created_at, updated_at

## 🔌 API Endpoints

### Schedule Management

- `GET /slots` - Get all schedule entries
- `GET /slots/{id}` - Get specific slot
- `POST /slots` - Create new slot
- `PUT /slots/{id}` - Update slot
- `DELETE /slots/{id}` - Delete slot

### Validation & Analytics

- `POST /validate` - Validate entire schedule
- `GET /efficiency` - Get efficiency metrics

### Data Import

- `POST /upload-csv` - Upload CSV file

### System

- `GET /health` - Health check

## 📝 API Usage Examples

### Create a Schedule Slot

```bash
curl -X POST http://localhost:8000/slots \
  -H "Content-Type: application/json" \
  -d '{
    "course_id": "CS101",
    "section_id": "S1",
    "lecture_number": 1,
    "day": "Monday",
    "start_time": "09:00",
    "end_time": "10:30",
    "room_id": "Lab1",
    "instructor_id": "I001"
  }'
```

### Update a Slot

```bash
curl -X PUT http://localhost:8000/slots/1 \
  -H "Content-Type: application/json" \
  -d '{
    "day": "Tuesday",
    "start_time": "14:00"
  }'
```

### Validate Schedule

```bash
curl -X POST http://localhost:8000/validate
```

### Upload CSV

```bash
curl -X POST http://localhost:8000/upload-csv \
  -F "file=@schedule.csv"
```

## 📄 CSV Format

The system accepts CSV files with the following columns:

```csv
course_id,section_id,lecture_number,day,start_time,end_time,room_id,instructor_id
CS101,S1,1,Monday,09:00,10:30,Lab1,I001
CS102,S1,1,Monday,11:00,12:30,Room101,I002
```

### Required Columns

- `course_id`: Course identifier (max 50 chars)
- `section_id`: Section identifier (max 50 chars)
- `lecture_number`: Integer 1-10
- `day`: Monday-Sunday
- `start_time`: HH:MM format (e.g., 09:00)
- `end_time`: HH:MM format (e.g., 10:30)
- `room_id`: Room identifier (max 50 chars)
- `instructor_id`: Instructor identifier (max 50 chars)

## 🔍 Validation Rules

### Hard Constraints (Must Not Violate)

1. **Instructor Conflict**: No instructor can teach multiple classes simultaneously
2. **Room Conflict**: No room can host multiple classes simultaneously
3. **Section Conflict**: No section can attend multiple classes simultaneously
4. **Time Validity**: End time must be after start time

### Soft Constraints (Warnings)

1. **Gaps**: Warns about idle time for rooms and students
2. **Utilization**: Flags underutilized (<30%) or overloaded (>90%) resources
3. **Time Preferences**: Warns about early morning (<8 AM) or late evening (>6 PM) classes

## ⚙️ Configuration

Edit `config.py` to customize:

```python
# Database settings
db_config.db_path = "custom_path.db"

# API settings
api_config.port = 8080
api_config.host = "0.0.0.0"

# Schedule validation
schedule_config.working_hours_per_day = 10
schedule_config.min_gap_warning_hours = 2.0
```

## 🧪 Testing

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests (create tests/ directory first)
pytest tests/
```

## 📈 Efficiency Metrics

The system calculates:

- **Overall Efficiency**: Average utilization across resources
- **Room Utilization**: Percentage of available hours used per room
- **Instructor Utilization**: Teaching load per instructor
- **Gap Analysis**: Idle time periods
- **Warnings**: Specific inefficiencies and issues

## 🛠️ Extending the System

### Adding New Constraints

1. Edit `src/validator.py`
2. Add validation method to `ScheduleValidator`
3. Call from `validate_slot()` or `validate_entire_schedule()`

### Adding New API Endpoints

1. Edit `src/api.py`
2. Add route in `_register_routes()`
3. Use dependency injection to access managers

### Supporting New Data Formats

1. Edit `src/parser.py`
2. Add new parsing method to `DataParser`
3. Register in API upload endpoint

## 📚 Class Responsibilities

### `DatabaseManager` (database.py)
- SQLite connection management
- CRUD operations for all entities
- Conflict detection queries
- Transaction management

### `DataParser` (parser.py)
- CSV file parsing
- Data validation and cleaning
- Format conversion
- Error handling for malformed data

### `ScheduleValidator` (validator.py)
- Hard constraint checking
- Soft constraint warnings
- Efficiency calculations
- Utilization analysis

### `SlotManager` (manager.py)
- High-level slot operations
- Coordination between DB and validator
- Bulk operations
- Transaction orchestration

### `APIHandler` (api.py)
- FastAPI application setup
- Route registration
- HTTP request/response handling
- Error transformation

## 📋 Best Practices Implemented

✅ **Dependency Injection**: Clean separation of concerns  
✅ **Context Managers**: Proper resource cleanup  
✅ **Logging**: Comprehensive activity tracking  
✅ **Type Hints**: Enhanced code readability  
✅ **Docstrings**: Complete API documentation  
✅ **Error Handling**: Graceful failure management  
✅ **Validation**: Input sanitization at multiple layers  
✅ **Indexing**: Optimized database queries  
✅ **Transactions**: ACID compliance  
✅ **PEP 8**: Python style guide compliance  

## 🐛 Troubleshooting

### Database locked error
- Close any database browser tools
- Check for concurrent access

### CSV parsing fails
- Verify CSV format and encoding (UTF-8)
- Check for required columns
- Validate time format (HH:MM)

### Conflicts not detected
- Verify data exists in database
- Check time overlap logic
- Review validator configuration

## 📞 Support

For issues or questions:
1. Check the logs: `timetable.log`
2. Review API docs: http://localhost:8000/docs
3. Validate configuration: `config.py`

## 📄 License

Educational project for Intelligent Systems course.
