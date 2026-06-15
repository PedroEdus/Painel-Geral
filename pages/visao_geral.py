import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import date, timedelta

from core.theme import aplicar_tema
from core.ui import exibir_logo, kpis
from core.format import (
    _br, 
    _rgba,
    VERDE,
    CANAL_BRAND_COLORS
)
from core.charts import (
    _LAYOUT_BASE, 
    _titulo_layout, 
    _tema, 
    _html,
    grafico_donut,
    grafico_barras_h_card,
    grafico_barras_mensais,
    tabela_html
)

from sources.google_ads import carregar_google_ads
from sources.meta import carregar_dados as carregar_meta
from sources.ga4 import carregar_overview as carregar_ga4_overview
from sources.publya import carregar_publya
from sources.funil import carregar_leads as carregar_crm


# Apply visual theme
aplicar_tema()

st.title("Marketing Analytics")

# ── Carregar Todas as Fontes de Dados ────────────────────────────────────────
with st.spinner("Carregando bases de dados do BigQuery..."):
    df_gads = carregar_google_ads()
    df_meta = carregar_meta()
    df_ga4 = carregar_ga4_overview()
    df_publya = carregar_publya()
    df_funil = carregar_crm()


# ── Determinar Range de Datas Global ──────────────────────────────────────────
min_dates = []
max_dates = []

if not df_gads.empty:
    min_dates.append(df_gads["date"].min().date())
    max_dates.append(df_gads["date"].max().date())
if not df_meta.empty:
    min_dates.append(min(df_meta["date_start"]))
    max_dates.append(max(df_meta["date_start"]))
if not df_ga4.empty:
    min_dates.append(df_ga4["date"].min().date())
    max_dates.append(df_ga4["date"].max().date())

global_min = min(min_dates) if min_dates else date(2026, 1, 1)
global_max = max(max_dates) if max_dates else date(2026, 12, 31)

# Ensure min/max range limits allow for full year 2026 selection
limit_min = min(global_min, date(2026, 1, 1))
limit_max = max(global_max, date(2026, 12, 31))

# Filtro global de período na lateral
st.sidebar.header("Filtros")
periodo_sel = st.sidebar.date_input(
    "Período Global",
    value=(date(2026, 1, 1), date(2026, 12, 31)),
    min_value=limit_min,
    max_value=limit_max
)

start_date, end_date = global_min, global_max
if isinstance(periodo_sel, list) or isinstance(periodo_sel, tuple):
    if len(periodo_sel) == 2:
        start_date, end_date = periodo_sel[0], periodo_sel[1]
    elif len(periodo_sel) == 1:
        start_date, end_date = periodo_sel[0], periodo_sel[0]

# ── Aplicar Filtros de Datas Localmente ────────────────────────────────────────
gads = df_gads[(df_gads["date"].dt.date >= start_date) & (df_gads["date"].dt.date <= end_date)].copy() if not df_gads.empty else pd.DataFrame()
meta = df_meta[(df_meta["date_start"] >= start_date) & (df_meta["date_start"] <= end_date)].copy() if not df_meta.empty else pd.DataFrame()
ga4 = df_ga4[(df_ga4["date"].dt.date >= start_date) & (df_ga4["date"].dt.date <= end_date)].copy() if not df_ga4.empty else pd.DataFrame()
funil = df_funil[(df_funil["DataCadastro"].dt.date >= start_date) & (df_funil["DataCadastro"].dt.date <= end_date)].copy() if not df_funil.empty else pd.DataFrame()


# Publya possui datas por campanha (data_inicio / data_fim). Filtramos se houver overlap de datas.
publya = df_publya.copy() if not df_publya.empty else pd.DataFrame()
if not publya.empty:
    if "data_inicio" in publya.columns and publya["data_inicio"].notna().any():
        publya = publya[
            publya["data_inicio"].isna() |
            (publya["data_inicio"].dt.date >= start_date)
        ]
    if "data_fim" in publya.columns and publya["data_fim"].notna().any():
        publya = publya[
            publya["data_fim"].isna() |
            (publya["data_fim"].dt.date <= end_date)
        ]

