"""
Build a flat HTML+Tailwind+Chart.js dashboard from the ULearn CSV data.
Run: python build_dashboard.py
"""
import csv
import json
import re
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "ulearn_data.csv"
ONCLOCK_PATH = BASE_DIR / "flex_onclock.csv"
OUT_PATH = BASE_DIR / "ulearn_dashboard.html"

TODAY = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
SHIFT_RE = re.compile(r"_S(\d)\s*$")


def extract_shift(shift_field: str) -> str:
    m = SHIFT_RE.search(shift_field.strip())
    if m:
        return f"S{m.group(1)}"
    return "N/A"


def parse_date(s: str):
    s = s.strip()
    if not s:
        return None
    try:
        return datetime.strptime(s, "%m/%d/%Y")
    except ValueError:
        return None


def norm_name(s: str) -> str:
    # Normalize for matching: uppercase, strip anything that isn't a
    # letter/digit/space (hyphens, apostrophes, etc). Handles cases like
    # 'ROSE-BERLANDE DES' vs 'ROSEBERLANDE DESINOR' referring to the same person.
    return re.sub(r"[^A-Z0-9 ]", "", s.upper()).strip()


def name_candidates(full_name: str):
    normalized = norm_name(full_name)
    words = normalized.split()
    out = {normalized}
    for k in range(1, len(words)):
        given = " ".join(words[:k])
        out.add(f"{given} {words[k][:3]}")
    return out


def load_onclock_roster(path: Path):
    """Loads an optional Drax on-clock snapshot (Associate, WIN, Status, Shift,
    PulledAt columns). Returns (lookup_dict, pulled_at_str) where lookup_dict
    maps every truncated-name candidate -> roster row. Missing file = empty
    roster (Flex tab will just show all S7 associates with a warning banner)."""
    lookup = {}
    pulled_at = None
    if not path.exists():
        return lookup, pulled_at
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            full_name = row["Associate"].strip()
            if not full_name:
                continue
            pulled_at = row.get("PulledAt", "").strip() or pulled_at
            for cand in name_candidates(full_name):
                lookup[cand] = row
    return lookup, pulled_at


