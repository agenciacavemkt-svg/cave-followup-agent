# Cave Follow-up Agent — Interação Amigável 1

Agente de follow-up comercial da Cave. Ele lê o CRM no Notion e envia no Telegram uma lista dos leads que precisam de atenção.

## O que esta versão faz

- Lê o CRM no Notion.
- Foca somente em leads com `Status/Etapa = Interação Amigável 1` por padrão.
- Ignora automaticamente `Novo lead`, `Off` e `Venda Realizada`.
- Verifica a coluna `Data do Último Contato`.
- Envia no Telegram os leads com último contato há 5+ dias.
- Divide mensagens grandes automaticamente para não estourar o limite do Telegram.
- Organiza por prioridade:
  - Urgentes / sem data / 15+ dias
  - Fazer hoje / 8 a 14 dias
  - Se sobrar tempo / 5 a 7 dias
- Scheduler todos os dias às 08:30.

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
FOLLOWUP_DAYS=5
FOLLOWUP_MAX_LEADS=40
FOLLOWUP_INCLUDE_STATUSES=Interação Amigável 1
FOLLOWUP_IGNORE_STATUSES=Off,Venda Realizada,Novo lead
```

Para incluir Interação Amigável 2 depois:

```txt
FOLLOWUP_INCLUDE_STATUSES=Interação Amigável 1,Interação Amigável 2
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
