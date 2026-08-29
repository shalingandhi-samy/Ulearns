"""
One-off converter: raw_ulearn_export.csv (Associate, Job Description, Item Name,
Due Date [Excel serial], Manager) -> ulearn_data.csv (Associate Name, Shift,
Ulearn, Due Date [MM/DD/YYYY], Managers) as expected by build_dashboard.py.
"""
import csv
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SRC = BASE_DIR / "raw_ulearn_export.csv"
DST = BASE_DIR / "ulearn_data.csv"

EXCEL_EPOCH = datetime(1899, 12, 30)  # Excel's serial-date epoch (accounts for the 1900 leap bug)


def serial_to_date(serial: str) -> str:
    serial = serial.strip()
    if not serial:
        return ""
    try:
        dt = EXCEL_EPOCH + timedelta(days=int(float(serial)))
        return dt.strftime("%m/%d/%Y")
    except ValueError:
        return serial  # already a plain date string, leave as-is


def main():
    with SRC.open(newline="", encoding="utf-8") as f_in:
        reader = csv.DictReader(f_in)
        rows = list(reader)

    with DST.open("w", newline="", encoding="utf-8") as f_out:
        writer = csv.writer(f_out)
        writer.writerow(["Associate Name", "Shift", "Ulearn", "Due Date", "Managers"])
        for r in rows:
            writer.writerow([
                r["Associate"].strip(),
                r["Job Description"].strip(),
                r["Item Name"].strip(),
                serial_to_date(r["Due Date"]),
                r["Manager"].strip(),
            ])

    print(f"Wrote {DST} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
