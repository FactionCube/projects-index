#!/usr/bin/env python3
"""
build_index_v3_4_recent_ui.py — HTML index with:
- theme toggle, search, date filters
- per-section collapse memory
- Export CSV (with Extension + Recent columns)
- "Recently Added" badges
- Legend explaining "New", plus an in-page control to adjust RECENT_DAYS (persists)
"""

from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

# ---------- Configuration ----------
EXTENSIONS = {".pdf", ".md", ".txt", ".py", ".bat", ".ps1"}
EXCLUDES = {"projects_index_auto.md", "projects_index_auto_cleaned.md"}
DEFAULT_CATEGORY = "🗃️ Other"
RECENT_DAYS = 7  # Initial default; can be changed from the UI

CATEGORY_RULES: Dict[str, Tuple[str, ...]] = {
    "📘 Mathematics": (
        "tensor", "summation", "einstein", "directioncosines",
        "potentialvorticity", "geometricoperators",
        "differentialforms", "continuum", "indexnotation", "indicial"
    ),
    "🍳 Cooking Guides": (
        "blackberry", "muesli", "bircher", "pasty", "scone", "recipe"
    ),
    "🛠️ Technical Manuals": (
        "miele", "manual", "greaseweazle", "gw_", "imac", "vm",
        "snow leopard", "toolkit", "project-toolkit", "readme"
    ),
    "📱 Devices & Experiments": (
        "ipad", "apple pencil", "tilt", "pressure", "resilience", "screen"
    ),
    "📑 Notes & Essays": (
        "notes from chatgpt", "reasoning", "populate_ceres", "ellen von unwerth"
    ),
    "🧑‍⚕️ Health & Care": (
        "foot care", "corn softening", "routine", "treatment"
    ),
    "🔬 Physics & Simulations": (
        "quantum entanglement", "simulation", "bell", "theorem"
    ),
    "💻 Scripts & Code": (
        ".py", "python", "script",
        ".bat", "batch",
        ".ps1", "powershell",
        "install", "setup", "build"
    ),
}

# ---------- Helpers ----------
def gather_files(root: Path, recursive: bool) -> List[Path]:
    it = root.rglob("*") if recursive else root.glob("*")
    out = []
    for p in it:
        if p.is_file() and p.suffix.lower() in EXTENSIONS:
            if p.name.lower() in EXCLUDES:
                continue
            out.append(p)
    return out

def categorize(filename: str) -> str:
    name = filename.lower()
    for cat, keywords in CATEGORY_RULES.items():
        if any(k in name for k in keywords):
            return cat
    return DEFAULT_CATEGORY

def build_entries(root: Path, files: List[Path]) -> List[dict]:
    now = datetime.now()
    cutoff = now - timedelta(days=RECENT_DAYS)
    entries = []
    for p in files:
        try:
            stat = p.stat()
        except FileNotFoundError:
            continue
        mtime = datetime.fromtimestamp(stat.st_mtime)
        rel = p.relative_to(root) if str(p).startswith(str(root)) else p.name
        entries.append({
            "path": p,
            "rel": rel,
            "title": p.stem.replace("_", " "),
            "date": mtime.strftime("%Y-%m-%d"),
            "category": categorize(p.name + " " + str(rel)),
            "mtime": stat.st_mtime,
            "ext": p.suffix.lower(),
            "is_recent": mtime >= cutoff,
        })
    return entries

def group_and_sort(entries: List[dict]):
    buckets: Dict[str, List[dict]] = {}
    for e in entries:
        buckets.setdefault(e["category"], []).append(e)
    cat_order = list(CATEGORY_RULES.keys()) + [DEFAULT_CATEGORY]
    for c in list(buckets.keys()):
        if c not in cat_order:
            cat_order.append(c)
    for cat in buckets:
        buckets[cat].sort(key=lambda x: -x["mtime"])
    return [(c, buckets[c]) for c in cat_order if c in buckets]

