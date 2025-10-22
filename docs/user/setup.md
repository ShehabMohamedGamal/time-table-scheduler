# Timetable Generator Setup Guide

## Prerequisites

- Python 3.8 or higher
- SQLite 3
- pip (Python package manager)

## Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/time_table_scheduler.git
cd time_table_scheduler
```

2. Create a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Linux/Mac
```

3. Install dependencies:

```bash
# Install required packages
pip install -r requirements.txt

# For development, install additional packages
pip install -r requirements-dev.txt  # Optional
```

4. Verify installation:

```bash
# Check if packages are installed correctly
python -c "import sqlite3_utils; import click; import rich; print('Setup successful!')"
```

5. Initialize the database:

```bash
python scripts/init_db.py
```

## Dependencies Overview

The project requires the following main packages:

- `sqlite3-utils`: Database management
- `click`: Command-line interface
- `rich`: Terminal formatting
- `pytest`: Testing framework (development only)
- `tabulate`: Table output formatting

## Configuration

1. Create a `levels.json` file:

```json
{
  "level_1": ["CSC111", "MTH101"],
  "level_2": [
    "CSC112",
    ["PHY101", "BIO101"] // Elective group
  ]
}
```

2. Configure database connection in `config.ini`:

```ini
[database]
path = data/timetable.db
```
