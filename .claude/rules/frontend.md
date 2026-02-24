---
paths:
  - "src/release_manager/templates/**/*.html"
  - "src/release_manager/static/style.css"
---

# Frontend Rules

## HTML & Templates
- 4-space indentation
- Full pages extend `base.html` with `{% extends "base.html" %}` + `{% block content %}`
- Partials are standalone fragments — no `<html>`, no `{% extends %}`, no `<head>`
- Jinja2: `{% %}` for logic, `{{ }}` for output

## CSS Architecture
- **Tailwind CSS** via CDN script in `base.html` — use utility classes directly in HTML
- Tailwind config in `base.html` `<script>` block (custom colors, fonts)
- Custom styles only in `static/style.css` for things Tailwind can't do:
  - HTMX indicators/transitions, scrollbar styling, nav tooltips, animations, export dropdown
- Dark mode: Tailwind `dark:` prefix, configured as `darkMode: 'class'`
- Color scheme: gray-50/white (light), #0f1117/#1a1d26 (dark)

## JavaScript
- Global JS (toast, theme toggle) lives in `base.html` `<script>` block
- Page-specific JS (fetchRepo, toggleAll) lives inline in each page template
- `const`/`let` only, never `var`
- `async/await` for fetch calls
- Template literals for HTML building
- Always escape user text before DOM insertion

## HTMX vs JS Rule
- Server returns HTML → use HTMX (`hx-post`, `hx-target`)
- Server returns JSON → use vanilla JS (`fetch()` + DOM manipulation)

## Layout
- Vertical icon nav sidebar (`<nav>` w-16) with logo + page links + theme toggle at bottom
- Main content area (`<main>` flex-1 overflow-y-auto)
- Content pages use `max-w-6xl mx-auto` with `p-6` padding
- Nav items use `.nav-item` class with `.nav-tooltip` for hover labels
- Active page highlighted via `active_page` Jinja2 variable
- Toast container is fixed, outside the flex layout

## Pages
- `/` — Repositories (scan + repo table)
- `/draft` — Draft page
- `/releases` — Releases page

## Vendor Files
- `static/htmx.min.js` — HTMX 2.0.4, never modify
- No external CDN links except Tailwind script and Google Fonts