# ── Separação dos Sites Institucionais e Empreendimentos (GA4) ───────────────
_INST_KEYWORDS = ["institucional", "btsa | site"]

def _is_inst(name: str) -> bool:
    n = str(name).lower()
    short = n.split("—")[-1].strip()
    return any(k in n for k in _INST_KEYWORDS) or short == "buriti empreendimentos"

def _nome_curto(full: str) -> str:
    return full.split("—")[-1].strip() if "—" in str(full) else str(full)

# Separa as propriedades de GA4
mask_ga4_inst = ga4["property_name"].apply(_is_inst) if not ga4.empty else pd.Series(dtype=bool)
ga4_inst_df = ga4[mask_ga4_inst].copy() if not ga4.empty else pd.DataFrame()
ga4_emp_df  = ga4[~mask_ga4_inst].copy() if not ga4.empty else pd.DataFrame()

ga4_inst_sessions = ga4_inst_df["sessions"].sum() if not ga4_inst_df.empty else 0.0
ga4_inst_users    = ga4_inst_df["totalUsers"].sum() if not ga4_inst_df.empty else 0.0

ga4_emp_sessions  = ga4_emp_df["sessions"].sum() if not ga4_emp_df.empty else 0.0
ga4_emp_users     = ga4_emp_df["totalUsers"].sum() if not ga4_emp_df.empty else 0.0

# ── Consolidação dos KPIs (Cross-channel) ─────────────────────────────────────
# Google Ads
gads_cost = gads["cost"].sum() if not gads.empty else 0.0
gads_clicks = gads["clicks"].sum() if not gads.empty else 0.0
gads_imp = gads["impressions"].sum() if not gads.empty else 0.0
# Google Ads conversions are forced to 0.0 (unreliable)
gads_conv = 0.0

# Meta Ads
meta_cost = meta["spend"].sum() if not meta.empty else 0.0
meta_clicks = meta["clicks"].sum() if not meta.empty else 0.0
meta_imp = meta["impressions"].sum() if not meta.empty else 0.0
meta_leads = meta["leads"].sum() if (not meta.empty and "leads" in meta.columns) else 0.0

# Publya
publya_cost = publya["budget"].sum() if not publya.empty else 0.0
publya_clicks = publya["clicks"].sum() if not publya.empty else 0.0
publya_imp = publya["impressions"].sum() if not publya.empty else 0.0
publya_conv = publya["conversions"].sum() if not publya.empty else 0.0

# Totais
total_spend = gads_cost + meta_cost + publya_cost
total_clicks = gads_clicks + meta_clicks + publya_clicks
total_imp = gads_imp + meta_imp + publya_imp
# Leads Totais ignora Google Ads
total_leads = meta_leads + publya_conv

# KPIs Row 1 (Métricas Absolutas)
kpis({
    "Investimento Total":       _br(total_spend, 2, "R$ "),
    "Impressões Totais":        _br(total_imp),
    "Cliques Totais":           _br(total_clicks),
    "Leads/Conversões":         _br(total_leads),
    "Sessões (Empreend.)":      _br(ga4_emp_sessions),
    "Usuários (Empreend.)":     _br(ga4_emp_users),
    "Sessões (Institucional)":  _br(ga4_inst_sessions),
    "Usuários (Institucional)": _br(ga4_inst_users)
})

# ── KPIs Row 2: Médias Diárias e Variação (Period-over-Period) ───────────────
# Período anterior equivalente
days_selected = (end_date - start_date).days + 1
prev_start = start_date - timedelta(days=days_selected)
prev_end = start_date - timedelta(days=1)

# Filtra período anterior
gads_prev = df_gads[(df_gads["date"].dt.date >= prev_start) & (df_gads["date"].dt.date <= prev_end)].copy() if not df_gads.empty else pd.DataFrame()
meta_prev = df_meta[(df_meta["date_start"] >= prev_start) & (df_meta["date_start"] <= prev_end)].copy() if not df_meta.empty else pd.DataFrame()

