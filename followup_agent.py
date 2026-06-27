import requests
from collections import Counter
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Dict, List, Optional, Tuple

from config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    TIMEZONE,
    FOLLOWUP_DAYS,
    FOLLOWUP_MAX_LEADS,
    FOLLOWUP_IGNORE_STATUSES,
    FOLLOWUP_INCLUDE_STATUSES,
    FOLLOWUP_INCLUDE_EMPTY_DATES,
    SUMMARY_STALE_DAYS,
    SUMMARY_REACTIVATION_SOON_DAYS,
    SUMMARY_REACTIVATION_DAYS,
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


def _hoje():
    return datetime.now(ZoneInfo(TIMEZONE)).date()


def _dias_desde(data_texto: str) -> Optional[int]:
    data = _parse_date(data_texto)
    if not data:
        return None
    return (_hoje() - data).days


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


def _pegar_props_schema(schema: Dict) -> Dict[str, Optional[Tuple[str, str]]]:
    return {
        "nome": find_property(schema, ["Nome Empresa", "Nome Contato", "Nome", "Name"], ["title"]),
        "instagram": find_property(schema, ["Instagram da Empresa", "Instagram", "@Instagram", "IG"], ["rich_text", "url"]),
        "status": find_property(schema, ["Status/Etapa", "Status", "Etapa"], ["select", "multi_select", "rich_text"]),
        "ultimo": find_property(schema, ["Data do Último Contato", "Data do ultimo contato", "Data do último contato", "Último contato", "Data Último Contato"], ["date"]),
        "entrada": find_property(schema, ["Data de Entrada", "Data Entrada", "Criado em"], ["date"]),
        "proxima": find_property(schema, ["Próxima Ação", "Proxima Acao", "Próxima ação"], ["select", "multi_select", "rich_text"]),
        "potencial": find_property(schema, ["Potencial"], ["select", "multi_select", "rich_text"]),
        "resultado": find_property(schema, ["Resultado", "Resposta", "Status da Resposta"], ["select", "multi_select", "rich_text", "checkbox"]),
    }


def _texto_prop(props: Dict, found: Optional[Tuple[str, str]]) -> str:
    return prop_to_text(props.get(found[0])) if found else ""


def ler_crm_completo() -> List[Dict]:
    schema = get_schema()
    print("✅ Conexão com Notion OK para Agente Comercial")
    refs = _pegar_props_schema(schema)

    if not refs.get("ultimo"):
        print("⚠️ Coluna de Data do Último Contato não encontrada.")

    leads = []
    for page in query_database():
        props = page.get("properties", {})

        ultimo = _texto_prop(props, refs.get("ultimo"))
        entrada = _texto_prop(props, refs.get("entrada"))
        status = _texto_prop(props, refs.get("status"))
        resultado = _texto_prop(props, refs.get("resultado"))

        lead = {
            "page_id": page.get("id"),
            "nome": _texto_prop(props, refs.get("nome")) or "Sem nome",
            "instagram": _texto_prop(props, refs.get("instagram")),
            "status": status or "Sem status",
            "ultimo_contato": ultimo or "",
            "dias_sem_contato": _dias_desde(ultimo),
            "data_entrada": entrada or "",
            "proxima_acao": _texto_prop(props, refs.get("proxima")) or "Sem próxima ação",
            "potencial": _texto_prop(props, refs.get("potencial")) or "Sem potencial",
            "resultado": resultado or "",
        }
        leads.append(lead)

    return leads


def _prioridade_status(status: str) -> int:
    prioridade = {
        normalize_key("Interação Amigável 2"): 0,
        normalize_key("Interação Amigável 1"): 1,
    }
    return prioridade.get(normalize_key(status), 99)


def selecionar_leads_para_followup(leads: List[Dict]) -> List[Dict]:
    selecionados = []
    for lead in leads:
        status = lead.get("status", "")
        if _status_ignorado(status):
            continue
        if not _status_incluido(status):
            continue

        dias = lead.get("dias_sem_contato")
        if dias is None:
            if not FOLLOWUP_INCLUDE_EMPTY_DATES:
                continue
        elif dias < FOLLOWUP_DAYS:
            continue

        selecionados.append(lead)

    selecionados.sort(
        key=lambda x: (
            _prioridade_status(x.get("status")),
            -(x.get("dias_sem_contato") or 0),
        )
    )
    return selecionados[:FOLLOWUP_MAX_LEADS]


