import json
import re
import requests
from typing import Dict, List

from config import GEMINI_API_KEY
from utils import safe_float

GEMINI_MODELS = [
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
]

CAVE_CONTEXT = """
A Cave Conteúdo é uma agência de marketing estratégico especializada em profissionais da saúde.
Posicionamento: conteúdos em vídeo que transformam atenção em desejo e posicionam marcas da saúde para atrair pacientes que escolhem excelência, não preço.
Ticket ideal de cliente: R$ 2.500 a R$ 4.000/mês, aceitando em alguns casos R$ 2.000.
Cliente ideal: profissional da saúde, preferencialmente mulher, 28 a 55 anos, negócio estabilizado, clínica própria ou consultório estruturado, ticket médio bom, aceita orientação estratégica e quer aumentar percepção profissional e captação de pacientes.

Nichos PRIORITÁRIOS para score alto:
- Harmonização facial
- Odontologia estética
- Facetas, lentes, implantes, reabilitação oral, Invisalign
- Biomedicina estética
- Dermatologia estética
- Cirurgia plástica
- Clínicas premium de estética e saúde
- Clínicas multidisciplinares estruturadas

Nichos bons, mas precisam de mais critério:
- Psicologia: priorizar clínicas, institutos, psicólogas com método/estrutura; não priorizar profissional iniciante solo.
- Fonoaudiologia: priorizar clínicas infantis, disfagia, voz, linguagem, motricidade orofacial e clínicas estruturadas.
- Nutrição/Fisioterapia: só pontuar bem se houver estética, esportiva premium, dermatofuncional, pélvica ou estrutura de clínica.

Sinais positivos:
- Bairro nobre ou região com poder aquisitivo
- Clínica própria ou consultório refinado
- Avaliação alta e volume relevante no Google
- Presença digital existente, mas com oportunidade clara de melhorar posicionamento
- Especialidade de alto ticket
- Nome de profissional com marca pessoal
- Serviços premium e recorrentes

Sinais negativos que devem derrubar nota:
- Clínica popular, convênio, baixo custo, preço popular
- Profissional iniciante
- Perfil sem sinais de maturidade comercial
- Resultado muito genérico de busca, artigo, vaga ou conteúdo que não seja lead real
- LinkedIn pessoal sem indício claro de clínica/serviço vendável
- Fono/psicologia/nutrição/fisio sem estrutura ou sem ticket percebido

Regra de pontuação:
- 9 a 10: lead excelente, prioridade máxima, forte chance de pagar Cave.
- 8 a 8.9: lead muito bom, vale prospectar.
- 7 a 7.9: lead bom, mas precisa validar manualmente.
- 5 a 6.9: lead fraco/morno, só entra se faltar lead.
- abaixo de 5: descartar.

Se não houver dados suficientes, NÃO chute alto. Dê nota média ou baixa.
"""


def estimar_faturamento(score: float, ramo: str, bairro: str, nome: str = "") -> str:
    texto = f"{ramo} {bairro} {nome}".lower()
    high_ticket = ["cirurg", "plást", "plastic", "dermato", "implanto", "faceta", "lente", "invisalign", "harmon", "biomed", "reabilitação", "reabilitacao"]
    premium_place = ["barra", "recreio", "leblon", "ipanema", "gávea", "gavea", "jardim botânico", "jardim botanico", "niterói", "niteroi", "icaraí", "icarai"]

    if score >= 9 and any(t in texto for t in high_ticket) and any(b in texto for b in premium_place):
        return "100k-300k"
    if score >= 8 and any(t in texto for t in high_ticket):
        return "30k-100k"
    if score >= 7:
        return "30k-100k"
    return "Até 30k"


