import pandas as pd
import streamlit as st
from datetime import date

from core.theme import aplicar_tema
from core.ui import cabecalho, exibir_logo, kpis, botao_download_csv
from core.format import (
    _br, 
    _rgba,
    VERDE, 
    LANCAMENTO_COLOR_MAP, 
    OBJECTIVE_COLOR_MAP, 
    OBJECTIVE_LABELS,
    label_obj
)
from core.charts import (
    _LAYOUT_BASE, 
    _titulo_layout, 
    _tema, 
    _html,
    grafico_evolucao,
    grafico_donut,
    tabela,
    tabela_matriz_html
)
from sources.meta import carregar_dados, agregar_por_campanha

aplicar_tema()

cabecalho("Meta Ads — Campanhas", "Performance de campanhas Meta")

# ── Carregar Dados ────────────────────────────────────────────────────────────
with st.spinner("Carregando dados do Meta Ads..."):
    df = carregar_dados()

if df.empty:
    st.info("Sem dados de Meta Ads cadastrados ou disponíveis no BigQuery.")
    st.stop()

# Calcular campanhas ativas (que possuem dados na última data de extração, D-1)
max_date_meta = df["date_start"].max()
camp_max_dates_meta = df.groupby("campaign_name")["date_start"].max()
active_campaigns_meta = set(camp_max_dates_meta[camp_max_dates_meta == max_date_meta].index.tolist())

# ── Filtros (Sidebar) ─────────────────────────────────────────────────────────
st.sidebar.header("Filtros")

# 1. Período
if "date_start" in df.columns:
    datas = sorted(df["date_start"].dropna().unique())
    if len(datas) >= 2:
        data_min, data_max = min(datas), max(datas)
        default_start = max(date(2026, 1, 1), data_min)
        data_sel = st.sidebar.date_input(
            "Período", [default_start, data_max], min_value=data_min, max_value=data_max
        )
        if isinstance(data_sel, list) or isinstance(data_sel, tuple):
            if len(data_sel) == 2:
                df = df[(df["date_start"] >= data_sel[0]) & (df["date_start"] <= data_sel[1])]

# 2. Tipo (Estoque / Lançamento)
if "Tipo_Lancamento" in df.columns:
    tipos_opts = ["Todos"] + sorted(df["Tipo_Lancamento"].dropna().unique().tolist())
    tipo_sel = st.sidebar.selectbox("Tipo", tipos_opts)
    if tipo_sel != "Todos":
        df = df[df["Tipo_Lancamento"] == tipo_sel]

# 3. UF
if "UF" in df.columns:
    ufs_opts = sorted(df["UF"].dropna().unique().tolist())
    if ufs_opts:
        uf_sel = st.sidebar.multiselect("UF", ufs_opts, placeholder="Todas")
        if uf_sel:
            df = df[df["UF"].isin(uf_sel)]

# 4. Cidade
if "Cidade" in df.columns:
    cidades_opts = sorted(df["Cidade"].dropna().unique().tolist())
    if cidades_opts:
        cidade_sel = st.sidebar.multiselect("Cidade", cidades_opts, placeholder="Todas")
        if cidade_sel:
            df = df[df["Cidade"].isin(cidade_sel)]

# 5. Objetivo
if "objective" in df.columns:
    objs_opts = ["Todos"] + sorted(df["objective"].dropna().unique().tolist())
    obj_sel = st.sidebar.selectbox("Objetivo", objs_opts)
    if obj_sel != "Todos":
        df = df[df["objective"] == obj_sel]

# 6. Campanhas
if "campaign_name" in df.columns:
    camps_opts = sorted(df["campaign_name"].dropna().unique().tolist())
    camps_sel = st.sidebar.multiselect("Campanhas", camps_opts, placeholder="Todas")
    if camps_sel:
        df = df[df["campaign_name"].isin(camps_sel)]

# 7. Status da campanha
status_sel = st.sidebar.selectbox("Status da campanha", ["Todas", "Ativas", "Inativas"])
if status_sel == "Ativas":
    df = df[df["campaign_name"].isin(active_campaigns_meta)]
elif status_sel == "Inativas":
    df = df[~df["campaign_name"].isin(active_campaigns_meta)]

# ── Validar Estado Pós-Filtros ────────────────────────────────────────────────
if df.empty:
    st.warning("Nenhum dado encontrado para os filtros selecionados.")
    st.stop()

# Agregar dados para visualização a nível de campanha
df_filtrado = agregar_por_campanha(df)

n_camps = df_filtrado["campaign_name"].nunique() if "campaign_name" in df_filtrado.columns else 0
n_active = df_filtrado[df_filtrado["campaign_name"].isin(active_campaigns_meta)]["campaign_name"].nunique() if "campaign_name" in df_filtrado.columns else 0
st.markdown(
    f"<div style='font-size:13px;color:#232329;'>{n_camps} campanha(s) exibida(s) · {n_active} ativa(s)</div>",
    unsafe_allow_html=True,
)

# ── KPIs ──────────────────────────────────────────────────────────────────────
# Calcula totais
spend_t = df["spend"].sum()
imp_t = df["impressions"].sum()
reach_t = df["reach"].sum()
clk_t = df["clicks"].sum()
leads_t = df["leads"].sum()
ctr_t = (clk_t / imp_t * 100) if imp_t else 0
cpl_t = (spend_t / leads_t) if leads_t else 0
cpm_t = (spend_t / imp_t * 1000) if imp_t else 0

