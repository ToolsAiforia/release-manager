import re

LINEAR_KEY_RE = re.compile(r"\b([A-Za-z]+-\d+)\b")


def extract_linear_keys(text: str) -> list[str]:
    """Extract Linear issue keys from text, normalized to uppercase, deduplicated."""
    matches = LINEAR_KEY_RE.findall(text)
    seen: set[str] = set()
    result: list[str] = []
    for match in matches:
        key = match.upper()
        if key not in seen:
            seen.add(key)
            result.append(key)
    return result
