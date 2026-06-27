# Cave Comercial Agent — Fase 1

Agente diário do comercial da Cave. Ele lê o CRM no Notion e envia no Telegram um resumo comercial + lista de leads para follow-up.

## O que esta versão faz

- Lê o CRM no Notion.
- Envia um painel diário no Telegram.
- Mostra quantos leads entraram ontem pela `Data de Entrada`.
- Mostra o pipeline atual por status principais.
- Mostra alertas:
  - leads parados há 7+ dias;
  - leads sem data de último contato;
  - leads perto de reativação;
  - respostas/sinais registrados no CRM.
- Lista até 20 leads para falar hoje.
- Foca em `Interação Amigável 1` e `Interação Amigável 2`.
- Prioriza `Interação Amigável 2`.
- Usa regra de 2+ dias sem contato.
- Ignora `Novo lead`, `Off`, `Venda Realizada`, `Na Reserva`, `Enviado ao CRM` e `Descartado`.
- Telegram em texto limpo, sem HTML.

## Variáveis obrigatórias no Railway

```txt
NOTION_TOKEN=seu_token_notion
NOTION_DATABASE_ID=id_do_database
TELEGRAM_BOT_TOKEN=token_do_bot
TELEGRAM_CHAT_ID=seu_chat_id
TZ=America/Sao_Paulo
```

## Variáveis opcionais

```txt
FOLLOWUP_DAYS=2
FOLLOWUP_MAX_LEADS=20
FOLLOWUP_INCLUDE_STATUSES=Interação Amigável 1,Interação Amigável 2
FOLLOWUP_IGNORE_STATUSES=Novo lead,Off,Venda Realizada,Na Reserva,Enviado ao CRM,Descartado
FOLLOWUP_INCLUDE_EMPTY_DATES=false
SUMMARY_STALE_DAYS=7
SUMMARY_REACTIVATION_SOON_DAYS=10
SUMMARY_REACTIVATION_DAYS=15
```

## Teste manual

```bash
python followup_agent.py
```

ou:

```bash
python agent.py
```

## Rodar automaticamente

O `Procfile` usa:

```txt
worker: python scheduler.py
```

O scheduler roda todos os dias às 08:30.

## Observação importante

Nesta Fase 1, o agente ainda não mede com precisão “quantos passaram para Interação 2 ontem”, porque isso exigiria uma coluna de data/histórico da mudança de etapa. Ele mostra o pipeline atual e os alertas com base nas colunas já existentes.
