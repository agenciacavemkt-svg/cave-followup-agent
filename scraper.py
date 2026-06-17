import time
import requests
from typing import Dict, List, Optional, Set

from config import SERPER_KEY, RIO_BAIRROS, ESPECIALIDADES, SOCIAL_QUERIES, MAX_LEADS_BRUTOS
from utils import extract_instagram, extract_phone, unique_by_name_or_link, clean_text, normalize_key

SERPER_PLACES_URL = "https://google.serper.dev/places"
SERPER_SEARCH_URL = "https://google.serper.dev/search"

BAD_TERMS = [
    "curso", "cursos", "pós-graduação", "pos-graduacao", "congresso", "evento",
    "artigo", "blog", "vaga", "emprego", "professor", "treinamento", "aprenda",
    "domine", "photos and videos", "on instagram", "linkedin", "jornada", "workshop",
]


def _headers() -> Dict[str, str]:
    return {
        "X-API-KEY": SERPER_KEY,
        "Content-Type": "application/json",
    }


def ramo_macro(texto: str) -> str:
    texto = (texto or "").lower()
    mapa = [
        (["dent", "odonto", "faceta", "lente", "implanto", "invisalign", "ortodont", "reabilitação", "reabilitacao"], "Dentista"),
        (["biomed"], "Biomédica(o)"),
        (["dermato", "tricologia", "capilar"], "Dermatologista"),
        (["cirurg", "plást", "plastic"], "Cirurgiã(o)"),
        (["fono"], "Fonoaudióloga(o)"),
        (["psic"], "Psicóloga(o)"),
        (["nutri"], "Nutricionista"),
        (["fisi"], "Fisioterapeuta"),
        (["clínica", "clinica", "estética", "estetica", "harmon"], "Clínica"),
    ]
    for termos, ramo in mapa:
        if any(t in texto for t in termos):
            return ramo
    return "Saúde / Estética"


def deve_descartar(texto: str) -> bool:
    texto = (texto or "").lower()
    return any(t in texto for t in BAD_TERMS)


def lead_keys(lead: Dict) -> Set[str]:
    vals = [lead.get("instagram"), lead.get("nome"), lead.get("website"), lead.get("linkedin"), lead.get("telefone")]
    return {normalize_key(v) for v in vals if normalize_key(v)}


def lead_bloqueado(lead: Dict, chaves_bloqueadas: Optional[Set[str]]) -> bool:
    if not chaves_bloqueadas:
        return False
    return any(k in chaves_bloqueadas for k in lead_keys(lead))


def buscar_places(query: str, limit: int = 10, chaves_bloqueadas: Optional[Set[str]] = None) -> List[Dict]:
    try:
        r = requests.post(
            SERPER_PLACES_URL,
            headers=_headers(),
            json={"q": query, "gl": "br", "hl": "pt-br", "num": limit},
            timeout=30,
        )
        if r.status_code != 200:
            print(f"   ⚠️ Serper Places {r.status_code}: {r.text[:120]}")
            return []
        data = r.json()
        itens = data.get("places", []) or []
        leads = []
        for item in itens:
            nome = clean_text(item.get("title"))
            if not nome:
                continue
            endereco = clean_text(item.get("address"))
            site = clean_text(item.get("website"))
            telefone = clean_text(item.get("phoneNumber") or item.get("phone"))
            texto = " ".join([nome, endereco, site, telefone, query])
            if deve_descartar(texto):
                continue
            lead = {
                "nome": nome,
                "ramo": ramo_macro(query + " " + nome),
                "cidade": "Rio de Janeiro",
                "bairro": inferir_bairro(query, endereco),
                "telefone": telefone or extract_phone(texto),
                "website": site,
                "instagram": extract_instagram(texto),
                "linkedin": "",
                "nota_google": item.get("rating"),
                "avaliacoes_google": item.get("ratingCount") or item.get("reviews"),
                "endereco": endereco,
                "fonte": "Google Maps / Serper Places",
                "raw": item,
            }
            if lead_bloqueado(lead, chaves_bloqueadas):
                continue
            leads.append(lead)
        return leads
    except Exception as e:
        print(f"   ⚠️ erro Places: {e}")
        return []


