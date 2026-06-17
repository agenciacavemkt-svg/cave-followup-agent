import time
from typing import Dict, List, Optional, Tuple
import requests

from config import NOTION_TOKEN, NOTION_DATABASE_ID
from utils import normalize_key, clean_text

NOTION_VERSION = "2022-06-28"
NOTION_BASE = "https://api.notion.com/v1"


def notion_headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def validar_conexao() -> Dict:
    if not NOTION_TOKEN:
        raise RuntimeError("NOTION_TOKEN vazio.")
    if not NOTION_DATABASE_ID:
        raise RuntimeError("NOTION_DATABASE_ID vazio.")

    r = requests.get(
        f"{NOTION_BASE}/databases/{NOTION_DATABASE_ID}",
        headers=notion_headers(),
        timeout=30,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Notion erro {r.status_code}: {r.text[:600]}")
    return r.json()


def get_schema() -> Dict:
    db = validar_conexao()
    return db.get("properties", {})


def find_property(schema: Dict, candidates: List[str], allowed_types: Optional[List[str]] = None) -> Optional[Tuple[str, str]]:
    for name in candidates:
        if name in schema:
            ptype = schema[name].get("type")
            if allowed_types is None or ptype in allowed_types:
                return name, ptype

    norm_candidates = {normalize_key(c): c for c in candidates}
    for prop_name, meta in schema.items():
        if normalize_key(prop_name) in norm_candidates:
            ptype = meta.get("type")
            if allowed_types is None or ptype in allowed_types:
                return prop_name, ptype

    if allowed_types and "title" in allowed_types:
        for prop_name, meta in schema.items():
            if meta.get("type") == "title":
                return prop_name, "title"

    return None


def prop_to_text(prop: Dict) -> str:
    if not prop:
        return ""
    ptype = prop.get("type")
    if ptype == "title":
        return "".join([x.get("plain_text", "") for x in prop.get("title", [])]).strip()
    if ptype == "rich_text":
        return "".join([x.get("plain_text", "") for x in prop.get("rich_text", [])]).strip()
    if ptype == "url":
        url = clean_text(prop.get("url"))
        if "instagram.com/" in url:
            handle = url.split("instagram.com/", 1)[1].split("/", 1)[0]
            return "@" + handle.lstrip("@") if handle else url
        return url
    if ptype == "phone_number":
        return clean_text(prop.get("phone_number"))
    if ptype == "email":
        return clean_text(prop.get("email"))
    if ptype == "select":
        return clean_text((prop.get("select") or {}).get("name"))
    if ptype == "multi_select":
        return ", ".join([x.get("name", "") for x in prop.get("multi_select", [])]).strip()
    if ptype == "number":
        val = prop.get("number")
        return "" if val is None else str(val)
    if ptype == "date":
        date = prop.get("date") or {}
        return clean_text(date.get("start"))
    if ptype == "checkbox":
        return "true" if prop.get("checkbox") else "false"
    return ""


def query_database(page_size: int = 100):
    cursor = None
    while True:
        payload = {"page_size": page_size}
        if cursor:
            payload["start_cursor"] = cursor

        r = requests.post(
            f"{NOTION_BASE}/databases/{NOTION_DATABASE_ID}/query",
            headers=notion_headers(),
            json=payload,
            timeout=30,
        )
        if r.status_code != 200:
            raise RuntimeError(f"Erro lendo Notion {r.status_code}: {r.text[:600]}")

        resp = r.json()
        for page in resp.get("results", []):
            yield page

        if not resp.get("has_more"):
            break
        cursor = resp.get("next_cursor")
        time.sleep(0.2)
