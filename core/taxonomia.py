import re

_UF_BR = {
    "AC","AL","AP","AM","BA","CE","DF","ES","GO","MA",
    "MT","MS","MG","PA","PB","PR","PE","PI","RJ","RN",
    "RS","RO","RR","SC","SP","SE","TO",
}

# Regex to match Cidade/UF pattern (e.g. "Rio Verde / GO")
_RE_CUF = re.compile(r'([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s\.]+?)\s*/\s*([A-Z]{2})(?:\b|$)')

def _tipo_lancamento(nome: str) -> str:
    """Classifica a campanha pelo nome: Estoque / Lançamento / Outros."""
    n = str(nome)
    if re.search(r"estoque", n, re.IGNORECASE):
        return "Estoque"
    if re.search(r"lan[cç]amento", n, re.IGNORECASE):
        return "Lançamento"
    return "Outros"

def _extrair_cidade_uf(nome: str) -> tuple:
    """
    Extrai (Cidade, UF) do nome da campanha usando múltiplos padrões.
    Retorna (Cidade, UF) ou ("Não identificado", None).
    """
    n = str(nome).strip()

    # Padrão 1: "Estoque | Cidade/UF" ou "Lançamento | Cidade/UF"
    if re.match(r'^(?:Estoque|Lan[cç]amento)\s*\|', n, re.IGNORECASE):
        apos = re.sub(r'^(?:Estoque|Lan[cç]amento)\s*\|\s*', '', n, flags=re.IGNORECASE)
        m = _RE_CUF.match(apos)
        if m and m.group(2) in _UF_BR:
            return m.group(1).strip(), m.group(2)
        return "Não identificado", None

    # Padrão 2: "Campanha de ... - Cidade/UF"
    if re.match(r'^Campanha\b', n, re.IGNORECASE):
        partes = n.split(' - ', 1)
        if len(partes) > 1:
            m = _RE_CUF.match(partes[1].strip())
            if m and m.group(2) in _UF_BR:
                return m.group(1).strip(), m.group(2)
        return "Não identificado", None

    # Padrão 3: "Cidade/UF - ..."
    m = _RE_CUF.match(n)
    if m and m.group(2) in _UF_BR:
        return m.group(1).strip(), m.group(2)

    # Padrão 4: Catch-all, busca qualquer ocorrência de "Cidade/UF" no nome
    m = _RE_CUF.search(n)
    if m and m.group(2) in _UF_BR:
        return m.group(1).strip(), m.group(2)

    return "Não identificado", None
