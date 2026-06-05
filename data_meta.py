"""Loader de dados do Meta Ads para o showcase (lê silver.meta_ads do BigQuery)."""
import os
import re

import pandas as pd
import streamlit as st
from google.cloud import bigquery
from google.oauth2 import service_account

PROJECT_ID = "buriti-marketing-analytics"
DATASET    = "buriti_marketing_silver"
TABELA     = "meta_ads"

# SA com leitura no projeto (fallback local). Não commitar a key.
_KEY_FALLBACK = r"C:/Users/pedro.moura/Documents/Big Query Teste/keys/buriti-marketing-analytics-8466b517c505.json"

_ACTION_COLS = [
    "action__lead", "action__purchase", "action__complete_registration",
    "action__landing_page_view", "action__view_content",
    "action__add_to_cart", "action__initiate_checkout",
]

_UF_BR = {"AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS","MG","PA",
          "PB","PR","PE","PI","RJ","RN","RS","RO","RR","SC","SP","SE","TO"}


def _tipo_lancamento(nome: str) -> str:
    n = str(nome)
    if re.search(r"estoque", n, re.IGNORECASE):
        return "Estoque"
    if re.search(r"lan[cç]amento", n, re.IGNORECASE):
        return "Lançamento"
    return "Outros"


def _extrair_cidade_uf(nome: str) -> tuple:
    nome = str(nome)
    m = re.search(r"/\s*([A-Z]{2})\b", nome)
    if not m or m.group(1) not in _UF_BR:
        return None, None
    uf = m.group(1)
    before = nome[: m.start()].strip()
    partes = re.split(r"\s*[-–|:]\s*", before)
    cidade = partes[-1].strip()
    return cidade if cidade else None, uf


def _criar_client() -> bigquery.Client:
    try:
        if "gcp_service_account" in st.secrets:
            creds = service_account.Credentials.from_service_account_info(st.secrets["gcp_service_account"])
            return bigquery.Client(credentials=creds, project=PROJECT_ID)
    except Exception:
        pass
    if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        return bigquery.Client(project=PROJECT_ID)
    if os.path.exists(_KEY_FALLBACK):
        creds = service_account.Credentials.from_service_account_file(_KEY_FALLBACK)
        return bigquery.Client(credentials=creds, project=PROJECT_ID)
    return bigquery.Client(project=PROJECT_ID)


@st.cache_data(ttl=3600)
def carregar_dados() -> pd.DataFrame:
    client = _criar_client()
    df = client.query(f"SELECT * FROM `{PROJECT_ID}.{DATASET}.{TABELA}`").to_dataframe()
    if df.empty:
        return df

    if "date_start" in df.columns:
        df["date_start"] = pd.to_datetime(df["date_start"])

    num_cols = ["spend", "impressions", "reach", "clicks", "inline_link_clicks"] + _ACTION_COLS
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    existing = [c for c in _ACTION_COLS if c in df.columns]
    df["conversions"] = df[existing].sum(axis=1) if existing else 0.0

    df["Tipo_Lancamento"] = df["campaign_name"].map(_tipo_lancamento)
    cidade_uf = df["campaign_name"].map(_extrair_cidade_uf)
    df["Cidade"] = cidade_uf.map(lambda x: x[0])
    df["UF"]     = cidade_uf.map(lambda x: x[1])
    return df


def agregar_por_campanha(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega por campanha + objetivo e deriva CTR / CPM / CPL."""
    if df.empty:
        return df
    action_cols = [c for c in df.columns if c.startswith("action__")]
    cols_soma = [c for c in ["spend", "impressions", "reach", "clicks", "inline_link_clicks", "conversions"]
                 if c in df.columns] + action_cols
    group_keys = [c for c in ["campaign_name", "objective", "Tipo_Lancamento", "Cidade", "UF"] if c in df.columns]
    if not group_keys:
        return df

    agg = df.groupby(group_keys, as_index=False)[cols_soma].sum()
    imp = agg["impressions"].replace(0, float("nan"))
    agg["CTR (%)"]  = (agg["clicks"] / imp * 100).round(2)
    agg["CPM (R$)"] = (agg["spend"] / imp * 1000).round(2)
    if "action__lead" in agg.columns:
        leads = pd.to_numeric(agg["action__lead"], errors="coerce").replace(0, float("nan"))
        agg["CPL (R$)"] = (agg["spend"] / leads).round(2)
    else:
        agg["CPL (R$)"] = float("nan")
    return agg