def calcular_resumo_comercial(leads: List[Dict]) -> Dict:
    hoje = _hoje()
    ontem = hoje - timedelta(days=1)

    status_counts = Counter(clean_text(l.get("status")) or "Sem status" for l in leads)

    entraram_ontem = [l for l in leads if _parse_date(l.get("data_entrada", "")) == ontem]

    leads_followup_base = [
        l for l in leads
        if (not _status_ignorado(l.get("status", ""))) and _status_incluido(l.get("status", ""))
    ]

    parados_7 = [
        l for l in leads_followup_base
        if l.get("dias_sem_contato") is not None and l.get("dias_sem_contato") >= SUMMARY_STALE_DAYS
    ]

    sem_data = [
        l for l in leads_followup_base
        if l.get("dias_sem_contato") is None
    ]

    perto_reativacao = [
        l for l in leads_followup_base
        if l.get("dias_sem_contato") is not None
        and SUMMARY_REACTIVATION_SOON_DAYS <= l.get("dias_sem_contato") < SUMMARY_REACTIVATION_DAYS
    ]

    responderam_sinalizados = [
        l for l in leads
        if any(
            termo in normalize_key(" ".join([l.get("status", ""), l.get("resultado", ""), l.get("proxima_acao", "")]))
            for termo in ["respondeu", "resposta", "retornou", "interessado", "chamou"]
        )
    ]

    return {
        "entraram_ontem": len(entraram_ontem),
        "status_counts": status_counts,
        "interacao_1": status_counts.get("Interação Amigável 1", 0),
        "interacao_2": status_counts.get("Interação Amigável 2", 0),
        "novo_lead": status_counts.get("Novo lead", 0) + status_counts.get("Novo Lead", 0),
        "venda_realizada": status_counts.get("Venda Realizada", 0),
        "off": status_counts.get("Off", 0),
        "parados_7": len(parados_7),
        "sem_data": len(sem_data),
        "perto_reativacao": len(perto_reativacao),
        "responderam_sinalizados": len(responderam_sinalizados),
    }


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


def montar_mensagem_comercial(leads_followup: List[Dict], resumo: Dict) -> str:
    agora = datetime.now(ZoneInfo(TIMEZONE)).strftime("%d/%m/%Y às %H:%M")

    total_interacao_2_hoje = len([
        l for l in leads_followup
        if normalize_key(l.get("status")) == normalize_key("Interação Amigável 2")
    ])
    total_interacao_1_hoje = len([
        l for l in leads_followup
        if normalize_key(l.get("status")) == normalize_key("Interação Amigável 1")
    ])

    linhas = [
        "📊 Comercial Cave | Resumo Diário",
        f"Executado em: {agora}",
        "",
        "📥 Entrada",
        f"Novos leads adicionados ontem: {resumo['entraram_ontem']}",
        "",
        "🔥 Pipeline atual",
        f"Novo lead: {resumo['novo_lead']}",
        f"Interação Amigável 1: {resumo['interacao_1']}",
        f"Interação Amigável 2: {resumo['interacao_2']}",
        f"Venda Realizada: {resumo['venda_realizada']}",
        f"Off: {resumo['off']}",
        "",
        "⚠️ Atenção",
        f"Leads parados há {SUMMARY_STALE_DAYS}+ dias: {resumo['parados_7']}",
        f"Leads sem data de último contato: {resumo['sem_data']}",
        f"Perto de reativação ({SUMMARY_REACTIVATION_SOON_DAYS} a {SUMMARY_REACTIVATION_DAYS - 1} dias): {resumo['perto_reativacao']}",
        f"Respostas/sinais registrados no CRM: {resumo['responderam_sinalizados']}",
        "",
        "🔥 Para falar hoje",
        f"Regra: último contato há {FOLLOWUP_DAYS}+ dias",
        f"Limite: até {FOLLOWUP_MAX_LEADS} leads",
        f"Interação Amigável 2: {total_interacao_2_hoje}",
        f"Interação Amigável 1: {total_interacao_1_hoje}",
        "",
    ]

    if not leads_followup:
        linhas.append("✅ Nenhum lead atrasado para follow-up hoje.")
        return "\n".join(linhas)

    grupos = [
        ("🔥 Prioridade 1 — Interação Amigável 2", [l for l in leads_followup if normalize_key(l.get("status")) == normalize_key("Interação Amigável 2")]),
        ("🟡 Prioridade 2 — Interação Amigável 1", [l for l in leads_followup if normalize_key(l.get("status")) == normalize_key("Interação Amigável 1")]),
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
        l for l in leads_followup
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
    print("Cave Comercial Agent — resumo diário + follow-up")
    print("=" * 70)

    leads = ler_crm_completo()
    resumo = calcular_resumo_comercial(leads)
    leads_followup = selecionar_leads_para_followup(leads)
    print(f"📊 {len(leads)} leads lidos no CRM")
    print(f"📌 {len(leads_followup)} leads encontrados para follow-up")

    mensagem = montar_mensagem_comercial(leads_followup, resumo)
    enviar_telegram(mensagem)

    print("✅ Agente Comercial finalizado")
    return {"leads_lidos": len(leads), "leads_followup": len(leads_followup), **resumo}


if __name__ == "__main__":
    rodar_followup()
