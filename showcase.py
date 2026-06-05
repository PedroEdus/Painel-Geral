"""
Showcase dos componentes padrão — usa dados reais do Meta Ads (silver.meta_ads).
Cada bloco traz um caption com o nome da função de components.py que o gera.

Rodar:  streamlit run showcase.py
"""
import pandas as pd
import streamlit as st

import components as c
from data_meta import agregar_por_campanha, carregar_dados

st.set_page_config(page_title="Showcase de Componentes — Buriti", page_icon="📊", layout="wide")

c.aplicar_tema()
c.exibir_logo()
st.title("Showcase de Componentes")
st.caption("Biblioteca padrão `components.py` aplicada a dados reais do Meta Ads (`silver.meta_ads`).")

# ── Dados ───────────────────────────────────────────────────────────────────
try:
    with st.spinner("Carregando dados do BigQuery..."):
        raw = carregar_dados()
except Exception as e:
    st.error(f"Erro ao carregar dados: {e}")
    st.stop()

if raw.empty:
    st.warning("Nenhum dado encontrado em silver.meta_ads.")
    st.stop()

# ── Filtros (sidebar) ─────────────────────────────────────────────────────────
st.sidebar.header("Filtros")

dmin, dmax = raw["date_start"].min().date(), raw["date_start"].max().date()
periodo = st.sidebar.date_input("Período", value=(dmax - pd.Timedelta(days=180), dmax),
                                min_value=dmin, max_value=dmax)
raw_f = raw.copy()
if isinstance(periodo, tuple) and len(periodo) == 2:
    raw_f = raw_f[(raw_f["date_start"].dt.date >= periodo[0]) & (raw_f["date_start"].dt.date <= periodo[1])]

objs = sorted(raw_f["objective"].dropna().unique().tolist())
sel_obj = st.sidebar.multiselect("Objetivo", objs, placeholder="Todos")
if sel_obj:
    raw_f = raw_f[raw_f["objective"].isin(sel_obj)]

tipos = ["Todos"] + sorted(raw_f["Tipo_Lancamento"].dropna().unique().tolist())
sel_tipo = st.sidebar.selectbox("Tipo", tipos)
if sel_tipo != "Todos":
    raw_f = raw_f[raw_f["Tipo_Lancamento"] == sel_tipo]

if raw_f.empty:
    st.warning("Sem dados para os filtros selecionados.")
    st.stop()

agg = agregar_por_campanha(raw_f)

# Mapa de cor por objetivo, indexado pelo rótulo traduzido (para o donut)
obj_color_label: dict[str, str] = {}
for _k, _v in c.OBJECTIVE_COLOR_MAP.items():
    obj_color_label.setdefault(c.label_obj(_k), _v)

# ════════════════════════════════════════════════════════════════════════════
# KPIs  →  components.kpis(dict)
# ════════════════════════════════════════════════════════════════════════════
st.caption("`kpis(dict)` — linha de métricas genérica")
_imp, _clk = raw_f["impressions"].sum(), raw_f["clicks"].sum()
_spend, _leads = raw_f["spend"].sum(), raw_f["action__lead"].sum()
c.kpis({
    "Investimento": c._br(_spend, 2, "R$ "),
    "Impressões":   c._br(_imp),
    "Cliques":      c._br(_clk),
    "Alcance":      c._br(raw_f["reach"].sum()),
    "Leads":        c._br(_leads),
    "CTR":          c._br((_clk / _imp * 100) if _imp else 0, 2) + "%",
    "CPL":          c._br((_spend / _leads) if _leads else 0, 2, "R$ "),
})
st.divider()

# ════════════════════════════════════════════════════════════════════════════
# Abas
# ════════════════════════════════════════════════════════════════════════════
ab_evo, ab_rank, ab_camp, ab_tab, ab_sem = st.tabs([
    "📈 Evolução", "🏆 Ranking & Donuts", "🗂️ Por campanha", "📋 Tabelas", "🚦 Semáforo & Badges",
])

# ── Evolução ──────────────────────────────────────────────────────────────────
with ab_evo:
    st.caption("`grafico_evolucao(df, date_col, value_col, ...)` — área (diário) / barras (mensal)")
    c.grafico_evolucao(raw_f, "date_start", "spend", "Investimento",
                       cor=c.VERDE, fmt=lambda v: c._br(v, 2, "R$ "), key="evo_spend")

    st.divider()
    mensal = raw_f.copy()
    mensal["mes"] = mensal["date_start"].dt.to_period("M").dt.to_timestamp()

    col1, col2 = st.columns(2)
    with col1:
        st.caption("`grafico_barras_mensais(...)` — simples")
        m_imp = mensal.groupby("mes", as_index=False)["impressions"].sum()
        c.grafico_barras_mensais(m_imp, "mes", "impressions", "Impressões por mês")
    with col2:
        st.caption("`grafico_barras_mensais(..., color=...)` — empilhado por tipo")
        m_tipo = mensal.groupby(["mes", "Tipo_Lancamento"], as_index=False)["spend"].sum()
        c.grafico_barras_mensais(m_tipo, "mes", "spend", "Investimento por mês × tipo",
                                 color="Tipo_Lancamento", color_map=c.LANCAMENTO_COLOR_MAP)