def main():
    onclock_lookup, onclock_pulled_at = load_onclock_roster(ONCLOCK_PATH)

    rows = []
    with CSV_PATH.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            name = r["Associate Name"].strip()
            shift_raw = r["Shift"].strip()
            course = r["Ulearn"].strip()
            due_raw = r["Due Date"].strip()
            manager = r["Managers"].strip() or "Unassigned"
            if not name:
                continue
            due_dt = parse_date(due_raw)
            shift_code = extract_shift(shift_raw)
            # Source tags status explicitly via "Late" / "Next 7/14/30/60 Days"
            # flag columns (marked with an "X") instead of leaving it to us to
            # compute purely from the due date. Priority order matches urgency:
            # a row overdue AND coincidentally flagged "Next 30 Days" (shouldn't
            # happen, but be defensive) is still "overdue" first and foremost.
            if "Late" in r:
                status = ""
                for flag_col, label in [
                    ("Late", "overdue"),
                    ("DueSoon7", "due_7"),
                    ("DueSoon14", "due_14"),
                    ("DueSoon30", "due_30"),
                    ("DueSoon60", "due_60"),
                ]:
                    if r.get(flag_col, "").strip().upper() == "X":
                        status = label
                        break
                overdue = status == "overdue"
                due_soon = status == "due_7"
            else:
                # Older-style CSV without flag columns at all -- fall back to a
                # computed date comparison so this still degrades gracefully.
                overdue = bool(due_dt and due_dt < TODAY)
                due_soon = False
                status = "overdue" if overdue else ""
            onclock_row = onclock_lookup.get(norm_name(name))
            rows.append({
                "name": name,
                "shift_raw": shift_raw,
                "shift": shift_code,
                "course": course,
                "due": due_raw,
                "due_sort": due_dt.strftime("%Y-%m-%d") if due_dt else "9999-99-99",
                "manager": manager,
                "overdue": overdue,
                "due_soon": due_soon,
                "status": status,
                "on_clock": onclock_row is not None,
            })

    total = len(rows)
    unique_assoc = len({r["name"] for r in rows})
    unique_managers = len({r["manager"] for r in rows if r["manager"] != "Unassigned"})
    overdue_count = sum(1 for r in rows if r["overdue"])
    due_soon_count = sum(1 for r in rows if r["due_soon"])
    due_14_count = sum(1 for r in rows if r["status"] == "due_14")
    due_30_count = sum(1 for r in rows if r["status"] == "due_30")
    due_60_count = sum(1 for r in rows if r["status"] == "due_60")
    shifts = sorted({r["shift"] for r in rows}, key=lambda s: (s == "N/A", s))
    managers = sorted({r["manager"] for r in rows})

    data_json = json.dumps(rows)
    shifts_json = json.dumps(shifts)
    managers_json = json.dumps(managers)
    onclock_count = len(onclock_lookup)
    onclock_note = (
        f"Live on-clock snapshot pulled from Drax Starting Lineup as of {onclock_pulled_at}."
        if onclock_pulled_at else
        " No Drax on-clock snapshot loaded (missing flex_onclock.csv) — showing ALL S7 flex "
        "associates with pending trainings, regardless of clock status."
    )

    html = HTML_TEMPLATE.format(
        data_json=data_json,
        shifts_json=shifts_json,
        managers_json=managers_json,
        total=total,
        unique_assoc=unique_assoc,
        unique_managers=unique_managers,
        overdue_count=overdue_count,
        due_soon_count=due_soon_count,
        due_14_count=due_14_count,
        due_30_count=due_30_count,
        due_60_count=due_60_count,
        today_str=TODAY.strftime("%B %d, %Y"),
        onclock_note=onclock_note,
    )
    OUT_PATH.write_text(html, encoding="utf-8")
    print(f"Wrote {OUT_PATH} ({total} rows, {unique_assoc} associates, {overdue_count} overdue, "
          f"{due_soon_count} due in 7 days, {due_14_count} due in 14 days, {due_30_count} due in 30 days, "
          f"{due_60_count} due in 60 days, {onclock_count} on-clock flex names loaded)")


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ULearn Pending Trainings Dashboard</title>
<script src="https://cdn.tailwindcss.com"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<script src="https://unpkg.com/htmx.org@1.9.10"></script>
<script src="https://cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.full.min.js"></script>
<style>
  :root {{ --wm-blue: #0053e2; --wm-spark: #ffc220; }}
  body {{ font-family: -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; }}
  .badge {{ display:inline-block; padding:2px 10px; border-radius:999px; font-size:0.72rem; font-weight:600; }}
  th.sortable {{ cursor:pointer; user-select:none; }}
  th.sortable:hover {{ background:#e6efff; }}
</style>
</head>
<body class="bg-gray-50 text-gray-900">

<header class="bg-[#0053e2] text-white px-6 py-5 shadow-md">
  <div class="max-w-7xl mx-auto flex items-center justify-between flex-wrap gap-3">
    <div>
      <h1 class="text-2xl font-bold">🎓 ULearn Pending Trainings Dashboard</h1>
      <p class="text-sm text-blue-100">Data as of {today_str}</p>
    </div>
    <span class="badge bg-[#ffc220] text-[#995213]">{total} pending course assignments</span>
  </div>
</header>

<main class="max-w-7xl mx-auto px-6 py-6 space-y-6">

  <!-- Tabs -->
  <section class="flex gap-2 border-b border-gray-200">
    <button type="button" class="tab-btn px-4 py-2 text-sm font-semibold border-b-2 border-[#0053e2] text-[#0053e2]" data-tab="all">All Associates</button>
    <button type="button" class="tab-btn px-4 py-2 text-sm font-semibold border-b-2 border-transparent text-gray-500 hover:text-gray-700" data-tab="flex">Flex Associates on Clock</button>
  </section>
  <div id="onclockNote" class="hidden text-xs text-amber-800 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">{onclock_note}</div>

  <!-- Executive Insights (top) -->
  <section class="grid grid-cols-1 sm:grid-cols-3 gap-4">
    <div class="bg-white rounded-xl shadow p-4 border-l-4 border-[#0053e2]">
      <p class="text-xs text-gray-500 uppercase tracking-wide">Total Pending</p>
      <p class="text-3xl font-bold text-[#0053e2]" id="cardTotal">{total}</p>
      <p class="text-xs text-gray-400 mt-1">course assignments in current view</p>
    </div>
    <div class="bg-white rounded-xl shadow p-4 border-l-4 border-green-600">
      <p class="text-xs text-gray-500 uppercase tracking-wide">Associates Affected</p>
      <p class="text-3xl font-bold text-green-700" id="cardAssoc">{unique_assoc}</p>
      <p class="text-xs text-gray-400 mt-1">unique associates in current view</p>
    </div>
    <div class="bg-white rounded-xl shadow p-4 border-l-4 border-purple-600">
      <p class="text-xs text-gray-500 uppercase tracking-wide">Managers Involved</p>
      <p class="text-3xl font-bold text-purple-700" id="cardMgrs">{unique_managers}</p>
      <p class="text-xs text-gray-400 mt-1">distinct managers in current view</p>
    </div>
  </section>

  <!-- Status buckets -->
  <section class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
    <div class="bg-white rounded-xl shadow p-4 border-l-4 border-red-600">
      <p class="text-xs text-gray-500 uppercase tracking-wide">Past Due</p>
      <p class="text-2xl font-bold text-red-600" id="cardStatusOverdue">{overdue_count}</p>
    </div>
    <div class="bg-white rounded-xl shadow p-4 border-l-4 border-orange-500">
      <p class="text-xs text-gray-500 uppercase tracking-wide">Due in 7 Days</p>
      <p class="text-2xl font-bold text-orange-600" id="cardDueSoon">{due_soon_count}</p>
    </div>
    <div class="bg-white rounded-xl shadow p-4 border-l-4 border-amber-400">
      <p class="text-xs text-gray-500 uppercase tracking-wide">Due in 14 Days</p>
      <p class="text-2xl font-bold text-amber-600" id="cardDue14">{due_14_count}</p>
    </div>
    <div class="bg-white rounded-xl shadow p-4 border-l-4 border-cyan-500">
      <p class="text-xs text-gray-500 uppercase tracking-wide">Due in 30 Days</p>
      <p class="text-2xl font-bold text-cyan-600" id="cardDue30">{due_30_count}</p>
    </div>
    <div class="bg-white rounded-xl shadow p-4 border-l-4 border-slate-400">
      <p class="text-xs text-gray-500 uppercase tracking-wide">Due in 60 Days</p>
      <p class="text-2xl font-bold text-slate-600" id="cardDue60">{due_60_count}</p>
    </div>
  </section>

  <!-- Filters -->
  <section class="bg-white rounded-xl shadow p-4">
    <div class="flex flex-wrap gap-4 items-end">
      <div class="flex-1 min-w-[220px] relative" id="managerFilterWrap">
        <label class="block text-xs font-semibold text-gray-500 mb-1">Manager</label>
        <button type="button" id="managerFilterBtn" class="w-full text-left border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-[#0053e2]">
          <span id="managerFilterLabel">All Managers</span>
        </button>
        <div id="managerFilterPanel" class="hidden absolute z-20 mt-1 w-full bg-white border border-gray-200 rounded-lg shadow-lg max-h-64 overflow-y-auto p-2">
          <input id="managerSearchBox" type="text" placeholder="Search managers..." class="w-full border border-gray-200 rounded px-2 py-1 text-xs mb-2 focus:outline-none focus:ring-1 focus:ring-[#0053e2]">
          <div class="flex justify-between text-xs mb-2">
            <button type="button" id="managerSelectAll" class="text-[#0053e2] font-semibold hover:underline">Select all</button>
            <button type="button" id="managerSelectNone" class="text-gray-500 font-semibold hover:underline">Clear</button>
          </div>
          <div id="managerCheckboxList" class="space-y-1"></div>
        </div>
      </div>
      <div class="flex-1 min-w-[150px]">
        <label for="shiftFilter" class="block text-xs font-semibold text-gray-500 mb-1">Shift</label>
        <select id="shiftFilter" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#0053e2]">
          <option value="">All Shifts</option>
        </select>
      </div>
      <div class="flex-1 min-w-[220px]">
        <label for="searchBox" class="block text-xs font-semibold text-gray-500 mb-1">Search (name or course)</label>
        <input id="searchBox" type="text" placeholder="Type to search..." class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#0053e2]">
      </div>
      <div class="flex-1 min-w-[160px]">
        <label for="statusFilter" class="block text-xs font-semibold text-gray-500 mb-1">Status</label>
        <select id="statusFilter" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#0053e2]">
          <option value="">All Statuses</option>
          <option value="overdue">Past Due</option>
          <option value="due_7">Due in 7 Days</option>
          <option value="due_14">Due in 14 Days</option>
          <option value="due_30">Due in 30 Days</option>
          <option value="due_60">Due in 60 Days</option>
        </select>
      </div>
      <button id="clearFilters" class="text-sm text-[#0053e2] font-semibold hover:underline pb-2">Clear filters</button>
      <button id="downloadExcel" class="flex items-center gap-1 text-sm bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg px-3 py-2">
        Download Excel
      </button>
    </div>
  </section>

  <!-- Charts -->
  <section class="grid grid-cols-1 lg:grid-cols-2 gap-4">
    <div class="bg-white rounded-xl shadow p-4">
      <h2 class="font-semibold text-sm text-gray-700 mb-2">Pending Items by Shift</h2>
      <div class="relative h-64"><canvas id="shiftChart"></canvas></div>
    </div>
    <div class="bg-white rounded-xl shadow p-4">
      <h2 class="font-semibold text-sm text-gray-700 mb-2">Top 10 Managers by Pending Count</h2>
      <div class="relative h-64"><canvas id="managerChart"></canvas></div>
    </div>
  </section>

  <!-- Table -->
  <section class="bg-white rounded-xl shadow p-4">
    <div class="flex items-center justify-between mb-3">
      <h2 class="font-semibold text-gray-700">Detail (<span id="rowCount">0</span> rows)</h2>
    </div>
    <div class="overflow-x-auto max-h-[600px] overflow-y-auto border border-gray-100 rounded-lg">
      <table class="min-w-full text-sm">
        <thead class="bg-gray-100 sticky top-0 z-10">
          <tr>
            <th class="sortable px-3 py-2 text-left" data-key="name">Associate Name</th>
            <th class="sortable px-3 py-2 text-left" data-key="shift">Shift</th>
            <th class="px-3 py-2 text-left">Role / Shift Detail</th>
            <th class="sortable px-3 py-2 text-left" data-key="course">Pending ULearn</th>
            <th class="sortable px-3 py-2 text-left" data-key="due_sort">Due Date</th>
            <th class="px-3 py-2 text-left">Status</th>
            <th class="sortable px-3 py-2 text-left" data-key="manager">Manager</th>
          </tr>
        </thead>
        <tbody id="tableBody"></tbody>
      </table>
    </div>
  </section>

  <!-- Executive Insights (bottom) -->
  <section class="bg-white rounded-xl shadow p-5 border-t-4 border-[#ffc220]">
    <h2 class="font-bold text-gray-800 mb-2">📌 Executive Insights</h2>
    <ul class="list-disc list-inside text-sm text-gray-700 space-y-1" id="insightsList">
      <li>Loading insights...</li>
    </ul>
  </section>

</main>

<footer class="text-center text-xs text-gray-400 py-6">
  Built with 🐶 SAMY — Code Puppy | Source: 8.25 ulearn.xlsx
</footer>

<script>
const RAW_DATA = {data_json};
const SHIFTS = {shifts_json};
const MANAGERS = {managers_json};

let sortKey = "due_sort";
let sortDir = 1;
let selectedManagers = new Set();
let activeTab = "all";

const shiftFilter = document.getElementById("shiftFilter");
const searchBox = document.getElementById("searchBox");
const statusFilter = document.getElementById("statusFilter");
const tableBody = document.getElementById("tableBody");
const rowCount = document.getElementById("rowCount");
const tabButtons = document.querySelectorAll(".tab-btn");

const managerFilterBtn = document.getElementById("managerFilterBtn");
const managerFilterPanel = document.getElementById("managerFilterPanel");
const managerFilterLabel = document.getElementById("managerFilterLabel");
const managerSearchBox = document.getElementById("managerSearchBox");
const managerCheckboxList = document.getElementById("managerCheckboxList");
const managerSelectAll = document.getElementById("managerSelectAll");
const managerSelectNone = document.getElementById("managerSelectNone");
const onclockNote = document.getElementById("onclockNote");

tabButtons.forEach(btn => {{
  btn.addEventListener("click", () => {{
    activeTab = btn.dataset.tab;
    tabButtons.forEach(b => {{
      const active = b === btn;
      b.classList.toggle("border-[#0053e2]", active);
      b.classList.toggle("text-[#0053e2]", active);
      b.classList.toggle("border-transparent", !active);
      b.classList.toggle("text-gray-500", !active);
    }});
    // Flex tab is scoped to associates who are S7 (flex role) AND currently
    // on-clock per the Drax snapshot -- the shift dropdown would just be a
    // redundant/confusing no-op there, so reset + disable it.
    if (activeTab === "flex") {{
      shiftFilter.value = "";
      shiftFilter.disabled = true;
      onclockNote.classList.remove("hidden");
    }} else {{
      shiftFilter.disabled = false;
      onclockNote.classList.add("hidden");
    }}
    renderTable();
  }});
}});

function populateSelect(sel, values) {{
  values.forEach(v => {{
    const opt = document.createElement("option");
    opt.value = v; opt.textContent = v;
    sel.appendChild(opt);
  }});
}}
populateSelect(shiftFilter, SHIFTS);

function updateManagerLabel() {{
  const n = selectedManagers.size;
  if (n === 0) {{
    managerFilterLabel.textContent = "All Managers";
  }} else if (n === 1) {{
    managerFilterLabel.textContent = [...selectedManagers][0];
  }} else {{
    managerFilterLabel.textContent = n + " managers selected";
  }}
}}

function renderManagerCheckboxes() {{
  const q = managerSearchBox.value.trim().toLowerCase();
  const visible = MANAGERS.filter(m => m.toLowerCase().includes(q));
  managerCheckboxList.innerHTML = "";
  if (visible.length === 0) {{
    managerCheckboxList.innerHTML = '<p class="text-xs text-gray-400 px-1">No managers match.</p>';
    return;
  }}
  visible.forEach(m => {{
    const label = document.createElement("label");
    label.className = "flex items-center gap-2 text-sm px-1 py-0.5 rounded hover:bg-blue-50 cursor-pointer";
    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.className = "managerCheckbox w-4 h-4 accent-[#0053e2]";
    cb.value = m;
    cb.checked = selectedManagers.has(m);
    cb.addEventListener("change", () => {{
      if (cb.checked) {{ selectedManagers.add(m); }} else {{ selectedManagers.delete(m); }}
      updateManagerLabel();
      renderTable();
    }});
    const span = document.createElement("span");
    span.textContent = m;
    label.appendChild(cb);
    label.appendChild(span);
    managerCheckboxList.appendChild(label);
  }});
}}
renderManagerCheckboxes();

managerFilterBtn.addEventListener("click", () => {{
  managerFilterPanel.classList.toggle("hidden");
}});
document.addEventListener("click", (e) => {{
  if (!document.getElementById("managerFilterWrap").contains(e.target)) {{
    managerFilterPanel.classList.add("hidden");
  }}
}});
managerSearchBox.addEventListener("input", renderManagerCheckboxes);
managerSelectAll.addEventListener("click", () => {{
  MANAGERS.forEach(m => selectedManagers.add(m));
  updateManagerLabel();
  renderManagerCheckboxes();
  renderTable();
}});
managerSelectNone.addEventListener("click", () => {{
  selectedManagers.clear();
  updateManagerLabel();
  renderManagerCheckboxes();
  renderTable();
}});

function getFiltered() {{
  const s = shiftFilter.value;
  const q = searchBox.value.trim().toLowerCase();
  const st = statusFilter.value;
  let rows = RAW_DATA.filter(r => {{
    if (activeTab === "flex" && (r.shift !== "S7" || !r.on_clock)) return false;
    if (selectedManagers.size > 0 && !selectedManagers.has(r.manager)) return false;
    if (s && r.shift !== s) return false;
    if (st && r.status !== st) return false;
    if (q && !(r.name.toLowerCase().includes(q) || r.course.toLowerCase().includes(q))) return false;
    return true;
  }});
  rows.sort((a, b) => {{
    const av = a[sortKey], bv = b[sortKey];
    if (av < bv) return -1 * sortDir;
    if (av > bv) return 1 * sortDir;
    return 0;
  }});
  return rows;
}}

const STATUS_META = {{
  overdue: {{ label: "Past Due", badge: "bg-red-100 text-red-700", row: "bg-red-50" }},
  due_7: {{ label: "Due in 7 Days", badge: "bg-orange-100 text-orange-800", row: "bg-orange-50" }},
  due_14: {{ label: "Due in 14 Days", badge: "bg-amber-100 text-amber-800", row: "" }},
  due_30: {{ label: "Due in 30 Days", badge: "bg-cyan-100 text-cyan-800", row: "" }},
  due_60: {{ label: "Due in 60 Days", badge: "bg-slate-100 text-slate-700", row: "" }},
}};

function renderTable() {{
  const rows = getFiltered();
  rowCount.textContent = rows.length;
  tableBody.innerHTML = rows.map(r => {{
    const meta = STATUS_META[r.status];
    const rowBg = meta ? meta.row : "";
    const statusBadge = meta ? `<span class="badge ${{meta.badge}}">${{meta.label}}</span>` : "";
    return `
    <tr class="border-b border-gray-100 hover:bg-blue-50 ${{rowBg}}">
      <td class="px-3 py-2">${{r.name}}</td>
      <td class="px-3 py-2"><span class="badge bg-blue-100 text-blue-800">${{r.shift}}</span></td>
      <td class="px-3 py-2 text-gray-500">${{r.shift_raw}}</td>
      <td class="px-3 py-2">${{r.course}}</td>
      <td class="px-3 py-2 ${{r.overdue ? 'text-red-600 font-semibold' : ''}}">${{r.due}}</td>
      <td class="px-3 py-2">${{statusBadge}}</td>
      <td class="px-3 py-2">${{r.manager}}</td>
    </tr>
  `;
  }}).join("");
  renderCharts(rows);
  renderInsights(rows);
  renderCards(rows);
}}

function renderCards(rows) {{
  document.getElementById("cardTotal").textContent = rows.length;
  document.getElementById("cardAssoc").textContent = new Set(rows.map(r => r.name)).size;
  document.getElementById("cardMgrs").textContent = new Set(rows.filter(r => r.manager !== "Unassigned").map(r => r.manager)).size;
  document.getElementById("cardStatusOverdue").textContent = rows.filter(r => r.status === "overdue").length;
  document.getElementById("cardDueSoon").textContent = rows.filter(r => r.status === "due_7").length;
  document.getElementById("cardDue14").textContent = rows.filter(r => r.status === "due_14").length;
  document.getElementById("cardDue30").textContent = rows.filter(r => r.status === "due_30").length;
  document.getElementById("cardDue60").textContent = rows.filter(r => r.status === "due_60").length;
}}

let shiftChart, managerChart;
function renderCharts(rows) {{
  const shiftCounts = {{}};
  rows.forEach(r => shiftCounts[r.shift] = (shiftCounts[r.shift] || 0) + 1);
  const shiftLabels = Object.keys(shiftCounts).sort();
  const shiftValues = shiftLabels.map(l => shiftCounts[l]);

  const mgrCounts = {{}};
  rows.forEach(r => mgrCounts[r.manager] = (mgrCounts[r.manager] || 0) + 1);
  const topMgrs = Object.entries(mgrCounts).sort((a,b) => b[1]-a[1]).slice(0, 10);

  if (shiftChart) shiftChart.destroy();
  shiftChart = new Chart(document.getElementById("shiftChart"), {{
    type: "bar",
    data: {{ labels: shiftLabels, datasets: [{{ label: "Pending Items", data: shiftValues, backgroundColor: "#0053e2" }}] }},
    options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ display: false }} }} }}
  }});

  if (managerChart) managerChart.destroy();
  managerChart = new Chart(document.getElementById("managerChart"), {{
    type: "bar",
    data: {{
      labels: topMgrs.map(m => m[0]),
      datasets: [{{ label: "Pending Items", data: topMgrs.map(m => m[1]), backgroundColor: "#ffc220" }}]
    }},
    options: {{ responsive: true, maintainAspectRatio: false, indexAxis: "y", plugins: {{ legend: {{ display: false }} }} }}
  }});
}}