# ---------- Renderers ----------
def render_markdown(root: Path, grouped) -> str:
    lines = [
        "# 📚 Projects Index (Auto‑Sorted)",
        "",
        f"_Scanned folder_: `{root}`",
        "",
        f"Files modified in the last **{RECENT_DAYS} days** are considered *recent*.",
        "",
        "---",
        "",
    ]
    for cat, items in grouped:
        lines.append(f"## {cat}")
        lines.append("")
        for e in items:
            rel = str(e["rel"]).replace("\\", "/")
            tag = "  *(New)*" if e.get("is_recent") else ""
            lines.append(f"- [{e['title']}](./{rel}) — *Date: {e['date']}*{tag}")
        lines.append("")
        lines.append("---")
        lines.append("")
    lines += [
        "### 🛠 How to use",
        "",
        "- Place your PDFs/MD/TXT in this folder (or subfolders if using `--recursive`).",
        "",
        "- Re‑run this script to refresh the index.",
        "",
        "- Edit `CATEGORY_RULES` and `RECENT_DAYS` in the script to tweak grouping and recency.",
        ""
    ]
    return "\n".join(lines)

def render_html(root: Path, grouped) -> str:
    from html import escape
    parts = []
    parts.append(f"""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Projects Index</title>
<style>
  :root {{
    --bg:#0b0d10; --fg:#e7ebee; --muted:#9aa7b0; --card:#12161a; --accent:#83c5be;
    --border:#1f252b; --link:#a8e0db; --badge:#22c55e;
  }}
  [data-theme="light"] {{
    --bg:#f7f8fa; --fg:#0d1117; --muted:#6b7280; --card:#ffffff; --accent:#0ea5a3;
    --border:#e5e7eb; --link:#0ea5a3; --badge:#16a34a;
  }}
  body {{ background:var(--bg); color:var(--fg); font-family:system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,Cantarell,Helvetica,Arial,sans-serif; margin:0; }}
  header {{ padding:24px 20px; border-bottom:1px solid var(--border); position:sticky; top:0; background:var(--bg); z-index:10; }}
  h1 {{ margin:0 0 8px 0; font-size:22px; }}
  .meta {{ color:var(--muted); font-size:13px; }}
  .container {{ max-width:980px; margin:0 auto; padding:20px; }}
  .controls {{ display:flex; flex-wrap:wrap; gap:10px; align-items:center; margin-top:12px; }}
  .btn {{ padding:8px 12px; background:transparent; color:var(--fg); border:1px solid var(--border); border-radius:10px; cursor:pointer; }}
  .btn:hover {{ border-color:color-mix(in oklab, var(--border), var(--fg) 25%); }}
  .search, .date, .num {{ padding:10px 12px; font-size:14px; border-radius:10px; border:1px solid var(--border); background:transparent; color:var(--fg); outline:none; }}
  .date {{ width: 150px; }}
  .num {{ width: 120px; }}
  .legend {{ color:var(--muted); font-size:12px; margin-left: 10px; }}
  section {{ margin:24px 0 36px; }}
  h2 {{ font-size:18px; color:var(--accent); margin:6px 0 12px; cursor:pointer; user-select:none; }}
  ul {{ list-style:none; padding:0; margin:0; display:grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap:10px; }}
  li {{ background:var(--card); border:1px solid var(--border); border-radius:12px; padding:12px 14px; }}
  a {{ color:var(--link); text-decoration:none; }}
  a:hover {{ text-decoration:underline; }}
  .date-stamp {{ color:var(--muted); font-size:12px; margin-top:6px; }}
  .hidden {{ display:none !important; }}
  .badge {{ display:inline-block; font-size:11px; padding:2px 6px; border-radius:999px; margin-left:8px; background:var(--badge); color:white; }}
  footer {{ color:var(--muted); font-size:12px; padding:24px 20px; border-top:1px solid var(--border); }}
</style>
</head>
<body>
<header class="container">
  <h1>Projects Index</h1>
  <div class="meta">Source: {escape(str(root))}</div>
  <div class="controls">
    <button id="theme" class="btn" title="Toggle light/dark theme">🌗 Theme</button>
    <input id="q" class="search" type="search" placeholder="Filter (e.g. tensor, muesli, 2025-08)" autocomplete="off">
    <input id="from" class="date" type="month" placeholder="From (YYYY-MM)">
    <input id="to" class="date" type="month" placeholder="To (YYYY-MM)">
    <button id="clear" class="btn">Clear filters</button>
    <span class="legend">Legend: <span class="badge">New</span> = modified within the last <strong id="legendDays">{RECENT_DAYS}</strong> days</span>
    <button id="toggle" class="btn" title="Collapse/expand all" style="margin-left:auto">Collapse all</button>
    <button id="recentOnly" class="btn" title="Show only recently added">Recent only</button>
    <input id="recentDays" class="num" type="number" min="1" step="1" value="{RECENT_DAYS}" title="Set Recent-days window">
    <button id="applyRecent" class="btn" title="Apply recent window">Apply</button>
    <button id="csv" class="btn" title="Download CSV">Export CSV</button>
  </div>
</header>
<main class="container">
""")
    for section_title, entries in grouped:
        parts.append(f'<section data-section="{escape(section_title)}">')
        parts.append(f"<h2>{escape(section_title)}</h2>")
        parts.append("<ul>")
        for e in entries:
            title = escape(e["title"])
            link = str(e["rel"]).replace("\\", "/")
            date = escape(e["date"])
            ext = escape(e["ext"])
            recent_attr = "true" if e.get("is_recent") else "false"
            badge = ' <span class="badge">New</span>' if e.get("is_recent") else ""
            parts.append(
                f'<li data-title="{title.lower()}" data-date="{date}" '
                f'data-section="{escape(section_title).lower()}" '
                f'data-link="./{link}" data-ext="{ext}" data-recent="{recent_attr}">'
                f'<div><a href="./{link}" target="_blank" rel="noopener">{title}</a>{badge}</div>'
                f'<div class="date-stamp">Date: {date}</div>'
                f"</li>"
            )
        parts.append("</ul></section>")
    parts.append("""
</main>
<footer class="container">
  Generated by build_index_v3_4_recent_ui.py. Links are relative; open this file from the same folder tree for best results.
</footer>
<script>
  // --- Theme init: saved -> system -> dark ---
  const html = document.documentElement;
  const savedTheme = localStorage.getItem('proj.theme');
  if (savedTheme) {
    html.setAttribute('data-theme', savedTheme);
  } else {
    const prefersLight = window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches;
    html.setAttribute('data-theme', prefersLight ? 'light' : 'dark');
  }

  // --- Theme toggle button ---
  const themeBtn = document.getElementById('theme');
  themeBtn.addEventListener('click', () => {
    const current = html.getAttribute('data-theme') === 'light' ? 'dark' : 'light';
    html.setAttribute('data-theme', current);
    localStorage.setItem('proj.theme', current);
    themeBtn.blur();
  });

  // --- Controls ---
  const q = document.getElementById('q');
  const from = document.getElementById('from');
  const to = document.getElementById('to');
  const clearBtn = document.getElementById('clear');
  const toggle = document.getElementById('toggle');
  const recentOnlyBtn = document.getElementById('recentOnly');
  const csvBtn = document.getElementById('csv');
  const recentDaysInput = document.getElementById('recentDays');
  const applyRecentBtn = document.getElementById('applyRecent');
  const legendDays = document.getElementById('legendDays');
  let collapsed = false;
  let recentOnly = false;

  // Persisted recent days in localStorage
  const savedDays = parseInt(localStorage.getItem('proj.recentDays') || '', 10);
  if (!isNaN(savedDays) && savedDays > 0) {
    recentDaysInput.value = String(savedDays);
    legendDays.textContent = String(savedDays);
  }

  function passDateRange(dateStr) {
    const valFrom = from.value; // "YYYY-MM"
    const valTo = to.value;     // "YYYY-MM"
    const key = dateStr.slice(0, 7);
    if (valFrom && key < valFrom) return false;
    if (valTo && key > valTo) return false;
    return true;
  }

  function recomputeRecentBadges(days) {
    const now = new Date();
    const cutoff = new Date(now.getTime() - days * 24 * 60 * 60 * 1000);
    document.querySelectorAll('li').forEach(li => {
      const dateStr = li.dataset.date;            // "YYYY-MM-DD"
      const d = new Date(dateStr + 'T00:00:00');
      const isRecent = d >= cutoff;
      li.dataset.recent = isRecent ? 'true' : 'false';
      const titleDiv = li.querySelector('div:first-child');
      let badge = titleDiv.querySelector('.badge');
      if (isRecent && !badge) {
        badge = document.createElement('span');
        badge.className = 'badge';
        badge.textContent = 'New';
        titleDiv.appendChild(badge);
      } else if (!isRecent && badge) {
        badge.remove();
      }
    });
  }

  function applyFilters() {
    const term = q.value.trim().toLowerCase();
    document.querySelectorAll('section').forEach(sec => {
      let hideSection = true;
      sec.querySelectorAll('li').forEach(li => {
        const hay = (li.dataset.title + ' ' + li.dataset.date + ' ' + li.dataset.section).toLowerCase();
        const matchTerm = term === '' || hay.includes(term);
        const matchDate = passDateRange(li.dataset.date);
        const matchRecent = !recentOnly || li.dataset.recent === 'true';
        const show = matchTerm && matchDate && matchRecent;
        li.classList.toggle('hidden', !show);
        if (show) hideSection = false;
      });
      sec.classList.toggle('hidden', hideSection);
    });
  }

  [q, from, to].forEach(el => el.addEventListener('input', applyFilters));
  clearBtn.addEventListener('click', () => {
    q.value = ''; from.value = ''; to.value = ''; recentOnly = false; recentOnlyBtn.textContent = 'Recent only'; applyFilters();
  });

  // Collapse/expand all
  toggle.addEventListener('click', () => {
    collapsed = !collapsed;
    document.querySelectorAll('section').forEach(sec => {
      const ul = sec.querySelector('ul'); if (!ul) return;
      ul.style.display = collapsed ? 'none' : 'grid';
    });
    toggle.textContent = collapsed ? 'Expand all' : 'Collapse all';
    toggle.blur();
  });

  // Recent only toggle
  recentOnlyBtn.addEventListener('click', () => {
    recentOnly = !recentOnly;
    recentOnlyBtn.textContent = recentOnly ? 'All items' : 'Recent only';
    applyFilters();
  });

  // Apply new Recent-days window
  applyRecentBtn.addEventListener('click', () => {
    const days = parseInt(recentDaysInput.value, 10);
    if (isNaN(days) || days < 1) { alert('Please enter a positive number of days.'); return; }
    localStorage.setItem('proj.recentDays', String(days));
    legendDays.textContent = String(days);
    recomputeRecentBadges(days);
    applyFilters();
  });

  // Initialize with saved recent days (if any)
  if (!isNaN(savedDays) && savedDays > 0) {
    recomputeRecentBadges(savedDays);
  }

  // --- Export CSV ---
  csvBtn.addEventListener('click', () => {
    const rows = [['Category','Title','Path','Date','Extension','Recent']];
    document.querySelectorAll('section').forEach(sec => {
      const category = sec.querySelector('h2').textContent;
      sec.querySelectorAll('li').forEach(li => {
        if (li.classList.contains('hidden')) return; // export only visible after filters
        const title = li.querySelector('a').textContent;
        const path = li.dataset.link || li.querySelector('a').getAttribute('href');
        const date = li.dataset.date;
        const ext = li.dataset.ext || '';
        const rec = li.dataset.recent === 'true' ? 'Yes' : 'No';
        rows.push([category, title, path, date, ext, rec]);
      });
    });
    const csv = rows.map(r => r.map(x => `"${(x||'').replace(/"/g,'""')}"`).join(',')).join('\\r\\n');
    const blob = new Blob([csv], {type: 'text/csv;charset=utf-8;'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'Projects_Index.csv';
    a.style.display = 'none';
    document.body.appendChild(a);
    a.click();
    setTimeout(() => { URL.revokeObjectURL(url); a.remove(); }, 1000);
  });

  // Initial pass
  applyFilters();
</script>
</body>
</html>""")
    return "\n".join(parts)

