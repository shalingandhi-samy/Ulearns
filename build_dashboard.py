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


def main():
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
            overdue = bool(due_dt and due_dt < TODAY)
            rows.append({
                "name": name,
                "shift_raw": shift_raw,
                "shift": shift_code,
                "course": course,
                "due": due_raw,
                "due_sort": due_dt.strftime("%Y-%m-%d") if due_dt else "9999-99-99",
                "manager": manager,
                "overdue": overdue,
            })

    total = len(rows)
    unique_assoc = len({r["name"] for r in rows})
    unique_managers = len({r["manager"] for r in rows if r["manager"] != "Unassigned"})
    overdue_count = sum(1 for r in rows if r["overdue"])
    shifts = sorted({r["shift"] for r in rows}, key=lambda s: (s == "N/A", s))
    managers = sorted({r["manager"] for r in rows})

    data_json = json.dumps(rows)
    shifts_json = json.dumps(shifts)
    managers_json = json.dumps(managers)

    html = HTML_TEMPLATE.format(
        data_json=data_json,
        shifts_json=shifts_json,
        managers_json=managers_json,
        total=total,
        unique_assoc=unique_assoc,
        unique_managers=unique_managers,
        overdue_count=overdue_count,
        today_str=TODAY.strftime("%B %d, %Y"),
    )
    OUT_PATH.write_text(html, encoding="utf-8")
    print(f"Wrote {OUT_PATH} ({total} rows, {unique_assoc} associates, {overdue_count} overdue)")


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ULearn Pending Trainings Dashboard</title>
<script src="https://cdn.tailwindcss.com"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<script src="https://unpkg.com/htmx.org@1.9.10"></script>
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

  <!-- Executive Insights (top) -->
  <section class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
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
    <div class="bg-white rounded-xl shadow p-4 border-l-4 border-red-600">
      <p class="text-xs text-gray-500 uppercase tracking-wide">Past Due</p>
      <p class="text-3xl font-bold text-red-600" id="cardOverdue">{overdue_count}</p>
      <p class="text-xs text-gray-400 mt-1">already overdue as of {today_str}</p>
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
      <div class="flex items-center gap-2 pb-2">
        <input id="overdueOnly" type="checkbox" class="w-4 h-4 accent-red-600">
        <label for="overdueOnly" class="text-sm text-gray-700">Past due only</label>
      </div>
      <button id="clearFilters" class="text-sm text-[#0053e2] font-semibold hover:underline pb-2">Clear filters</button>
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

const shiftFilter = document.getElementById("shiftFilter");
const searchBox = document.getElementById("searchBox");
const overdueOnly = document.getElementById("overdueOnly");
const tableBody = document.getElementById("tableBody");
const rowCount = document.getElementById("rowCount");

const managerFilterBtn = document.getElementById("managerFilterBtn");
const managerFilterPanel = document.getElementById("managerFilterPanel");
const managerFilterLabel = document.getElementById("managerFilterLabel");
const managerSearchBox = document.getElementById("managerSearchBox");
const managerCheckboxList = document.getElementById("managerCheckboxList");
const managerSelectAll = document.getElementById("managerSelectAll");
const managerSelectNone = document.getElementById("managerSelectNone");

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
  const od = overdueOnly.checked;
  let rows = RAW_DATA.filter(r => {{
    if (selectedManagers.size > 0 && !selectedManagers.has(r.manager)) return false;
    if (s && r.shift !== s) return false;
    if (od && !r.overdue) return false;
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

function renderTable() {{
  const rows = getFiltered();
  rowCount.textContent = rows.length;
  tableBody.innerHTML = rows.map(r => `
    <tr class="border-b border-gray-100 hover:bg-blue-50 ${{r.overdue ? 'bg-red-50' : ''}}">
      <td class="px-3 py-2">${{r.name}}</td>
      <td class="px-3 py-2"><span class="badge bg-blue-100 text-blue-800">${{r.shift}}</span></td>
      <td class="px-3 py-2 text-gray-500">${{r.shift_raw}}</td>
      <td class="px-3 py-2">${{r.course}}</td>
      <td class="px-3 py-2 ${{r.overdue ? 'text-red-600 font-semibold' : ''}}">${{r.due}}${{r.overdue ? ' ⚠️' : ''}}</td>
      <td class="px-3 py-2">${{r.manager}}</td>
    </tr>
  `).join("");
  renderCharts(rows);
  renderInsights(rows);
  renderCards(rows);
}}

function renderCards(rows) {{
  document.getElementById("cardTotal").textContent = rows.length;
  document.getElementById("cardAssoc").textContent = new Set(rows.map(r => r.name)).size;
  document.getElementById("cardMgrs").textContent = new Set(rows.filter(r => r.manager !== "Unassigned").map(r => r.manager)).size;
  document.getElementById("cardOverdue").textContent = rows.filter(r => r.overdue).length;
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
  const overdue = rows.filter(r => r.overdue).length;
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
    <li><strong>${{rows.length}}</strong> pending course assignments in current view, <strong>${{overdue}}</strong> already past due.</li>
    <li>Most common outstanding course: <strong>${{topCourse[0]}}</strong> (${{topCourse[1]}} assignments).</li>
    <li>Manager with the most pending items: <strong>${{topMgr[0]}}</strong> (${{topMgr[1]}} assignments).</li>
    <li>Shift with the most pending items: <strong>${{topShift[0]}}</strong> (${{topShift[1]}} assignments).</li>
  `;
}}

[shiftFilter, searchBox, overdueOnly].forEach(el => {{
  el.addEventListener("input", renderTable);
  el.addEventListener("change", renderTable);
}});

document.getElementById("clearFilters").addEventListener("click", () => {{
  shiftFilter.value = ""; searchBox.value = ""; overdueOnly.checked = false;
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

renderTable();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