# ── Ranking & Donuts ───────────────────────────────────────────────────────────
with ab_rank:
    st.caption("`grafico_barras_h_card(...)` — ranking top-N (barra horizontal)")
    top = agg.groupby("campaign_name", as_index=False)["spend"].sum()
    c.grafico_barras_h_card(top, "spend", "campaign_name", "Top campanhas — Investimento",
                            top_n=12, fmt=lambda v: c._br(v, 2, "R$ "))

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.caption("`grafico_donut(..., total_centro=True, label_func=...)`")
        c.grafico_donut(raw_f, "objective", "spend", "Investimento por objetivo",
                        color_map=obj_color_label, total_centro=True,
                        fmt=lambda v: c._br(v, 2, "R$ "), label_func=c.label_obj)
    with col2:
        st.caption("`grafico_donut(...)` — por tipo de campanha")
        c.grafico_donut(raw_f, "Tipo_Lancamento", "clicks", "Cliques por tipo",
                        color_map=c.LANCAMENTO_COLOR_MAP)

# ── Por campanha (paginado) ─────────────────────────────────────────────────────
with ab_camp:
    st.caption("`grafico_barras_campanha(...)` — paginado (20/pág), colorido por tipo")
    c.grafico_barras_campanha(raw_f, "spend", "Investimento por campanha (R$)", key="bar_camp",
                              fmt=lambda v: c._br(v, 2, "R$ "),
                              cor_por="Tipo_Lancamento", color_map=c.LANCAMENTO_COLOR_MAP)

# ── Tabelas ──────────────────────────────────────────────────────────────────
with ab_tab:
    st.caption("`tabela_html(...)` — tabela estilizada com badges e linha TOTAL")
    resumo = raw_f.groupby("objective", as_index=False).agg(
        Campanhas=("campaign_name", "nunique"),
        impressions=("impressions", "sum"),
        clicks=("clicks", "sum"),
        spend=("spend", "sum"),
        action__lead=("action__lead", "sum"),
    )
    _imp_r = resumo["impressions"].replace(0, float("nan"))
    resumo["CTR (%)"]  = (resumo["clicks"] / _imp_r * 100).round(2)
    resumo["CPL (R$)"] = (resumo["spend"] / resumo["action__lead"].replace(0, float("nan"))).round(2)
    c.tabela_html(
        resumo,
        col_specs=[
            {"key": "objective",    "header": "Objetivo"},
            {"key": "Campanhas",    "header": "Campanhas",         "num": True},
            {"key": "impressions",  "header": "Impressões",        "num": True},
            {"key": "clicks",       "header": "Cliques",           "num": True},
            {"key": "CTR (%)",      "header": "CTR (%)",           "num": True, "dec": 2, "somar": False},
            {"key": "spend",        "header": "Investimento (R$)", "num": True, "dec": 2, "pref": "R$ "},
            {"key": "action__lead", "header": "Leads",             "num": True},
            {"key": "CPL (R$)",     "header": "CPL (R$)",          "num": True, "dec": 2, "pref": "R$ ", "somar": False},
        ],
        com_total=True, badge_col="objective",
        badge_map=c.OBJECTIVE_COLOR_MAP, badge_label=c.label_obj,
    )

    st.divider()
    st.caption("`tabela(df)` — dataframe nativo (dado bruto / export)")
    cols_show = ["campaign_name", "objective", "Tipo_Lancamento", "spend",
                 "impressions", "clicks", "action__lead", "CTR (%)", "CPL (R$)"]
    c.tabela(agg[[col for col in cols_show if col in agg.columns]].head(50))

# ── Semáforo & Badges ──────────────────────────────────────────────────────────
with ab_sem:
    st.caption("`badge_html(...)` — pílulas coloridas por categoria")
    badges = " ".join(c.badge_html(o, c.OBJECTIVE_COLOR_MAP, c.label_obj)
                      for o in raw_f["objective"].dropna().unique()[:10])
    c._html(f'<div class="pub-card"><div class="pub-card-title">Objetivos</div>{badges}</div>')

    st.divider()
    st.caption("`_dot()` + `cor_cpc()` — semáforo de CPC vs. média (verde/amarelo/vermelho)")
    base = agg.copy()
    base["CPC"] = (base["spend"] / base["clicks"].replace(0, pd.NA)).round(2)
    base = base[base["CPC"].notna() & (base["CPC"] > 0)].nlargest(10, "spend")
    media_cpc = base["CPC"].mean()
    rows = ""
    for _, r in base.iterrows():
        cor = c.cor_cpc(float(r["CPC"]), media_cpc)
        nome = (str(r["campaign_name"])[:48] + "…") if len(str(r["campaign_name"])) > 48 else r["campaign_name"]
        rows += (f'<div style="display:flex;align-items:center;padding:6px 0;border-bottom:1px solid #1f1f1f">'
                 f'{c._dot(cor)}<span style="flex:1;font-size:13px">{nome}</span>'
                 f'<span style="font-family:JetBrains Mono,monospace;font-size:12px">{c._br(float(r["CPC"]), 2, "R$ ")}</span></div>')
    c._html(f'<div class="pub-card"><div class="pub-card-title">CPC por campanha · média {c._br(media_cpc, 2, "R$ ")}</div>{rows}</div>')