function renderInsights(rows) {{
  const list = document.getElementById("insightsList");
  if (rows.length === 0) {{
    list.innerHTML = "<li>No records match the current filters.</li>";
    return;
  }}
  const overdue = rows.filter(r => r.status === "overdue").length;
  const due7 = rows.filter(r => r.status === "due_7").length;
  const due14 = rows.filter(r => r.status === "due_14").length;
  const due30 = rows.filter(r => r.status === "due_30").length;
  const due60 = rows.filter(r => r.status === "due_60").length;
  const byCourse = {{}};
  rows.forEach(r => byCourse[r.course] = (byCourse[r.course] || 0) + 1);
  const topCourse = Object.entries(byCourse).sort((a,b) => b[1]-a[1])[0];
  const byMgr = {{}};
  rows.forEach(r => byMgr[r.manager] = (byMgr[r.manager] || 0) + 1);
  const topMgr = Object.entries(byMgr).sort((a,b) => b[1]-a[1])[0];
  const bySh = {{}};
  rows.forEach(r => bySh[r.shift] = (bySh[r.shift] || 0) + 1);
  const topShift = Object.entries(bySh).sort((a,b) => b[1]-a[1])[0];

  list.innerHTML = `
    <li><strong>${{rows.length}}</strong> pending course assignments in current view: <strong>${{overdue}}</strong> past due, <strong>${{due7}}</strong> due in 7 days, <strong>${{due14}}</strong> due in 14 days, <strong>${{due30}}</strong> due in 30 days, <strong>${{due60}}</strong> due in 60 days.</li>
    <li>Most common outstanding course: <strong>${{topCourse[0]}}</strong> (${{topCourse[1]}} assignments).</li>
    <li>Manager with the most pending items: <strong>${{topMgr[0]}}</strong> (${{topMgr[1]}} assignments).</li>
    <li>Shift with the most pending items: <strong>${{topShift[0]}}</strong> (${{topShift[1]}} assignments).</li>
  `;
}}

