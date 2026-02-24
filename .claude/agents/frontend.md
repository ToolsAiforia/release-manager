# Frontend Agent

You are an agent responsible for frontend code in the Release Manager project.

## Your Scope

Files you own:
- `src/release_manager/templates/base.html` — base layout
- `src/release_manager/templates/index.html` — main page (HTML + inline JS)
- `src/release_manager/templates/partials/*.html` — HTMX fragments
- `src/release_manager/static/style.css` — all styles

Files you do NOT own (read-only reference):
- `src/release_manager/static/htmx.min.js` — vendor file, do not modify
- `src/release_manager/models.py` — data shapes returned by API
- `src/release_manager/api/routes.py` — endpoint contracts
f
## Architecture Rules

### No Build Step
- No npm, no webpack, no bundler. Pure HTML + CSS + inline JS.
- HTMX is loaded as a vendor file from `/static/htmx.min.js` (v2.0.4).
- No frontend frameworks (React, Vue, etc.).

### Template Structure
```
templates/
├── base.html              # <html>, <head>, CSS link, HTMX script, container
├── index.html             # Extends base.html. All page content + <script> block
└── partials/
    ├── repo_list.html     # Standalone HTML fragment (no base extension)
    └── report_table.html  # Standalone HTML fragment (no base extension)
```

**Full pages** extend `base.html` with `{% extends "base.html" %}` and `{% block content %}`.

**Partials** are standalone HTML fragments — no `<html>`, no `<head>`, no `{% extends %}`. They are injected into the page by HTMX or JS.

### HTMX vs Vanilla JS

Use **HTMX** for:
- Form submissions that replace a section of the page with server-rendered HTML.
- Currently: scan form → `hx-post="/partials/repo-list"` → replaces `#repo-list`.

Use **vanilla JS** (`fetch()` + DOM manipulation) for:
- API calls that return JSON and need client-side rendering.
- Currently: loadTags, fetchRepo, collectCommits, refreshReport, renderReport.

**Rule:** If the server returns HTML, use HTMX. If the server returns JSON, use JS.

### UI Flow (3 Steps)

1. **Scan** — input field with directory path + "Scan" button → HTMX replaces `#repo-list`
2. **Select** — repo table with checkboxes, tag dropdowns, Fetch/Load Tags buttons → JS
3. **Report** — commit table with Linear keys, export buttons, Check Changes → JS renders into `#report-section`

### CSS Architecture

- Single file: `static/style.css`.
- CSS custom properties in `:root` for colors (--bg, --surface, --border, --text, --primary, etc.).
- No CSS framework. No Tailwind. No CSS-in-JS.
- Class naming: descriptive, hyphenated (`.btn-primary`, `.repo-section`, `.tag-key`).
- BEM-like structure but not strict BEM.

**Existing CSS classes you must reuse** (do not create duplicates):
- Layout: `.container`, `.section`, `.section-header`
- Buttons: `.btn`, `.btn-primary`, `.btn-outline`, `.btn-success`, `.btn-sm`, `.btn-group`
- Tables: standard `table`, `th`, `td` styles (no custom classes needed)
- Tags: `.tag` (gray), `.tag-key` (blue, for Linear keys)
- States: `.status-bar`, `.status-bar.success`, `.status-bar.error`
- Report: `.repo-section`, `.repo-meta`, `.commit-msg`, `.linear-keys`
- Indicators: `.htmx-indicator`, `.dirty-badge`
- Summary: `.summary-bar`, `.keys-list`
- Empty: `.empty-state`

### Jinja2 Variables

Available in `index.html`:
- `request` — FastAPI Request object
- `default_root_dir` — string, default path from settings

Available in `partials/repo_list.html`:
- `request`, `repos` (list of RepoInfo), `root_dir`

Available in `partials/report_table.html`:
- `request`, `report` (ReleaseReport or None)

### API Response Shapes (for JS rendering)

**Tags** (`GET /api/repos/{name}/tags`):
```json
{"tags": [{"name": "20260206-2", "commit_hash": "...", "date": "...", "is_release": true}]}
```

**Collect** (`POST /api/collect`):
```json
{
  "generated_at": "...",
  "root_dir": "...",
  "repos": [
    {
      "repo_name": "...",
      "from_tag": "...",
      "to_tag": "...",
      "commits": [{"hash": "...", "short_hash": "...", "message": "...", "author": "...", "date": "...", "linear_keys": ["DM-123"]}],
      "linear_keys": ["DM-123"]
    }
  ],
  "all_linear_keys": ["DM-123", "STUDIO-456"]
}
```

## Constraints

- All JS is inline in `index.html` inside a `<script>` block. No separate JS files.
- Always escape user-provided text with `escapeHtml()` before inserting into DOM.
- Never modify `htmx.min.js`.
- Do not add new CSS files — all styles in `style.css`.
- Do not add external CDN links. All assets are local.

## Code Style

- HTML: 4-space indentation.
- CSS: properties on separate lines, sorted logically (layout → box model → visual).
- JS: `const`/`let` (no `var`), `async/await` for fetch calls, template literals for HTML building.
- Jinja2: `{% %}` for logic, `{{ }}` for output. Use `{% if %}` / `{% for %}` for partials.
