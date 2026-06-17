import os
from dotenv import load_dotenv

load_dotenv()

SERPER_KEY = os.getenv("SERPER_KEY", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
NOTION_TOKEN = os.getenv("NOTION_TOKEN", "").strip()
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID", "").strip().replace("-", "")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
TIMEZONE = os.getenv("TZ", "America/Sao_Paulo").strip() or "America/Sao_Paulo"
RESPONSAVEL_PADRAO = os.getenv("RESPONSAVEL_PADRAO", "João Haze").strip() or "João Haze"

MAX_LEADS_BRUTOS = int(os.getenv("MAX_LEADS_BRUTOS", "180"))
TOP_LEADS = int(os.getenv("TOP_LEADS", "15"))
MIN_SCORE = float(os.getenv("MIN_SCORE", "7.5"))
PENDENTES_LIMITE = int(os.getenv("PENDENTES_LIMITE", "20"))

FOLLOWUP_DAYS = int(os.getenv("FOLLOWUP_DAYS", "5"))
FOLLOWUP_MAX_LEADS = int(os.getenv("FOLLOWUP_MAX_LEADS", "40"))
FOLLOWUP_IGNORE_STATUSES = [
    s.strip() for s in os.getenv("FOLLOWUP_IGNORE_STATUSES", "Off,Venda Realizada").split(",") if s.strip()
]

RIO_BAIRROS = [
    "Barra da Tijuca", "Recreio dos Bandeirantes", "Leblon", "Ipanema", "Copacabana",
    "Botafogo", "Flamengo", "Laranjeiras", "Jardim Botânico", "Gávea", "Lagoa",
    "Tijuca", "Vila Isabel", "Grajaú", "Méier", "Cachambi", "Freguesia Jacarepaguá",
    "Jacarepaguá", "Taquara", "Vargem Pequena", "Vargem Grande", "Campo Grande",
    "Niterói", "Icaraí", "Santa Rosa Niterói", "Jardim Icaraí"
]

ESPECIALIDADES = [
    "harmonização facial", "odontologia estética", "dentista estética", "clínica odontológica",
    "ortodontia invisalign", "implantodontia", "facetas resina", "lentes de contato dental",
    "biomedicina estética", "biomédica estética", "clínica estética avançada",
    "dermatologista", "dermatologia estética", "tricologia", "cirurgião plástico",
    "clínica médica estética", "médico estética", "fonoaudióloga", "fonoaudiologia",
    "clínica de psicologia", "psicóloga clínica", "nutricionista esportiva", "nutrição estética",
    "fisioterapia dermatofuncional", "fisioterapia pélvica"
]

SOCIAL_QUERIES = [
    "site:instagram.com biomédica estética Rio de Janeiro harmonização",
    "site:instagram.com dentista estética Rio de Janeiro facetas resina",
    "site:instagram.com dermatologista Rio de Janeiro estética",
    "site:instagram.com fonoaudióloga Rio de Janeiro clínica",
    "site:instagram.com psicóloga clínica Rio de Janeiro",
    "site:linkedin.com/in dentista estética Rio de Janeiro",
    "site:linkedin.com/in biomédica estética Rio de Janeiro",
    "site:linkedin.com/in dermatologista Rio de Janeiro",
    "site:linkedin.com/in fonoaudióloga Rio de Janeiro",
    "site:linkedin.com/company clínica odontológica Rio de Janeiro",
]
