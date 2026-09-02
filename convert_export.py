"""
One-off converter: raw_ulearn_export.csv -> ulearn_data.csv (Associate Name,
Shift, Ulearn, Due Date [MM/DD/YYYY], Managers, Late, DueSoon7) as expected by
build_dashboard.py.

Source format (as of Sept 2026): 13 columns --
Associate, WIN, User ID, Job Description, Item Name, Due Date, Late,
Next 7 Days, Next 14 Days, Next 30 Days, Next 60 Days, Manager, Position

Only Late and Next 7 Days are carried through today (the dashboard buckets
pending items into "Past Due" and "Due in 7 Days"). Next 14/30/60 Days and
Position are ignored for now -- easy to wire in later if a need shows up.
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


def get(row: dict, *names: str) -> str:
    """Source column headers sometimes carry stray trailing spaces (e.g.
    'Late ', 'Next 14 Days '). Try each candidate name, stripped or not."""
    for name in names:
        for key in (name, f"{name} ", name.strip()):
            if key in row:
                return row[key].strip()
    return ""


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
        key = (get(r, "Associate"), get(r, "Job Description"),
               get(r, "Item Name"), get(r, "Due Date"), get(r, "Manager"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(r)
    dupe_count = len(rows) - len(deduped)

    with DST.open("w", newline="", encoding="utf-8") as f_out:
        writer = csv.writer(f_out)
        writer.writerow(["Associate Name", "Shift", "Ulearn", "Due Date", "Managers", "Late", "DueSoon7"])
        for r in deduped:
            writer.writerow([
                get(r, "Associate"),
                get(r, "Job Description"),
                get(r, "Item Name"),
                serial_to_date(get(r, "Due Date")),
                get(r, "Manager"),
                get(r, "Late"),
                get(r, "Next 7 Days"),
            ])

    print(f"Wrote {DST} ({len(deduped)} rows, {dupe_count} exact-duplicate rows dropped)")


if __name__ == "__main__":
    main()
