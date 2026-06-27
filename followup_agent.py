import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict, List, Optional

from config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    TIMEZONE,
    FOLLOWUP_DAYS,
    FOLLOWUP_MAX_LEADS,
    FOLLOWUP_IGNORE_STATUSES,
    FOLLOWUP_INCLUDE_STATUSES,
    FOLLOWUP_INCLUDE_EMPTY_DATES,
)
from notion_reader import get_schema, find_property, prop_to_text, query_database
from utils import normalize_key, clean_text

TELEGRAM_LIMIT = 3500  # margem segura abaixo do limite oficial de 4096 caracteres


def enviar_telegram(mensagem: str) -> bool:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Telegram não configurado. Pulei envio da mensagem.")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    partes = [mensagem[i:i + TELEGRAM_LIMIT] for i in range(0, len(mensagem), TELEGRAM_LIMIT)] or [mensagem]
    sucesso = True

    for idx, parte in enumerate(partes, start=1):
        if len(partes) > 1:
            parte = f"Parte {idx}/{len(partes)}\n\n" + parte

        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": parte,
            "disable_web_page_preview": True,
        }

        try:
            r = requests.post(url, json=payload, timeout=20)
            if r.status_code != 200:
                print(f"⚠️ Erro Telegram follow-up: {r.status_code} {r.text[:500]}")
                sucesso = False
            else:
                print(f"✅ Telegram enviado ({idx}/{len(partes)}).")
        except Exception as erro:
            print(f"⚠️ Falha ao enviar Telegram follow-up: {erro}")
            sucesso = False

    return sucesso


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


def _status_incluido(status: str) -> bool:
    status_norm = normalize_key(status)
    incluidos = [normalize_key(s) for s in FOLLOWUP_INCLUDE_STATUSES]
    return status_norm in incluidos


def _formatar_data_br(data_iso: str) -> str:
    data = _parse_date(data_iso)
    if not data:
        return "Sem registro"
    return data.strftime("%d/%m/%Y")


def ler_leads_para_followup() -> List[Dict]:
    schema = get_schema()
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

    for page in query_database():
        props = page.get("properties", {})

        nome = prop_to_text(props.get(nome_prop[0])) if nome_prop else "Sem nome"
        instagram = prop_to_text(props.get(instagram_prop[0])) if instagram_prop else ""
        status = prop_to_text(props.get(status_prop[0])) if status_prop else ""
        ultimo = prop_to_text(props.get(ultimo_prop[0])) if ultimo_prop else ""
        proxima = prop_to_text(props.get(proxima_prop[0])) if proxima_prop else ""
        potencial = prop_to_text(props.get(potencial_prop[0])) if potencial_prop else ""

        if _status_ignorado(status):
            continue

        # O agente de follow-up deve focar apenas nas etapas comerciais configuradas.
        # Por padrão, somente "Interação Amigável 1" entra no relatório.
        if not _status_incluido(status):
            continue

        dias = _dias_sem_contato(ultimo)
        # Por padrão, follow-up só entra quando já existe data de último contato.
        # Se FOLLOWUP_INCLUDE_EMPTY_DATES=true, leads sem data entram para organização.
        if dias is None:
            if not FOLLOWUP_INCLUDE_EMPTY_DATES:
                continue
        elif dias < FOLLOWUP_DAYS:
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

    # Prioriza Interação Amigável 2, depois Interação Amigável 1, e dentro de cada grupo os mais atrasados.
    prioridade_status = {
        normalize_key("Interação Amigável 2"): 0,
        normalize_key("Interação Amigável 1"): 1,
    }
    leads.sort(
        key=lambda x: (
            prioridade_status.get(normalize_key(x.get("status")), 99),
            -(x.get("dias_sem_contato") or 0),
        )
    )
    return leads[:FOLLOWUP_MAX_LEADS]


def _linha_lead(i: int, lead: Dict) -> str:
    instagram = clean_text(lead.get("instagram")) or "Sem @"
    nome = clean_text(lead.get("nome")) or "Sem nome"
    ultimo = _formatar_data_br(lead.get("ultimo_contato", ""))
    dias = lead.get("dias_sem_contato")
    dias_txt = "sem data" if dias is None else f"{dias} dias"
    status = lead.get("status", "-")
    proxima = lead.get("proxima_acao", "-")

    return (
        f"{i}. {instagram} — {nome}\n"
        f"Último contato: {ultimo} ({dias_txt})\n"
        f"Status: {status}\n"
        f"Próxima ação: {proxima}\n"
    )


def montar_mensagem_followup(leads: List[Dict]) -> str:
    agora = datetime.now(ZoneInfo(TIMEZONE)).strftime("%d/%m/%Y às %H:%M")

    total_interacao_2 = len([l for l in leads if normalize_key(l.get("status")) == normalize_key("Interação Amigável 2")])
    total_interacao_1 = len([l for l in leads if normalize_key(l.get("status")) == normalize_key("Interação Amigável 1")])

    linhas = [
        "📌 Follow-up Comercial Cave",
        f"Executado em: {agora}",
        f"Regra: último contato há {FOLLOWUP_DAYS}+ dias",
        f"Limite do dia: até {FOLLOWUP_MAX_LEADS} leads",
        f"Focando em: {', '.join(FOLLOWUP_INCLUDE_STATUSES)}",
        f"Ignorando: {', '.join(FOLLOWUP_IGNORE_STATUSES)}",
        "",
    ]

    if not leads:
        linhas.append("✅ Nenhum lead atrasado para follow-up hoje.")
        return "\n".join(linhas)

    linhas.extend([
        f"⚠️ {len(leads)} leads precisam de atenção hoje",
        f"🔥 Interação Amigável 2: {total_interacao_2}",
        f"🟡 Interação Amigável 1: {total_interacao_1}",
        "",
    ])

    grupos = [
        ("🔥 Prioridade 1 — Interação Amigável 2", [l for l in leads if normalize_key(l.get("status")) == normalize_key("Interação Amigável 2")]),
        ("🟡 Prioridade 2 — Interação Amigável 1", [l for l in leads if normalize_key(l.get("status")) == normalize_key("Interação Amigável 1")]),
    ]

    contador = 1
    for titulo, grupo in grupos:
        if not grupo:
            continue
        linhas.append(titulo)
        linhas.append("")
        for lead in grupo:
            linhas.append(_linha_lead(contador, lead))
            contador += 1
        linhas.append("--------------------")
        linhas.append("")

    outros = [
        l for l in leads
        if normalize_key(l.get("status")) not in [
            normalize_key("Interação Amigável 1"),
            normalize_key("Interação Amigável 2"),
        ]
    ]
    if outros:
        linhas.append("📎 Outros status incluídos")
        linhas.append("")
        for lead in outros:
            linhas.append(_linha_lead(contador, lead))
            contador += 1

    return "\n".join(linhas).strip()


def rodar_followup():
    print("=" * 70)
    print("Cave Follow-up Agent — leitura CRM e aviso Telegram")
    print("=" * 70)

    leads = ler_leads_para_followup()
    print(f"📌 {len(leads)} leads encontrados para follow-up")

    mensagem = montar_mensagem_followup(leads)
    enviar_telegram(mensagem)

    print("✅ Follow-up finalizado")
    return {"leads_followup": len(leads)}


if __name__ == "__main__":
    rodar_followup()
