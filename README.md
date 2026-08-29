# ULearn Pending Trainings Dashboard 🎓

A flat, self-contained HTML dashboard for tracking associates with pending ULearn
compliance trainings — filterable by **Manager** and **Shift**.

## What it does

- Ingests a CSV export of pending ULearn assignments (Associate Name, Shift, Course,
  Due Date, Manager)
- Parses out the shift code (`S1`–`S7`) from the raw shift/role text
- Flags items that are already past due
- Renders a single static `ulearn_dashboard.html` file with:
  - Executive summary cards (Total Pending, Associates Affected, Managers Involved, Past Due)
  - Filters: Manager, Shift, free-text search, "Past due only" toggle
  - Bar charts: pending items by shift, top 10 managers by pending count
  - Sortable, scrollable detail table
  - Executive insights blurb that recalculates live as you filter

No backend required — it's pure HTML/JS (Tailwind CDN + Chart.js CDN), so you can just
open it in a browser or host it anywhere static files are served (e.g. Puppy Pages).

## Usage

### From a raw ULearn Excel export (e.g. `8.25 ulearn.xlsx`, columns: `Associate,
Job Description, Item Name, Due Date, Manager`)

1. Pull the sheet data into `raw_ulearn_export.csv` (same 5 raw columns, Due Date
   as the Excel serial number).
2. Convert it into the dashboard's format:

   ```bash
   python convert_export.py
   ```

   This maps columns to `Associate Name, Shift, Ulearn, Due Date, Managers` and
   converts Excel serial dates to `MM/DD/YYYY`.
3. Regenerate the dashboard: `python build_dashboard.py`.

### From an already-formatted CSV

1. Drop your latest export into `ulearn_data.csv` (5-column format: `Associate Name,
   Shift, Ulearn, Due Date, Managers`).
2. Regenerate the dashboard:

   ```bash
   python build_dashboard.py
   ```

3. Open `ulearn_dashboard.html` in a browser (or double-click it).

## Data notes

⚠️ **This CSV contains real associate and manager names.** Keep this repo **private**
and don't share the raw CSV outside of your team. The generated dashboard HTML also
embeds the raw data as inline JSON — treat it with the same care as the CSV.

## Files

| File | Purpose |
|---|---|
| `build_dashboard.py` | Parses `ulearn_data.csv` and generates `ulearn_dashboard.html` |
| `ulearn_data.csv` | Source data export |
| `ulearn_dashboard.html` | Generated static dashboard (open this in a browser) |

---
Built with 🐶 [Code Puppy](https://puppy.walmart.com)
