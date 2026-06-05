import pandas as pd
import streamlit as st
from core.bq import get_client, PROJECT_ID

DATASET = "buriti_marketing_raw"
_NUMERIC_OVERVIEW = [
    "sessions", "totalUsers", "newUsers", "engagedSessions",
    "engagementRate", "bounceRate", "screenPageViews", "averageSessionDuration",
]
_NUMERIC_UTM = ["sessions", "totalUsers", "engagedSessions", "screenPageViews"]

# Regras de agrupamento de mídias/origens GA4
_PAID_MEDIUMS   = {"cpc", "cpm", "paid", "lead_ad", "native_ad", "link_ad",
                   "banner_300x250", "reconhecimento", "formulario", "story", "lamina"}
_SOCIAL_MEDIUMS = {"whatsapp", "instagram_buriti", "social", "instagram"}
_SOCIAL_SOURCES = {"linktree", "l.wl.co", "facebook.com", "instagram.com"}

def classificar_canal(medium: str, source: str) -> str:
    """Classifica a origem e mídia em canais de tráfego amigáveis do GA4."""
    m = str(medium).lower().strip()
    s = str(source).lower().strip()
    if m == "organic":
        return "Orgânico"
    if s == "(direct)" and m in {"(none)", "", "(not set)"}:
        return "Direto"
    if m in _PAID_MEDIUMS:
        return "Pago"
    if m in _SOCIAL_MEDIUMS or s in _SOCIAL_SOURCES:
        return "Social"
    if m == "referral":
        return "Referência"
    return "Outros"

def _parse_date(df: pd.DataFrame) -> pd.DataFrame:
    """GA4 retorna datas como YYYYMMDD string -> converte para datetime."""
    if "date" in df.columns:
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"].astype(str), format="%Y%m%d", errors="coerce")
    return df

@st.cache_data(ttl=3600)
def carregar_overview() -> pd.DataFrame:
    """Carrega dados gerais (Overview) do GA4 dedupados por property_id e date."""
    client = get_client()
    query  = f"""
        SELECT * EXCEPT(rn)
        FROM (
            SELECT *,
                   ROW_NUMBER() OVER (
                       PARTITION BY property_id, date
                       ORDER BY _loaded_at DESC
                   ) AS rn
            FROM `{PROJECT_ID}.{DATASET}.ga4_overview_raw`
        )
        WHERE rn = 1
        ORDER BY date DESC
    """
    try:
        df = client.query(query).to_dataframe()
    except Exception as e:
        st.warning(f"Erro ao carregar dados do GA4 Overview: {e}")
        return pd.DataFrame()

    df = _parse_date(df)
    for col in _NUMERIC_OVERVIEW:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df

@st.cache_data(ttl=3600)
def carregar_utm() -> pd.DataFrame:
    """Carrega dados detalhados de UTM do GA4 dedupados pela chave UTM completa."""
    client = get_client()
    query  = f"""
        SELECT * EXCEPT(rn)
        FROM (
            SELECT *,
                   ROW_NUMBER() OVER (
                       PARTITION BY property_id, date, landingPage,
                                    sessionSource, sessionMedium,
                                    sessionCampaignName, sessionManualAdContent
                       ORDER BY _loaded_at DESC
                   ) AS rn
            FROM `{PROJECT_ID}.{DATASET}.ga4_utm_raw`
        )
        WHERE rn = 1
        ORDER BY date DESC
    """
    try:
        df = client.query(query).to_dataframe()
    except Exception as e:
        st.warning(f"Erro ao carregar dados do GA4 UTM: {e}")
        return pd.DataFrame()

    df = _parse_date(df)
    for col in _NUMERIC_UTM:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df
