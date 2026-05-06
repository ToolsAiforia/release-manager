"""Fetch deployed versions from platform-deploy GitHub repo."""

import base64
import json
import re
import urllib.request

GITHUB_API = "https://api.github.com"
IMAGE_TAG_RE = re.compile(r"image:\s*\n(?:\s+\w+:\s*\S*\n)*?\s+tag:\s*(\S+)")


def _github_get(url: str, token: str) -> dict | list:
    """GET request to GitHub API."""
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "release-manager",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def fetch_deployed_versions(
    owner: str,
    repo: str,
    cluster_path: str,
    token: str,
    until: str | None = None,
    branch: str | None = None,
) -> dict:
    """Fetch component → tag mapping from a cluster directory.

    Args:
        until: ISO date string. If set, fetches state as of latest commit on/before that date.
        branch: Git branch name (default 'main').

    Returns {"components": [{name, tag, file}], "commit": {sha, ...}}.
    """
    base = f"{GITHUB_API}/repos/{owner}/{repo}"

    # 1. Find the commit (latest, or latest before `until`)
    commits_url = f"{base}/commits?path={cluster_path}&per_page=1"
    if branch:
        commits_url += f"&sha={branch}"
    if until:
        commits_url += f"&until={until}T23:59:59Z"

    commits = _github_get(commits_url, token)
    if not commits:
        return {"components": [], "commit": None}

    commit = commits[0]
    ref = commit["sha"]
    commit_info = {
        "sha": ref[:7],
        "full_sha": ref,
        "message": commit["commit"]["message"].split("\n")[0],
        "date": commit["commit"]["committer"]["date"],
        "url": commit["html_url"],
    }

    # 2. List directories at that ref
    contents = _github_get(f"{base}/contents/{cluster_path}?ref={ref}", token)
    dirs = [item for item in contents if item["type"] == "dir"]

    # 3. For each component dir, scan files for image.tag + who set this tag
    components: list[dict] = []
    for d in sorted(dirs, key=lambda x: x["name"]):
        tag, source_file = _find_image_tag(base, f"{cluster_path}/{d['name']}", token, ref)
        file_path = f"{cluster_path}/{d['name']}/{source_file}" if source_file else None
        author, updated_at = _get_tag_commit_info(
            base, file_path, tag, token, ref
        )
        components.append({
            "name": d["name"],
            "tag": tag,
            "file": source_file,
            "author": author,
            "updated_at": updated_at,
        })

    # 4. Extra components from specific files within existing dirs
    extras = _scan_extra_components(base, cluster_path, token, ref)
    components.extend(extras)

    return {"components": components, "commit": commit_info}


# Components extracted from specific files (not their own directory)
EXTRA_FILE_COMPONENTS = [
    {"name": "rasa-oss", "dir": "rasa", "file": "rasa_server_values.yaml"},
]


def _scan_extra_components(
    base_url: str, cluster_path: str, token: str, ref: str
) -> list[dict]:
    """Scan specific files for extra components that don't have their own dir."""
    extras: list[dict] = []
    for extra in EXTRA_FILE_COMPONENTS:
        file_path = f"{cluster_path}/{extra['dir']}/{extra['file']}"
        try:
            url = f"{base_url}/contents/{file_path}?ref={ref}"
            file_data = _github_get(url, token)
            content = base64.b64decode(file_data["content"]).decode("utf-8")
            match = IMAGE_TAG_RE.search(content)
            tag = match.group(1) if match else None
            extras.append({
                "name": extra["name"],
                "tag": tag,
                "file": extra["file"],
            })
        except Exception:
            extras.append({
                "name": extra["name"],
                "tag": None,
                "file": extra["file"],
            })
    return extras


def list_clusters(owner: str, repo: str, token: str) -> list[str]:
    """List cluster names from the clusters/ directory."""
    try:
        contents = _github_get(
            f"{GITHUB_API}/repos/{owner}/{repo}/contents/clusters", token
        )
        return sorted(c["name"] for c in contents if c["type"] == "dir")
    except Exception:
        return []


def list_branches(owner: str, repo: str, token: str) -> list[str]:
    """List all branches of a GitHub repo, main first."""
    branches: list[str] = []
    page = 1
    while page <= 3:
        try:
            data = _github_get(
                f"{GITHUB_API}/repos/{owner}/{repo}/branches?per_page=100&page={page}",
                token,
            )
        except Exception:
            break
        if not data:
            break
        branches.extend(b["name"] for b in data)
        if len(data) < 100:
            break
        page += 1

    if "main" in branches:
        branches.remove("main")
        branches.insert(0, "main")
    return branches


