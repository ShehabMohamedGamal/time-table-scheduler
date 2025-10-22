import csv
import sys
from typing import List

def read_csv_rows(filename: str, max_preview: int = 5) -> List[List[str]]:
    try:
        with open(filename, newline='') as f:
            reader = csv.reader(f)
            header = next(reader, [])
            rows = [r for r in reader]
            print(f"Total rows (excluding header): {len(rows)}")
            print("Field names: " + ", ".join(header))
            print("\nFirst rows:")
            for row in rows[:max_preview]:
                print(" | ".join(row))
            return rows
    except FileNotFoundError:
        print(f"File not found: {filename}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"Error reading CSV: {e}", file=sys.stderr)
        return []

if __name__ == "__main__":
    read_csv_rows("aapl.csv")
