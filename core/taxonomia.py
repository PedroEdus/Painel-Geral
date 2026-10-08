import re
import unicodedata
from functools import lru_cache

_UF_BR = {
    "AC","AL","AP","AM","BA","CE","DF","ES","GO","MA",
    "MT","MS","MG","PA","PB","PR","PE","PI","RJ","RN",
    "RS","RO","RR","SC","SP","SE","TO",
}

# Regex to match Cidade/UF pattern (e.g. "Rio Verde / GO")
_RE_CUF = re.compile(r'([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s\.]+?)\s*/\s*([A-Z]{2})(?:\b|$)')

# Cidades conhecidas (grafia canônica → UF): cidades já usadas nas campanhas +
# cidades das empresas (gold_dim_empresa, projeto de conciliação). Usado para
# padronizar a grafia e como fallback quando o nome não traz "Cidade/UF".
_CIDADES = {
    "Alagoinhas": "BA", "Alta Floresta": "MT", "Altamira": "PA",
    "Aparecida de Goiânia": "GO", "Araguaína": "TO", "Arapiraca": "AL",
    "Ariquemes": "RO", "Avaré": "SP", "Balsas": "MA", "Barra dos Coqueiros": "SE",
    "Barreiras": "BA", "Bela Vista de Goiás": "GO", "Cacoal": "RO",
    "Cachoeira do Sul": "RS", "Caçapava": "SP", "Cáceres": "MT",
    "Caldas Novas": "GO", "Canaã dos Carajás": "PA", "Caxias do Sul": "RS",
    "Colatina": "ES", "Crato": "CE", "Cuiabá": "MT", "Duque de Caxias": "RJ",
    "Eldorado do Carajás": "PA", "Formosa": "GO", "Fortaleza": "CE",
    "Goiânia": "GO", "Gramado": "RS", "Guaíba": "RS", "Guarapuava": "PR",
    "Gurupi": "TO", "Itaboraí": "RJ", "Itaituba": "PA", "Itajaí": "SC",
    "Itapipoca": "CE", "Itatiaia": "RJ", "Ji-Paraná": "RO", "Lorena": "SP",
    "Luzimangues": "TO",
    "Maceió": "AL", "Marabá": "PA", "Marau": "RS", "Marechal Deodoro": "AL",
    "Montes Claros": "MG", "Nova Serrana": "MG", "Palmas": "TO",
    "Paragominas": "PA", "Parauapebas": "PA", "Pelotas": "RS", "Penedo": "AL",
    "Porangatu": "GO", "Porto Alegre": "RS", "Porto Nacional": "TO",
    "Porto Velho": "RO", "Presidente Prudente": "SP", "Redenção": "PA",
    "Rio Branco": "AC", "Rio Grande": "RS", "Rio Largo": "AL", "Rio Verde": "GO",
    "Rolim de Moura": "RO", "Santa Maria de Itabira": "MG",
    "Santana do Araguaia": "PA", "Santarém": "PA",
    "São Gonçalo do Amarante": "CE", "São Leopoldo": "RS",
    "São Miguel dos Campos": "AL", "São Paulo": "SP", "Sertãozinho": "SP",
    "Taquaralto": "TO", "Tauá": "CE", "Tucumã": "PA", "Tucuruí": "PA", "Uberaba": "MG",
    "Viamão": "RS", "Vila Velha": "ES", "Xinguara": "PA",
}

# Apelidos e abreviações → cidade canônica. Taquaralto (Palmas) e Luzimangues
# (Porto Nacional) ficam como localidades próprias em _CIDADES.
_APELIDOS = {
    "Presidente": "Presidente Prudente",
    "PP": "Presidente Prudente",
    "São Miguel": "São Miguel dos Campos",
    "Palmas Taquaralto": "Taquaralto",
    "Residencial Jardim Tropical Itapipoca": "Itapipoca",
}

