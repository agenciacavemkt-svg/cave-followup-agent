import os
from dotenv import load_dotenv

load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN", "").strip()
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID", "").strip().replace("-", "")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
TIMEZONE = os.getenv("TZ", "America/Sao_Paulo").strip() or "America/Sao_Paulo"

# Regra principal do follow-up
FOLLOWUP_DAYS = int(os.getenv("FOLLOWUP_DAYS", "5"))
FOLLOWUP_MAX_LEADS = int(os.getenv("FOLLOWUP_MAX_LEADS", "40"))

# Status/etapas que nunca devem entrar no relatório
FOLLOWUP_IGNORE_STATUSES = [
    s.strip() for s in os.getenv(
        "FOLLOWUP_IGNORE_STATUSES",
        "Off,Venda Realizada"
    ).split(",")
    if s.strip()
]
