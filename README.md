# Cave Follow-up Agent — Interação Amigável 1 e 2

Agente de follow-up comercial da Cave. Ele lê o CRM no Notion e envia no Telegram uma lista dos leads que precisam de atenção.

## O que esta versão faz

- Lê o CRM no Notion.
- Foca em `Interação Amigável 1` e `Interação Amigável 2`.
- Prioriza primeiro `Interação Amigável 2`, depois `Interação Amigável 1`.
- Ignora automaticamente `Novo lead`, `Off`, `Venda Realizada`, `Na Reserva`, `Enviado ao CRM` e `Descartado`.
- Verifica a coluna `Data do Último Contato`.
- Envia no Telegram leads com último contato há 2+ dias.
- Envia até 20 leads por execução.
- Divide mensagens grandes automaticamente para não estourar o limite do Telegram.
- Scheduler todos os dias às 08:30.

## Variáveis obrigatórias no Railway

```txt
NOTION_TOKEN=seu_token_notion
NOTION_DATABASE_ID=id_do_database
TELEGRAM_BOT_TOKEN=token_do_bot
TELEGRAM_CHAT_ID=seu_chat_id
TZ=America/Sao_Paulo
```

## Variáveis opcionais recomendadas

```txt
FOLLOWUP_DAYS=2
FOLLOWUP_MAX_LEADS=20
FOLLOWUP_INCLUDE_STATUSES=Interação Amigável 1,Interação Amigável 2
FOLLOWUP_IGNORE_STATUSES=Novo lead,Off,Venda Realizada,Na Reserva,Enviado ao CRM,Descartado
FOLLOWUP_INCLUDE_EMPTY_DATES=false
```

## Teste manual

```bash
python followup_agent.py
```

## Rodar automaticamente

O `Procfile` usa:

```txt
worker: python scheduler.py
```
