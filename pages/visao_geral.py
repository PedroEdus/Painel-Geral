import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, timedelta

from core.theme import aplicar_tema
from core.ui import cabecalho, kpis
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
    trapezio_svg,
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

cabecalho("Marketing Analytics", "Visão executiva · todos os canais")

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

limit_min = min(global_min, date(2026, 1, 1))
limit_max = max(global_max, date(2026, 12, 31))

# Filtro global de período na lateral
st.sidebar.header("Filtros")
periodo_sel = st.sidebar.date_input(
    "Período Global",
    value=(date(2026, 1, 1), date(2026, 12, 31)),
    min_value=limit_min,
    max_value=limit_max,
    format="DD/MM/YYYY",
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
        publya = publya[publya["data_inicio"].isna() | (publya["data_inicio"].dt.date >= start_date)]
    if "data_fim" in publya.columns and publya["data_fim"].notna().any():
        publya = publya[publya["data_fim"].isna() | (publya["data_fim"].dt.date <= end_date)]

# ── Separação dos Sites Institucionais e Empreendimentos (GA4) ───────────────
_INST_KEYWORDS = ["institucional", "btsa | site"]

def _is_inst(name: str) -> bool:
    n = str(name).lower()
    short = n.split("—")[-1].strip()
    return any(k in n for k in _INST_KEYWORDS) or short == "buriti empreendimentos"

mask_ga4_inst = ga4["property_name"].apply(_is_inst) if not ga4.empty else pd.Series(dtype=bool)
ga4_inst_df = ga4[mask_ga4_inst].copy() if not ga4.empty else pd.DataFrame()
ga4_emp_df  = ga4[~mask_ga4_inst].copy() if not ga4.empty else pd.DataFrame()

ga4_inst_sessions = ga4_inst_df["sessions"].sum() if not ga4_inst_df.empty else 0.0
ga4_inst_users    = ga4_inst_df["totalUsers"].sum() if not ga4_inst_df.empty else 0.0
ga4_emp_sessions  = ga4_emp_df["sessions"].sum() if not ga4_emp_df.empty else 0.0
ga4_emp_users     = ga4_emp_df["totalUsers"].sum() if not ga4_emp_df.empty else 0.0

# ── Consolidação de mídia (período atual) ────────────────────────────────────
gads_cost = gads["cost"].sum() if not gads.empty else 0.0
gads_clicks = gads["clicks"].sum() if not gads.empty else 0.0
gads_imp = gads["impressions"].sum() if not gads.empty else 0.0

meta_cost = meta["spend"].sum() if not meta.empty else 0.0
meta_clicks = meta["clicks"].sum() if not meta.empty else 0.0
meta_imp = meta["impressions"].sum() if not meta.empty else 0.0
meta_leads = meta["leads"].sum() if (not meta.empty and "leads" in meta.columns) else 0.0

publya_cost = publya["budget"].sum() if not publya.empty else 0.0
publya_clicks = publya["clicks"].sum() if not publya.empty else 0.0
publya_imp = publya["impressions"].sum() if not publya.empty else 0.0
publya_conv = publya["conversions"].sum() if not publya.empty else 0.0

total_spend = gads_cost + meta_cost + publya_cost
total_clicks = gads_clicks + meta_clicks + publya_clicks
total_imp = gads_imp + meta_imp + publya_imp
total_leads = meta_leads + publya_conv  # leads de mídia (ignora Google Ads)

# ── Período anterior equivalente (para variações) ────────────────────────────
days_selected = (end_date - start_date).days + 1
prev_start = start_date - timedelta(days=days_selected)
prev_end = start_date - timedelta(days=1)

gads_prev = df_gads[(df_gads["date"].dt.date >= prev_start) & (df_gads["date"].dt.date <= prev_end)].copy() if not df_gads.empty else pd.DataFrame()
meta_prev = df_meta[(df_meta["date_start"] >= prev_start) & (df_meta["date_start"] <= prev_end)].copy() if not df_meta.empty else pd.DataFrame()
publya_prev = df_publya.copy() if not df_publya.empty else pd.DataFrame()
if not publya_prev.empty:
    if "data_inicio" in publya_prev.columns and publya_prev["data_inicio"].notna().any():
        publya_prev = publya_prev[publya_prev["data_inicio"].isna() | (publya_prev["data_inicio"].dt.date >= prev_start)]
    if "data_fim" in publya_prev.columns and publya_prev["data_fim"].notna().any():
        publya_prev = publya_prev[publya_prev["data_fim"].isna() | (publya_prev["data_fim"].dt.date <= prev_end)]

total_spend_prev = (gads_prev["cost"].sum() if not gads_prev.empty else 0.0) + (meta_prev["spend"].sum() if not meta_prev.empty else 0.0) + (publya_prev["budget"].sum() if not publya_prev.empty else 0.0)
total_clicks_prev = (gads_prev["clicks"].sum() if not gads_prev.empty else 0.0) + (meta_prev["clicks"].sum() if not meta_prev.empty else 0.0) + (publya_prev["clicks"].sum() if not publya_prev.empty else 0.0)
total_imp_prev = (gads_prev["impressions"].sum() if not gads_prev.empty else 0.0) + (meta_prev["impressions"].sum() if not meta_prev.empty else 0.0) + (publya_prev["impressions"].sum() if not publya_prev.empty else 0.0)

# Médias diárias e taxas
avg_spend_sel = total_spend / days_selected
avg_clicks_sel = total_clicks / days_selected
avg_imp_sel = total_imp / days_selected
avg_cpc_sel = total_spend / total_clicks if total_clicks else 0.0
avg_cpm_sel = (total_spend / total_imp * 1000) if total_imp else 0.0
ctr_sel = (total_clicks / total_imp * 100) if total_imp else 0.0

avg_spend_prev = total_spend_prev / days_selected
avg_clicks_prev = total_clicks_prev / days_selected
avg_imp_prev = total_imp_prev / days_selected
avg_cpc_prev = total_spend_prev / total_clicks_prev if total_clicks_prev else 0.0
avg_cpm_prev = (total_spend_prev / total_imp_prev * 1000) if total_imp_prev else 0.0


def get_delta_str(curr, prev):
    if prev <= 0:
        return None
    pct = (curr - prev) / prev * 100
    return f"{pct:+.1f}% vs período ant."


# ── Métricas do CRM (canal de marketing por lead) ────────────────────────────
def classificar_canal_crm(row):
    source = str(row.get("UtmSource", "")).lower()
    forma = str(row.get("FormaCadastro", "")).lower()
    campaign = str(row.get("UtmCampaign", "")).lower()
    if "publya" in source or "publya" in forma or "publya" in campaign:
        return "Publya"
    if any(k in source or k in forma for k in ["meta", "facebook", "instagram", "ig"]):
        return "Meta Ads"
    if any(k in source or k in forma for k in ["google", "gads", "google-ads"]):
        return "Google Ads"
    return "Outros"


def _crm_resumo(df_in: pd.DataFrame) -> dict:
    if df_in.empty:
        return {"leads": 0, "ganhas": 0, "por_canal": {}, "ciclo": None}
    d = df_in.copy()
    d["Canal_Marketing"] = d.apply(classificar_canal_crm, axis=1)
    ganhas = int(d["Etapa_NF"].eq("Venda Ganha").sum()) if "Etapa_NF" in d.columns else 0
    ciclo = None
    if "Etapa_NF" in d.columns and "TempoCiclo_h" in d.columns:
        tc = d.loc[d["Etapa_NF"].eq("Venda Ganha") & d["TempoCiclo_h"].notna() & (d["TempoCiclo_h"] > 0), "TempoCiclo_h"]
        ciclo = round(float(tc.mean()), 1) if not tc.empty else None
    return {
        "leads": len(d),
        "ganhas": ganhas,
        "por_canal": d["Canal_Marketing"].value_counts().to_dict(),
        "ciclo": ciclo,
        "paid_ganhas": int((d["Canal_Marketing"].isin(["Google Ads", "Meta Ads", "Publya"]) & d["Etapa_NF"].eq("Venda Ganha")).sum()) if "Etapa_NF" in d.columns else 0,
    }


crm = _crm_resumo(funil)
crm_leads_total = crm["leads"]
crm_ganhas = crm["ganhas"]
crm_conversao = (crm_ganhas / crm_leads_total * 100) if crm_leads_total else 0.0
tempo_medio_ganhas = crm["ciclo"]
paid_ganhas = crm.get("paid_ganhas", 0)
crm_leads_gads = crm["por_canal"].get("Google Ads", 0)
crm_leads_meta = crm["por_canal"].get("Meta Ads", 0)
crm_leads_publya = crm["por_canal"].get("Publya", 0)
cpl_crm = (total_spend / crm_leads_total) if crm_leads_total else None

funil_prev = df_funil[(df_funil["DataCadastro"].dt.date >= prev_start) & (df_funil["DataCadastro"].dt.date <= prev_end)].copy() if not df_funil.empty else pd.DataFrame()
crm_prev = _crm_resumo(funil_prev)
crm_leads_prev = crm_prev["leads"]
crm_ganhas_prev = crm_prev["ganhas"]
cpl_crm_prev = (total_spend_prev / crm_leads_prev) if crm_leads_prev else None


# ═════════════════════════════════════════════════════════════════════════════
# 1 · RESULTADO DA OPERAÇÃO (destaques)
# ═════════════════════════════════════════════════════════════════════════════
d1, d2, d3, d4 = st.columns(4)
d1.metric("Investimento Total", _br(total_spend, 2, "R$ "),
          delta=get_delta_str(total_spend, total_spend_prev), delta_color="inverse")
d2.metric("Leads CRM", _br(crm_leads_total),
          delta=get_delta_str(crm_leads_total, crm_leads_prev))
d3.metric("Vendas Ganhas", _br(crm_ganhas),
          delta=get_delta_str(crm_ganhas, crm_ganhas_prev))
d4.metric("CPL CRM", _br(cpl_crm, 2, "R$ ") if cpl_crm else "—",
          delta=get_delta_str(cpl_crm, cpl_crm_prev) if (cpl_crm and cpl_crm_prev) else None,
          delta_color="inverse",
          help="Custo por lead do CRM: gasto total de mídia ÷ leads que entraram no funil.")

st.write("")

# ═════════════════════════════════════════════════════════════════════════════
# 2 · JORNADA CROSS-CANAL (funil)
# ═════════════════════════════════════════════════════════════════════════════
st.subheader("Jornada cross-canal")
_labels = ["Cliques", "Leads mídia", "Leads CRM", "Vendas"]
_icons = ["fa-arrow-pointer", "fa-user-plus", "fa-database", "fa-trophy"]
_vals = [float(total_clicks), float(total_leads), float(crm_leads_total), float(crm_ganhas)]

_INFO_ETAPA = {
    "Cliques": "Soma de cliques em Google Ads, Meta e Publya no período.",
    "Leads mídia": "Conversões/leads reportados pelas plataformas de mídia (Meta + Publya). Não inclui Google Ads.",
    "Leads CRM": "Leads que efetivamente entraram no funil do CRM no período (todas as origens).",
    "Vendas": "Leads que chegaram à etapa Venda Ganha no CRM.",
}
_etapas = [(lab, cor, v) for lab, cor, v in zip(
    _labels, ["#15431f", "#1e7d34", "#2a9d45", "#5ec172"], _vals) if v > 0]

if _etapas:
    base = _vals[0] or 1
    n = len(_etapas)
    W_TOP, W_BOT = 92, 30
    step_w = (W_TOP - W_BOT) / max(n - 1, 1)

    stages_html = ""
    for i, (etapa, cor, count) in enumerate(_etapas):
        w = W_TOP - i * step_w
        w_n = W_TOP - (i + 1) * step_w
        ml = (100 - w) / 2
        ml_n = (100 - w_n) / 2
        pct = count / base * 100 if base else 0
        info = _INFO_ETAPA.get(etapa, "")
        tip = (f'<span class="fn-tip">?<span class="fn-tipbox">{info}</span></span>') if info else ""
        stages_html += f"""
        <div style="position:relative;margin-bottom:6px;height:74px;">
          {tip}
          {trapezio_svg(ml, ml_n, cor, h=74)}
          <div style="position:absolute;inset:0;display:flex;align-items:center;
            justify-content:center;flex-direction:column;gap:2px;pointer-events:none;">
            <span class="fn-num" style="font-size:22px;font-weight:800;color:#fff;
              font-family:'Roboto Condensed',sans-serif;">{_br(count)}</span>
            <span style="font-size:9px;font-weight:600;color:rgba(255,255,255,0.82);
              text-transform:uppercase;letter-spacing:1.1px;">{etapa}</span>
          </div>
          <div class="fn-pct" style="position:absolute;right:4px;top:50%;transform:translateY(-50%);
            color:#6b6b74;font-size:12px;font-weight:700;
            font-family:'Roboto Condensed',sans-serif;">{pct:.1f}%</div>
        </div>"""
        if i < n - 1:
            prox = _etapas[i + 1][2]
            conv = prox / count * 100 if count else 0
            stages_html += f"""
        <div style="display:flex;justify-content:center;margin:-1px 0 2px;">
          <span style="font-size:10px;font-weight:700;color:rgba(30,125,52,0.95);
            font-family:'Roboto Condensed',sans-serif;background:rgba(42,157,69,0.08);
            border:1px solid rgba(42,157,69,0.22);border-radius:10px;padding:1px 9px;"
            title="Passagem {etapa} → {_etapas[i + 1][0]}">▼ {conv:.1f}%</span>
        </div>"""

    _lead_venda = (crm_ganhas / crm_leads_total * 100) if crm_leads_total else 0.0
    _cards = [
        ("Impressões", _br(total_imp)),
        ("CTR", _br(ctr_sel, 2) + "%"),
        ("Conversão lead→venda", _br(_lead_venda, 2) + "%"),
        ("Ciclo de fechamento", (f"{_br(tempo_medio_ganhas, 1)} h") if tempo_medio_ganhas else "—"),
    ]
    _cards_html = "".join(
        f'<div style="flex:1;background:#fff;border:1px solid #ececed;border-radius:14px;'
        f'box-shadow:0 1px 3px rgba(0,0,0,.06);position:relative;overflow:hidden;'
        f'padding:12px 18px;display:flex;flex-direction:column;justify-content:center;">'
        f'<div style="position:absolute;top:0;left:0;right:0;height:3px;'
        f'background:linear-gradient(90deg,#4ab861,#7dd190);"></div>'
        f'<div style="font-size:13px;color:#6b6b74;">{lab}</div>'
        f'<div style="font-family:\'Roboto Condensed\',sans-serif;font-size:26px;font-weight:700;'
        f'color:#232329;letter-spacing:-.4px;line-height:1.1;margin-top:2px;">{val}</div>'
        f'</div>'
        for lab, val in _cards
    )

    # Funil + cards no MESMO bloco flex (align-items:stretch) → a coluna de cards
    # estica exatamente até a altura do funil, sem cálculo de pixel.
    _html(f"""
    <style>
    .fn-tip{{position:absolute;left:8px;top:50%;transform:translateY(-50%);z-index:6;
      width:17px;height:17px;border-radius:50%;background:#fff;border:1px solid #2a9d45;
      color:#1e7d34;font-size:10px;font-weight:700;display:inline-flex;align-items:center;
      justify-content:center;cursor:help;font-family:'Segoe UI',sans-serif;}}
    .fn-tip .fn-tipbox{{visibility:hidden;opacity:0;position:absolute;left:24px;top:50%;
      transform:translateY(-50%);background:#232329;color:#f5f5f6;font-size:11px;font-weight:400;
      line-height:1.5;padding:8px 11px;border-radius:7px;width:240px;text-align:left;
      text-transform:none;letter-spacing:normal;box-shadow:0 4px 14px rgba(0,0,0,.28);
      transition:opacity .15s;z-index:9999;}}
    .fn-tip:hover .fn-tipbox{{visibility:visible;opacity:1;}}
    </style>
    <div class="fn-journey" style="display:flex;gap:16px;align-items:stretch;">
      <div class="pub-card" style="flex:3;padding:22px 22px 18px;position:relative;margin-bottom:0;">
        <div style="font-size:10px;letter-spacing:2px;text-transform:uppercase;
          color:#8f8f96;margin-bottom:4px;">Da mídia à venda</div>
        <div style="font-size:13px;color:#6b6b74;margin-bottom:18px;">
          Impressões: <b style="color:#232329">{_br(total_imp)}</b> · CTR: <b style="color:#232329">{_br(ctr_sel, 2)}%</b>
        </div>
        <div class="fn-stages" style="padding-right:52px;">{stages_html}</div>
      </div>
      <div class="fn-jcards" style="flex:1;display:flex;flex-direction:column;gap:10px;">{_cards_html}</div>
    </div>
    """)
else:
    st.info("Sem dados suficientes para a jornada no período.")

st.write("")

# ═════════════════════════════════════════════════════════════════════════════
# 3 · EFICIÊNCIA DE MÍDIA (médias diárias, Δ vs período anterior)
# ═════════════════════════════════════════════════════════════════════════════
st.subheader("Eficiência de mídia")
e1, e2, e3, e4, e5 = st.columns(5)
e1.metric("Gasto/dia", _br(avg_spend_sel, 2, "R$ "), delta=get_delta_str(avg_spend_sel, avg_spend_prev), delta_color="inverse")
e2.metric("Cliques/dia", _br(avg_clicks_sel), delta=get_delta_str(avg_clicks_sel, avg_clicks_prev))
e3.metric("CTR", _br(ctr_sel, 2) + "%")
e4.metric("CPC Médio", _br(avg_cpc_sel, 2, "R$ "), delta=get_delta_str(avg_cpc_sel, avg_cpc_prev), delta_color="inverse")
e5.metric("CPM Médio", _br(avg_cpm_sel, 2, "R$ "), delta=get_delta_str(avg_cpm_sel, avg_cpm_prev), delta_color="inverse")

st.divider()

# ═════════════════════════════════════════════════════════════════════════════
# 4 · POR CANAL (tabela comparativa + donut de investimento)
# ═════════════════════════════════════════════════════════════════════════════
st.subheader("Por canal")
col1, col2 = st.columns([3, 2])

with col1:
    comparativo_rows = []
    if gads_cost > 0 or gads_imp > 0:
        comparativo_rows.append({
            "Canal": "Google Ads", "Investimento": gads_cost, "Impressões": gads_imp, "Cliques": gads_clicks,
            "CTR": (gads_clicks / gads_imp * 100) if gads_imp else 0.0,
            "CPC": (gads_cost / gads_clicks) if gads_clicks else 0.0,
            "Leads": None, "CPL": None, "Leads_CRM": crm_leads_gads,
            "CPL_CRM": (gads_cost / crm_leads_gads) if crm_leads_gads > 0 else None,
        })
    if meta_cost > 0 or meta_imp > 0:
        comparativo_rows.append({
            "Canal": "Meta Ads", "Investimento": meta_cost, "Impressões": meta_imp, "Cliques": meta_clicks,
            "CTR": (meta_clicks / meta_imp * 100) if meta_imp else 0.0,
            "CPC": (meta_cost / meta_clicks) if meta_clicks else 0.0,
            "Leads": meta_leads, "CPL": (meta_cost / meta_leads) if meta_leads else 0.0,
            "Leads_CRM": crm_leads_meta,
            "CPL_CRM": (meta_cost / crm_leads_meta) if crm_leads_meta > 0 else None,
        })
    if publya_cost > 0 or publya_imp > 0:
        comparativo_rows.append({
            "Canal": "Publya", "Investimento": publya_cost, "Impressões": publya_imp, "Cliques": publya_clicks,
            "CTR": (publya_clicks / publya_imp * 100) if publya_imp else 0.0,
            "CPC": (publya_cost / publya_clicks) if publya_clicks else 0.0,
            "Leads": publya_conv, "CPL": (publya_cost / publya_conv) if publya_conv else 0.0,
            "Leads_CRM": crm_leads_publya,
            "CPL_CRM": (publya_cost / crm_leads_publya) if crm_leads_publya > 0 else None,
        })
    df_comp = pd.DataFrame(comparativo_rows)
    if not df_comp.empty:
        tabela_html(
            df_comp,
            col_specs=[
                {"key": "Canal", "header": "Canal"},
                {"key": "Investimento", "header": "Investimento", "num": True, "dec": 2, "pref": "R$ "},
                {"key": "Impressões", "header": "Impressões", "num": True},
                {"key": "Cliques", "header": "Cliques", "num": True},
                {"key": "CTR", "header": "CTR (%)", "num": True, "dec": 2, "somar": False},
                {"key": "CPC", "header": "CPC (R$)", "num": True, "dec": 2, "pref": "R$ ", "somar": False},
                {"key": "Leads", "header": "Leads (Mídia)", "num": True},
                {"key": "CPL", "header": "CPL (Mídia)", "num": True, "dec": 2, "pref": "R$ ", "somar": False},
                {"key": "Leads_CRM", "header": "Leads (CRM)", "num": True},
                {"key": "CPL_CRM", "header": "CPL (CRM)", "num": True, "dec": 2, "pref": "R$ ", "somar": False},
            ],
            com_total=True,
        )
    else:
        st.info("Sem dados comparativos para o período.")

with col2:
    donut_data = []
    if gads_cost > 0: donut_data.append({"Canal": "Google Ads", "Investimento": gads_cost})
    if meta_cost > 0: donut_data.append({"Canal": "Meta Ads", "Investimento": meta_cost})
    if publya_cost > 0: donut_data.append({"Canal": "Publya", "Investimento": publya_cost})
    df_donut = pd.DataFrame(donut_data)
    BRAND_COLORS_DONUT = {"Google Ads": "#FFCC00", "Meta Ads": "#1877F2", "Publya": "#888888"}
    if not df_donut.empty:
        grafico_donut(df_donut, "Canal", "Investimento", "Investimento por Canal",
                      color_map=BRAND_COLORS_DONUT, total_centro=True,
                      fmt=lambda v: _br(v, 2, "R$ "), altura=340)
    else:
        st.info("Sem dados para o gráfico de investimento.")

# ═════════════════════════════════════════════════════════════════════════════
# 5 · EVOLUÇÃO TEMPORAL (leads CRM por canal)
# ═════════════════════════════════════════════════════════════════════════════
CANAIS_SERIE = ["Meta Ads", "Google Ads", "Publya"]
BRAND_COLORS_SERIES = {"Google Ads": "#F59E0B", "Meta Ads": "#2563EB", "Publya": "#6b6b74"}

if not funil.empty:
    df_canal = funil.copy()
    df_canal["Canal_Marketing"] = df_canal.apply(classificar_canal_crm, axis=1)
    df_canal = df_canal[df_canal["Canal_Marketing"].isin(CANAIS_SERIE)].copy()
    df_canal["DataCadastro"] = pd.to_datetime(df_canal["DataCadastro"])
else:
    df_canal = pd.DataFrame(columns=["DataCadastro", "Canal_Marketing"])

if not df_canal.empty:
    with st.container(key="dfc_evol_canal"):
        _html('<div class="pub-card-title">Leads CRM por Canal</div>')
        gran_inv = st.radio("Visualização Série Temporal", ["Diário", "Mensal"], horizontal=True,
                            key="time_gran", label_visibility="collapsed")
        if gran_inv == "Mensal":
            df_canal["month"] = df_canal["DataCadastro"].dt.to_period("M").dt.to_timestamp()
            df_monthly = (df_canal.groupby(["month", "Canal_Marketing"]).size()
                          .reset_index(name="Leads").rename(columns={"Canal_Marketing": "Canal"}))
            grafico_barras_mensais(df_monthly, "month", "Leads", "",
                                   color="Canal", color_map=BRAND_COLORS_SERIES)
        else:
            df_canal["dia"] = df_canal["DataCadastro"].dt.normalize()
            df_daily = df_canal.groupby(["dia", "Canal_Marketing"]).size().reset_index(name="Leads")
            df_daily.columns = ["date", "Canal", "Leads"]
            fig = px.line(df_daily, x="date", y="Leads", color="Canal",
                          color_discrete_map=BRAND_COLORS_SERIES)
            fig.update_traces(line=dict(width=2.5, shape="spline"), line_smoothing=0.8)
            fig.update_layout(**{**_LAYOUT_BASE, **dict(
                height=340,
                title=dict(text=""),
                paper_bgcolor="#ffffff", plot_bgcolor="#ffffff",
                xaxis=dict(
                    title=None, showgrid=False, showline=False, ticks="",
                    tickfont=dict(size=12, color="#6b6b74", family="Segoe UI, system-ui, sans-serif"),
                ),
                yaxis=dict(
                    title=None, gridcolor="#eef1f5", griddash="dot",
                    zeroline=False, showline=False, ticks="",
                    tickfont=dict(size=12, color="#6b6b74", family="Segoe UI, system-ui, sans-serif"),
                ),
                legend=dict(
                    title=None, orientation="v", x=1, y=1, xanchor="right", yanchor="top",
                    font=dict(size=12, color="#232329", family="Segoe UI, system-ui, sans-serif"),
                    bgcolor="rgba(0,0,0,0)",
                ),
                margin=dict(l=4, r=4, t=10, b=8),
            )})
            st.plotly_chart(fig, use_container_width=True)
    st.markdown(
        "<div style='font-size:13px;color:#232329;'>Leads classificados por canal de marketing "
        "(UTM / forma de cadastro). Leads orgânicos/diretos ('Outros') não entram nesta série.</div>",
        unsafe_allow_html=True,
    )
else:
    st.info("Sem leads CRM classificados por canal pago no período selecionado.")

st.divider()

# ═════════════════════════════════════════════════════════════════════════════
# 6 · TRÁFEGO DO SITE (GA4) — bloco secundário
# ═════════════════════════════════════════════════════════════════════════════
st.subheader("Tráfego do site (GA4)")
g1, g2, g3, g4 = st.columns(4)
g1.metric("Sessões (Empreend.)", _br(ga4_emp_sessions))
g2.metric("Usuários (Empreend.)", _br(ga4_emp_users))
g3.metric("Sessões (Institucional)", _br(ga4_inst_sessions))
g4.metric("Usuários (Institucional)", _br(ga4_inst_users))
