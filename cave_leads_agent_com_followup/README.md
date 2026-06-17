# Cave Leads Agent — versão 15 leads ter/qui

Agente de captação, qualificação e sincronização de leads da Cave com Notion + relatório no Telegram.

## O que ele faz

- Lê o CRM do Notion antes da pesquisa.
- Se houver muitos leads pendentes, pausa a captação para não lotar o CRM.
- Busca leads inéditos no Rio de Janeiro usando Serper/Google.
- Remove duplicados antes de gastar Gemini/IA.
- Qualifica leads com Gemini usando o posicionamento da Cave.
- Filtra leads com `MIN_SCORE`.
- Envia apenas os top leads para o Notion.
- Não atualiza leads repetidos por padrão: lead repetido é ignorado.
- Preenche as colunas do CRM: Cidade, Responsável, Próxima Ação, Status do Perfil, Nota do Lead, Score IA, Faturamento Estimado etc.
- Envia relatório no Telegram.
- Roda automaticamente somente terças e quintas às 08:00.

## Configuração padrão desta versão

```txt
TOP_LEADS=15
MAX_LEADS_BRUTOS=180
MIN_SCORE=7.5
PENDENTES_LIMITE=20
TZ=America/Sao_Paulo
```

Na prática:

- Terça: até 15 leads novos.
- Quinta: até 15 leads novos.
- Se já existirem 20 leads pendentes no CRM, ele não capta nada e avisa no Telegram.

## Variáveis obrigatórias no Railway

```txt
SERPER_KEY=sua_chave_serper
GEMINI_API_KEY=sua_chave_gemini
NOTION_TOKEN=seu_token_notion
NOTION_DATABASE_ID=2682ffb6298581e6bf82d2f71c9ea637
```

## Variáveis opcionais recomendadas

```txt
TELEGRAM_BOT_TOKEN=token_do_bot
TELEGRAM_CHAT_ID=seu_chat_id
TZ=America/Sao_Paulo
RESPONSAVEL_PADRAO=João Haze
MAX_LEADS_BRUTOS=180
TOP_LEADS=15
MIN_SCORE=7.5
PENDENTES_LIMITE=20
```

## Arquivos

- `agent.py`: roda o agente e envia resumo no Telegram.
- `scheduler.py`: agenda terça e quinta às 08:00.
- `scraper.py`: captação de leads via Serper, já com filtro anti-lixo e anti-duplicidade.
- `qualifier.py`: qualificação com Gemini + fallback criterioso.
- `notion_sync.py`: sincronização robusta com Notion.
- `debug_notion.py`: teste rápido da conexão com o Notion.
- `Procfile`: comando para o Railway.
- `requirements.txt`: dependências.
- `nixpacks.toml`: build do Railway.

## Como testar

Depois de subir no GitHub e redeployar no Railway:

```bash
python debug_notion.py
python agent.py
```

No teste do agente, procure no log:

```txt
ETAPA 0 — Leitura do CRM antes da pesquisa
ETAPA 1 — Captação somente de leads inéditos
Enviando top 15 ao Notion
ETAPA 5 — Telegram
```

Para confirmar o scheduler, o log deve iniciar com:

```txt
🕐 Scheduler ativo — terças e quintas às 08:00 (America/Sao_Paulo).
```

## Observação de segurança

Se alguma chave foi exposta em conversa, regenere Serper, Gemini, Notion e Telegram depois que tudo funcionar.

## Novo agente: Follow-up Comercial

Arquivo: `followup_agent.py`

O que ele faz:

- Lê o CRM no Notion.
- Olha a coluna `Data do Último Contato` / `Data do ultimo contato`.
- Ignora leads com status `Off` e `Venda Realizada`.
- Envia no Telegram os leads cujo último contato passou do limite configurado.
- Também mostra leads sem data registrada para revisão.

Variáveis opcionais:

```txt
FOLLOWUP_DAYS=5
FOLLOWUP_MAX_LEADS=40
FOLLOWUP_IGNORE_STATUSES=Off,Venda Realizada
```

Como testar manualmente:

```bash
python followup_agent.py
```

Scheduler atualizado:

- Captação de novos leads: terça e quinta às 08:00.
- Follow-up comercial: todos os dias às 08:30.

