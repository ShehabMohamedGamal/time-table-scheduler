# Database schema — timetable.db

Readable reference for the SQLite schema used by the timetable scheduler. Each table includes columns, short description and examples.

Notes on loader behavior (current configuration)
- The CSV loader only imports session/timeslot rows into the `timetable` table (day, start_time, end_time and level).
- The loader does NOT import room_id, course_id or instructor_id values from the CSV into the `timetable` table — those fields remain NULL and must be set by application logic.
- Sessions in the CSV are replicated for levels 1..4 when no explicit level is provided in the CSV; if the CSV has a `level` (or `Level`) column that value is used.

---

## tables

### courses
| Column | Type | Null? | Description |
|---|---:|:---:|---|
| course_id | TEXT | NO (PK) | Course code (e.g. `MTH111`) |
| course_name | TEXT | NO | Human readable name |
| credits | REAL | NO | Number of credits |
| course_type | TEXT | NO | Used to match a room (e.g. `Lecture`, `Lab`) |

Example row:
| course_id | course_name | credits | course_type |
|---:|---|---:|---|
| MTH111 | Calculus I | 3.0 | Lecture |

---

### timetable
| Column | Type | Null? | Description |
|---|---:|:---:|---|
| id | INTEGER | NO (PK, AUTOINC) | Internal id |
| day | TEXT | NO | Day name (e.g. `Monday`) |
| start_time | TEXT | NO | `HH:MM` (24h) |
| end_time | TEXT | NO | `HH:MM` (24h) |
| level | INTEGER | NO (DEFAULT 1) | Student level (1..4). CSV rows are replicated into all levels if level not supplied. |
| room_id | TEXT | YES | FK → rooms.room_id (kept NULL by CSV loader) |
| course_id | TEXT | YES | FK → courses.course_id (kept NULL by CSV loader) |
| instructor_id | TEXT | YES | FK → instructors.instructor_id (kept NULL by CSV loader) |

Purpose: stores available timeslots (imported from CSV) and final assignments (filled by application). The loader inserts times/level rows only — room/course/instructor are left for application assignment.

Example row after CSV import (no assignment yet):
| id | day | start_time | end_time | level | room_id | course_id | instructor_id |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | Monday | 09:00 | 10:00 | 1 | NULL | NULL | NULL |

When an assignment is made by the app the row would be updated to set room_id / course_id / instructor_id.

---

### rooms
| Column | Type | Null? | Description |
|---|---:|:---:|---|
| room_id | TEXT | NO (PK) | Room code (CSV fallback: `Space`) |
| room_type | TEXT | NO | E.g. `Lecture`, `Lab` |
| room_capacity | INTEGER | YES | Nullable; capacity may be missing |

Population: the CSV loader is not relied on to fill rooms in the current configuration — populate via application logic or a dedicated import. If you keep CSV-based room import, the loader will look for `room_id` or fallback `Space` and `Type` or fallback `room_type`.

Example row:
| room_id | room_type | room_capacity |
|---:|---:|---:|
| R101 | Lecture | 60 |

---

### instructors
| Column | Type | Null? | Description |
|---|---:|:---:|---|
| instructor_id | TEXT | NO (PK) | Instructor identifier |
| instructor_name | TEXT | NO | Full name |
| preferred_slots | TEXT | YES | Optional; semicolon-separated `Day|HH:MM|HH:MM` tokens |

Population: populate instructors via application logic or a dedicated import. CSV loader does not insert instructor assignments into `timetable`.

Example row:
| instructor_id | instructor_name | preferred_slots |
|---:|---:|---|
| I001 | Alice Smith | Monday\|09:00\|10:00;Wednesday\|14:00\|15:00 |

Alternate: an `instructor_prefs(instructor_id, day, start_time, end_time)` table may be used instead of `preferred_slots`.

---

### qualified_courses
| Column | Type | Null? | Description |
|---|---:|:---:|---|
| instructor_id | TEXT | NO* | FK to instructors |
| course_id | TEXT | NO* | FK to courses |
Primary key: (instructor_id, course_id) — maps which instructors can teach which courses.

Population: you can populate this mapping from CSV or from a separate import. If using CSV, the loader expects a `qualified_courses` column with comma-separated codes (e.g. `MTH111,MTH212`) and an instructor id column — but note the CSV loader is configurable; in the current minimal loader the application should populate this table.

Example mapping rows:
| instructor_id | course_id |
|---:|---:|
| I001 | MTH111 |
| I001 | MTH212 |

---

## CSV → DB mapping summary (current loader behavior)
- The CSV loader imports only session/time rows into `timetable`:
  - Required CSV columns: `Day`, `start_time`, `end_time`.  
  - Optional CSV column: `level` / `Level` — if present and valid its value is used; otherwise the loader replicates the session for levels 1,2,3,4.
- The loader intentionally does NOT import `room_id`, `course_id` or `instructor_id` values from the CSV into the `timetable` table. Those fields must be assigned by the application at scheduling time.
- All other tables (courses, rooms, instructors, qualified_courses) should be populated via application logic or separate import scripts unless you enable CSV-based imports.

Minimal example CSV (header + one row) for the current loader:
Day,start_time,end_time,Level
Monday,09:00,10:00,

This will produce four rows (levels 1..4) in `timetable` with room_id/course_id/instructor_id = NULL.

If your CSV already contains assignment columns and you want them ignored, ensure loader uses the "timeslots-only" mode.

---

## constraints & assumptions
- Time format: `HH:MM` (24-hour, zero-padded). Overlap checks in solver assume this format.
- `level` is integer 1..4 and NOT NULL for timetable rows.
- `room_capacity` may be NULL — treat as unknown or unbounded when matching capacity.
- `timetable` rows are the canonical set of timeslots; assignments (room/course/instructor) are written by the application.

---

## useful queries & examples

Get all timeslots for level 2:
```sql
SELECT day, start_time, end_time
FROM timetable
WHERE level = 2
ORDER BY day, start_time;
```

Mark a timeslot assignment (example):
```sql
UPDATE timetable
SET room_id = 'R101', course_id = 'MTH111', instructor_id = 'I001'
WHERE id = 1;
```

Suggested indexes:
```sql
CREATE INDEX IF NOT EXISTS idx_timetable_level_day_time ON timetable(level, day, start_time);
```

---

## tips
- Use the CSV loader only to populate timeslots. Maintain courses, rooms and instructors with dedicated imports or the application UI/API to avoid accidental assignments from CSV.
- Ensure CSV times are `HH:MM` zero-padded for correct ordering and overlap checks.
- If you want the loader to also populate rooms/instructors/qualified mappings from CSV later, update loader behavior and this schema doc accordingly.
