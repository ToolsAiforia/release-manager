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
## Architecture Rules

### No Build Step
- No npm, no webpack, no bundler. Pure HTML + CSS + inline JS.
- HTMX is loaded as a vendor file from `/static/htmx.min.js` (v2.0.4).
- No frontend frameworks (React, Vue, etc.).

### Template Structure
```
templates/
├── base.html              # <html>, <head>, nav sidebar, toast, theme toggle, global JS
├── index.html             # Repositories page (scan + repo table + page JS)
├── draft.html             # Draft page (report editing)
├── releases.html          # Releases page (release history)
└── partials/
    ├── repo_list.html     # HTMX fragment: repo table
    └── report_table.html  # HTMX fragment: report
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

- **Tailwind CSS** via CDN `<script>` in `base.html` — use utility classes directly in HTML.
- Tailwind config (custom colors, fonts) lives in `base.html` `<script>` block.
- `darkMode: 'class'` — toggle via `.dark` class on `<html>`.
- Custom styles only in `static/style.css` for things Tailwind can't handle:
  - HTMX indicators/transitions, scrollbar styling, nav tooltips, animations, collapse, export dropdown.
- Color scheme: gray-50/white (light), `#0f1117`/`#1a1d26` (dark).
- Accent color: indigo-500.

### Layout

- Vertical icon nav sidebar (`<nav class="nav-sidebar w-16">`) — logo, page links, theme toggle at bottom.
- Main content area (`<main class="flex-1 overflow-y-auto">`).
- Content pages use `max-w-6xl mx-auto` with `p-6` padding.
- Nav items highlight active page via `active_page` Jinja2 variable.
- Toast container is fixed, defined in `base.html`.
- Global JS (toast, theme toggle) lives in `base.html`.

### Multi-Page Structure

- `/` — Repositories page (`index.html`): scan directory, repo table, collect commits
- `/draft` — Draft page: report editing
- `/releases` — Releases page: release history

### Jinja2 Variables

Available in all pages (set in `base.html`):
- `request` — FastAPI Request object
- `active_page` — string identifying the current page (`"repos"`, `"draft"`, `"releases"`)

Available in `index.html`:
- `default_root_dir` — string, default path from settings

Available in `partials/repo_list.html`:
- `request`, `repos` (list of RepoInfo), `repo_tags` (dict of repo name → list of TagInfo)

Available in `partials/report_table.html`:
- `request`, `report` (ReleaseReport or None), `error` (string or None)

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
