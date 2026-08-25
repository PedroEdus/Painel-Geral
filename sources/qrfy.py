import re

import pandas as pd
import streamlit as st
from unidecode import unidecode
from core.bq import get_client, PROJECT_ID

DATASET = "buriti_marketing_silver"
TABELA  = "qrfy_scans"

# Cidades que aparecem em buriti_marketing_silver.funil_leads (ClickMenos) —
# lista oficial de empreendimentos, deduplicada por grafia (a API do ClickMenos
# mistura ALL CAPS e Title Case pra mesma cidade). Usada pra achar a cidade
# real dentro do nome do QR, em vez de assumir que é sempre a primeira parte.
_CIDADES_CLICKMENOS = [
    "Alagoinhas", "Alta Floresta", "Arapiraca", "Ariquemes", "Barreiras",
    "Bela Vista de Goiás", "Cacoal", "Canaã dos Carajás", "Colatina",
    "Conceição do Araguaia", "Duque de Caxias", "Eldorado dos Carajás",
    "Formosa", "Goiânia", "Gurupi", "Guaíba", "Itaituba", "Itapipoca",
    "Luzimangues", "Marabá", "Marechal Deodoro", "Montes Claros",
    "Nova Serrana", "Paragominas", "Porangatu", "Porto Nacional",
    "Porto Velho", "Presidente Prudente", "Palmas", "Parauapebas", "Penedo",
    "Redenção", "Rio Branco", "Rio Grande", "Rio Largo", "Rio Verde",
    "Rolim de Moura", "Santana do Araguaia", "Santarém", "São Leopoldo",
    "São Miguel dos Campos", "São Gonçalo do Amarante", "Tauá", "Tucuruí",
    "Tucumã", "Uberaba", "Viamão", "Xinguara", "Águas Lindas de Goiás",
]


def _norm_txt(s: str) -> str:
    # "_" conta como caractere de palavra pro regex (\b não quebra em "VIAMAO_RS") —
    # troca por espaço pra separadores como "Viamão_RS" funcionarem igual a "Viamão/RS".
    return unidecode(str(s)).upper().replace("_", " ")


# Mais longas primeiro — evita que uma cidade curta "vença" por acidente
# quando outra mais específica também aparece no nome.
_CIDADES_NORM = sorted(
    ((_norm_txt(c), c) for c in _CIDADES_CLICKMENOS),
    key=lambda par: -len(par[0]),
)


def _extrair_cidade_qr(nome: str) -> str | None:
    """Procura, dentro do nome do QR, qual cidade da lista do ClickMenos
    aparece (ignorando acento/caixa). Nomes sem nenhuma cidade conhecida
    (páginas genéricas, hotsite, linktree etc.) retornam None."""
    n_norm = _norm_txt(nome)
    for cidade_norm, cidade_original in _CIDADES_NORM:
        if re.search(rf"\b{re.escape(cidade_norm)}\b", n_norm):
            return cidade_original
    return None


@st.cache_data(ttl=3600)
def carregar_dados() -> pd.DataFrame:
    """Carrega leituras de QR code (QRFY) do BigQuery."""
    client = get_client()
    query = f"SELECT * FROM `{PROJECT_ID}.{DATASET}.{TABELA}`"
    try:
        df = client.query(query).to_dataframe()
    except Exception as e:
        st.warning(f"Erro ao carregar dados da QRFY: {e}")
        return pd.DataFrame()

    if df.empty:
        return df

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["data"] = df["date"].dt.date

    df["folder"] = df["folder"].fillna("").replace("", "Sem pasta")
    df["city"] = df["city"].fillna("Desconhecida").replace("", "Desconhecida")
    df["os"] = df["os"].fillna("Desconhecido").replace("", "Desconhecido")

    df["leitura"] = 1
    df["visitante_unico"] = df["uniqueVisitor"].fillna(False).astype(bool)
    df["cidade_qr"] = df["name"].map(_extrair_cidade_qr)

    return df