publya_prev = df_publya.copy() if not df_publya.empty else pd.DataFrame()
if not publya_prev.empty:
    if "data_inicio" in publya_prev.columns and publya_prev["data_inicio"].notna().any():
        publya_prev = publya_prev[publya_prev["data_inicio"].isna() | (publya_prev["data_inicio"].dt.date >= prev_start)]
    if "data_fim" in publya_prev.columns and publya_prev["data_fim"].notna().any():
        publya_prev = publya_prev[publya_prev["data_fim"].isna() | (publya_prev["data_fim"].dt.date <= prev_end)]

# Valores anteriores
gads_cost_prev = gads_prev["cost"].sum() if not gads_prev.empty else 0.0
gads_clicks_prev = gads_prev["clicks"].sum() if not gads_prev.empty else 0.0
gads_imp_prev = gads_prev["impressions"].sum() if not gads_prev.empty else 0.0

meta_cost_prev = meta_prev["spend"].sum() if not meta_prev.empty else 0.0
meta_clicks_prev = meta_prev["clicks"].sum() if not meta_prev.empty else 0.0
meta_imp_prev = meta_prev["impressions"].sum() if not meta_prev.empty else 0.0

publya_cost_prev = publya_prev["budget"].sum() if not publya_prev.empty else 0.0
publya_clicks_prev = publya_prev["clicks"].sum() if not publya_prev.empty else 0.0
publya_imp_prev = publya_prev["impressions"].sum() if not publya_prev.empty else 0.0

total_spend_prev = gads_cost_prev + meta_cost_prev + publya_cost_prev
total_clicks_prev = gads_clicks_prev + meta_clicks_prev + publya_clicks_prev
total_imp_prev = gads_imp_prev + meta_imp_prev + publya_imp_prev

# Médias diárias e taxas
avg_spend_sel = total_spend / days_selected
avg_clicks_sel = total_clicks / days_selected
avg_imp_sel = total_imp / days_selected
avg_cpc_sel = total_spend / total_clicks if total_clicks else 0.0
avg_cpm_sel = (total_spend / total_imp * 1000) if total_imp else 0.0

avg_spend_prev = total_spend_prev / days_selected
avg_clicks_prev = total_clicks_prev / days_selected
avg_imp_prev = total_imp_prev / days_selected
avg_cpc_prev = total_spend_prev / total_clicks_prev if total_clicks_prev else 0.0
avg_cpm_prev = (total_spend_prev / total_imp_prev * 1000) if total_imp_prev else 0.0

# Helper de variação percentual
def get_delta_str(curr, prev):
    if prev <= 0:
        return None
    pct = (curr - prev) / prev * 100
    return f"{pct:+.1f}% vs período ant."

st.markdown("<p style='font-size: 14px; font-weight:600; color:rgba(255,255,255,0.6); margin: 15px 0 5px;'>MÉDIAS DIÁRIAS (Comparação Período Anterior)</p>", unsafe_allow_html=True)
c_avg1, c_avg2, c_avg3, c_avg4, c_avg5 = st.columns(5)
c_avg1.metric("Média Gasto Diário", _br(avg_spend_sel, 2, "R$ "), delta=get_delta_str(avg_spend_sel, avg_spend_prev), delta_color="inverse")
c_avg2.metric("Média Cliques Diários", _br(avg_clicks_sel), delta=get_delta_str(avg_clicks_sel, avg_clicks_prev))
c_avg3.metric("Média Impressões Diárias", _br(avg_imp_sel), delta=get_delta_str(avg_imp_sel, avg_imp_prev))
c_avg4.metric("CPC Médio", _br(avg_cpc_sel, 2, "R$ "), delta=get_delta_str(avg_cpc_sel, avg_cpc_prev), delta_color="inverse")
c_avg5.metric("CPM Médio", _br(avg_cpm_sel, 2, "R$ "), delta=get_delta_str(avg_cpm_sel, avg_cpm_prev), delta_color="inverse")

