import os
import time
import schedule
from datetime import datetime
from zoneinfo import ZoneInfo

from config import TIMEZONE
from followup_agent import rodar_followup, enviar_telegram

os.environ["TZ"] = TIMEZONE
try:
    time.tzset()
except AttributeError:
    pass


def job():
    agora = datetime.now(ZoneInfo(TIMEZONE))
    try:
        print(f"▶️ Rodando follow-up em {agora.strftime('%d/%m/%Y %H:%M')}")
        rodar_followup()
    except Exception as e:
        erro = f"❌ Erro no Cave Follow-up Agent: {e}"
        print(erro)
        enviar_telegram(erro)


# Roda todos os dias às 08:30 no horário configurado.
schedule.every().day.at("08:30").do(job)

print(f"🕐 Scheduler ativo — todos os dias às 08:30 ({TIMEZONE}).")
print("Para testar agora, rode: python followup_agent.py")

while True:
    schedule.run_pending()
    time.sleep(30)
