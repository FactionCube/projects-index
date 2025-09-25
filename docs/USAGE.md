# 📖 Usage Guide — Projects Index Generator

This document provides step-by-step instructions for running and customizing the index generator.

---

## 🔧 Requirements

- Python **3.8+**
- No external libraries required (pure standard library)

---

## 🚀 Running the Script

Basic usage (default: current folder, both HTML + Markdown outputs):
```bash
python scripts/build_index.py
```

Index a specific folder:
```bash
python scripts/build_index.py ~/Documents
```

Recursive mode (include subfolders):
```bash
python scripts/build_index.py ~/Documents --recursive
```

HTML only:
```bash
python scripts/build_index.py --format html
```

Markdown only:
```bash
python scripts/build_index.py --format md
```

Custom output filenames:
```bash
python scripts/build_index.py ~/Library \
  --out-html index.html --out-md INDEX.md
```

---

## 🎛️ Interactive Dashboard Features

- **Search box** → type any keyword (title, date, category) to filter  
- **Date range filters** → limit items between `From` and `To` months  
- **Recent only toggle** → show only items with the 🆕 **New** badge  
- **Recent days input** → adjust the recency window (default: 7 days), persists via browser localStorage  
- **Collapse/Expand sections** → click headers or use the “Collapse all” button (state remembered across sessions)  
- **Export CSV** → saves a filtered CSV with Category, Title, Path, Date, Extension, and Recent status  

---

## ⚙️ Configuration (script level)

At the top of the Python script:
- **`EXTENSIONS`** → which file types to include (default: `.pdf`, `.md`, `.txt`, `.py`, `.bat`, `.ps1`)  
- **`CATEGORY_RULES`** → dictionary of keywords to group files into categories  
- **`RECENT_DAYS`** → default recency threshold (overridden by UI)  

---

## 🧩 Tips

- Keep the HTML file in the same folder tree as your indexed files → ensures relative links open correctly.  
- Use `git` to track script changes and `docs/CHANGELOG.md` to log new features.  
- Add screenshots of your generated dashboard to `examples/` for quick previews.  

---
