import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import date

from core.theme import aplicar_tema
from core.ui import exibir_logo, kpis, botao_download_csv
from core.format import (
    _br, 
    _rgba,
    VERDE, 
    LANCAMENTO_COLOR_MAP, 
    CHANNEL_COLORS_GADS, 
    CHANNEL_LABELS_GADS
)
from core.charts import (
    _LAYOUT_BASE, 
    _titulo_layout, 
    _tema, 
    _html,
    grafico_evolucao,
    grafico_donut,
    grafico_barras_h_card,
    tabela_matriz_html
)
from sources.google_ads import carregar_google_ads

aplicar_tema()

st.title("Google Ads — Buriti")

# ── Carregar Dados ────────────────────────────────────────────────────────────
with st.spinner("Carregando dados do Google Ads..."):
    df = carregar_google_ads()

if df.empty:
    st.info("Sem dados de Google Ads cadastrados ou disponíveis no BigQuery.")
    st.stop()

# Calcular campanhas ativas (que possuem dados na última data de extração, D-1)
max_date_gads = df["date"].max()
camp_max_dates_gads = df.groupby("campaign_name")["date"].max()
active_campaigns_gads = set(camp_max_dates_gads[camp_max_dates_gads == max_date_gads].index.tolist())

# ── Filtros (Sidebar) ─────────────────────────────────────────────────────────
st.sidebar.header("Filtros")

df_orig = df.copy()

# 1. Período
dmin, dmax = df["date"].min().date(), df["date"].max().date()
default_start = max(date(2026, 1, 1), dmin)
periodo = st.sidebar.date_input("Período", value=(default_start, dmax), min_value=dmin, max_value=dmax)
if isinstance(periodo, tuple) and len(periodo) == 2:
    df = df[(df["date"].dt.date >= periodo[0]) & (df["date"].dt.date <= periodo[1])]

# 2. Tipo de campanha
tipos_opts = ["Lançamento", "Estoque", "Outros"]
sel_tipo = st.sidebar.multiselect("Tipo de campanha", tipos_opts, placeholder="Todos")
if sel_tipo:
    df = df[df["Tipo_Lancamento"].isin(sel_tipo)]

# 3. Conta
contas_opts = sorted(df_orig["customer_name"].dropna().unique())
sel_conta = st.sidebar.multiselect("Conta", contas_opts, placeholder="Todas")
if sel_conta:
    df = df[df["customer_name"].isin(sel_conta)]

# 4. UF
ufs_opts = sorted(df_orig["UF"].dropna().unique())
sel_uf = st.sidebar.multiselect("UF", ufs_opts, placeholder="Todas")
if sel_uf:
    df = df[df["UF"].isin(sel_uf) | df["UF"].isna()]

# 5. Cidade (cascateia após UF)
df_para_cidade = df_orig[df_orig["UF"].isin(sel_uf)] if sel_uf else df_orig
cidades_opts = sorted(
    df_para_cidade["Cidade"].dropna()
    .loc[lambda s: s != "Não identificado"].unique()
)
sel_cidade = st.sidebar.multiselect("Cidade", cidades_opts, placeholder="Todas")
if sel_cidade:
    df = df[df["Cidade"].isin(sel_cidade) | (df["Cidade"] == "Não identificado") | df["Cidade"].isna()]

# 6. Campanha
campanhas_opts = sorted(df["campaign_name"].dropna().unique())
sel_campanha = st.sidebar.multiselect("Campanha", campanhas_opts, placeholder="Todas")
if sel_campanha:
    df = df[df["campaign_name"].isin(sel_campanha)]

# 7. Status da campanha
sel_status = st.sidebar.selectbox("Status da campanha", ["Todas", "Ativas", "Inativas"])
if sel_status == "Ativas":
    df = df[df["campaign_name"].isin(active_campaigns_gads)]
elif sel_status == "Inativas":
    df = df[~df["campaign_name"].isin(active_campaigns_gads)]

# ── Validar Estado Pós-Filtros ────────────────────────────────────────────────
if df.empty:
    st.warning("Nenhum dado encontrado para a combinação de filtros selecionada.")
    st.stop()

# ── KPIs ──────────────────────────────────────────────────────────────────────
custo = df["cost"].sum()
clk = df["clicks"].sum()
imp = df["impressions"].sum()
ctr = (clk / imp * 100) if imp else 0
cpc = (custo / clk) if clk else 0

kpis({
    "Investimento": _br(custo, 2, "R$ "),
    "Cliques":      _br(clk),
    "Impressões":   _br(imp),
    "CTR médio":    _br(ctr, 2) + "%",
    "CPC médio":    _br(cpc, 2, "R$ "),
})
st.divider()

