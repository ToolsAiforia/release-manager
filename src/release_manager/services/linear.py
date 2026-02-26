"""Linear GraphQL API client — fetch issue details by identifier."""

import json
import urllib.request

API_URL = "https://api.linear.app/graphql"

ISSUE_FIELDS = """
    id
    identifier
    title
    description
    state { name color }
    assignee { name displayName avatarUrl }
    priority
    priorityLabel
    labels { nodes { name color } }
    project { name }
    comments { nodes { body user { name displayName } createdAt } }
    relations { nodes { type relatedIssue { identifier title url } } }
    createdAt
    updatedAt
    url
"""


def _graphql(query: str, variables: dict, api_key: str) -> dict:
    """Execute a GraphQL request against Linear API."""
    payload = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(
        API_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": api_key,
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def fetch_issue(identifier: str, api_key: str) -> dict | None:
    """Fetch a single issue by identifier (e.g. 'ABC-123') via search."""
    query = """
    query($term: String!) {
        searchIssues(term: $term, first: 1) {
            nodes { %s }
        }
    }
    """ % ISSUE_FIELDS
    variables = {"term": identifier}
    try:
        data = _graphql(query, variables, api_key)
        nodes = data.get("data", {}).get("searchIssues", {}).get("nodes", [])
        # Verify exact match (search may return fuzzy results)
        for n in nodes:
            if n.get("identifier", "").upper() == identifier.upper():
                return _normalize(n)
        return None
    except Exception:
        return None


def fetch_issues(identifiers: list[str], api_key: str) -> dict[str, dict]:
    """Batch-fetch multiple issues. Returns {identifier: issue_data}."""
    if not identifiers:
        return {}
    # Linear searchIssues doesn't support batch, so search per-issue
    # Use a single search with all identifiers joined by OR-like term
    # For reliability, fetch one by one (Linear API is fast)
    result: dict[str, dict] = {}
    for key in identifiers:
        issue = fetch_issue(key, api_key)
        if issue:
            result[issue["identifier"]] = issue
    return result


def _normalize(node: dict) -> dict:
    """Flatten nested Linear API response into a clean dict."""
    assignee = node.get("assignee") or {}
    state = node.get("state") or {}
    project = node.get("project") or {}
    labels = [
        {"name": l["name"], "color": l.get("color", "")}
        for l in (node.get("labels", {}).get("nodes") or [])
    ]
    comments = [
        {
            "body": c["body"],
            "author": (c.get("user") or {}).get("displayName")
            or (c.get("user") or {}).get("name", ""),
            "created_at": c.get("createdAt", ""),
        }
        for c in (node.get("comments", {}).get("nodes") or [])
    ]
    relations = [
        {
            "type": r["type"],
            "identifier": r.get("relatedIssue", {}).get("identifier", ""),
            "title": r.get("relatedIssue", {}).get("title", ""),
            "url": r.get("relatedIssue", {}).get("url", ""),
        }
        for r in (node.get("relations", {}).get("nodes") or [])
    ]
    return {
        "identifier": node.get("identifier", ""),
        "title": node.get("title", ""),
        "description": node.get("description", ""),
        "status": state.get("name", ""),
        "status_color": state.get("color", ""),
        "assignee": assignee.get("displayName") or assignee.get("name", ""),
        "assignee_avatar": assignee.get("avatarUrl", ""),
        "priority": node.get("priorityLabel", ""),
        "priority_num": node.get("priority", 0),
        "labels": labels,
        "project": project.get("name", ""),
        "comments": comments,
        "relations": relations,
        "created_at": node.get("createdAt", ""),
        "updated_at": node.get("updatedAt", ""),
        "url": node.get("url", ""),
    }
