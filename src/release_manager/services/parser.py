import re

LINEAR_KEY_RE = re.compile(r"\b([A-Za-z]+-\d+)\b")
LINEAR_KEY_NO_DASH_RE = re.compile(r"\b([A-Z][A-Za-z]{1,7})\s+(\d+)\b")

BLACKLIST_PREFIXES = {
    "MACOS", "HTTP", "UTF", "SHA", "SSL", "TCP", "UDP", "DNS",
    "URL", "SSH", "GPG", "NPM", "NODE", "ARM", "AMD", "WPS",
    "PEP", "RFC", "CVE", "ISO", "RELEASE", "ADD", "UBUNTU",
}


def extract_linear_keys(text: str) -> list[str]:
    """Extract Linear issue keys from text, normalized to uppercase, deduplicated.

    Matches both 'PLCORE-978' and 'Plcore 978' (without dash) formats.
    """
    seen: set[str] = set()
    result: list[str] = []

    # Standard format: PLCORE-978
    for match in LINEAR_KEY_RE.findall(text):
        key = match.upper()
        prefix = key.split("-")[0]
        if prefix in BLACKLIST_PREFIXES:
            continue
        if key not in seen:
            seen.add(key)
            result.append(key)

    # No-dash format: Plcore 978 → PLCORE-978
    for prefix, num in LINEAR_KEY_NO_DASH_RE.findall(text):
        p = prefix.upper()
        if len(p) < 2:
            continue
        if p in BLACKLIST_PREFIXES:
            continue
        key = f"{p}-{num}"
        if key not in seen:
            seen.add(key)
            result.append(key)

    return result
