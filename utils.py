import re
import unicodedata
from typing import Any, Dict, Optional


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def normalize_key(value: Any) -> str:
    text = clean_text(value).lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^a-z0-9@._/-]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def extract_instagram(text: str) -> str:
    if not text:
        return ""
    patterns = [
        r"instagram\.com/([A-Za-z0-9._]+)",
        r"@([A-Za-z0-9._]{3,40})",
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            handle = m.group(1).strip("./ ")
            if handle and handle.lower() not in {"p", "reel", "stories", "explore"}:
                return "@" + handle.lstrip("@")
    return ""


def extract_phone(text: str) -> str:
    if not text:
        return ""
    m = re.search(r"(?:\+55\s?)?(?:\(?\d{2}\)?\s?)?(?:9\d{4}|\d{4})[-\s]?\d{4}", text)
    return m.group(0).strip() if m else ""


def unique_by_name_or_link(leads):
    seen = set()
    result = []
    for lead in leads:
        key = normalize_key(lead.get("instagram") or lead.get("website") or lead.get("linkedin") or lead.get("nome"))
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(lead)
    return result


def safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default