[shiftFilter, searchBox, statusFilter].forEach(el => {{
  el.addEventListener("input", renderTable);
  el.addEventListener("change", renderTable);
}});

document.getElementById("clearFilters").addEventListener("click", () => {{
  shiftFilter.value = ""; searchBox.value = ""; statusFilter.value = "";
  selectedManagers.clear(); updateManagerLabel(); renderManagerCheckboxes();
  requestAnimationFrame(() => requestAnimationFrame(renderTable));
}});

document.querySelectorAll("th.sortable").forEach(th => {{
  th.addEventListener("click", () => {{
    const key = th.dataset.key;
    if (sortKey === key) {{ sortDir *= -1; }} else {{ sortKey = key; sortDir = 1; }}
    renderTable();
  }});
}});

function downloadExcel() {{
  const rows = getFiltered();
  const exportRows = rows.map(r => ({{
    "Associate Name": r.name,
    "Shift": r.shift,
    "Role / Shift Detail": r.shift_raw,
    "Pending ULearn": r.course,
    "Due Date": r.due,
    "Status": STATUS_META[r.status] ? STATUS_META[r.status].label : "",
    "Manager": r.manager,
  }}));
  const sheetName = activeTab === "flex" ? "Flex On Clock" : "All Associates";
  const ws = XLSX.utils.json_to_sheet(exportRows);
  ws["!cols"] = [
    {{ wch: 22 }}, {{ wch: 8 }}, {{ wch: 30 }}, {{ wch: 40 }}, {{ wch: 12 }}, {{ wch: 10 }}, {{ wch: 22 }},
  ];
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, sheetName);
  const stamp = new Date().toISOString().slice(0, 10);
  XLSX.writeFile(wb, `ulearn_pending_trainings_${{stamp}}.xlsx`);
}}

document.getElementById("downloadExcel").addEventListener("click", downloadExcel);

renderTable();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
