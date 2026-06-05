import pandas as pd
import streamlit as st
from core.bq import get_client, PROJECT_ID
from core.taxonomia import _tipo_lancamento, _extrair_cidade_uf

DATASET = "buriti_marketing_silver"
TABELA  = "meta_ads"

_ACTION_COLS = [
    "action__lead", "action__purchase", "action__complete_registration",
    "action__landing_page_view", "action__view_content",
    "action__add_to_cart", "action__initiate_checkout",
]

@st.cache_data(ttl=3600)
def carregar_dados() -> pd.DataFrame:
    """Loads Meta Ads records with partition key date_start filter from BigQuery."""
    client = get_client()
    query = f"""
        SELECT * 
        FROM `{PROJECT_ID}.{DATASET}.{TABELA}`
        WHERE date_start >= '2024-01-01'
    """
    try:
        df = client.query(query).to_dataframe()
    except Exception as e:
        st.warning(f"Erro ao carregar dados do Meta Ads: {e}")
        return pd.DataFrame()

    if df.empty:
        return df

    if "date_start" in df.columns:
        df["date_start"] = pd.to_datetime(df["date_start"]).dt.date

    num_cols = ["spend", "impressions", "reach", "clicks", "inline_link_clicks"] + _ACTION_COLS
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    existing_actions = [c for c in _ACTION_COLS if c in df.columns]
    df["conversions"] = df[existing_actions].sum(axis=1) if existing_actions else 0.0

    # Estoque vs Lançamento
    df["Tipo_Lancamento"] = df["campaign_name"].map(_tipo_lancamento)

    # Cidade e UF extraídas
    cidade_uf = df["campaign_name"].map(_extrair_cidade_uf)
    df["Cidade"] = cidade_uf.map(lambda x: x[0])
    df["UF"]     = cidade_uf.map(lambda x: x[1])

    return df

def agregar_por_campanha(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega df filtrado por campaign_name + objective e computa métricas derivadas."""
    if df.empty:
        return df

    action_cols = [c for c in df.columns if c.startswith("action__")]
    cols_soma = [
        c for c in ["spend", "impressions", "reach", "clicks", "inline_link_clicks", "conversions"]
        if c in df.columns
    ] + action_cols

    group_keys = [c for c in ["campaign_name", "objective", "Tipo_Lancamento", "Cidade", "UF"]
                  if c in df.columns]
    if not group_keys:
        return df

    agg = df.groupby(group_keys, as_index=False)[cols_soma].sum()

    imp = agg["impressions"].replace(0, pd.NA)
    agg["CTR (%)"]  = (agg["clicks"] / imp * 100).round(2)
    agg["CPM (R$)"] = (agg["spend"] / imp * 1000).round(2)

    # CPL — custo por lead, usando apenas action__lead
    if "action__lead" in agg.columns:
        leads = pd.to_numeric(agg["action__lead"], errors="coerce").replace(0, float("nan"))
        agg["CPL (R$)"] = (agg["spend"] / leads).round(2)
    else:
        agg["CPL (R$)"] = float("nan")

    return agg