# Helper de classificação do CRM
def classificar_canal_crm(row):
    source = str(row.get("UtmSource", "")).lower()
    forma = str(row.get("FormaCadastro", "")).lower()
    campaign = str(row.get("UtmCampaign", "")).lower()
    if "publya" in source or "publya" in forma or "publya" in campaign:
        return "Publya"
    elif any(k in source or k in forma for k in ["meta", "facebook", "instagram", "ig"]):
        return "Meta Ads"
    elif any(k in source or k in forma for k in ["google", "gads", "google-ads"]):
        return "Google Ads"
    return "Outros"

# Calcular métricas do CRM
if not funil.empty:
    funil_copy = funil.copy()
    funil_copy["Canal_Marketing"] = funil_copy.apply(classificar_canal_crm, axis=1)
    
    crm_leads_gads = int(funil_copy["Canal_Marketing"].eq("Google Ads").sum())
    crm_leads_meta = int(funil_copy["Canal_Marketing"].eq("Meta Ads").sum())
    crm_leads_publya = int(funil_copy["Canal_Marketing"].eq("Publya").sum())
    crm_leads_total = len(funil_copy)
    
    crm_ganhas = int(funil_copy["Etapa_NF"].eq("Venda Ganha").sum())
    crm_conversao = (crm_ganhas / crm_leads_total * 100) if crm_leads_total else 0.0
    paid_ganhas = int((funil_copy["Canal_Marketing"].isin(["Google Ads", "Meta Ads", "Publya"]) & funil_copy["Etapa_NF"].eq("Venda Ganha")).sum())
    # Ciclo Fecham. — mesma métrica do painel de funil: média de TempoCiclo_h dos Venda Ganha (horas)
    _tc_fech = funil_copy.loc[
        funil_copy["Etapa_NF"].eq("Venda Ganha")
        & funil_copy["TempoCiclo_h"].notna()
        & (funil_copy["TempoCiclo_h"] > 0),
        "TempoCiclo_h",
    ] if "TempoCiclo_h" in funil_copy.columns else pd.Series(dtype=float)
    tempo_medio_ganhas = round(float(_tc_fech.mean()), 1) if not _tc_fech.empty else None
else:
    crm_leads_gads = 0
    crm_leads_meta = 0
    crm_leads_publya = 0
    crm_leads_total = 0
    crm_ganhas = 0
    crm_conversao = 0.0
    paid_ganhas = 0
    tempo_medio_ganhas = None

# CPL CRM = gasto total de mídia ÷ leads que entraram no funil do CRM
cpl_crm = (total_spend / crm_leads_total) if crm_leads_total else None

st.markdown("<p style='font-size: 14px; font-weight:600; color:rgba(255,255,255,0.6); margin: 15px 0 5px;'>FUNIL E RESULTADOS DE VENDAS (CRM)</p>", unsafe_allow_html=True)
c_crm1, c_crm2, c_crm3, c_crm4, c_crm5, c_crm6 = st.columns(6)
c_crm1.metric("Leads Totais CRM", _br(crm_leads_total))
c_crm2.metric("Vendas Ganhas", _br(crm_ganhas))
c_crm3.metric("Taxa Conversão CRM", _br(crm_conversao, 2) + "%")
c_crm4.metric("Vendas Mídias Pagas", _br(paid_ganhas))
c_crm5.metric(
    "Ciclo Fecham.",
    f"{_br(tempo_medio_ganhas, 1)} h" if tempo_medio_ganhas else "—",
    help="Tempo médio (horas) dos leads que chegaram a Venda Ganha. Mesma métrica do painel de funil.",
)
c_crm6.metric(
    "CPL CRM",
    _br(cpl_crm, 2, "R$ ") if cpl_crm else "—",
    help="Custo por lead do CRM: gasto total de mídia (Google + Meta + Publya) ÷ leads que entraram no funil.",
)

st.divider()


