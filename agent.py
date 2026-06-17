from datetime import datetime
from zoneinfo import ZoneInfo
import requests

from config import (
    NOTION_TOKEN,
    NOTION_DATABASE_ID,
    SERPER_KEY,
    GEMINI_API_KEY,
    TOP_LEADS,
    MIN_SCORE,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    TIMEZONE,
    PENDENTES_LIMITE,
)
from scraper import captar_leads
from qualifier import qualificar_leads
from notion_sync import (
    sincronizar,
    carregar_chaves_existentes,
    filtrar_leads_ineditos,
    contar_leads_pendentes,
)


def checar_variaveis():
    faltando = []
    if not SERPER_KEY:
        faltando.append("SERPER_KEY")
    if not GEMINI_API_KEY:
        print("⚠️ GEMINI_API_KEY vazia: o agente usará pontuação fallback.")
    if not NOTION_TOKEN:
        faltando.append("NOTION_TOKEN")
    if not NOTION_DATABASE_ID:
        faltando.append("NOTION_DATABASE_ID")
    if faltando:
        raise RuntimeError("Variáveis faltando no Railway: " + ", ".join(faltando))


def enviar_telegram(mensagem: str):
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
            print(f"⚠️ Erro Telegram: {r.status_code} {r.text[:500]}")
            return False
        print("✅ Resumo enviado no Telegram.")
        return True
    except Exception as erro:
        print(f"⚠️ Falha ao enviar Telegram: {erro}")
        return False


def montar_resumo_sem_captacao(pendentes: int):
    agora = datetime.now(ZoneInfo(TIMEZONE)).strftime("%d/%m/%Y às %H:%M")
    return "\n".join([
        "🚀 <b>Relatório Comercial Cave</b>",
        f"Executado em: {agora}",
        "",
        "⏸️ <b>Captação pausada hoje</b>",
        f"Motivo: já existem {pendentes} leads pendentes no CRM.",
        f"Limite configurado: {PENDENTES_LIMITE} pendentes.",
        "",
        "Ação sugerida: trabalhar os leads atuais antes de abastecer o CRM de novo."
    ])


def montar_resumo_telegram(leads_captados, qualificados, selecionados, resumo_notion, chaves_crm, pendentes_antes):
    agora = datetime.now(ZoneInfo(TIMEZONE)).strftime("%d/%m/%Y às %H:%M")

    linhas = [
        "🚀 <b>Relatório Comercial Cave</b>",
        f"Executado em: {agora}",
        "",
        f"Leads pendentes antes da busca: {pendentes_antes}",
        f"Chaves lidas no CRM antes da busca: {len(chaves_crm)}",
        f"Leads inéditos captados: {len(leads_captados)}",
        f"Leads aprovados acima do score mínimo ({MIN_SCORE}): {len(qualificados)}",
        f"Leads enviados ao Notion: {len(selecionados)}",
        "",
        f"Criados: {resumo_notion.get('criados', 0)}",
        f"Atualizados: {resumo_notion.get('atualizados', 0)}",
        f"Ignorados: {resumo_notion.get('ignorados', 0)}",
        f"Duplicados barrados na sincronização: {resumo_notion.get('duplicados', 0)}",
        "",
        "🔥 <b>Top leads do dia</b>",
    ]

    for i, lead in enumerate(selecionados[:10], start=1):
        nome = lead.get("nome", "Sem nome")
        score = lead.get("score", "-")
        potencial = lead.get("potencial", "-")
        cidade = lead.get("cidade") or lead.get("bairro") or "Sem cidade"
        ramo = lead.get("ramo", "-")
        analise = lead.get("analise", "")

        linhas.append(
            f"{i}. <b>{nome}</b>\n"
            f"Nota: {score} | Potencial: {potencial}\n"
            f"Cidade: {cidade}\n"
            f"Ramo: {ramo}\n"
            f"Análise: {analise[:220]}\n"
        )

    quentes = [l for l in selecionados if float(l.get("score", 0) or 0) >= 9 and l.get("potencial") == "Alto"]
    if quentes:
        linhas.append("\n🔥 <b>Alertas de lead quente</b>")
        for lead in quentes[:5]:
            linhas.append(f"• {lead.get('nome')} — {lead.get('score')} — {lead.get('bairro') or lead.get('cidade')}")

    return "\n".join(linhas)


def rodar_agente():
    print("=" * 70)
    print("Cave Leads Agent — captação e sincronização Notion")
    print("=" * 70)

    checar_variaveis()

    print("\nETAPA 0 — Leitura do CRM antes da pesquisa")
    pendentes_antes = contar_leads_pendentes(NOTION_TOKEN, NOTION_DATABASE_ID)

    if pendentes_antes >= PENDENTES_LIMITE:
        print(f"⏸️ Captação pausada: {pendentes_antes} leads pendentes >= limite {PENDENTES_LIMITE}.")
        enviar_telegram(montar_resumo_sem_captacao(pendentes_antes))
        resumo = {"criados": 0, "atualizados": 0, "ignorados": 0, "duplicados": 0, "pausado_por_pendentes": pendentes_antes}
        print("\n✅ Processo finalizado sem captação")
        print(resumo)
        return resumo

    chaves_crm = carregar_chaves_existentes(NOTION_TOKEN, NOTION_DATABASE_ID)

    print("\nETAPA 1 — Captação somente de leads inéditos")
    leads = captar_leads(chaves_bloqueadas=chaves_crm)

    # Segurança extra: caso algum repetido passe pela captação, barra antes da IA.
    leads = filtrar_leads_ineditos(leads, chaves_crm)

    print("\nETAPA 2 — Qualificação")
    qualificados_todos = qualificar_leads(leads)

    print("\nETAPA 3 — Seleção dos melhores")
    qualificados = [
        l for l in qualificados_todos
        if float(l.get("score", 0) or 0) >= MIN_SCORE
    ]
    qualificados.sort(key=lambda x: float(x.get("score", 0) or 0), reverse=True)
    selecionados = qualificados[:TOP_LEADS]
    print(f"🎯 {len(qualificados)} passaram no filtro mínimo {MIN_SCORE}. Enviando top {len(selecionados)} ao Notion.")

    for i, lead in enumerate(selecionados, start=1):
        print(f"   {i:02d}. {lead.get('nome')} | {lead.get('score')} {lead.get('potencial')} | {lead.get('bairro')} | {lead.get('fonte')}")

    print("\nETAPA 4 — Sincronização com Notion")
    resumo = sincronizar(NOTION_TOKEN, NOTION_DATABASE_ID, selecionados)

    print("\nETAPA 5 — Telegram")
    mensagem = montar_resumo_telegram(leads, qualificados, selecionados, resumo, chaves_crm, pendentes_antes)
    enviar_telegram(mensagem)

    print("\n✅ Processo finalizado")
    print(resumo)
    return resumo


if __name__ == "__main__":
    rodar_agente()
