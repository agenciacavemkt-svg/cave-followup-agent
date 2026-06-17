import time
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from config import RESPONSAVEL_PADRAO
from utils import normalize_key, clean_text

NOTION_VERSION = "2022-06-28"
NOTION_BASE = "https://api.notion.com/v1"


def notion_headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def validar_conexao(token: str, database_id: str) -> Dict:
    r = requests.get(
        f"{NOTION_BASE}/databases/{database_id}",
        headers=notion_headers(token),
        timeout=30,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Notion erro {r.status_code}: {r.text[:600]}")
    return r.json()


def get_schema(token: str, database_id: str) -> Dict:
    db = validar_conexao(token, database_id)
    return db.get("properties", {})


def find_property(schema: Dict, candidates: List[str], allowed_types: Optional[List[str]] = None) -> Optional[Tuple[str, str]]:
    for name in candidates:
        if name in schema:
            ptype = schema[name].get("type")
            if allowed_types is None or ptype in allowed_types:
                return name, ptype

    norm_candidates = {normalize_key(c): c for c in candidates}
    for prop_name, meta in schema.items():
        if normalize_key(prop_name) in norm_candidates:
            ptype = meta.get("type")
            if allowed_types is None or ptype in allowed_types:
                return prop_name, ptype

    if allowed_types and "title" in allowed_types:
        for prop_name, meta in schema.items():
            if meta.get("type") == "title":
                return prop_name, "title"

    return None


def prop_to_text(prop: Dict) -> str:
    if not prop:
        return ""
    ptype = prop.get("type")
    if ptype == "title":
        return "".join([x.get("plain_text", "") for x in prop.get("title", [])]).strip()
    if ptype == "rich_text":
        return "".join([x.get("plain_text", "") for x in prop.get("rich_text", [])]).strip()
    if ptype == "url":
        return clean_text(prop.get("url"))
    if ptype == "phone_number":
        return clean_text(prop.get("phone_number"))
    if ptype == "email":
        return clean_text(prop.get("email"))
    if ptype == "select":
        return clean_text((prop.get("select") or {}).get("name"))
    if ptype == "multi_select":
        return ", ".join([x.get("name", "") for x in prop.get("multi_select", [])]).strip()
    if ptype == "number":
        val = prop.get("number")
        return "" if val is None else str(val)
    if ptype == "date":
        date = prop.get("date") or {}
        return clean_text(date.get("start"))
    if ptype == "checkbox":
        return "true" if prop.get("checkbox") else "false"
    return ""


def set_prop(schema: Dict, props_out: Dict, candidates: List[str], value, preferred_types: List[str]) -> None:
    found = find_property(schema, candidates, preferred_types)
    if not found or value is None:
        return

    name, ptype = found
    value_str = clean_text(value)

    if ptype == "title":
        if value_str:
            props_out[name] = {"title": [{"text": {"content": value_str[:2000]}}]}
    elif ptype == "rich_text":
        if value_str:
            props_out[name] = {"rich_text": [{"text": {"content": value_str[:2000]}}]}
    elif ptype == "url":
        if value_str and value_str.startswith("http"):
            props_out[name] = {"url": value_str}
        elif value_str.startswith("@"):
            props_out[name] = {"url": f"https://instagram.com/{value_str.lstrip('@')}"}
    elif ptype == "phone_number":
        if value_str:
            props_out[name] = {"phone_number": value_str[:200]}
    elif ptype == "number":
        try:
            props_out[name] = {"number": float(value)}
        except Exception:
            return
    elif ptype == "select":
        if value_str:
            props_out[name] = {"select": {"name": value_str[:100]}}
    elif ptype == "multi_select":
        if isinstance(value, list):
            vals = [clean_text(v) for v in value if clean_text(v)]
        else:
            vals = [v.strip() for v in value_str.split(",") if v.strip()]
        if vals:
            props_out[name] = {"multi_select": [{"name": v[:100]} for v in vals[:5]]}
    elif ptype == "date":
        if value_str:
            props_out[name] = {"date": {"start": value_str[:10]}}
    elif ptype == "checkbox":
        props_out[name] = {"checkbox": bool(value)}


def ler_todos_leads(token: str, database_id: str, schema: Dict) -> Dict:
    print("📖 Lendo CRM atual do Notion...")
    leads_existentes = {}
    cursor = None

    title_prop = find_property(schema, ["Nome Empresa", "Nome Contato", "Nome", "Name"], ["title"])
    instagram_prop = find_property(schema, ["Instagram da Empresa", "Instagram", "@Instagram", "IG"], ["rich_text", "url"])
    status_prop = find_property(schema, ["Status/Etapa", "Status"], ["select", "multi_select", "rich_text"])
    resultado_prop = find_property(schema, ["Resultado", "Não Prospectar Novamente", "Não prospectar"], ["select", "checkbox", "rich_text"])
    ultimo_prop = find_property(schema, ["Data do Último Contato", "Data do último contato", "Último contato", "Data Último Contato"], ["date"])

    while True:
        payload = {"page_size": 100}
        if cursor:
            payload["start_cursor"] = cursor

        r = requests.post(
            f"{NOTION_BASE}/databases/{database_id}/query",
            headers=notion_headers(token),
            json=payload,
            timeout=30,
        )
        if r.status_code != 200:
            raise RuntimeError(f"Erro lendo Notion {r.status_code}: {r.text[:600]}")
        resp = r.json()

        for page in resp.get("results", []):
            page_id = page.get("id")
            props = page.get("properties", {})

            nome = prop_to_text(props.get(title_prop[0])) if title_prop else ""
            ig = prop_to_text(props.get(instagram_prop[0])) if instagram_prop else ""
            status = prop_to_text(props.get(status_prop[0])) if status_prop else ""

            resultado_texto = ""
            nao_prospectar = False
            if resultado_prop:
                prop = props.get(resultado_prop[0], {})
                if prop.get("type") == "checkbox":
                    nao_prospectar = bool(prop.get("checkbox"))
                else:
                    resultado_texto = prop_to_text(prop)
                    nao_prospectar = normalize_key(resultado_texto) in [
                        normalize_key("Não prospectar"),
                        normalize_key("Fechado com concorrente"),
                        normalize_key("Sem interesse"),
                    ]

            ultimo_contato = prop_to_text(props.get(ultimo_prop[0])) if ultimo_prop else None

            info = {
                "page_id": page_id,
                "ultimo_contato": ultimo_contato or None,
                "status": status,
                "resultado": resultado_texto,
                "nao_prospectar": nao_prospectar,
            }

            for key in [normalize_key(nome), normalize_key(ig)]:
                if key:
                    leads_existentes[key] = info

        if not resp.get("has_more"):
            break
        cursor = resp.get("next_cursor")
        time.sleep(0.2)

    print(f"📚 {len(leads_existentes)} chaves existentes mapeadas no CRM")
    return leads_existentes



def carregar_chaves_existentes(token: str, database_id: str) -> set:
    """Lê o CRM antes da pesquisa e devolve um set de chaves para bloquear duplicados."""
    schema = get_schema(token, database_id)
    existentes = ler_todos_leads(token, database_id, schema)
    return set(existentes.keys())


def lead_keys(lead: Dict) -> set:
    vals = [lead.get("instagram"), lead.get("nome"), lead.get("website"), lead.get("linkedin"), lead.get("telefone")]
    return {normalize_key(v) for v in vals if normalize_key(v)}


def filtrar_leads_ineditos(leads: List[Dict], chaves_existentes: set) -> List[Dict]:
    """Filtro de segurança antes da IA: remove o que já existe no CRM ou repetiu na execução."""
    ineditos = []
    vistos = set()
    duplicados = 0

    for lead in leads:
        keys = lead_keys(lead)
        if not keys:
            continue
        if keys & chaves_existentes or keys & vistos:
            duplicados += 1
            continue
        ineditos.append(lead)
        vistos.update(keys)

    print(f"🧹 Filtro anti-duplicidade antes da IA: {len(ineditos)} inéditos | {duplicados} duplicados barrados")
    return ineditos


def contar_leads_pendentes(token: str, database_id: str) -> int:
    """Conta leads ainda não trabalhados para não lotar o CRM sem necessidade."""
    schema = get_schema(token, database_id)
    status_prop = find_property(schema, ["Status/Etapa", "Status"], ["select", "multi_select", "rich_text"])
    resultado_prop = find_property(schema, ["Resultado"], ["select", "multi_select", "rich_text"])

    if not status_prop:
        return 0

    pendentes_status = {
        normalize_key("Novo lead"),
        normalize_key("Aguardando primeiro contato"),
        normalize_key("Interação Amigável 1"),
        normalize_key("Seguir no Instagram"),
    }
    resultados_encerrados = {
        normalize_key("Sem interesse"),
        normalize_key("Fechado"),
        normalize_key("Fechado com concorrente"),
        normalize_key("Não prospectar"),
    }

    cursor = None
    total = 0
    while True:
        payload = {"page_size": 100}
        if cursor:
            payload["start_cursor"] = cursor
        r = requests.post(
            f"{NOTION_BASE}/databases/{database_id}/query",
            headers=notion_headers(token),
            json=payload,
            timeout=30,
        )
        if r.status_code != 200:
            raise RuntimeError(f"Erro contando pendentes no Notion {r.status_code}: {r.text[:600]}")
        resp = r.json()
        for page in resp.get("results", []):
            props = page.get("properties", {})
            status = normalize_key(prop_to_text(props.get(status_prop[0])))
            resultado = normalize_key(prop_to_text(props.get(resultado_prop[0]))) if resultado_prop else ""
            if status in pendentes_status and resultado not in resultados_encerrados:
                total += 1
        if not resp.get("has_more"):
            break
        cursor = resp.get("next_cursor")
        time.sleep(0.2)

    print(f"📌 Leads pendentes no CRM: {total}")
    return total


def decidir_proxima_acao(lead: Dict) -> str:
    potencial = lead.get("potencial")
    score = float(lead.get("score", 0) or 0)
    if potencial in ["Alto", "Médio"] or score >= 7:
        return "Interagir nos Stories"
    return "Nenhuma"


def montar_properties(schema: Dict, lead: Dict, is_update: bool = False) -> Dict:
    props = {}
    hoje = datetime.now().date().isoformat()
    cidade = lead.get("cidade") or lead.get("bairro") or "Rio de Janeiro"

    set_prop(schema, props, ["Nome Empresa", "Nome Contato", "Nome", "Name"], lead.get("nome"), ["title"])
    set_prop(schema, props, ["Nome Contato"], lead.get("nome_contato", ""), ["rich_text"])
    set_prop(schema, props, ["Ramo", "Especialidade", "Área", "Area"], lead.get("ramo"), ["multi_select", "select", "rich_text"])
    set_prop(schema, props, ["Instagram da Empresa", "Instagram", "@Instagram", "IG"], lead.get("instagram"), ["url", "rich_text"])
    set_prop(schema, props, ["LinkedIn", "Linkedin"], lead.get("linkedin"), ["url", "rich_text"])
    set_prop(schema, props, ["Telefone/Whats", "Telefone", "WhatsApp", "Whatsapp"], lead.get("telefone"), ["phone_number", "rich_text"])
    set_prop(schema, props, ["Cidade"], cidade, ["select", "multi_select", "rich_text"])
    set_prop(schema, props, ["Bairro", "Região", "Regiao"], lead.get("bairro"), ["select", "multi_select", "rich_text"])
    set_prop(schema, props, ["Site", "Website", "URL"], lead.get("website"), ["url", "rich_text"])
    set_prop(schema, props, ["Endereço", "Endereco"], lead.get("endereco"), ["rich_text"])
    set_prop(schema, props, ["Nota Google", "Avaliação Google", "Avaliacao Google"], lead.get("nota_google"), ["number", "rich_text"])
    set_prop(schema, props, ["Avaliações Google", "Avaliacoes Google", "Número de avaliações"], lead.get("avaliacoes_google"), ["number", "rich_text"])

    set_prop(schema, props, ["Score IA", "Score"], lead.get("score"), ["number"])
    set_prop(schema, props, ["Nota do Lead (0–10)", "Nota do Lead (0-10)", "Nota do Lead"], lead.get("score"), ["number"])
    set_prop(schema, props, ["Potencial"], lead.get("potencial"), ["select", "multi_select", "rich_text"])
    set_prop(schema, props, ["Análise IA", "Analise IA", "Análise", "Analise"], lead.get("analise"), ["rich_text"])
    set_prop(schema, props, ["Alerta", "Observação IA", "Observacao IA", "OBS", "Observações", "Observacoes"], lead.get("alerta"), ["rich_text"])
    set_prop(schema, props, ["Origem do Lead", "Origem", "Fonte"], lead.get("fonte"), ["select", "multi_select", "rich_text"])
    set_prop(schema, props, ["CNPJ"], lead.get("cnpj", ""), ["rich_text"])
    set_prop(schema, props, ["Faturamento estimado", "Faturamento Estimado", "Faturamento", "Porte"], lead.get("faturamento_estimado", ""), ["rich_text", "select", "number"])
    set_prop(schema, props, ["Responsável", "Responsavel"], RESPONSAVEL_PADRAO, ["select", "multi_select", "rich_text", "people"])
    set_prop(schema, props, ["Status do Perfil", "Perfil analisado?", "Status Perfil"], "Analisado", ["select", "multi_select", "rich_text"])
    set_prop(schema, props, ["Próxima Ação", "Proxima Acao"], decidir_proxima_acao(lead), ["select", "multi_select", "rich_text"])

    if not is_update:
        set_prop(schema, props, ["Data de Entrada", "Data Entrada", "Criado em"], hoje, ["date"])
        set_prop(schema, props, ["Status/Etapa", "Status"], "Novo lead", ["select", "rich_text"])
        # Data do Último Contato fica vazia em lead novo.

    return props


def criar_lead(token: str, database_id: str, schema: Dict, lead: Dict) -> Optional[str]:
    props = montar_properties(schema, lead, is_update=False)
    payload = {"parent": {"database_id": database_id}, "properties": props}
    r = requests.post(f"{NOTION_BASE}/pages", headers=notion_headers(token), json=payload, timeout=30)
    if r.status_code in (200, 201):
        page_id = r.json().get("id")
        print(f"✅ Novo no Notion: {lead.get('nome')} | {lead.get('score')} {lead.get('potencial')}")
        return page_id
    print(f"❌ Erro criando {lead.get('nome')}: {r.status_code} {r.text[:500]}")
    return None


def atualizar_lead(token: str, page_id: str, schema: Dict, lead: Dict) -> bool:
    if not page_id or normalize_key(page_id) in ["novo", "none", "null"]:
        print(f"⚠️ Atualização ignorada: page_id inválido para {lead.get('nome')}: {page_id}")
        return False

    props = montar_properties(schema, lead, is_update=True)
    payload = {"properties": props}
    r = requests.patch(f"{NOTION_BASE}/pages/{page_id}", headers=notion_headers(token), json=payload, timeout=30)
    if r.status_code == 200:
        print(f"🔄 Atualizado: {lead.get('nome')} | {lead.get('score')} {lead.get('potencial')}")
        return True
    print(f"⚠️ Erro atualizando {lead.get('nome')}: {r.status_code} {r.text[:500]}")
    return False


def precisa_reativar(info: Dict) -> bool:
    data = info.get("ultimo_contato")
    if not data:
        return False
    try:
        dt = datetime.fromisoformat(data[:10])
        return dt.date() <= (datetime.now().date() - timedelta(days=30))
    except Exception:
        return False



def sincronizar(token: str, database_id: str, leads: List[Dict]) -> Dict:
    if not token:
        raise RuntimeError("NOTION_TOKEN vazio. Confira Variables no Railway.")
    if not database_id:
        raise RuntimeError("NOTION_DATABASE_ID vazio. Confira Variables no Railway.")

    schema = get_schema(token, database_id)
    print("✅ Conexão com Notion OK")
    print("📌 Colunas encontradas:", ", ".join(schema.keys()))

    existentes = ler_todos_leads(token, database_id, schema)

    criados = 0
    atualizados = 0
    ignorados = 0
    duplicados = 0

    for lead in leads:
        keys = lead_keys(lead)
        existente_info = next((existentes[k] for k in keys if k in existentes), None)

        if existente_info and existente_info.get("nao_prospectar"):
            print(f"🚫 Ignorado (não prospectar): {lead.get('nome')}")
            ignorados += 1
            continue

        if existente_info:
            # Na versão comercial, lead repetido NÃO atualiza CRM. Ele só atrapalha o fluxo.
            print(f"⏭️ Duplicado ignorado, não atualizei: {lead.get('nome')}")
            duplicados += 1
            ignorados += 1
            continue

        novo_page_id = criar_lead(token, database_id, schema, lead)
        if novo_page_id:
            criados += 1
            for k in keys:
                existentes[k] = {"page_id": novo_page_id, "nao_prospectar": False}
        else:
            ignorados += 1
        time.sleep(0.2)

    resumo = {"criados": criados, "atualizados": atualizados, "ignorados": ignorados, "duplicados": duplicados}
    print(f"✅ Sincronização finalizada: {resumo}")
    return resumo
