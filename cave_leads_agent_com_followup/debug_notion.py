import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

token = os.getenv("NOTION_TOKEN", "").strip()
db_id = os.getenv("NOTION_DATABASE_ID", "").strip().replace("-", "")
headers = {
    "Authorization": f"Bearer {token}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

print("TOKEN:", "OK" if token else "VAZIO")
print("DATABASE:", db_id or "VAZIO")

r = requests.get(f"https://api.notion.com/v1/users/me", headers=headers)
print("USERS/ME:", r.status_code, r.text[:300])

r = requests.get(f"https://api.notion.com/v1/databases/{db_id}", headers=headers)
print("DATABASE GET:", r.status_code)
print(r.text[:1000])

if r.status_code == 200:
    data = r.json()
    print("\nCOLUNAS:")
    print(json.dumps({k: v.get("type") for k, v in data.get("properties", {}).items()}, ensure_ascii=False, indent=2))
