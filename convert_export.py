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
        pass
    # Not a serial number -- likely already a plain date string (e.g. Graph
    # returned "3/9/2026" instead of a serial). Normalize to zero-padded
    # MM/DD/YYYY for consistent display; if that also fails, leave as-is.
    try:
        dt = datetime.strptime(serial, "%m/%d/%Y")
        return dt.strftime("%m/%d/%Y")
    except ValueError:
        return serial


def main():
    with SRC.open(newline="", encoding="utf-8") as f_in:
        reader = csv.DictReader(f_in)
        rows = list(reader)

    # Guard against exact-duplicate rows -- OneDrive/Graph chunked pulls have
    # occasionally repeated a window of rows verbatim; a real pending ULearn
    # never has the same associate/course/due-date/manager listed twice.
    seen = set()
    deduped = []
    for r in rows:
        key = (r["Associate"].strip(), r["Job Description"].strip(),
               r["Item Name"].strip(), r["Due Date"].strip(), r["Manager"].strip())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(r)
    dupe_count = len(rows) - len(deduped)

    with DST.open("w", newline="", encoding="utf-8") as f_out:
        writer = csv.writer(f_out)
        writer.writerow(["Associate Name", "Shift", "Ulearn", "Due Date", "Managers"])
        for r in deduped:
            writer.writerow([
                r["Associate"].strip(),
                r["Job Description"].strip(),
                r["Item Name"].strip(),
                serial_to_date(r["Due Date"]),
                r["Manager"].strip(),
            ])

    print(f"Wrote {DST} ({len(deduped)} rows, {dupe_count} exact-duplicate rows dropped)")


if __name__ == "__main__":
    main()
