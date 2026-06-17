import os
import time
import schedule
from datetime import datetime
from zoneinfo import ZoneInfo

from config import TIMEZONE
from agent import rodar_agente, enviar_telegram
from followup_agent import rodar_followup, enviar_telegram_followup

os.environ["TZ"] = TIMEZONE
try:
    time.tzset()
except AttributeError:
    pass


def job_captacao():
    agora = datetime.now(ZoneInfo(TIMEZONE))
    # 1=terça, 3=quinta
    if agora.weekday() not in (1, 3):
        print("Hoje não é terça nem quinta. Agente de captação não roda.")
        return
    try:
        rodar_agente()
    except Exception as e:
        erro = f"❌ Erro no Cave Leads Agent: {e}"
        print(erro)
        enviar_telegram(erro)


def job_followup():
    try:
        rodar_followup()
    except Exception as e:
        erro = f"❌ Erro no Cave Follow-up Agent: {e}"
        print(erro)
        enviar_telegram_followup(erro)


# Captação: terça e quinta às 08:00
schedule.every().tuesday.at("08:00").do(job_captacao)
schedule.every().thursday.at("08:00").do(job_captacao)

# Follow-up: todos os dias às 08:30
schedule.every().day.at("08:30").do(job_followup)

print(f"🕐 Scheduler ativo — captação terças/quintas às 08:00 e follow-up diário às 08:30 ({TIMEZONE}).")
print("Para testar captação agora: python agent.py")
print("Para testar follow-up agora: python followup_agent.py")

while True:
    schedule.run_pending()
    time.sleep(30)