def fallback_score(lead: Dict) -> Dict:
    score = 2.0
    motivos = []

    nome = str(lead.get("nome", "")).lower()
    ramo = str(lead.get("ramo", "")).lower()
    bairro = str(lead.get("bairro", "")).lower()
    fonte = str(lead.get("fonte", "")).lower()

    premium_terms = ["harmon", "dermato", "faceta", "implanto", "invisalign", "biomed", "plástica", "plastica", "lentes", "reabilitação", "reabilitacao"]
    if any(t in ramo or t in nome for t in premium_terms):
        score += 2.5
        motivos.append("especialidade com potencial de ticket alto")

    estetica_terms = ["estética", "estetica", "clínica estética", "clinica estetica"]
    if any(t in ramo or t in nome for t in estetica_terms):
        score += 1.0
        motivos.append("atua em estética/saúde com apelo comercial")

    bairros_fortes = ["barra", "recreio", "leblon", "ipanema", "jardim botânico", "jardim botanico", "gávea", "gavea", "botafogo", "niterói", "niteroi", "icaraí", "icarai", "tijuca"]
    if any(b in bairro for b in bairros_fortes):
        score += 1.5
        motivos.append("região com maior potencial de ticket")

    if lead.get("instagram"):
        score += 1.0
        motivos.append("Instagram encontrado")
    elif lead.get("linkedin"):
        score += 0.3
        motivos.append("LinkedIn encontrado, mas exige validação manual")

    rating = safe_float(lead.get("nota_google"), 0)
    reviews = safe_float(lead.get("avaliacoes_google"), 0)
    if rating >= 4.5:
        score += 0.8
        motivos.append("boa nota no Google")
    if reviews >= 30:
        score += 0.8
        motivos.append("volume de avaliações relevante")

    low_terms = ["popular", "convênio", "convenio", "preço popular", "baixo custo", "sus", "amil", "hapvida", "metlife", "primavida", "sulamerica"]
    if any(t in nome or t in ramo for t in low_terms):
        score -= 2.5
        motivos.append("possível perfil de baixo ticket/convênio")

    weak_terms = ["vaga", "curso", "aprenda", "domine", "photos and videos", "on instagram", "linkedin"]
    if any(t in nome or t in fonte for t in weak_terms):
        score -= 1.5
        motivos.append("resultado pode não ser lead comercial direto")

    score = max(1.0, min(10.0, round(score, 1)))
    potencial = "Alto" if score >= 8 else "Médio" if score >= 7 else "Baixo"
    faturamento = estimar_faturamento(score, ramo, bairro, nome)

    return {
        "score": score,
        "potencial": potencial,
        "analise": "; ".join(motivos) or "Lead com dados limitados; avaliar manualmente antes de abordar.",
        "alerta": "Pontuação fallback, sem retorno da IA." if not GEMINI_API_KEY else "",
        "faturamento_estimado": faturamento,
        "cidade": lead.get("cidade") or lead.get("bairro") or "Rio de Janeiro",
    }


def _extract_json(text: str) -> Dict:
    if not text:
        return {}
    text = text.strip()
    text = re.sub(r"^```(?:json)?", "", text, flags=re.I).strip()
    text = re.sub(r"```$", "", text).strip()
    m = re.search(r"\{.*\}", text, flags=re.S)
    if m:
        text = m.group(0)
    try:
        return json.loads(text)
    except Exception:
        return {}


def qualificar_com_gemini(lead: Dict) -> Dict:
    if not GEMINI_API_KEY:
        return fallback_score(lead)

    prompt = f"""
{CAVE_CONTEXT}

Avalie o lead abaixo para prospecção da Cave.
Responda apenas em JSON válido, neste formato:
{{
  "score": 0-10,
  "potencial": "Alto|Médio|Baixo",
  "analise": "explicação comercial curta e útil",
  "alerta": "risco/observação curta",
  "faturamento_estimado": "Até 30k|30k-100k|100k-300k|300k+",
  "cidade": "cidade ou região identificada"
}}

Lead:
{json.dumps(lead, ensure_ascii=False)[:3500]}
"""

    for model in GEMINI_MODELS:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.15, "maxOutputTokens": 450},
            }
            r = requests.post(url, json=payload, timeout=30)
            if r.status_code != 200:
                continue
            data = r.json()
            text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            parsed = _extract_json(text)
            if parsed:
                score = max(1.0, min(10.0, safe_float(parsed.get("score"), 0)))
                potencial = parsed.get("potencial") or ("Alto" if score >= 8 else "Médio" if score >= 7 else "Baixo")
                if potencial not in ["Alto", "Médio", "Baixo"]:
                    potencial = "Alto" if score >= 8 else "Médio" if score >= 7 else "Baixo"
                return {
                    "score": round(score, 1),
                    "potencial": potencial,
                    "analise": str(parsed.get("analise", ""))[:900],
                    "alerta": str(parsed.get("alerta", ""))[:500],
                    "faturamento_estimado": str(parsed.get("faturamento_estimado") or estimar_faturamento(score, lead.get("ramo", ""), lead.get("bairro", ""), lead.get("nome", "")))[:100],
                    "cidade": str(parsed.get("cidade") or lead.get("bairro") or "Rio de Janeiro")[:100],
                }
        except Exception:
            continue

    return fallback_score(lead)


def qualificar_leads(leads: List[Dict]) -> List[Dict]:
    qualificados = []
    total = len(leads)
    print(f"🤖 Qualificando {total} leads...")
    for idx, lead in enumerate(leads, start=1):
        q = qualificar_com_gemini(lead)
        lead.update(q)
        qualificados.append(lead)
        print(f"[{idx}/{total}] {lead.get('nome','Sem nome')[:55]} | {lead.get('score')} {lead.get('potencial')}")
    return qualificados
