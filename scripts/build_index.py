#!/usr/bin/env python3
"""
build_index_config_exclude_v2.py — index builder with robust excludes

Enhancements vs build_index_config_exclude.py:
- Exclude patterns may be quoted in text/INI (we strip surrounding ' ' or " ").
- Directory excludes support two modes:
  * Component mode (simple names/globs): 'venv', '__pycache__', 'node_modules*'
  * Path mode (pattern contains '/' or '\'): matched against the RELATIVE path
    normalized to POSIX ('Topfolder/Subfolder1*', '*Topfolder/Subfolder2*')
- File excludes unchanged (basename glob match), but also strip quotes.
"""

from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Iterable, Set
from fnmatch import fnmatch
import configparser

# ---------- Configuration ----------
EXTENSIONS = {".pdf", ".md", ".txt", ".bat", ".ps1"}

EXCLUDE_FILES_DEFAULT: Set[str] = {
    "Projects_Index.html",
    "projects_index_auto.md",
    "projects_index_auto_cleaned.md",
    "top_level.txt",
    "entry_points.txt",
    ".exclude_dirs.txt",
    ".exclude_files.txt"
}

EXCLUDE_DIRS_DEFAULT: Set[str] = {
    "venv",
}

DEFAULT_CATEGORY = "🗃️ Other"
RECENT_DAYS = 7

