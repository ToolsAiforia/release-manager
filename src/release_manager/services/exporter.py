import csv
import io
import json
import re
from dataclasses import dataclass

from release_manager.models import ReleaseReport

BOT_PATTERNS = [
    re.compile(p, re.I)
    for p in [
        r"\[bot\]",
        r"^dependabot",
        r"^renovate",
        r"^github-actions",
        r"^bender-",
        r"^aiphoria-ai$",
    ]
]


def _is_bot(name: str) -> bool:
    return any(p.search(name) for p in BOT_PATTERNS)


@dataclass
class TaskRow:
    component: str
    key: str
    contributors: list[str]


def _build_tasks(report: ReleaseReport) -> list[TaskRow]:
    """Build task rows grouped by component (same logic as the Jinja2 template)."""
    rows: list[TaskRow] = []
    for repo in report.repos:
        for key in repo.linear_keys:
            contributors: list[str] = []
            seen: set[str] = set()
            for c in repo.commits:
                if key in c.linear_keys and c.author not in seen and not _is_bot(c.author):
                    seen.add(c.author)
                    contributors.append(c.author)
            rows.append(TaskRow(component=repo.repo_name, key=key, contributors=contributors))
    return rows


# ── Tasks export (the main release export) ─────────────────


def to_csv(report: ReleaseReport) -> str:
    """Export tasks table as CSV: Component, Linear Key, Contributors."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Component", "Linear Key", "Contributors"])
    for task in _build_tasks(report):
        writer.writerow([
            task.component,
            task.key,
            ", ".join(task.contributors),
        ])
    return output.getvalue()


def to_markdown(report: ReleaseReport) -> str:
    """Export tasks table as Markdown grouped by component."""
    lines: list[str] = []
    lines.append("# Release Tasks")
    lines.append(f"Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M')}")
    lines.append("")
    for repo in report.repos:
        if not repo.linear_keys:
            continue
        lines.append(f"## {repo.repo_name}")
        lines.append(f"{repo.from_tag} → {repo.to_tag}")
        lines.append("")
        lines.append("| Linear Key | Contributors |")
        lines.append("|------------|--------------|")
        for key in repo.linear_keys:
            devs: list[str] = []
            seen: set[str] = set()
            for c in repo.commits:
                if key in c.linear_keys and c.author not in seen and not _is_bot(c.author):
                    seen.add(c.author)
                    devs.append(c.author)
            lines.append(f"| {key} | {', '.join(devs)} |")
        lines.append("")
    return "\n".join(lines)


def to_json(report: ReleaseReport) -> str:
    """Export tasks table as JSON grouped by component."""
    components = []
    for repo in report.repos:
        if not repo.linear_keys:
            continue
        tasks = []
        for key in repo.linear_keys:
            devs: list[str] = []
            seen: set[str] = set()
            for c in repo.commits:
                if key in c.linear_keys and c.author not in seen and not _is_bot(c.author):
                    seen.add(c.author)
                    devs.append(c.author)
            tasks.append({"linear_key": key, "contributors": devs})
        components.append({
            "component": repo.repo_name,
            "version_range": f"{repo.from_tag} → {repo.to_tag}",
            "tasks": tasks,
        })
    return json.dumps(components, indent=2, ensure_ascii=False)


# ── Contributors by Component export ───────────────────────


def contributors_to_csv(report: ReleaseReport) -> str:
    """Export contributors by component as CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Component", "Version Range", "Developers"])
    for repo in report.repos:
        authors: list[str] = []
        seen: set[str] = set()
        for c in repo.commits:
            if c.author not in seen and not _is_bot(c.author):
                seen.add(c.author)
                authors.append(c.author)
        writer.writerow([
            repo.repo_name,
            f"{repo.from_tag} -> {repo.to_tag}",
            ", ".join(authors),
        ])
    return output.getvalue()


# ── Commits export ─────────────────────────────────────────


def commits_to_csv(report: ReleaseReport) -> str:
    """Export all commits as CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        ["Repo", "From Tag", "To Tag", "Commit", "Author", "Date", "Message", "Linear Keys"]
    )
    for repo in report.repos:
        for commit in repo.commits:
            writer.writerow([
                repo.repo_name,
                repo.from_tag,
                repo.to_tag,
                commit.short_hash,
                commit.author,
                commit.date.strftime("%Y-%m-%d %H:%M"),
                commit.message.split("\n")[0],
                ", ".join(commit.linear_keys),
            ])
    return output.getvalue()
