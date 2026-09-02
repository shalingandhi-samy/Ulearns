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
  - **Download Excel** button that exports exactly what's currently filtered/visible
    (including the active tab -- All Associates or Flex on Clock) to a `.xlsx` file,
    named `ulearn_pending_trainings_<date>.xlsx`
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

## Flex Associates on Clock tab

The dashboard has a second tab, Flex Associates on Clock, scoped to associates
who are both of the following: a Flex associate per the ULearn data (job
description ends in _S7), and currently clocked in per Drax Starting Lineup.
Note that Drax uses its own shift code for Flex, S6, which is a completely
different numbering scheme from ULearn's _S7 role suffix -- don't confuse the two.

Being Flex (_S7 in ULearn) does not mean someone is on the clock right now --
that has to be cross-checked against Drax separately, since on-clock status
changes throughout the day.

### Refreshing the on-clock snapshot

1. Get today's Drax Starting Lineup URL for the site/date/areas you care about,
   e.g. https://drax.walmart.com/startinglineup/?date=YYYY-MM-DD&area=...&shift=S6
2. Ask a browser-automation agent (qa-kitten) to load that URL and extract every
   row where shift equals S6 and status is In or In minus Late (name, WIN,
   status, shift).
3. Save the results into flex_onclock.csv with columns: Associate, WIN, Status,
   Shift, PulledAt (Associate = full untruncated name as shown on Drax; PulledAt
   = a human-readable pull date/label).
4. Re-run python build_dashboard.py. It matches Drax's full names against
   ULearn's truncated-name convention automatically and tags each pending item
   with whether that associate is currently on-clock.
5. If flex_onclock.csv is missing or stale, the Flex tab shows a warning banner
   and falls back to listing all _S7 associates regardless of clock status.

flex_onclock.csv is a point-in-time snapshot, not live -- re-pull it whenever you
need current-shift accuracy.

## Data notes

⚠️ **This CSV contains real associate and manager names.** Keep this repo **private**
and don't share the raw CSV outside of your team. The generated dashboard HTML also
embeds the raw data as inline JSON — treat it with the same care as the CSV.

## Files

| File | Purpose |
|---|---|
| `build_dashboard.py` | Parses `ulearn_data.csv` (+ optional `flex_onclock.csv`) and generates `ulearn_dashboard.html` |
| `ulearn_data.csv` | Source data export |
| `flex_onclock.csv` | Optional Drax on-clock snapshot for the Flex tab (Associate, WIN, Status, Shift, PulledAt) |
| `ulearn_dashboard.html` | Generated static dashboard (open this in a browser) |

---
Built with 🐶 [Code Puppy](https://puppy.walmart.com)