# ── Helpers Específicos do CPC ────────────────────────────────────────────────
def exibir_evolucao_cpc(df_cpc):
    gran = st.radio("Visualização", ["Diário", "Mensal"], horizontal=True, key="cpc_gran", label_visibility="collapsed")
    d = df_cpc.copy()
    d["date"] = pd.to_datetime(d["date"])
    if gran == "Mensal":
        d["periodo"] = d["date"].dt.to_period("M").dt.to_timestamp()
    else:
        d["periodo"] = d["date"].dt.normalize()
        
    agg = d.groupby("periodo", as_index=False)[["cost", "clicks"]].sum()
    agg["cpc"] = agg["cost"] / agg["clicks"].replace(0, float("nan"))
    agg["cpc"] = agg["cpc"].fillna(0.0)

    titulo_full = f"Custo por clique (R$) ({'mês' if gran == 'Mensal' else 'dia'})"

    if gran == "Mensal":
        agg["periodo_str"] = agg["periodo"].dt.strftime("%b/%Y")
        y_max = float(agg["cpc"].max()) or 1
        fig = px.bar(agg, x="periodo_str", y="cpc")
        fig.update_traces(
            marker_color="#33aa77", text=[_br(v, 2, "R$ ") for v in agg["cpc"]],
            texttemplate="%{text}", textposition="outside",
            textfont=dict(size=10, color="rgba(255,255,255,0.7)"), cliponaxis=False,
        )
        fig.update_layout(**{**_LAYOUT_BASE, **dict(
            height=400, bargap=0.28,
            xaxis=dict(title=None, type="category", gridcolor="#2a2a2a"),
            yaxis=dict(title=None, gridcolor="#2a2a2a", range=[0, y_max * 1.22]),
            title=_titulo_layout(titulo_full),
        )})
    else:
        fig = px.area(agg, x="periodo", y="cpc", color_discrete_sequence=["#33aa77"])
        fig.update_traces(line=dict(width=2, color="#33aa77"), fillcolor=_rgba("#33aa77", 0.13))
        fig.update_layout(**{**_LAYOUT_BASE, **dict(height=380, title=_titulo_layout(titulo_full))})
        
    st.plotly_chart(fig, use_container_width=True)

def exibir_cpc_agrupado(df_cpc, coluna_grupo, titulo, color_map=None):
    agg = df_cpc.groupby(coluna_grupo, as_index=False).agg(
        cost=("cost", "sum"), clicks=("clicks", "sum")
    )
    agg["cpc"] = agg["cost"] / agg["clicks"].replace(0, float("nan"))
    agg = agg[agg["cpc"] > 0].sort_values("cpc", ascending=False)
    
    if coluna_grupo == "advertising_channel_type":
        agg["_label"] = agg[coluna_grupo].map(lambda x: CHANNEL_LABELS_GADS.get(str(x), str(x)))
        agg["_color"] = agg["_label"].map(lambda x: CHANNEL_COLORS_GADS.get(x, "#888888"))
    else:
        agg["_label"] = agg[coluna_grupo]
        agg["_color"] = agg[coluna_grupo].map(lambda x: (color_map or LANCAMENTO_COLOR_MAP).get(x, "#888888"))

    if agg.empty:
        _html(f'<div class="pub-card"><div class="pub-card-title">{titulo}</div><div style="color:#888">Sem dados.</div></div>')
        return

    max_val = agg["cpc"].max() or 1
    rows_html = ""
    for _, row in agg.iterrows():
        bar_w = row["cpc"] / max_val * 100
        val = _br(row["cpc"], 2, "R$ ")
        name = str(row["_label"])
        rows_html += (
            f'<div class="pub-bar-row">'
            f'<div class="pub-bar-name" title="{name}">{name}</div>'
            f'<div class="pub-bar-track">'
            f'<div class="pub-bar-fill" style="width:{bar_w:.2f}%;background:{row["_color"]};"></div>'
            f'</div>'
            f'<div class="pub-bar-value">{val}</div>'
            f'</div>'
        )
    _html(f'<div class="pub-card"><div class="pub-card-title">{titulo}</div><div class="pub-bar-list">{rows_html}</div></div>')

def agregar_por_campanha_gads(df_gads: pd.DataFrame) -> pd.DataFrame:
    """Agrega df de Google Ads filtrado por campaign_name e computa métricas."""
    if df_gads.empty:
        return df_gads
    
    group_keys = [c for c in ["campaign_name", "customer_name", "Tipo_Lancamento", "Cidade", "UF"]
                  if c in df_gads.columns]
    
    agg = df_gads.groupby(group_keys, as_index=False).agg(
        impressions=("impressions", "sum"),
        clicks=("clicks", "sum"),
        cost=("cost", "sum"),
    )
    
    imp = agg["impressions"].replace(0, pd.NA)
    clk = agg["clicks"].replace(0, pd.NA)
    agg["CTR (%)"] = (agg["clicks"] / imp * 100).round(2)
    agg["CPC (R$)"] = (agg["cost"] / clk).round(2)
    
    return agg