# ── Comparativo por Canal (Totais do Período) ─────────────────────────────────
st.subheader("Comparativo por Canal")

col1, col2 = st.columns([3, 2])

with col1:
    # Tabela comparativa cruzada
    comparativo_rows = []
    
    if gads_cost > 0 or gads_imp > 0:
        comparativo_rows.append({
            "Canal": "Google Ads",
            "Investimento": gads_cost,
            "Impressões": gads_imp,
            "Cliques": gads_clicks,
            "CTR": (gads_clicks / gads_imp * 100) if gads_imp else 0.0,
            "CPC": (gads_cost / gads_clicks) if gads_clicks else 0.0,
            "Leads": None, # Removed leads
            "CPL": None,
            "Leads_CRM": crm_leads_gads,
            "CPL_CRM": (gads_cost / crm_leads_gads) if crm_leads_gads > 0 else None
        })
        
    if meta_cost > 0 or meta_imp > 0:
        comparativo_rows.append({
            "Canal": "Meta Ads",
            "Investimento": meta_cost,
            "Impressões": meta_imp,
            "Cliques": meta_clicks,
            "CTR": (meta_clicks / meta_imp * 100) if meta_imp else 0.0,
            "CPC": (meta_cost / meta_clicks) if meta_clicks else 0.0,
            "Leads": meta_leads,
            "CPL": (meta_cost / meta_leads) if meta_leads else 0.0,
            "Leads_CRM": crm_leads_meta,
            "CPL_CRM": (meta_cost / crm_leads_meta) if crm_leads_meta > 0 else None
        })
        
    if publya_cost > 0 or publya_imp > 0:
        comparativo_rows.append({
            "Canal": "Publya",
            "Investimento": publya_cost,
            "Impressões": publya_imp,
            "Cliques": publya_clicks,
            "CTR": (publya_clicks / publya_imp * 100) if publya_imp else 0.0,
            "CPC": (publya_cost / publya_clicks) if publya_clicks else 0.0,
            "Leads": publya_conv,
            "CPL": (publya_cost / publya_conv) if publya_conv else 0.0,
            "Leads_CRM": crm_leads_publya,
            "CPL_CRM": (publya_cost / crm_leads_publya) if crm_leads_publya > 0 else None
        })
        
    df_comp = pd.DataFrame(comparativo_rows)
    
    if not df_comp.empty:
        tabela_html(
            df_comp,
            col_specs=[
                {"key": "Canal",        "header": "Canal"},
                {"key": "Investimento", "header": "Investimento",    "num": True, "dec": 2, "pref": "R$ "},
                {"key": "Impressões",   "header": "Impressões",      "num": True},
                {"key": "Cliques",      "header": "Cliques",         "num": True},
                {"key": "CTR",          "header": "CTR (%)",         "num": True, "dec": 2, "somar": False},
                {"key": "CPC",          "header": "CPC (R$)",        "num": True, "dec": 2, "pref": "R$ ", "somar": False},
                {"key": "Leads",        "header": "Leads (Mídia)",   "num": True},
                {"key": "CPL",          "header": "CPL (Mídia)",     "num": True, "dec": 2, "pref": "R$ ", "somar": False},
                {"key": "Leads_CRM",    "header": "Leads (CRM)",     "num": True},
                {"key": "CPL_CRM",      "header": "CPL (CRM)",       "num": True, "dec": 2, "pref": "R$ ", "somar": False},
            ],
            com_total=True
        )

    else:
        st.info("Sem dados comparativos para o período.")

with col2:
    # Gráficos Donut
    donut_data = []
    if gads_cost > 0: donut_data.append({"Canal": "Google Ads", "Investimento": gads_cost})
    if meta_cost > 0: donut_data.append({"Canal": "Meta Ads", "Investimento": meta_cost})
    if publya_cost > 0: donut_data.append({"Canal": "Publya", "Investimento": publya_cost})
    df_donut = pd.DataFrame(donut_data)
    
    # Customizado cores: Google Ads vira Amarelo para não confundir com Meta
    BRAND_COLORS_DONUT = {
        "Google Ads": "#FFCC00", # Yellow
        "Meta Ads":   "#1877F2", # Blue
        "Publya":     "#888888", # Gray
    }
    
    if not df_donut.empty:
        grafico_donut(df_donut, "Canal", "Investimento", "Investimento por Canal", color_map=BRAND_COLORS_DONUT, total_centro=True, fmt=lambda v: _br(v, 2, "R$ "))
    else:
        st.info("Sem dados para o gráfico de investimento.")

