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
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def fetch_issue(identifier: str, api_key: str) -> dict | None:
    """Fetch a single issue by identifier (e.g. 'ABC-123')."""
    query = """
    query($id: String!) {
        issue(id: $id) { %s }
    }
    """ % ISSUE_FIELDS
    try:
        data = _graphql(query, {"id": identifier}, api_key)
        node = data.get("data", {}).get("issue")
        if node:
            return _normalize(node)
    except Exception:
        pass
    # Fallback to search if direct lookup fails
    return _fetch_issue_by_search(identifier, api_key)


def _fetch_issue_by_search(identifier: str, api_key: str) -> dict | None:
    """Fallback: fetch issue via search."""
    query = """
    query($term: String!) {
        searchIssues(term: $term, first: 1) {
            nodes { %s }
        }
    }
    """ % ISSUE_FIELDS
    try:
        data = _graphql(query, {"term": identifier}, api_key)
        nodes = data.get("data", {}).get("searchIssues", {}).get("nodes", [])
        for n in nodes:
            if n.get("identifier", "").upper() == identifier.upper():
                return _normalize(n)
    except Exception:
        pass
    return None


def fetch_issues(identifiers: list[str], api_key: str) -> dict[str, dict]:
    """Batch-fetch multiple issues. Returns {identifier: issue_data}."""
    if not identifiers:
        return {}

    # Try batch via filter first (much faster for many keys)
    result = _fetch_issues_batch(identifiers, api_key)

    # Fallback: fetch missing ones individually
    missing = [k for k in identifiers if k not in result]
    for key in missing:
        issue = fetch_issue(key, api_key)
        if issue:
            result[issue["identifier"]] = issue

    return result


def _fetch_issues_batch(identifiers: list[str], api_key: str) -> dict[str, dict]:
    """Fetch issues in batches using filter query."""
    result: dict[str, dict] = {}
    # Process in chunks of 50
    for i in range(0, len(identifiers), 50):
        chunk = identifiers[i:i + 50]
        # Use issueSearch with filter by identifier
        query = """
        query($filter: IssueFilter, $first: Int) {
            issues(filter: $filter, first: $first) {
                nodes { %s }
            }
        }
        """ % ISSUE_FIELDS
        # Build OR filter for identifiers
        id_filters = [{"identifier": {"eq": k}} for k in chunk]
        variables = {
            "filter": {"or": id_filters},
            "first": len(chunk),
        }
        try:
            data = _graphql(query, variables, api_key)
            nodes = data.get("data", {}).get("issues", {}).get("nodes", [])
            for n in nodes:
                normalized = _normalize(n)
                result[normalized["identifier"]] = normalized
        except Exception:
            pass
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