# ---------- CLI ----------
def main():
    import argparse
    ap = argparse.ArgumentParser(description="Generate an auto‑sorted index with Recent badges, legend, and adjustable window.")
    ap.add_argument("path", nargs="?", default=".", help="Folder to scan (default: current directory)")
    ap.add_argument("--recursive", action="store_true", help="Scan subfolders recursively")
    ap.add_argument("--format", choices=["md","html","both"], default="both", help="Output format (default: both)")
    ap.add_argument("--out-md", default="PROJECTS_INDEX_AUTO.md", help="Markdown output filename")
    ap.add_argument("--out-html", default="Projects_Index.html", help="HTML output filename")
    args = ap.parse_args()

    root = Path(args.path).expanduser().resolve()
    files = gather_files(root, recursive=args.recursive)
    entries = build_entries(root, files)
    grouped = group_and_sort(entries)

    if args.format in ("md", "both"):
        md = render_markdown(root, grouped)
        (root / args.out_md).write_text(md, encoding="utf-8")
        print(f"Wrote {root / args.out_md}")

    if args.format in ("html", "both"):
        html = render_html(root, grouped)
        (root / args.out_html).write_text(html, encoding="utf-8")
        print(f"Wrote {root / args.out_html}")

if __name__ == "__main__":
    main()