# Regiões das campanhas de Holding (ex.: "Holding Sul", "Nordeste II")
_RE_HOLDING = re.compile(
    r'(?:Holding\s+)?(Brasil Terrenos|Sudeste|Sul|Tocantins|Oeste|Nordeste(?: II)?)',
    re.IGNORECASE,
)
# Campanhas sem cidade nem região (marca, promoções multicidade, posts)
_RE_INSTITUCIONAL = re.compile(
    r'holding|institucional|virada de pr[eê]mios|terreno show de bola|'
    r'm[eê]s imbat[ií]vel|engajamento|novos f[ãa]s|^post:',
    re.IGNORECASE,
)


def _norm(s: str) -> str:
    """Minúsculas, sem acento, hífen como espaço e espaços colapsados."""
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[\s\-]+", " ", s.lower()).strip()


# Termo normalizado → cidade canônica
_TERMOS = {_norm(c): c for c in _CIDADES}
_TERMOS.update({_norm(a): c for a, c in _APELIDOS.items()})
# Alternância do termo mais longo para o mais curto ("São Miguel dos Campos" antes de "São Miguel")
_RE_TERMOS = re.compile(
    r"\b(" + "|".join(re.escape(t) for t in sorted(_TERMOS, key=len, reverse=True)) + r")\b"
)


def _tipo_lancamento(nome: str) -> str:
    """Classifica a campanha pelo nome: Estoque / Lançamento / Outros."""
    n = str(nome)
    if re.search(r"estoque", n, re.IGNORECASE):
        return "Estoque"
    if re.search(r"lan[cç]amento", n, re.IGNORECASE):
        return "Lançamento"
    return "Outros"


def _extrair_padrao_cuf(n: str):
    """Extrai (Cidade, UF) pelo padrão "Cidade/UF" no nome. None se não achar."""
    # Padrão 1: "Estoque | Cidade/UF" ou "Lançamento | Cidade/UF"
    if re.match(r'^(?:Estoque|Lan[cç]amento)\s*\|', n, re.IGNORECASE):
        apos = re.sub(r'^(?:Estoque|Lan[cç]amento)\s*\|\s*', '', n, flags=re.IGNORECASE)
        m = _RE_CUF.match(apos)
        if m and m.group(2) in _UF_BR:
            return m.group(1).strip(), m.group(2)

    # Padrão 2: "Campanha de ... - Cidade/UF"
    elif re.match(r'^Campanha\b', n, re.IGNORECASE):
        partes = n.split(' - ', 1)
        if len(partes) > 1:
            m = _RE_CUF.match(partes[1].strip())
            if m and m.group(2) in _UF_BR:
                return m.group(1).strip(), m.group(2)

    # Padrões 1 e 2 sem match seguem para o catch-all (Padrão 4)

    # Padrão 3: "Cidade/UF - ..."
    m = _RE_CUF.match(n)
    if m and m.group(2) in _UF_BR:
        return m.group(1).strip(), m.group(2)

    # Padrão 4: Catch-all, busca qualquer ocorrência de "Cidade/UF" no nome
    m = _RE_CUF.search(n)
    if m and m.group(2) in _UF_BR:
        return m.group(1).strip(), m.group(2)

    return None


@lru_cache(maxsize=None)
def _extrair_cidade_uf(nome: str) -> tuple:
    """
    Extrai (Cidade, UF) do nome da campanha. Ordem:
      1. Padrão "Cidade/UF" (grafia padronizada por _CIDADES/_APELIDOS);
      2. Cidade conhecida em qualquer posição do nome;
      3. Campanhas de Holding → ("Holding <região>", None);
      4. Campanhas institucionais/multicidade → ("Institucional", None).
    Retorna ("Não identificado", None) se nada se aplicar.
    """
    n = str(nome).strip()

    cuf = _extrair_padrao_cuf(n)
    if cuf:
        cidade, uf = cuf
        canon = _TERMOS.get(_norm(cidade))
        if canon:
            return canon, _CIDADES[canon]
        return cidade, uf

    m = _RE_TERMOS.search(_norm(n))
    if m:
        canon = _TERMOS[m.group(1)]
        return canon, _CIDADES[canon]

    for seg in n.split("|"):
        seg = re.sub(r"\s+", " ", seg).strip()
        m = _RE_HOLDING.fullmatch(seg)
        if m:
            return f"Holding {m.group(1)}", None

    if _RE_INSTITUCIONAL.search(n):
        return "Institucional", None

    return "Não identificado", None