kpis({
    "Investimento": _br(spend_t, 2, "R$ "),
    "Impressões":   _br(imp_t),
    "Alcance":      _br(reach_t),
    "Cliques":      _br(clk_t),
    "Leads":        _br(leads_t),
    "CTR":          _br(ctr_t, 2) + "%",
    "CPM":          _br(cpm_t, 2, "R$ "),
    "CPL":          _br(cpl_t, 2, "R$ "),
})
st.divider()

# Rótulo de cor por objetivo traduzido para uso no donut
obj_color_label = {}
for k, v in OBJECTIVE_COLOR_MAP.items():
    obj_color_label.setdefault(label_obj(k), v)

# ── Helpers de Tabelas e Visualizações ────────────────────────────────────────
def exibir_matriz_meta(df_tabela, active_campaigns, df_download):
    col_specs = [
        {"header": "Hierarquia (Conta ➔ UF ➔ Cidade ➔ Objetivo ➔ Campanha)", "key": "name"},
        {"header": "Campanhas", "key": "campaign_name", "dec": 0},
        {"header": "Impressões", "key": "impressions", "dec": 0},
        {"header": "Cliques", "key": "clicks", "dec": 0},
        {"header": "CTR (%)", "key": "CTR", "dec": 2, "is_pct": True},
        {"header": "Investimento", "key": "spend", "dec": 2, "pref": "R$ "},
        {"header": "Leads", "key": "leads", "dec": 0},
        {"header": "CPL (R$)", "key": "CPL", "dec": 2, "pref": "R$ "},
    ]
    agg_rules = {
        "campaign_name": "nunique",
        "impressions": "sum",
        "clicks": "sum",
        "spend": "sum",
        "leads": "sum",
    }
    def derived_meta(agg):
        imp = agg.get("impressions", 0)
        clk = agg.get("clicks", 0)
        spd = agg.get("spend", 0)
        lds = agg.get("leads", 0)
        
        ctr = (clk / imp * 100) if imp else 0
        cpl = (spd / lds) if lds else 0
        return {"CTR": ctr, "CPL": cpl}

    tabela_matriz_html(
        df=df_tabela,
        group_cols=["account_name", "UF", "Cidade", "objective", "campaign_name"],
        col_specs=col_specs,
        agg_rules=agg_rules,
        derived_func=derived_meta,
        grid_template="minmax(320px, 3.5fr) 0.8fr 1fr 1fr 0.8fr 1.2fr 0.8fr 1.2fr",
        active_campaigns=active_campaigns,
        key="meta",
        df_download=df_download,
        download_filename="meta_ads_detalhe_campanhas.csv",
        download_label="📥 Baixar CSV"
    )


# ── Abas ──────────────────────────────────────────────────────────────────────
aba_imp, aba_clk, aba_inv, aba_leads, aba_tab = st.tabs([
    "📢 Impressões", "🖱️ Cliques", "💰 Investimento", "🎯 Leads", "📋 Tabela"
])

with aba_imp:
    grafico_evolucao(df, "date_start", "impressions", "Impressões", cor=VERDE, fmt=lambda v: _br(v), key="meta_imp")
    col1, col2 = st.columns(2)
    with col1:
        grafico_donut(df, "objective", "impressions", "Impressões por objetivo", color_map=obj_color_label, label_func=label_obj)
    with col2:
        grafico_donut(df, "Tipo_Lancamento", "impressions", "Impressões por tipo", color_map=LANCAMENTO_COLOR_MAP)

with aba_clk:
    grafico_evolucao(df, "date_start", "clicks", "Cliques", cor="#4ab861", fmt=lambda v: _br(v), key="meta_clicks")
    col1, col2 = st.columns(2)
    with col1:
        grafico_donut(df, "objective", "clicks", "Cliques por objetivo", color_map=obj_color_label, label_func=label_obj)
    with col2:
        grafico_donut(df, "Tipo_Lancamento", "clicks", "Cliques por tipo", color_map=LANCAMENTO_COLOR_MAP)

with aba_inv:
    grafico_evolucao(df, "date_start", "spend", "Investimento", cor=VERDE, fmt=lambda v: _br(v, 2, "R$ "), key="meta_spend")
    col1, col2 = st.columns(2)
    with col1:
        grafico_donut(df, "objective", "spend", "Investimento por objetivo", color_map=obj_color_label, total_centro=True, fmt=lambda v: _br(v, 2, "R$ "), label_func=label_obj)
    with col2:
        grafico_donut(df, "Tipo_Lancamento", "spend", "Investimento por tipo", color_map=LANCAMENTO_COLOR_MAP)

with aba_leads:
    grafico_evolucao(df, "date_start", "leads", "Leads", cor="#008274", fmt=lambda v: _br(v), key="meta_leads")
    col1, col2 = st.columns(2)
    with col1:
        grafico_donut(df, "objective", "leads", "Leads por objetivo", color_map=obj_color_label, label_func=label_obj)
    with col2:
        grafico_donut(df, "Tipo_Lancamento", "leads", "Leads por tipo", color_map=LANCAMENTO_COLOR_MAP)

with aba_tab:
    st.subheader("Matriz de Desempenho (Conta ➔ UF ➔ Cidade ➔ Objetivo ➔ Campanha)")
    
    n_camps = df_filtrado["campaign_name"].nunique() if "campaign_name" in df_filtrado.columns else 0
    n_active = df_filtrado[df_filtrado["campaign_name"].isin(active_campaigns_meta)]["campaign_name"].nunique() if "campaign_name" in df_filtrado.columns else 0
    
    st.markdown(
        f"<div style='font-size:13px;color:#232329;'>{n_camps} campanha(s) exibida(s) · "
        f"{n_active} ativa(s) · Clique em ▶ para expandir</div>",
        unsafe_allow_html=True,
    )
    exibir_matriz_meta(df, active_campaigns_meta, df_filtrado)