CATEGORY_RULES: Dict[str, Tuple[str, ...]] = {
    "📘 Mathematics": (
        "tensor", "summation", "einstein", "directioncosines",
        "potentialvorticity", "geometricoperators",
        "differentialforms", "continuum", "indexnotation", "indicial"
    ),
    "🍳 Cooking Guides": (
        "blackberry", "muesli", "bircher", "pasty", "scone", "recipe",
        "cooking", "baking", "bread", "dough", "curry", "spanakopita",
        "cake", "filo", "cake", "roll"
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

DEFAULT_INI = ".index_excludes.ini"
DEFAULT_DIRS_TXT = ".exclude_dirs.txt"
DEFAULT_FILES_TXT = ".exclude_files.txt"

# ---------- Helpers ----------
def _strip_quotes(s: str) -> str:
    if len(s) >= 2 and ((s[0] == s[-1] == '"') or (s[0] == s[-1] == "'")):
        return s[1:-1]
    return s

def _normalize_patterns(patterns: Iterable[str]) -> List[str]:
    out: List[str] = []
    for p in patterns or []:
        p = _strip_quotes(p.strip())
        if p:
            out.append(p)
    return out

def any_parent_matches(rel: Path, patterns: Iterable[str]) -> bool:
    """
    Return True if any exclude-dir pattern matches the relative path.
    Two strategies:
      - If pattern contains a path sep ('/' or '\\'), compare against rel.as_posix() (whole relative path).
      - Otherwise, compare against each component name (case-insensitive).
    """
    pats = _normalize_patterns(patterns)
    if not pats:
        return False

    rel_posix = rel.as_posix().lower()
    parts = [p.lower() for p in rel.parts]

    for pat in pats:
        lpat = pat.lower()
        if ("/" in lpat) or ("\\" in lpat):
            lpat_norm = lpat.replace("\\", "/")
            if fnmatch(rel_posix, lpat_norm):
                return True
        else:
            for name in parts:
                if fnmatch(name, lpat):
                    return True
    return False

def matches_any_file(name: str, patterns: Iterable[str]) -> bool:
    pats = _normalize_patterns(patterns)
    if not pats:
        return False
    lname = name.lower()
    for pat in pats:
        if fnmatch(lname, pat.lower()):
            return True
    return False

def read_patterns_textfile(path: Path) -> List[str]:
    out: List[str] = []
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except FileNotFoundError:
        return out
    for line in content.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or s.startswith(";"):
            continue
        out.append(_strip_quotes(s))
    return out

def read_patterns_ini(path: Path) -> Tuple[List[str], List[str]]:
    dirs: List[str] = []
    files: List[str] = []
    if not path.exists():
        return dirs, files
    cfg = configparser.ConfigParser()
    try:
        cfg.read(path, encoding="utf-8")
    except Exception:
        return dirs, files

    def parse_list(val: str) -> List[str]:
        if not val:
            return []
        parts = []
        for line in val.replace("\r", "\n").split("\n"):
            line = line.strip()
            if not line or line.startswith("#") or line.startswith(";"):
                continue
            parts.extend([_strip_quotes(p.strip()) for p in line.split(",") if p.strip()])
        return parts

    if cfg.has_section("exclude_dirs"):
        raw = cfg.get("exclude_dirs", "patterns", fallback="")
        dirs = parse_list(raw)
    if cfg.has_section("exclude_files"):
        raw = cfg.get("exclude_files", "patterns", fallback="")
        files = parse_list(raw)

    return dirs, files

def gather_files(root: Path, recursive: bool, exclude_dirs: Iterable[str], exclude_files: Iterable[str]) -> List[Path]:
    it = root.rglob("*") if recursive else root.glob("*")
    out = []
    for p in it:
        try:
            rel = p.relative_to(root)
        except Exception:
            rel = p

        if any_parent_matches(rel.parent, exclude_dirs):
            continue

        if p.is_file() and p.suffix.lower() in EXTENSIONS:
            if matches_any_file(p.name, exclude_files):
                continue
            out.append(p)
    return out

def categorize(filename: str) -> str:
    name = filename.lower()
    for cat, keywords in CATEGORY_RULES.items():
        if any(k in name for k in keywords):
            return cat
    return DEFAULT_CATEGORY

def build_entries(root: Path, files: List[Path]):
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

def group_and_sort(entries):
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

def render_markdown(root: Path, grouped) -> str:
    lines = [
        "# 📚 Projects Index (Auto-Sorted)",
        "",
        f"_Scanned folder_: `{root}`",
        "",
        f"Files modified in the last **{RECENT_DAYS} days** are considered *recent*.",
        "",
        "---",
        "",
    ]
    for cat, items in grouped:
        lines.append(f"## {cat}\n")
        for e in items:
            rel = str(e["rel"]).replace("\\", "/")
            tag = "  *(New)*" if e.get("is_recent") else ""
            lines.append(f"- [{e['title']}](./{rel}) — *Date: {e['date']}*{tag}")
        lines.append("\n---\n")
    lines += [
        "### 🛠 Exclude patterns",
        "",
        "- **Component match** (names only): `venv`, `__pycache__`, `node_modules*`",
        "- **Path match** (include `/` or `\\`): `Hacking/Ghidra_and_Java*`, `*Hacking/Nvidia*`",
        "- Quotes around patterns are optional; we strip them if present.",
        "",
    ]
    return "\n".join(lines)

#def render_html(root: Path, grouped) -> str:
def render_html(root: Path, grouped, show_ext: bool = False) -> str:
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
  .ext-badge {{ 
    display:inline-block; 
    font-size:11px; 
    padding:2px 6px; 
    border-radius:999px; 
    margin-left:8px; 
    background:var(--border); 
    color:var(--muted); 
    }}              
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
            ext = escape(e["ext"])  # like ".md", ".pdf", ".bat"
            recent_attr = "true" if e.get("is_recent") else "false"
            new_badge = ' <span class="badge">New</span>' if e.get("is_recent") else ""
            ext_badge = f' <span class="ext-badge">{ext}</span>' if show_ext else ""

            parts.append(
                f'<li data-title="{title.lower()}" data-date="{date}" '
                f'data-section="{escape(section_title).lower()}" '
                f'data-link="./{link}" data-ext="{ext}" data-recent="{recent_attr}">'
                f'<div><a href="./{link}" target="_blank" rel="noopener">{title}</a>{ext_badge}{new_badge}</div>'
                f'<div class="date-stamp">Date: {date}</div>'
                f"</li>"
            )
            
        parts.append("</ul></section>")
    parts.append("""
</main>
<footer class="container">
  Generated by build_index_config_exclude_v2.py.
</footer>
<script>
  const html = document.documentElement;
  const savedTheme = localStorage.getItem('proj.theme');
  if (savedTheme) {
    html.setAttribute('data-theme', savedTheme);
  } else {
    const prefersLight = window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches;
    html.setAttribute('data-theme', prefersLight ? 'light' : 'dark');
  }
  const themeBtn = document.getElementById('theme');
  themeBtn.addEventListener('click', () => {
    const current = html.getAttribute('data-theme') === 'light' ? 'dark' : 'light';
    html.setAttribute('data-theme', current);
    localStorage.setItem('proj.theme', current);
    themeBtn.blur();
  });

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

  const savedDays = parseInt(localStorage.getItem('proj.recentDays') || '', 10);
  if (!isNaN(savedDays) && savedDays > 0) {
    recentDaysInput.value = String(savedDays);
    legendDays.textContent = String(savedDays);
  }

  function passDateRange(dateStr) {
    const valFrom = from.value;
    const valTo = to.value;
    const key = dateStr.slice(0, 7);
    if (valFrom && key < valFrom) return false;
    if (valTo && key > valTo) return false;
    return true;
  }

  function recomputeRecentBadges(days) {
    const now = new Date();
    const cutoff = new Date(now.getTime() - days * 24 * 60 * 60 * 1000);
    document.querySelectorAll('li').forEach(li => {
      const dateStr = li.dataset.date;
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

  toggle.addEventListener('click', () => {
    collapsed = !collapsed;
    document.querySelectorAll('section').forEach(sec => {
      const ul = sec.querySelector('ul'); if (!ul) return;
      ul.style.display = collapsed ? 'none' : 'grid';
    });
    toggle.textContent = collapsed ? 'Expand all' : 'Collapse all';
    toggle.blur();
  });

  recentOnlyBtn.addEventListener('click', () => {
    recentOnly = !recentOnly;
    recentOnlyBtn.textContent = recentOnly ? 'All items' : 'Recent only';
    applyFilters();
  });

  applyRecentBtn.addEventListener('click', () => {
    const days = parseInt(recentDaysInput.value, 10);
    if (isNaN(days) || days < 1) { alert('Please enter a positive number of days.'); return; }
    localStorage.setItem('proj.recentDays', String(days));
    legendDays.textContent = String(days);
    recomputeRecentBadges(days);
    applyFilters();
  });

  if (!isNaN(savedDays) && savedDays > 0) {
    recomputeRecentBadges(savedDays);
  }

  csvBtn.addEventListener('click', () => {
    const rows = [['Category','Title','Path','Date','Extension','Recent']];
    document.querySelectorAll('section').forEach(sec => {
      const category = sec.querySelector('h2').textContent;
      sec.querySelectorAll('li').forEach(li => {
        if (li.classList.contains('hidden')) return;
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

  applyFilters();
</script>
</body>
</html>""")
    return "\n".join(parts)

def main():
    import argparse
    ap = argparse.ArgumentParser(description="Index with robust excludes (quoted patterns + path-aware)")
    ap.add_argument("path", nargs="?", default=".", help="Folder to scan (default: current directory)")
    ap.add_argument("--recursive", action="store_true", help="Scan subfolders recursively")
    ap.add_argument("--format", choices=["md","html","both"], default="both", help="Output format (default: both)")
    ap.add_argument("--out-md", default="PROJECTS_INDEX_AUTO.md", help="Markdown output filename")
    ap.add_argument("--out-html", default="Projects_Index.html", help="HTML output filename")

    ap.add_argument("--config", default=None, help="Path to INI config (default: search .index_excludes.ini)")
    ap.add_argument("--exclude-dirs-file", default=None, help="Path to text file with directory patterns (default: search .exclude_dirs.txt)")
    ap.add_argument("--exclude-files-file", default=None, help="Path to text file with file patterns (default: search .exclude_files.txt)")
    ap.add_argument("--exclude-dir", action="append", default=[], metavar="PATTERN",
                    help="Exclude directories by name or glob pattern (repeatable)")
    ap.add_argument("--exclude-file", action="append", default=[], metavar="PATTERN",
                    help="Exclude files by basename or glob pattern (repeatable)")


    ap.add_argument("--show-ext", action="store_true",
                help="Show file extensions as badges in the HTML index")


    args = ap.parse_args()
    root = Path(args.path).expanduser().resolve()

    # Defaults
    exclude_dirs: Set[str] = set(EXCLUDE_DIRS_DEFAULT)
    exclude_files: Set[str] = set(EXCLUDE_FILES_DEFAULT)

    # INI
    ini_path = Path(args.config) if args.config else (root / DEFAULT_INI)
    ini_dirs, ini_files = read_patterns_ini(ini_path)
    exclude_dirs.update(ini_dirs)
    exclude_files.update(ini_files)

    # Text files
    dirs_file_path = Path(args.exclude_dirs_file) if args.exclude_dirs_file else (root / DEFAULT_DIRS_TXT)
    files_file_path = Path(args.exclude_files_file) if args.exclude_files_file else (root / DEFAULT_FILES_TXT)
    if dirs_file_path.exists():
        exclude_dirs.update(read_patterns_textfile(dirs_file_path))
    if files_file_path.exists():
        exclude_files.update(read_patterns_textfile(files_file_path))

    # CLI
    exclude_dirs.update(args.exclude_dir or [])
    exclude_files.update(args.exclude_file or [])

    files = gather_files(root, recursive=args.recursive,
                         exclude_dirs=exclude_dirs,
                         exclude_files=exclude_files)
    entries = build_entries(root, files)
    grouped = group_and_sort(entries)

    if args.format in ("md", "both"):
        md = render_markdown(root, grouped)
        (root / args.out_md).write_text(md, encoding="utf-8")
        print(f"Wrote {root / args.out_md}")

    if args.format in ("html", "both"):
#        html = render_html(root, grouped)
        html = render_html(root, grouped, show_ext=args.show_ext)
        (root / args.out_html).write_text(html, encoding="utf-8")
        print(f"Wrote {root / args.out_html}")

if __name__ == "__main__":
    main()