# ── Série Temporal de Leads CRM por Canal ─────────────────────────────────────
st.subheader("Evolução Temporal de Leads (CRM por Canal)")

CANAIS_SERIE = ["Meta Ads", "Google Ads", "Publya"]
# Cores: Google Ads = Amarelo, Meta Ads = Azul, Publya = Cinza
BRAND_COLORS_SERIES = {
    "Google Ads": "#FFCC00",
    "Meta Ads":   "#1877F2",
    "Publya":     "#888888",
}

if not funil.empty:
    df_canal = funil.copy()
    df_canal["Canal_Marketing"] = df_canal.apply(classificar_canal_crm, axis=1)
    df_canal = df_canal[df_canal["Canal_Marketing"].isin(CANAIS_SERIE)].copy()
    df_canal["DataCadastro"] = pd.to_datetime(df_canal["DataCadastro"])
else:
    df_canal = pd.DataFrame(columns=["DataCadastro", "Canal_Marketing"])

if not df_canal.empty:
    gran_inv = st.radio("Visualização Série Temporal", ["Diário", "Mensal"], horizontal=True, key="time_gran", label_visibility="collapsed")

    if gran_inv == "Mensal":
        df_canal["month"] = df_canal["DataCadastro"].dt.to_period("M").dt.to_timestamp()
        df_monthly = (
            df_canal.groupby(["month", "Canal_Marketing"]).size()
            .reset_index(name="Leads").rename(columns={"Canal_Marketing": "Canal"})
        )
        grafico_barras_mensais(df_monthly, "month", "Leads", "Leads CRM por Canal × Mês", color="Canal", color_map=BRAND_COLORS_SERIES)
    else:
        df_canal["dia"] = df_canal["DataCadastro"].dt.normalize()
        df_daily = df_canal.groupby(["dia", "Canal_Marketing"]).size().reset_index(name="Leads")
        df_daily.columns = ["date", "Canal", "Leads"]
        fig = px.line(
            df_daily,
            x="date",
            y="Leads",
            color="Canal",
            color_discrete_map=BRAND_COLORS_SERIES,
            title="Leads CRM Diários por Canal",
        )
        fig.update_traces(line=dict(width=2.5))
        fig.update_layout(**{**_LAYOUT_BASE, **dict(height=380, title=_titulo_layout("Leads CRM Diários por Canal"))})
        st.plotly_chart(fig, use_container_width=True)

    st.caption("Leads classificados por canal de marketing (UTM / forma de cadastro). Leads orgânicos/diretos ('Outros') não entram nesta série.")
else:
    st.info("Sem leads CRM classificados por canal pago no período selecionado.")

st.divider()

# ── Série Temporal de Sessões (GA4) ───────────────────────────────────────────
st.subheader("Tráfego do Site (GA4)")

