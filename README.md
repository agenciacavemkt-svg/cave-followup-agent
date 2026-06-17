# Cave Follow-up Agent

Agente separado para ler o CRM da Cave no Notion e mandar alertas de follow-up no Telegram.

## O que faz

- Lê o CRM no Notion.
- Ignora leads com status `Off` e `Venda Realizada`.
- Verifica a coluna `Data do Último Contato`.
- Envia no Telegram os leads com 5+ dias sem contato.
- Divide mensagens grandes automaticamente para não estourar o limite do Telegram.
- Roda todos os dias às 08:30.

## Variáveis no Railway

```txt
NOTION_TOKEN=
NOTION_DATABASE_ID=
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
TZ=America/Sao_Paulo
FOLLOWUP_DAYS=5
FOLLOWUP_MAX_LEADS=40
FOLLOWUP_IGNORE_STATUSES=Off,Venda Realizada
```

## Teste manual

```bash
python followup_agent.py
```

## Rodar automático

O Railway deve usar o `Procfile`:

```txt
worker: python scheduler.py
```

## Importante

Os arquivos precisam estar na raiz do repositório, e não dentro de uma pasta.
