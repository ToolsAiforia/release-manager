"""Fetch Linear keys from GitHub PRs associated with commits."""

import json
import urllib.request

from release_manager.services.parser import extract_linear_keys

GITHUB_API = "https://api.github.com"


def _github_get(url: str, token: str) -> dict | list:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "release-manager",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


import re as _re

_SKIP_PR_RE = _re.compile(
    r"^(release|maintenance|chore\(deps\))", _re.IGNORECASE
)


def get_merged_pr_keys(
    owner: str, repo: str, from_date: str, to_date: str, token: str
) -> dict[str, list[str]]:
    """Fetch merged PRs in date range, return {merge_commit_sha: [keys]}.

    - Skips release/maintenance/deps PRs (they contain old keys in body)
    - Extracts keys from PR title only (body often has changelogs)
    """
    result: dict[str, list[str]] = {}
    page = 1
    while page <= 5:  # max 500 PRs
        url = (
            f"{GITHUB_API}/repos/{owner}/{repo}/pulls"
            f"?state=closed&sort=updated&direction=desc"
            f"&per_page=100&page={page}"
        )
        try:
            prs = _github_get(url, token)
        except Exception:
            break

        if not prs:
            break

        found_older = False
        for pr in prs:
            if not pr.get("merged_at"):
                continue
            merged_at = pr["merged_at"][:10]
            if merged_at < from_date:
                found_older = True
                break
            if merged_at > to_date:
                continue

            title = pr.get("title", "")

            # Skip release/maintenance/deps PRs
            if _SKIP_PR_RE.search(title):
                continue

            # Extract keys from title only (not body — body has changelogs)
            keys = extract_linear_keys(title)
            if keys and pr.get("merge_commit_sha"):
                result[pr["merge_commit_sha"]] = keys

        if found_older or len(prs) < 100:
            break
        page += 1

    return result


def enrich_commits_with_pr_keys(
    commits: list[dict],
    owner: str,
    repo: str,
    token: str,
    from_date: str | None = None,
    to_date: str | None = None,
) -> list[dict]:
    """Add Linear keys from merged PRs to matching commits.

    Uses bulk PR fetch (1 request per page) instead of per-commit lookup.
    """
    if not from_date or not to_date:
        return commits

    pr_keys = get_merged_pr_keys(owner, repo, from_date, to_date, token)

    # Map commit SHA → PR keys
    for commit in commits:
        sha = commit.get("hash", "")
        matched_keys = pr_keys.get(sha, [])
        if matched_keys:
            existing = set(commit.get("linear_keys", []))
            for key in matched_keys:
                if key not in existing:
                    commit.setdefault("linear_keys", []).append(key)
                    existing.add(key)

    return commits


def get_repo_owner_name(url: str) -> tuple[str, str] | None:
    """Extract owner/repo from a GitHub URL."""
    url = url.rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]
    parts = url.split("/")
    if len(parts) >= 2:
        return parts[-2], parts[-1]
    return None