def exibir_matriz_gads(df_tabela, active_campaigns, df_download):
    col_specs = [
        {"header": "Hierarquia (Conta ➔ UF ➔ Cidade ➔ Campanha)", "key": "name"},
        {"header": "Campanhas", "key": "campaign_name", "dec": 0},
        {"header": "Impressões", "key": "impressions", "dec": 0},
        {"header": "Cliques", "key": "clicks", "dec": 0},
        {"header": "CTR (%)", "key": "CTR", "dec": 2, "is_pct": True},
        {"header": "Investimento", "key": "cost", "dec": 2, "pref": "R$ "},
        {"header": "CPC (R$)", "key": "CPC", "dec": 2, "pref": "R$ "},
    ]
    agg_rules = {
        "campaign_name": "nunique",
        "impressions": "sum",
        "clicks": "sum",
        "cost": "sum",
    }
    def derived_gads(agg):
        imp = agg.get("impressions", 0)
        clk = agg.get("clicks", 0)
        cst = agg.get("cost", 0)
        
        ctr = (clk / imp * 100) if imp else 0
        cpc = (cst / clk) if clk else 0
        return {"CTR": ctr, "CPC": cpc}

    tabela_matriz_html(
        df=df_tabela,
        group_cols=["customer_name", "UF", "Cidade", "campaign_name"],
        col_specs=col_specs,
        agg_rules=agg_rules,
        derived_func=derived_gads,
        grid_template="minmax(320px, 3.5fr) 0.8fr 1fr 1fr 0.8fr 1.2fr 1.2fr",
        active_campaigns=active_campaigns,
        key="gads",
        df_download=df_download,
        download_filename="google_ads_campanhas.csv",
        download_label="⬇️ Baixar CSV"
    )


# ── Abas ──────────────────────────────────────────────────────────────────────
aba_gasto, aba_cliques, aba_cpc, aba_tabela = st.tabs([
    "💰 Valor Gasto", "🖱️ Cliques", "💵 Custo por Clique", "📋 Tabela"
])

with aba_gasto:
    grafico_evolucao(df, "date", "cost", "Investimento", cor=VERDE, fmt=lambda v: _br(v, 2, "R$ "), key="google_spend")
    c1, c2 = st.columns(2)
    with c1:
        grafico_donut(df, "Tipo_Lancamento", "cost", "Investimento por tipo", color_map=LANCAMENTO_COLOR_MAP)
    with c2:
        grafico_donut(df, "advertising_channel_type", "cost", "Investimento por canal", 
                      color_map=CHANNEL_COLORS_GADS, label_func=lambda x: CHANNEL_LABELS_GADS.get(str(x), str(x)))

with aba_cliques:
    grafico_evolucao(df, "date", "clicks", "Cliques", cor="#00b359", fmt=lambda v: _br(v), key="google_clicks")
    c1, c2 = st.columns(2)
    with c1:
        grafico_donut(df, "Tipo_Lancamento", "clicks", "Cliques por tipo", color_map=LANCAMENTO_COLOR_MAP)
    with c2:
        grafico_donut(df, "advertising_channel_type", "clicks", "Cliques por canal", 
                      color_map=CHANNEL_COLORS_GADS, label_func=lambda x: CHANNEL_LABELS_GADS.get(str(x), str(x)))

with aba_cpc:
    exibir_evolucao_cpc(df)
    c1, c2 = st.columns(2)
    with c1:
        exibir_cpc_agrupado(df, "Tipo_Lancamento", "CPC médio por tipo")
    with c2:
        exibir_cpc_agrupado(df, "advertising_channel_type", "CPC médio por canal")

with aba_tabela:
    st.subheader("Matriz de Desempenho (Conta ➔ UF ➔ Cidade ➔ Campanha)")
    
    df_agg = agregar_por_campanha_gads(df)
    n_camps = df_agg["campaign_name"].nunique() if "campaign_name" in df_agg.columns else 0
    n_active = df_agg[df_agg["campaign_name"].isin(active_campaigns_gads)]["campaign_name"].nunique() if "campaign_name" in df_agg.columns else 0
    
    st.caption(f"{n_camps} campanha(s) exibida(s) · {n_active} ativa(s) · Clique em ▶ para expandir")
    exibir_matriz_gads(df, active_campaigns_gads, df_agg)

