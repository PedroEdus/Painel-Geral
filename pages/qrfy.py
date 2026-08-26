import pandas as pd
import streamlit as st
from datetime import date

from core.theme import aplicar_tema
from core.ui import cabecalho, kpis
from core.format import _br, VERDE
from core.charts import grafico_evolucao, grafico_donut, grafico_barras_h_card
from sources.qrfy import carregar_dados

aplicar_tema()

cabecalho("QRFY — Leituras de QR Code", "Protótipo — scans dos QR codes por período, local e dispositivo")

# ── Carregar Dados ────────────────────────────────────────────────────────────
with st.spinner("Carregando dados da QRFY..."):
    df = carregar_dados()

if df.empty:
    st.info("Sem dados de QRFY carregados no BigQuery ainda.")
    st.stop()

# ── Filtros (Sidebar) ─────────────────────────────────────────────────────────
st.sidebar.header("Filtros")

if "data" in df.columns:
    datas = sorted(df["data"].dropna().unique())
    if len(datas) >= 2:
        data_min, data_max = min(datas), max(datas)
        data_sel = st.sidebar.date_input(
            "Período", [data_min, data_max], min_value=data_min, max_value=data_max,
            format="DD/MM/YYYY",
        )
        if isinstance(data_sel, (list, tuple)) and len(data_sel) == 2:
            df = df[(df["data"] >= data_sel[0]) & (df["data"] <= data_sel[1])]

if "folder" in df.columns:
    pastas_opts = sorted(df["folder"].dropna().unique().tolist())
    pastas_sel = st.sidebar.multiselect("Pasta", pastas_opts, placeholder="Todas")
    if pastas_sel:
        df = df[df["folder"].isin(pastas_sel)]

if "name" in df.columns:
    qrs_opts = sorted(df["name"].dropna().unique().tolist())
    qrs_sel = st.sidebar.multiselect("QR code", qrs_opts, placeholder="Todos")
    if qrs_sel:
        df = df[df["name"].isin(qrs_sel)]

if "city" in df.columns:
    cidades_opts = sorted(df["city"].dropna().unique().tolist())
    cidades_sel = st.sidebar.multiselect("Cidade", cidades_opts, placeholder="Todas")
    if cidades_sel:
        df = df[df["city"].isin(cidades_sel)]

if "os" in df.columns:
    os_opts = sorted(df["os"].dropna().unique().tolist())
    os_sel = st.sidebar.multiselect("Sistema operacional", os_opts, placeholder="Todos")
    if os_sel:
        df = df[df["os"].isin(os_sel)]

if df.empty:
    st.warning("Nenhum dado encontrado para os filtros selecionados.")
    st.stop()

# ── KPIs ──────────────────────────────────────────────────────────────────────
total_leituras = len(df)
visitantes_unicos = int(df["visitante_unico"].sum())
qrs_ativos = df["name"].nunique()
cidades_atingidas = df["cidade_qr"].nunique()
pct_unico = (visitantes_unicos / total_leituras * 100) if total_leituras else 0

kpis({
    "Leituras":          _br(total_leituras),
    "Visitantes únicos": _br(visitantes_unicos),
    "% Visitante único": _br(pct_unico, 1) + "%",
    "QR codes ativos":   _br(qrs_ativos),
    "Cidades atingidas": _br(cidades_atingidas),
})
st.divider()

# ── Evolução + QR codes mais lidos (lado a lado) ─────────────────────────────
col1, col2 = st.columns(2)
with col1:
    grafico_evolucao(df, "data", "leitura", "Leituras por dia", cor=VERDE,
                     fmt=lambda v: _br(v), key="qrfy_evol")
with col2:
    top_qrs = df.groupby("name", as_index=False)["leitura"].sum()
    grafico_barras_h_card(top_qrs, "leitura", "name", "QR codes mais lidos", top_n=20,
                          fmt=lambda v: _br(v), altura=450)

# ── Dispositivo ───────────────────────────────────────────────────────────────
col1, col2 = st.columns(2)
with col1:
    grafico_donut(df, "os", "leitura", "Leituras por sistema operacional")
with col2:
    grafico_donut(df, "folder", "leitura", "Leituras por pasta", altura=320)

# ── Cidade do QR (extraída do nome) ──────────────────────────────────────────
sem_cidade = df["cidade_qr"].isna().sum()
st.caption(
    f"Cidade identificada dentro do nome do QR, cruzando com as cidades do ClickMenos. "
    f"{sem_cidade} leitura(s) sem cidade reconhecida no nome ficaram de fora."
)
agg_cidade_qr = (
    df.dropna(subset=["cidade_qr"])
    .groupby("cidade_qr", as_index=False)["leitura"].sum()
)
grafico_barras_h_card(agg_cidade_qr, "leitura", "cidade_qr", "Leituras por cidade do QR",
                      top_n=20, fmt=lambda v: _br(v))