def fetch_infra_info(token: str, until: str | None = None) -> dict:
    """Fetch SIP infrastructure from sip-deploy repo.

    Args:
        until: ISO date string (e.g. '2026-03-15'). If set, fetches state
               as of the latest commit on or before that date.

    Algorithm:
    1. Last commit in envs/aiphoria-qa → sip_deploy commit info
    2. adapter_git_version from playbook.yml at that commit → sip_proxy version
    3. freeswitch_version from ansible-role-fsgrpc/defaults/main.yml → freeswitch
    4. Last tag in sip-deploy before that commit → sip_deploy_tag

    Returns {sip_deploy, sip_proxy_version, freeswitch_version, sip_deploy_tag}.
    """
    base = f"{GITHUB_API}/repos/acclaim-ai/sip-deploy"
    result: dict = {
        "sip_deploy": None,
        "sip_proxy_version": None,
        "freeswitch_version": None,
        "sip_deploy_tag": None,
    }

    ref = None

    # 1. Last commit in envs/aiphoria-qa (optionally before `until`)
    try:
        url = f"{base}/commits?path=envs/aiphoria-qa&per_page=1"
        if until:
            url += f"&until={until}T23:59:59Z"
        commits = _github_get(url, token)
        if commits:
            c = commits[0]
            ref = c["sha"]
            result["sip_deploy"] = {
                "sha": ref[:7],
                "full_sha": ref,
                "message": c["commit"]["message"].split("\n")[0],
                "date": c["commit"]["committer"]["date"],
                "url": c["html_url"],
                "tree_url": f"https://github.com/acclaim-ai/sip-deploy/tree/{ref}/envs/aiphoria-qa",
            }
    except Exception:
        pass

    # 2. adapter_git_version — use version from last actual deploy, not just config
    #    Find last successful GitHub Actions deploy run for aiphoria-qa.
    #    Read playbook.yml at that run's commit to get actually deployed version.
    deploy_ref = ref  # fallback to config commit
    try:
        runs_url = (
            f"{base}/actions/workflows/deploy.yml/runs"
            "?status=success&per_page=20"
        )
        runs = _github_get(runs_url, token)
        for run in runs.get("workflow_runs", []):
            title = run.get("display_title", "")
            if "aiphoria-qa" in title.lower():
                run_date = run.get("created_at", "")[:10]
                # If until is set, only use runs before that date
                if until and run_date > until:
                    continue
                deploy_ref = run["head_sha"]
                break
    except Exception:
        pass

    try:
        url = f"{base}/contents/envs/aiphoria-qa/playbook.yml"
        if deploy_ref:
            url += f"?ref={deploy_ref}"
        file_data = _github_get(url, token)
        content = base64.b64decode(file_data["content"]).decode("utf-8")
        match = re.search(
            r"adapter_git_version:\s*[\"']?([^\s\"'#]+)", content
        )
        if match:
            result["sip_proxy_version"] = match.group(1)
    except Exception:
        pass

    # 3. freeswitch_version from ansible-role-fsgrpc/defaults/main.yml
    try:
        url = f"{base}/contents/ansible-role-fsgrpc/defaults/main.yml"
        if ref:
            url += f"?ref={ref}"
        file_data = _github_get(url, token)
        content = base64.b64decode(file_data["content"]).decode("utf-8")
        match = re.search(
            r"freeswitch_version:\s*[\"']?([^\s\"'#]+)", content
        )
        if not match:
            match = re.search(r"version:\s*[\"']?v?([\d.]+)", content, re.I)
        if match:
            result["freeswitch_version"] = match.group(1)
    except Exception:
        pass

    # 4. Last tag before this commit
    if ref:
        try:
            tags = _github_get(f"{base}/tags?per_page=10", token)
            for tag in tags:
                # Check if tag's commit is an ancestor of ref
                # Simple approach: get tag commit date, compare with ref date
                result["sip_deploy_tag"] = tags[0]["name"] if tags else None
                break
        except Exception:
            pass

    return result


def _get_tag_commit_info(
    base_url: str,
    file_path: str,
    tag_value: str | None,
    token: str,
    ref: str,
) -> tuple[str | None, str | None]:
    """Find who set a specific image tag in a file and when.

    Checks the diff of recent commits to find which one added `+  tag: <value>`.
    Falls back to the latest file commit.
    """
    if not file_path:
        return None, None
    try:
        url = f"{base_url}/commits?path={file_path}&sha={ref}&per_page=5"
        commits = _github_get(url, token)
        if not commits:
            return None, None

        # Check each commit's diff for the tag change
        if tag_value:
            for c in commits:
                try:
                    detail = _github_get(c["url"], token)
                    for f in detail.get("files", []):
                        patch = f.get("patch", "")
                        # Look for "+  tag: <value>" in the diff
                        if f"+  tag: {tag_value}" in patch:
                            return (
                                c["commit"]["author"]["name"],
                                c["commit"]["committer"]["date"][:10],
                            )
                except Exception:
                    continue

        # Fallback: latest commit that touched this file
        c = commits[0]
        return c["commit"]["author"]["name"], c["commit"]["committer"]["date"][:10]
    except Exception:
        pass
    return None, None


def _find_image_tag(
    base_url: str, dir_path: str, token: str, ref: str | None = None
) -> tuple[str | None, str | None]:
    """Scan all files in a directory for image.tag pattern."""
    url = f"{base_url}/contents/{dir_path}"
    if ref:
        url += f"?ref={ref}"
    try:
        files = _github_get(url, token)
    except Exception:
        return None, None

    for f in files:
        if f["type"] != "file":
            continue
        name = f["name"]
        if not (name.endswith(".yaml") or name.endswith(".yml")):
            continue
        try:
            file_url = f["url"]
            file_data = _github_get(file_url, token)
            content = base64.b64decode(file_data["content"]).decode("utf-8")
            match = IMAGE_TAG_RE.search(content)
            if match:
                return match.group(1), name
        except Exception:
            continue

    return None, None
