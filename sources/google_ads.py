import pandas as pd
import streamlit as st
from core.bq import get_client, PROJECT_ID
from core.taxonomia import _tipo_lancamento, _extrair_cidade_uf

DATASET = "buriti_marketing_silver"
TABELA  = "google_ads"
_NUM_COLS = ["impressions", "clicks", "cost", "conversions", "conversions_value"]

@st.cache_data(ttl=3600)
def carregar_google_ads() -> pd.DataFrame:
    """Loads and processes Google Ads data from BigQuery silver dataset."""
    client = get_client()
    query = f"""
        SELECT * EXCEPT(rn)
        FROM (
            SELECT *,
                   ROW_NUMBER() OVER (
                       PARTITION BY date, customer_id, campaign_id
                       ORDER BY _loaded_at DESC
                   ) AS rn
            FROM `{PROJECT_ID}.{DATASET}.{TABELA}`
        )
        WHERE rn = 1
    """
    try:
        df = client.query(query).to_dataframe()
    except Exception as e:
        # Fallback to an empty DataFrame to avoid crashing the dashboard if query fails
        st.warning(f"Erro ao carregar dados do Google Ads: {e}")
        return pd.DataFrame()

    if df.empty:
        return df

    df["date"] = pd.to_datetime(df["date"])
    for col in _NUM_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    # Filter out test campaigns starting with [TS]
    df = df[~df["campaign_name"].str.match(r"^\[TS\]", na=False)]

    # Classification
    df["Tipo_Lancamento"] = df["campaign_name"].map(_tipo_lancamento)

    # Cidade / UF extraction
    cidade_uf = df["campaign_name"].map(_extrair_cidade_uf)
    df["Cidade"] = cidade_uf.map(lambda x: x[0])
    df["UF"]     = cidade_uf.map(lambda x: x[1])

    return df
