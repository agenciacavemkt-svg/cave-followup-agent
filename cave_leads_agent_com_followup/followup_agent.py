import os
import time
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Dict, List, Optional, Tuple

from config import (
    NOTION_TOKEN,
    NOTION_DATABASE_ID,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    TIMEZONE,
    FOLLOWUP_DAYS,
    FOLLOWUP_MAX_LEADS,
    FOLLOWUP_IGNORE_STATUSES,
)
from notion_sync import get_schema, notion_headers, find_property, prop_to_text
from utils import normalize_key, clean_text

NOTION_BASE = "https://api.notion.com/v1"


def enviar_telegram_followup(mensagem: str) -> bool:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Telegram não configurado. Pulei envio da mensagem.")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensagem,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    try:
        r = requests.post(url, json=payload, timeout=20)
        if r.status_code != 200:
            print(f"⚠️ Erro Telegram follow-up: {r.status_code} {r.text[:500]}")
            return False
        print("✅ Relatório de follow-up enviado no Telegram.")
        return True
    except Exception as erro:
        print(f"⚠️ Falha ao enviar Telegram follow-up: {erro}")
        return False


def _parse_date(value: str):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value[:10]).date()
    except Exception:
        return None


def _dias_sem_contato(data_texto: str) -> Optional[int]:
    data = _parse_date(data_texto)
    if not data:
        return None
    hoje = datetime.now(ZoneInfo(TIMEZONE)).date()
    return (hoje - data).days


def _status_ignorado(status: str) -> bool:
    status_norm = normalize_key(status)
    ignorados = [normalize_key(s) for s in FOLLOWUP_IGNORE_STATUSES]
    return status_norm in ignorados


def ler_leads_para_followup() -> List[Dict]:
    if not NOTION_TOKEN:
        raise RuntimeError("NOTION_TOKEN vazio.")
    if not NOTION_DATABASE_ID:
        raise RuntimeError("NOTION_DATABASE_ID vazio.")

    schema = get_schema(NOTION_TOKEN, NOTION_DATABASE_ID)
    print("✅ Conexão com Notion OK para follow-up")

    nome_prop = find_property(schema, ["Nome Empresa", "Nome Contato", "Nome", "Name"], ["title"])
    instagram_prop = find_property(schema, ["Instagram da Empresa", "Instagram", "@Instagram", "IG"], ["rich_text", "url"])
    status_prop = find_property(schema, ["Status/Etapa", "Status", "Etapa"], ["select", "multi_select", "rich_text"])
    ultimo_prop = find_property(schema, ["Data do Último Contato", "Data do ultimo contato", "Data do último contato", "Último contato", "Data Último Contato"], ["date"])
    proxima_prop = find_property(schema, ["Próxima Ação", "Proxima Acao", "Próxima ação"], ["select", "multi_select", "rich_text"])
    potencial_prop = find_property(schema, ["Potencial"], ["select", "multi_select", "rich_text"])

    if not ultimo_prop:
        print("⚠️ Coluna de Data do Último Contato não encontrada. Vou considerar leads sem data como pendentes.")

    leads = []
    cursor = None

    while True:
        payload = {"page_size": 100}
        if cursor:
            payload["start_cursor"] = cursor

        r = requests.post(
            f"{NOTION_BASE}/databases/{NOTION_DATABASE_ID}/query",
            headers=notion_headers(NOTION_TOKEN),
            json=payload,
            timeout=30,
        )
        if r.status_code != 200:
            raise RuntimeError(f"Erro lendo Notion follow-up {r.status_code}: {r.text[:600]}")

        resp = r.json()
        for page in resp.get("results", []):
            props = page.get("properties", {})

            nome = prop_to_text(props.get(nome_prop[0])) if nome_prop else "Sem nome"
            instagram = prop_to_text(props.get(instagram_prop[0])) if instagram_prop else ""
            status = prop_to_text(props.get(status_prop[0])) if status_prop else ""
            ultimo = prop_to_text(props.get(ultimo_prop[0])) if ultimo_prop else ""
            proxima = prop_to_text(props.get(proxima_prop[0])) if proxima_prop else ""
            potencial = prop_to_text(props.get(potencial_prop[0])) if potencial_prop else ""

            if _status_ignorado(status):
                continue

            dias = _dias_sem_contato(ultimo)

            # Regra: entra se passou do limite OU se não tem data registrada.
            if dias is None:
                deve_entrar = True
            else:
                deve_entrar = dias >= FOLLOWUP_DAYS

            if not deve_entrar:
                continue

            leads.append({
                "nome": nome,
                "instagram": instagram,
                "status": status or "Sem status",
                "ultimo_contato": ultimo or "Sem registro",
                "dias_sem_contato": dias,
                "proxima_acao": proxima or "Sem próxima ação",
                "potencial": potencial or "Sem potencial",
            })

        if not resp.get("has_more"):
            break
        cursor = resp.get("next_cursor")
        time.sleep(0.2)

    # Mais antigos primeiro; sem data fica no topo, porque precisa revisar.
    leads.sort(key=lambda x: (-1 if x["dias_sem_contato"] is None else -x["dias_sem_contato"]))
    return leads[:FOLLOWUP_MAX_LEADS]


def montar_mensagem_followup(leads: List[Dict]) -> str:
    agora = datetime.now(ZoneInfo(TIMEZONE)).strftime("%d/%m/%Y às %H:%M")

    linhas = [
        "📌 <b>Follow-up Comercial Cave</b>",
        f"Executado em: {agora}",
        f"Regra: último contato há {FOLLOWUP_DAYS}+ dias",
        "Ignorando: Off e Venda Realizada",
        "",
    ]

    if not leads:
        linhas.append("✅ Nenhum lead atrasado para follow-up hoje.")
        return "\n".join(linhas)

    linhas.append(f"⚠️ <b>{len(leads)} leads precisam de atenção</b>")
    linhas.append("")

    for i, lead in enumerate(leads, start=1):
        instagram = clean_text(lead.get("instagram")) or "Sem @"
        nome = clean_text(lead.get("nome")) or "Sem nome"
        ultimo = lead.get("ultimo_contato") or "Sem registro"
        dias = lead.get("dias_sem_contato")
        dias_txt = "sem data registrada" if dias is None else f"há {dias} dias"
        status = lead.get("status", "-")
        proxima = lead.get("proxima_acao", "-")
        potencial = lead.get("potencial", "-")

        linhas.append(
            f"{i}. <b>{nome}</b>\n"
            f"Instagram: {instagram}\n"
            f"Último contato: {ultimo} ({dias_txt})\n"
            f"Status: {status}\n"
            f"Potencial: {potencial}\n"
            f"Ação: {proxima}\n"
        )

    return "\n".join(linhas)


def rodar_followup():
    print("=" * 70)
    print("Cave Follow-up Agent — leitura CRM e aviso Telegram")
    print("=" * 70)
    leads = ler_leads_para_followup()
    print(f"📌 {len(leads)} leads encontrados para follow-up")
    mensagem = montar_mensagem_followup(leads)
    enviar_telegram_followup(mensagem)
    print("✅ Follow-up finalizado")
    return {"leads_followup": len(leads)}


if __name__ == "__main__":
    rodar_followup()
