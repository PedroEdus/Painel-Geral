import pandas as pd
import streamlit as st
from core.bq import get_client, PROJECT_ID
from core.taxonomia import _tipo_lancamento, _extrair_cidade_uf

DATASET = "buriti_marketing_silver"
TABELA  = "publya_campanhas"

@st.cache_data(ttl=3600)
def carregar_publya() -> pd.DataFrame:
    """Loads and aggregates Publya campaign metrics from BigQuery."""
    client = get_client()
    query  = f"SELECT * FROM `{PROJECT_ID}.{DATASET}.{TABELA}`"
    try:
        df = client.query(query).to_dataframe()
    except Exception as e:
        st.warning(f"Erro ao carregar dados da Publya: {e}")
        return pd.DataFrame()

    if df.empty:
        return df

    # Aggregates rows where campaign_name and Tipo_Midia are equal
    cols_soma = [
        "impressions", "clicks", "budget", "reach", "conversions",
        "videoStarts", "videoCompletions", "audioStarts", "audioCompletions", "frequency",
    ]
    cols_soma = [c for c in cols_soma if c in df.columns]
    agg = {col: "sum" for col in cols_soma}

    if "data_inicio" in df.columns:
        df["data_inicio"] = pd.to_datetime(df["data_inicio"], errors="coerce")
        agg["data_inicio"] = "min"

    if "data_fim" in df.columns:
        df["data_fim"] = pd.to_datetime(df["data_fim"], errors="coerce")
        agg["data_fim"] = "max"

    df = df.groupby(["campaign_name", "Tipo_Midia"], as_index=False).agg(agg)

    # Derived metrics
    imp = df["impressions"].replace(0, pd.NA)
    clk = df["clicks"].replace(0, pd.NA)
    vs  = df["videoStarts"].replace(0, pd.NA)
    as_ = df["audioStarts"].replace(0, pd.NA)

    df["CTR (%)"]  = (df["clicks"] / imp * 100).round(2)
    df["CPM (R$)"] = (df["budget"] / imp * 1000).round(2)
    df["CPC (R$)"] = (df["budget"] / clk).round(2)
    df["VCR (%)"]  = (df["videoCompletions"] / vs * 100).round(2)
    df["ACR (%)"]  = (df["audioCompletions"] / as_ * 100).round(2)

    # Taxonomy mapping (Estoque vs Lançamento)
    df["Tipo_Lancamento"] = df["campaign_name"].map(_tipo_lancamento)

    # Cidade & UF extraction
    cidade_uf = df["campaign_name"].map(_extrair_cidade_uf)
    df["Cidade"] = cidade_uf.map(lambda x: x[0])
    df["UF"]     = cidade_uf.map(lambda x: x[1])

    return df
