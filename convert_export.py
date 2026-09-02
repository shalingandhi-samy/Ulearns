"""
Converter: source workbook (.xlsx, read directly -- see SRC_XLSX below) or a
fallback raw_ulearn_export.csv -> ulearn_data.csv (Associate Name, Shift,
Ulearn, Due Date [MM/DD/YYYY], Managers, Late, DueSoon7, DueSoon14,
DueSoon30, DueSoon60) as expected by build_dashboard.py.

Source format (as of Sept 2026): 13 columns --
Associate, WIN, User ID, Job Description, Item Name, Due Date, Late,
Next 7 Days, Next 14 Days, Next 30 Days, Next 60 Days, Manager, Position

All five status flag columns are carried through now (the dashboard buckets
pending items into Past Due / Due in 7 / 14 / 30 / 60 Days). WIN, User ID, and
Position are still ignored -- easy to wire in later if a need shows up.

PREFERRED PATH: read the source .xlsx directly with pandas if it's synced
locally via OneDrive (huge win over chunked Graph-API/chat pulls -- reads
the whole workbook in one shot, no row-count limits, no manual transcription).
Set SRC_XLSX to the local synced path. Falls back to raw_ulearn_export.csv
(a manually-assembled CSV) if the xlsx isn't found or pandas isn't installed.
"""
import csv
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SRC_XLSX = Path(r"C:\Users\S0G0K3S\OneDrive - Walmart Inc\Desktop\8.25 ulearn.xlsx")
SRC_XLSX_SHEET = "Ulearns"
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


def load_rows_from_xlsx() -> list[dict]:
    """Read the source workbook directly with pandas. Returns rows in the
    same dict-of-strings shape as csv.DictReader would, so downstream code
    (get/dedup/write) doesn't care which path was used."""
    import pandas as pd

    df = pd.read_excel(SRC_XLSX, sheet_name=SRC_XLSX_SHEET, dtype=object)
    df = df.rename(columns=lambda c: c.strip())
    rows = []
    for record in df.to_dict(orient="records"):
        row = {}
        for k, v in record.items():
            if v is None or (isinstance(v, float) and str(v) == "nan"):
                row[k] = ""
            elif isinstance(v, datetime):
                row[k] = v.strftime("%m/%d/%Y")
            else:
                row[k] = str(v).strip()
        rows.append(row)
    return rows


def load_rows_from_csv() -> list[dict]:
    with SRC.open(newline="", encoding="utf-8") as f_in:
        return list(csv.DictReader(f_in))


def main():
    if SRC_XLSX.exists():
        try:
            rows = load_rows_from_xlsx()
            print(f"Read {len(rows)} rows directly from {SRC_XLSX.name} (sheet '{SRC_XLSX_SHEET}')")
        except ImportError:
            print("pandas not installed -- falling back to raw_ulearn_export.csv")
            rows = load_rows_from_csv()
    else:
        print(f"{SRC_XLSX.name} not found locally -- falling back to raw_ulearn_export.csv")
        rows = load_rows_from_csv()

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
        writer.writerow(["Associate Name", "Shift", "Ulearn", "Due Date", "Managers",
                          "Late", "DueSoon7", "DueSoon14", "DueSoon30", "DueSoon60"])
        for r in deduped:
            writer.writerow([
                get(r, "Associate"),
                get(r, "Job Description"),
                get(r, "Item Name"),
                serial_to_date(get(r, "Due Date")),
                get(r, "Manager"),
                get(r, "Late"),
                get(r, "Next 7 Days"),
                get(r, "Next 14 Days"),
                get(r, "Next 30 Days"),
                get(r, "Next 60 Days"),
            ])

    print(f"Wrote {DST} ({len(deduped)} rows, {dupe_count} exact-duplicate rows dropped)")


if __name__ == "__main__":
    main()
