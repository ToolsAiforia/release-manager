import csv
import io
import json
from datetime import datetime

from release_manager.models import ReleaseReport


def to_csv(report: ReleaseReport) -> str:
    """Export report as CSV string."""
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


def to_markdown(report: ReleaseReport) -> str:
    """Export report as Markdown string."""
    lines: list[str] = []
    lines.append(f"# Release Notes")
    lines.append(f"Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"Root: `{report.root_dir}`\n")

    if report.all_linear_keys:
        lines.append("## All Linear Keys")
        lines.append(", ".join(report.all_linear_keys))
        lines.append("")

    for repo in report.repos:
        lines.append(f"## {repo.repo_name}")
        lines.append(f"**{repo.from_tag}** → **{repo.to_tag}** ({len(repo.commits)} commits)\n")
        if repo.linear_keys:
            lines.append(f"Linear keys: {', '.join(repo.linear_keys)}\n")
        for commit in repo.commits:
            first_line = commit.message.split("\n")[0]
            keys_str = f" [{', '.join(commit.linear_keys)}]" if commit.linear_keys else ""
            lines.append(f"- `{commit.short_hash}` {first_line}{keys_str}")
        lines.append("")

    return "\n".join(lines)


def to_json(report: ReleaseReport) -> str:
    """Export report as JSON string."""
    data = report.model_dump(mode="json")
    return json.dumps(data, indent=2, ensure_ascii=False, default=str)
