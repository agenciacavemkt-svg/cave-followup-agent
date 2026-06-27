import os
from dotenv import load_dotenv

load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN", "").strip()
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID", "").strip().replace("-", "")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
TIMEZONE = os.getenv("TZ", "America/Sao_Paulo").strip() or "America/Sao_Paulo"

# Follow-up principal
FOLLOWUP_DAYS = int(os.getenv("FOLLOWUP_DAYS", "2"))
FOLLOWUP_MAX_LEADS = int(os.getenv("FOLLOWUP_MAX_LEADS", "20"))

# Status/etapas que entram na lista de pessoas para falar hoje.
FOLLOWUP_INCLUDE_STATUSES = [
    s.strip() for s in os.getenv(
        "FOLLOWUP_INCLUDE_STATUSES",
        "Interação Amigável 1,Interação Amigável 2"
    ).split(",")
    if s.strip()
]

# Status/etapas ignoradas no follow-up e nos alertas de ação.
FOLLOWUP_IGNORE_STATUSES = [
    s.strip() for s in os.getenv(
        "FOLLOWUP_IGNORE_STATUSES",
        "Novo lead,Off,Venda Realizada,Na Reserva,Enviado ao CRM,Descartado"
    ).split(",")
    if s.strip()
]

# Por padrão, lead sem data não entra na lista de contato, mas aparece no painel de atenção.
FOLLOWUP_INCLUDE_EMPTY_DATES = os.getenv("FOLLOWUP_INCLUDE_EMPTY_DATES", "false").strip().lower() in ["1", "true", "sim", "yes"]

# Painel comercial diário - Fase 1
SUMMARY_STALE_DAYS = int(os.getenv("SUMMARY_STALE_DAYS", "7"))
SUMMARY_REACTIVATION_SOON_DAYS = int(os.getenv("SUMMARY_REACTIVATION_SOON_DAYS", "10"))
SUMMARY_REACTIVATION_DAYS = int(os.getenv("SUMMARY_REACTIVATION_DAYS", "15"))