def buscar_social(query: str, limit: int = 10, chaves_bloqueadas: Optional[Set[str]] = None) -> List[Dict]:
    try:
        r = requests.post(
            SERPER_SEARCH_URL,
            headers=_headers(),
            json={"q": query, "gl": "br", "hl": "pt-br", "num": limit},
            timeout=30,
        )
        if r.status_code != 200:
            print(f"   ⚠️ Serper Search {r.status_code}: {r.text[:120]}")
            return []
        data = r.json()
        itens = data.get("organic", []) or []
        leads = []
        for item in itens:
            title = clean_text(item.get("title"))
            link = clean_text(item.get("link"))
            snippet = clean_text(item.get("snippet"))
            if not title or not link:
                continue
            texto = f"{title} {link} {snippet} {query}"
            if deve_descartar(texto):
                continue
            is_instagram = "instagram.com" in link
            is_linkedin = "linkedin.com" in link
            lead = {
                "nome": title.replace("• Instagram", "").replace("| LinkedIn", "").strip(),
                "ramo": ramo_macro(query + " " + title + " " + snippet),
                "cidade": "Rio de Janeiro",
                "bairro": inferir_bairro(query, snippet),
                "telefone": extract_phone(snippet),
                "website": "",
                "instagram": extract_instagram(link + " " + snippet) if is_instagram else "",
                "linkedin": link if is_linkedin else "",
                "nota_google": None,
                "avaliacoes_google": None,
                "endereco": "",
                "fonte": "Instagram / Serper Search" if is_instagram else "LinkedIn / Serper Search" if is_linkedin else "Google Search / Serper",
                "raw": item,
            }
            if lead_bloqueado(lead, chaves_bloqueadas):
                continue
            leads.append(lead)
        return leads
    except Exception as e:
        print(f"   ⚠️ erro Search: {e}")
        return []


def inferir_bairro(query: str, fallback: str = "") -> str:
    texto = f"{query} {fallback}".lower()
    for bairro in RIO_BAIRROS:
        if bairro.lower() in texto:
            return bairro
    if "niteroi" in texto or "niterói" in texto:
        return "Niterói"
    return "Rio de Janeiro"


def captar_leads(chaves_bloqueadas: Optional[Set[str]] = None) -> List[Dict]:
    if not SERPER_KEY:
        raise RuntimeError("SERPER_KEY não configurada no Railway Variables.")

    leads = []
    print("🔎 Captando leads inéditos no Rio de Janeiro...")
    print(f"🎯 Limite bruto desta execução: {MAX_LEADS_BRUTOS}")
    if chaves_bloqueadas:
        print(f"🧱 Chaves bloqueadas carregadas do CRM: {len(chaves_bloqueadas)}")

    for bairro in RIO_BAIRROS:
        for especialidade in ESPECIALIDADES:
            if len(leads) >= MAX_LEADS_BRUTOS:
                break
            query = f"{especialidade} {bairro} Rio de Janeiro"
            print(f"   📍 {query}")
            encontrados = buscar_places(query, limit=10, chaves_bloqueadas=chaves_bloqueadas)
            leads.extend(encontrados)
            leads = unique_by_name_or_link(leads)
            print(f"      +{len(encontrados)} | total bruto inédito: {len(leads)}")
            time.sleep(0.25)
        if len(leads) >= MAX_LEADS_BRUTOS:
            break

    for query in SOCIAL_QUERIES:
        if len(leads) >= MAX_LEADS_BRUTOS:
            break
        print(f"   🌐 {query}")
        encontrados = buscar_social(query, limit=10, chaves_bloqueadas=chaves_bloqueadas)
        leads.extend(encontrados)
        leads = unique_by_name_or_link(leads)
        print(f"      +{len(encontrados)} | total bruto inédito: {len(leads)}")
        time.sleep(0.25)

    leads = unique_by_name_or_link(leads)[:MAX_LEADS_BRUTOS]
    print(f"✅ {len(leads)} leads inéditos únicos captados")
    return leads
