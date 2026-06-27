import os
from dotenv import load_dotenv

load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN", "").strip()
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID", "").strip().replace("-", "")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
TIMEZONE = os.getenv("TZ", "America/Sao_Paulo").strip() or "America/Sao_Paulo"

# Regra principal do follow-up
# Novo padrão: manter constância maior, avisando a partir de 2 dias sem contato.
FOLLOWUP_DAYS = int(os.getenv("FOLLOWUP_DAYS", "2"))
FOLLOWUP_MAX_LEADS = int(os.getenv("FOLLOWUP_MAX_LEADS", "20"))

# Status/etapas que devem entrar no relatório.
# Padrão: Interação Amigável 1 e Interação Amigável 2.
FOLLOWUP_INCLUDE_STATUSES = [
    s.strip() for s in os.getenv(
        "FOLLOWUP_INCLUDE_STATUSES",
        "Interação Amigável 1,Interação Amigável 2"
    ).split(",")
    if s.strip()
]

# Status/etapas que nunca devem entrar no relatório, mesmo que sejam incluídos por engano.
FOLLOWUP_IGNORE_STATUSES = [
    s.strip() for s in os.getenv(
        "FOLLOWUP_IGNORE_STATUSES",
        "Novo lead,Off,Venda Realizada,Na Reserva,Enviado ao CRM,Descartado"
    ).split(",")
    if s.strip()
]

# Lead sem data de último contato não entra no relatório por padrão.
FOLLOWUP_INCLUDE_EMPTY_DATES = os.getenv("FOLLOWUP_INCLUDE_EMPTY_DATES", "false").strip().lower() in ["1", "true", "sim", "yes"]
