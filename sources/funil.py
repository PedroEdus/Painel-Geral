import pandas as pd
import streamlit as st
from core.bq import get_client, PROJECT_ID

DATASET = "buriti_marketing_silver"
TABELA  = "funil_leads"

@st.cache_data(ttl=3600)
def carregar_leads() -> pd.DataFrame:
    """Loads and deduplicates CRM leads from BigQuery."""
    client = get_client()
    query = f"""
        SELECT * EXCEPT(row_num)
        FROM (
          SELECT *,
            ROW_NUMBER() OVER (
              PARTITION BY Codigo
              ORDER BY data_carga DESC
            ) AS row_num
          FROM `{PROJECT_ID}.{DATASET}.{TABELA}`
        )
        WHERE row_num = 1 AND DataCadastro >= '2026-01-01'
    """
    try:
        df = client.query(query).to_dataframe()
    except Exception as e:
        st.warning(f"Erro ao carregar dados do Funil de Leads: {e}")
        return pd.DataFrame()

    if df.empty:
        return df

    # Convert date and numeric fields
    for col in ("DataCadastro", "DataAlteracao"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    if "TempoTotal" in df.columns:
        df["TempoTotal"] = pd.to_numeric(df["TempoTotal"], errors="coerce")

    if "Codigo" in df.columns:
        df["Codigo"] = pd.to_numeric(df["Codigo"], errors="coerce")

    return df
