# ULearn Pending Trainings Dashboard 🎓

A flat, self-contained HTML dashboard for tracking associates with pending ULearn
compliance trainings — filterable by **Manager** and **Shift**.

## What it does

- Ingests a CSV export of pending ULearn assignments (Associate Name, Shift, Course,
  Due Date, Manager, Late flag, Due-in-7-days flag)
- Parses out the shift code (`S1`–`S7`) from the raw shift/role text
- Buckets each pending item into **Past Due / Due in 7 / 14 / 30 / 60 Days** using
  the source file's own status flag columns (trusted as authoritative, since that's
  what the source system itself considers due-soon vs. overdue)
- Renders a single static `ulearn_dashboard.html` file with:
  - Executive summary cards (Total Pending, Associates Affected, Managers Involved)
    plus a 5-card status-bucket row (Past Due / 7 / 14 / 30 / 60 Days)
  - Filters: Manager, Shift, free-text search, Status dropdown (All / Past Due /
    Due in 7 / 14 / 30 / 60 Days)
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
WIN, User ID, Job Description, Item Name, Due Date, Late, Next 7 Days,
Next 14 Days, Next 30 Days, Next 60 Days, Manager, Position`)

The source workbook has 13 columns, flagging status explicitly via X marks in
Late / Next 7 Days / Next 14 Days / Next 30 Days / Next 60 Days. All five are
used now (the dashboard buckets into all 5 statuses). WIN, User ID, and
Position are still ignored for the CSV output, but WIN is used internally as a
sanity-check identity anchor (see "Duplicate rows" below).

**Preferred: read the workbook directly.** If the source file is synced locally
via OneDrive (check the user's OneDrive folder -- a recursive search for
`*ulearn*.xlsx` finds it fast), point `SRC_XLSX` in `convert_export.py` at that
local path and just run:

```bash
uv venv --python 3.11
uv pip install --python .venv\Scripts\python.exe --index-url https://pypi.ci.artifacts.walmart.com/artifactory/api/pypi/external-pypi/simple --allow-insecure-host pypi.ci.artifacts.walmart.com pandas openpyxl
.venv\Scripts\python.exe convert_export.py
.venv\Scripts\python.exe build_dashboard.py
```

pandas reads all ~1,800 rows in one shot, in a couple of seconds. **Do not**
fetch this data by asking a chat-based Graph/msgraph agent to paste rows into
chat -- that path is bottlenecked by a ~10,000-character tool-output truncation
regardless of chunk size, so it requires dozens of small, error-prone manual
chunks (missed/duplicated columns, serial-vs-string date drift, chunk-boundary
overlap). If the workbook is open in Excel you'll get a PermissionError --
close it first.

**Fallback (no local file access):** pull the sheet data manually into
`raw_ulearn_export.csv` (same 10 columns, Due Date as either an Excel serial
number or M/D/YYYY string -- both are handled) and run `python
convert_export.py`; it'll use the CSV automatically if the xlsx path isn't found.

### Duplicate rows

The raw export routinely contains the *same* real assignment (same WIN, same
course, same due date, same manager) listed multiple times -- confirmed via two
independent dedup keys (name-based and WIN-based) landing on the identical
unique-row count. `convert_export.py` drops exact repeats on
`(Associate, Job Description, Item Name, Due Date, Manager)`. This is *not* a
name-truncation collision (different real people sharing a display name) --
it's the source data itself repeating the same requirement.

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