if not ga4.empty:
    # Botões / Radio no topo para escolher visão de GA4
    ga4_filter_type = st.radio("Origem do Tráfego (GA4)", ["Todos", "Empreendimentos", "Institucional"], horizontal=True, key="ga4_filter_type")
    
    if ga4_filter_type == "Empreendimentos":
        ga4_chart_df = ga4_emp_df
        chart_title = "Tráfego GA4 — Empreendimentos"
        chart_color = "#e67e22"
    elif ga4_filter_type == "Institucional":
        ga4_chart_df = ga4_inst_df
        chart_title = "Tráfego GA4 — Sites Institucionais"
        chart_color = "#008140"
    else:
        ga4_chart_df = ga4
        chart_title = "Tráfego GA4 — Total"
        chart_color = "#33aa77"
        
    if ga4_chart_df.empty:
        st.info("Sem tráfego para a origem selecionada no período.")
    else:
        ga4_chart_df = ga4_chart_df.copy()
        ga4_chart_df["month"] = ga4_chart_df["date"].dt.to_period("M").dt.to_timestamp()
        
        gran_ga4 = st.radio("Visualização Tráfego", ["Diário", "Mensal"], horizontal=True, key="ga4_gran", label_visibility="collapsed")
        
        if gran_ga4 == "Mensal":
            ga4_monthly = ga4_chart_df.groupby("month", as_index=False)["sessions"].sum()
            ga4_monthly = ga4_monthly.sort_values("month")
            ga4_monthly["month"] = ga4_monthly["month"].dt.strftime("%b/%Y")
            # Utiliza o grafico_barras_mensais central e força a cor selecionada
            fig = px.bar(ga4_monthly, x="month", y="sessions")
            y_max = float(ga4_monthly["sessions"].max()) if not ga4_monthly.empty else 1
            fig.update_layout(
                template=_tema(), height=400, margin=dict(l=20, r=20, t=40, b=20),
                xaxis=dict(title=None, type="category"),
                yaxis=dict(title=None, gridcolor="#2a2a2a", range=[0, y_max * 1.22]),
                plot_bgcolor="#1c1c1c", paper_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Manrope, sans-serif", color="#ffffff"),
                title=dict(font=dict(family="Manrope, sans-serif", size=15, color="#fff"), x=0, xanchor="left", pad=dict(l=4), text=chart_title),
                separators=",.",
            )
            fig.update_traces(
                marker_color=chart_color, text=[_br(v) for v in ga4_monthly["sessions"]], texttemplate="%{text}",
                textposition="outside", textfont=dict(size=11, color="rgba(255,255,255,0.75)"), cliponaxis=False,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            ga4_daily = ga4_chart_df.groupby("date", as_index=False)["sessions"].sum()
            fig = px.area(
                ga4_daily, 
                x="date", 
                y="sessions", 
                color_discrete_sequence=[chart_color],
                title=chart_title
            )
            fig.update_traces(line=dict(width=2, color=chart_color), fillcolor=_rgba(chart_color, 0.13))
            fig.update_layout(**{**_LAYOUT_BASE, **dict(height=380, title=_titulo_layout(chart_title))})
            st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Sem dados de tráfego GA4 para o período selecionado.")

st.divider()

# ── Série Temporal de Leads (CRM) ─────────────────────────────────────────────
st.subheader("Evolução dos Leads (CRM)")

if not funil.empty:
    gran_leads = st.radio("Visualização Leads", ["Diário", "Mensal"], horizontal=True, key="leads_gran", label_visibility="collapsed")
    
    # Preparar dados do CRM
    funil_temporal = funil.copy()
    funil_temporal["DataCadastro"] = pd.to_datetime(funil_temporal["DataCadastro"])
    
    if gran_leads == "Mensal":
        funil_temporal["month"] = funil_temporal["DataCadastro"].dt.to_period("M").dt.to_timestamp()
        agg_leads = funil_temporal.groupby("month").size().reset_index(name="Leads")
        agg_leads = agg_leads.sort_values("month")
        agg_leads["month_str"] = agg_leads["month"].dt.strftime("%b/%Y")
        
        y_max = float(agg_leads["Leads"].max()) if not agg_leads.empty else 1
        fig_leads = px.bar(
            agg_leads, x="month_str", y="Leads",
            color_discrete_sequence=[VERDE]
        )
        fig_leads.update_traces(
            text=[_br(v) for v in agg_leads["Leads"]],
            textposition="outside",
            textfont=dict(color="#ffffff", size=12, family="Manrope, sans-serif"),
            marker_line_width=0,
            cliponaxis=False,
        )
        fig_leads.update_layout(
            **{
                **_LAYOUT_BASE,
                **dict(
                    height=380,
                    xaxis=dict(title=None, type="category"),
                    yaxis=dict(title=None, gridcolor="#2a2a2a", range=[0, y_max * 1.22]),
                    title=_titulo_layout("Leads CRM por Mês"),
                )
            }
        )
    else:
        funil_temporal["day"] = funil_temporal["DataCadastro"].dt.normalize()
        agg_leads = funil_temporal.groupby("day").size().reset_index(name="Leads")
        agg_leads = agg_leads.sort_values("day")
        
        fig_leads = px.area(
            agg_leads, x="day", y="Leads",
            color_discrete_sequence=[VERDE]
        )
        fig_leads.update_traces(
            line=dict(width=2, color=VERDE),
            fillcolor=_rgba(VERDE, 0.13)
        )
        fig_leads.update_layout(
            **{
                **_LAYOUT_BASE,
                **dict(
                    height=380,
                    yaxis=dict(gridcolor="#2a2a2a"),
                    title=_titulo_layout("Leads CRM Diários"),
                )
            }
        )
        
    st.plotly_chart(fig_leads, use_container_width=True)
else:
    st.info("Sem dados de leads CRM para o período selecionado.")

st.divider()

# ── Drill-through (Navegação para Páginas Detalhadas) ──────────────────────────
st.subheader("Explorar Detalhes por Canal")

c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    st.markdown(
        f"""
        <div class="pub-card" style="min-height: 140px;">
            <div class="pub-card-title">🔍 Google Ads</div>
            <div style="font-size: 20px; font-weight: 700; color: #FFCC00; margin-bottom: 5px;">{_br(gads_cost, 2, "R$ ")}</div>
            <div style="font-size: 12px; color: rgba(255,255,255,0.6); margin-bottom: 12px;">Gasto no período</div>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.page_link("pages/google_ads.py", label="Ver painel completo", icon="➡️")

with c2:
    st.markdown(
        f"""
        <div class="pub-card" style="min-height: 140px;">
            <div class="pub-card-title">📱 Meta Ads</div>
            <div style="font-size: 20px; font-weight: 700; color: #1877F2; margin-bottom: 5px;">{_br(meta_cost, 2, "R$ ")}</div>
            <div style="font-size: 12px; color: rgba(255,255,255,0.6); margin-bottom: 12px;">Investimento no período</div>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.page_link("pages/meta_ads.py", label="Ver painel completo", icon="➡️")

with c3:
    st.markdown(
        f"""
        <div class="pub-card" style="min-height: 140px;">
            <div class="pub-card-title">📺 Publya</div>
            <div style="font-size: 20px; font-weight: 700; color: #888888; margin-bottom: 5px;">{_br(publya_cost, 2, "R$ ")}</div>
            <div style="font-size: 12px; color: rgba(255,255,255,0.6); margin-bottom: 12px;">Valor gasto no período</div>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.page_link("pages/publya.py", label="Ver painel completo", icon="➡️")

with c4:
    st.markdown(
        f"""
        <div class="pub-card" style="min-height: 140px;">
            <div class="pub-card-title">🏢 GA4 Empreend.</div>
            <div style="font-size: 20px; font-weight: 700; color: #e67e22; margin-bottom: 5px;">{_br(ga4_emp_sessions)}</div>
            <div style="font-size: 12px; color: rgba(255,255,255,0.6); margin-bottom: 12px;">Sessões no período</div>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.page_link("pages/ga4.py", label="Ver painel completo", icon="➡️")

with c5:
    st.markdown(
        f"""
        <div class="pub-card" style="min-height: 140px;">
            <div class="pub-card-title">🏛️ GA4 Institucional</div>
            <div style="font-size: 20px; font-weight: 700; color: #008140; margin-bottom: 5px;">{_br(ga4_inst_sessions)}</div>
            <div style="font-size: 12px; color: rgba(255,255,255,0.6); margin-bottom: 12px;">Sessões no período</div>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.page_link("pages/ga4.py", label="Ver painel completo", icon="➡️")
