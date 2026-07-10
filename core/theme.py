"""Identidade visual do Painel Geral — design system do Painel do Milhão (modo claro).

Tokens de marca (verde #2a9d45), tipografia Segoe UI + Roboto Condensed p/ números,
stat-cards com ícone, cards com header, badges e template Plotly. Base CLARA
(fundo branco/cinza, cards brancos com sombra).

`aplicar_tema()` injeta o CSS global e registra o template Plotly. Chamar 1x por página.
"""

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

# ── Tokens de marca ──────────────────────────────────────────────────────────
BRAND = {
    "50": "#f5f8f6", "100": "#d8f3de", "200": "#b3e6bc", "300": "#7dd190",
    "400": "#4ab861", "500": "#2a9d45", "600": "#1e7d34", "700": "#1a6229",
    "800": "#174f23", "900": "#0f3317", "950": "#081c0d",
}
GRAY = {
    "0": "#ffffff", "50": "#f5f5f6", "100": "#ececed", "200": "#d8d8da",
    "300": "#b8b8bc", "400": "#8f8f96", "500": "#6b6b74", "600": "#4e4e57",
    "700": "#35353e", "800": "#232329", "900": "#141418",
}
BRAND_RED = "#e2231a"
SEMANTIC = {
    "danger_50": "#fef2f2", "danger_500": "#ef4444", "danger_700": "#b91c1c",
    "warning_50": "#fffbeb", "warning_500": "#f59e0b", "warning_700": "#92400e",
    "info_50": "#eff6ff", "info_500": "#3b82f6", "info_700": "#1d4ed8",
}
ACENTO = {
    "amber": SEMANTIC["warning_500"], "red": SEMANTIC["danger_500"],
    "blue": SEMANTIC["info_500"], "green": BRAND["500"],
}
RADIUS = {"sm": "6px", "md": "10px", "lg": "14px", "xl": "20px"}

FONT = '"Segoe UI", system-ui, -apple-system, Roboto, Arial, sans-serif'
FONT_NUM = '"Roboto Condensed", "Bahnschrift", "Arial Narrow", sans-serif'

COLORWAY = [
    BRAND["500"], BRAND["300"], ACENTO["blue"], ACENTO["amber"],
    BRAND["700"], BRAND_RED, BRAND["200"], GRAY["400"],
]

# ── Paleta de superfície (modo claro) ────────────────────────────────────────
P = {
    "bg": GRAY["50"], "surface": GRAY["0"], "surface2": GRAY["50"],
    "text": GRAY["900"], "muted": GRAY["400"], "label": GRAY["500"],
    "border": GRAY["100"], "border2": GRAY["200"],
    "grid": "#eef1f5", "hover": "rgba(15,23,42,.05)", "hover_bg": "#fafafa",
    "input_bg": GRAY["0"], "sidebar_bg": GRAY["50"], "sidebar_border": "#e4e8ee",
    "shadow": "0 1px 3px rgba(0,0,0,.06)", "shadow_h": "0 6px 18px rgba(0,0,0,.10)",
    "neutral_bg": GRAY["100"], "neutral_fg": GRAY["600"],
}


def _css() -> str:
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Roboto+Condensed:wght@500;600;700&display=swap');
@import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css');

:root {{
  --font-text: {FONT};
  --font-num: {FONT_NUM};
  --brand: {BRAND['500']};
  --surface: {P['surface']};
  --bg: {P['bg']};
  --border: {P['border']};
  --text: {P['text']};
  --muted: {P['muted']};
}}

/* ── Remove espaço vazio no topo (deixa ~10px) ─────────────── */
header[data-testid="stHeader"] {{ background: transparent !important; height: 0 !important; }}
[data-testid="stDecoration"] {{ display: none !important; }}
[data-testid="stToolbar"] {{ top: 0 !important; }}
.block-container, [data-testid="stMainBlockContainer"] {{
  padding-top: 10px !important; }}

/* ── Tipografia ─────────────────────────────────────────────── */
html, body, [class*="css"], .stApp, [data-testid="stAppViewContainer"],
.stMarkdown, .stMarkdown p, h1, h2, h3, h4, h5, h6, label,
button[data-baseweb="tab"], [data-testid="stWidgetLabel"] p {{
  font-family: var(--font-text) !important; }}
.stat-val, .hero-value, [data-testid="stMetricValue"] {{
  font-family: var(--font-num) !important; font-feature-settings: "tnum" 1; }}

/* ── Base / superfícies ────────────────────────────────────── */
.stApp, [data-testid="stApp"], [data-testid="stAppViewContainer"], [data-testid="stMain"] {{
  background: {P['bg']} !important; color: {P['text']}; }}
.stMarkdown, .stMarkdown p, label, [data-testid="stWidgetLabel"] p {{ color: {P['text']}; }}
h1, h2, h3 {{ font-weight: 800 !important; color: {P['text']}; letter-spacing: -.3px; }}
h1 {{ font-size: 26px !important; }}
hr {{ border-color: {P['border']}; }}
div[data-testid="stCaptionContainer"] p {{ color: {P['muted']} !important; font-size: 13px !important; }}

/* ── KPI metric tiles nativos (st.metric) → stat-card claro ── */
div[data-testid="stMetric"], div[data-testid="metric-container"] {{
  background: {P['surface']} !important; border: 1px solid {P['border']} !important;
  border-radius: {RADIUS['lg']} !important; padding: 18px 20px !important;
  min-height: 104px !important; box-shadow: {P['shadow']} !important;
  position: relative; overflow: visible;
  transition: box-shadow 150ms cubic-bezier(.4,0,.2,1), transform 150ms cubic-bezier(.4,0,.2,1);
  animation: fadeUp .5s cubic-bezier(.4,0,.2,1) both; }}
div[data-testid="stMetric"]::before {{ content:''; position:absolute; top:0; left:0; right:0; height:3px;
  border-radius:{RADIUS['lg']} {RADIUS['lg']} 0 0;
  background: linear-gradient(90deg, {BRAND['400']}, {BRAND['300']}); }}
div[data-testid="stMetric"]:hover {{ box-shadow:{P['shadow_h']}; transform:translateY(-2px); border-color:{P['border2']} !important; }}
div[data-testid="stMetricLabel"] > div, div[data-testid="stMetricLabel"] label, div[data-testid="stMetricLabel"] p {{
  font-size: 13px !important; font-weight: 500 !important; color: {P['label']} !important; }}
div[data-testid="stMetricValue"], div[data-testid="stMetricValue"] > div {{
  font-size: 28px !important; font-weight: 700 !important; letter-spacing: -.4px !important;
  font-variant-numeric: tabular-nums !important; color: {P['text']} !important; }}
div[data-testid="stMetricDelta"] {{ font-size: 12px !important; }}
/* Tiles st.metric lado a lado: mesma altura mesmo quando só alguns têm delta.
   A linha estica (stHorizontalBlock align-items:stretch); forçamos a cadeia
   inteira da coluna a 100% p/ o tile preencher a altura da linha. */
[data-testid="stColumn"]:has(div[data-testid="stMetric"]) {{
  display: flex !important; flex-direction: column !important; }}
[data-testid="stColumn"]:has(div[data-testid="stMetric"]) > div {{ flex: 1 1 auto !important; height: 100% !important; }}
[data-testid="stColumn"]:has(div[data-testid="stMetric"]) [data-testid="stVerticalBlock"] {{ height: 100% !important; }}
[data-testid="stColumn"]:has(div[data-testid="stMetric"]) [data-testid="stElementContainer"]:has(div[data-testid="stMetric"]) {{ height: 100% !important; }}
[data-testid="stColumn"] div[data-testid="stMetric"] {{ height: 100% !important; box-sizing: border-box; }}

/* ── Multiselect tags ── */
span[data-baseweb="tag"] {{ background-color: {BRAND['500']} !important; }}
span[data-baseweb="tag"] span[role="img"] svg path {{ fill: rgba(255,255,255,.85) !important; }}

/* ── Sidebar ───────────────────────────────────────────────── */
section[data-testid="stSidebar"], section[data-testid="stSidebar"] > div {{
  background-color: {P['sidebar_bg']} !important; }}
[data-testid="stSidebar"] {{
  background-image:
    radial-gradient(ellipse 120% 24% at 50% 0%, rgba(42,157,69,.10) 0%, transparent 100%),
    linear-gradient(rgba(42,157,69,.035) 1px, transparent 1px),
    linear-gradient(90deg, rgba(42,157,69,.035) 1px, transparent 1px);
  background-size: 100% 100%, 9px 9px, 9px 9px;
  border-right: 1px solid {P['sidebar_border']}; }}
section[data-testid="stSidebar"] label {{ font-size: 13px !important; color: {P['label']} !important; font-weight: 500 !important; }}
[data-testid="stSidebarNav"] a span {{ color: {P['text']}; }}
[data-testid="stSidebarNav"] a:hover {{ background: {P['hover']}; border-radius: 8px; }}
section[data-testid="stSidebar"] .stMultiSelect > div,
section[data-testid="stSidebar"] .stSelectbox > div,
section[data-testid="stSidebar"] input[type="text"],
section[data-testid="stSidebar"] input[type="date"] {{
  background: {P['input_bg']} !important; border-color: {P['border2']} !important;
  border-radius: {RADIUS['md']} !important; font-size: 14px !important; }}

/* ── Tabs ──────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {{
  background: transparent !important; border-bottom: 1px solid {P['border']} !important; gap: 4px !important; }}
.stTabs [data-baseweb="tab"] {{
  font-size: 14px !important; color: {P['muted']} !important; background: transparent !important;
  border: none !important; border-bottom: 2.5px solid transparent !important;
  padding: 10px 16px 12px !important; border-radius: 0 !important; }}
.stTabs [data-baseweb="tab"]:hover {{ color: {P['text']} !important; background: transparent !important; }}
.stTabs [aria-selected="true"], .stTabs [data-baseweb="tab"][aria-selected="true"] {{
  color: {BRAND['600']} !important; font-weight: 600 !important;
  border-bottom-color: {BRAND['500']} !important; background: transparent !important; }}
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] {{
  background-color: {BRAND['500']} !important; height: 2px !important; }}

/* ── Inputs / botões ───────────────────────────────────────── */
input, textarea, [data-baseweb="input"], [data-baseweb="select"] > div {{
  background-color: {P['input_bg']} !important; color: {P['text']} !important; }}
input:focus, textarea:focus, [data-baseweb="input"]:focus-within {{
  border-color: {BRAND['400']} !important; box-shadow: 0 0 0 3px rgba(42,157,69,.12) !important; }}
.stButton > button {{ border-radius: {RADIUS['md']}; font-weight: 600; }}
.stButton > button[kind="primary"] {{ background: linear-gradient(135deg, {BRAND['400']}, {BRAND['600']});
  border: none; box-shadow: 0 2px 8px rgba(42,157,69,.25); }}
.stButton > button[kind="primary"]:hover {{ box-shadow: 0 4px 14px rgba(42,157,69,.35); transform: translateY(-1px); }}

/* ── Radio buttons ── */
[data-testid="stRadio"] label [data-testid="stMarkdownContainer"] p {{ color: {P['label']} !important; }}
div[role="radiogroup"] div[data-baseweb="radio"] input:checked + div div:first-child {{
  border-color: {BRAND['500']} !important; background-color: {BRAND['500']} !important; }}

/* ── Plotly card → aplicado no WRAPPER, não no stPlotlyChart ──
   Espelha o Painel do Milhão: o card é o container (cresce p/ caber o gráfico),
   o stPlotlyChart fica cru. Antes o padding ficava no stPlotlyChart, cuja altura
   o Streamlit fixa na altura da figura → o padding estourava → barra de rolagem. */
[data-testid="stElementContainer"]:has([data-testid="stPlotlyChart"]) {{
  background: {P['surface']} !important; border: 1px solid {P['border']} !important;
  border-radius: {RADIUS['lg']} !important; padding: 18px 20px 14px !important;
  box-shadow: {P['shadow']} !important; margin-bottom: 4px;
  /* overflow visible: o stElementContainer vinha com overflow-y:auto colado na
     altura do gráfico → labels/markers que saem 1px geravam barra de rolagem. */
  overflow: visible !important;
  animation: fadeIn 0.45s ease-out; }}
[data-testid="stPlotlyChart"], [data-testid="stPlotlyChart"] > div,
[data-testid="stPlotlyChart"] .js-plotly-plot, [data-testid="stPlotlyChart"] .plotly {{
  background: transparent !important; }}
/* esconde a barra de ferramentas do Plotly (câmera/zoom) — visual limpo */
[data-testid="stPlotlyChart"] .modebar {{ display: none !important; }}


/* ── Colunas de mesma altura: cards lado a lado esticam juntos ── */
[data-testid="stHorizontalBlock"] {{ align-items: stretch !important; }}
[data-testid="stColumn"] .pub-card {{ height: 100%; box-sizing: border-box; }}
/* cards dfc_ (tabela/gráfico em card) lado a lado: mesma altura na linha */
[data-testid="stColumn"] > [data-testid="stVerticalBlockBorderWrapper"]:has([class*="st-key-dfc_"]),
[data-testid="stColumn"] [class*="st-key-dfc_"] {{ height: 100%; box-sizing: border-box; }}

/* ── Dataframes (glide-data-grid: cantos no wrapper do canvas) ── */
/* O grid é um <canvas>: o fundo das células vem do tema (backgroundColor
   #FFFFFF), não do CSS. O CSS só controla o container DOM. Por isso o card
   (borda/sombra/raio) vai no container e o overflow:hidden precisa estar no
   wrapper que de fato envolve o canvas, senão os cantos quadrados vazam. */
[data-testid="stDataFrame"] {{
  background: {P['surface']} !important;
  border: 1px solid {P['border']} !important;
  border-radius: 14px !important;
  box-shadow: {P['shadow']} !important;
  overflow: hidden !important;
  margin-bottom: 4px !important; }}
/* mata a borda nativa do próprio grid e clipa os cantos no wrapper do canvas.
   NÃO pintar background no canvas/.dvn-stack: são camadas de overlay e cobrem
   os pixels já desenhados do grid (deixa o card branco e vazio). */
[data-testid="stDataFrame"] [data-testid="stDataFrameResizable"] {{
  border: none !important;
  border-radius: 14px !important;
  overflow: hidden !important; }}
[data-testid="stDataFrameResizable"] th {{ color: {P['muted']} !important; font-size: 12px !important; font-weight: 600 !important; }}
[data-testid="stDataFrameResizable"] td {{ font-size: 13px !important; }}

/* ── dataframe_card(): título + st.dataframe no MESMO pub-card branco ──
   O container keyed (st.container(key="dfc_…")) vira o card; o dataframe nativo
   lá dentro perde a própria borda/sombra p/ não duplicar. */
[class*="st-key-dfc_"] {{
  background: {P['surface']} !important; border: 1px solid {P['border']} !important;
  border-radius: {RADIUS['lg']} !important; padding: 18px 20px 16px !important;
  box-shadow: {P['shadow']} !important; margin-bottom: 4px !important; }}
[class*="st-key-dfc_"] [data-testid="stDataFrame"] {{
  border: none !important; box-shadow: none !important; border-radius: 0 !important;
  margin-bottom: 0 !important; }}
/* gráfico Plotly dentro de um card dfc_: anula o card próprio do Plotly p/ não duplicar */
[class*="st-key-dfc_"] [data-testid="stElementContainer"]:has([data-testid="stPlotlyChart"]) {{
  border: none !important; box-shadow: none !important; padding: 0 !important;
  background: transparent !important; margin-bottom: 0 !important; }}
[class*="st-key-dfc_"] .pub-card-title {{ margin-bottom: 12px !important; }}

/* ── Stat-cards / cards / badges ───────────────────────────── */
.stat-card {{ background:{P['surface']}; border:1px solid {P['border']}; border-radius:{RADIUS['lg']};
  padding:20px 22px; box-shadow:{P['shadow']}; position:relative; overflow:visible;
  transition: box-shadow 150ms cubic-bezier(.4,0,.2,1), transform 150ms cubic-bezier(.4,0,.2,1); }}
.stat-card::before {{ content:''; position:absolute; top:0; left:0; right:0; height:3px;
  border-radius:{RADIUS['lg']} {RADIUS['lg']} 0 0; background: linear-gradient(90deg, {BRAND['400']}, {BRAND['300']}); }}
.stat-card.amber::before {{ background: linear-gradient(90deg, {ACENTO['amber']}, #fbbf24); }}
.stat-card.red::before   {{ background: linear-gradient(90deg, {ACENTO['red']}, #f87171); }}
.stat-card.blue::before  {{ background: linear-gradient(90deg, {ACENTO['blue']}, #60a5fa); }}
.stat-card:hover {{ box-shadow:{P['shadow_h']}; transform:translateY(-2px); border-color:{P['border2']}; }}
.stats-row {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(200px,1fr)); gap:16px; margin-bottom:8px; }}
.stat-val {{ font-family:var(--font-num); font-size:23px; font-weight:700; color:{P['text']};
  line-height:1.1; letter-spacing:-.3px; white-space:nowrap; overflow:visible; text-overflow:clip; }}
.stat-label {{ font-size:13px; color:{P['label']}; font-weight:500; margin-top:4px; }}
.stat-foot {{ display:flex; align-items:center; gap:8px; margin-top:8px; }}
.stat-ico-sm {{ display:inline-flex; align-items:center; justify-content:center;
  width:26px; height:26px; border-radius:8px; font-size:12px; flex-shrink:0;
  background:{BRAND['50']}; color:{BRAND['600']}; }}
.stat-ico-sm.blue {{ background:{SEMANTIC['info_50']}; color:{SEMANTIC['info_700']}; }}
.stat-ico-sm.amber {{ background:{SEMANTIC['warning_50']}; color:{SEMANTIC['warning_700']}; }}
.stat-ico-sm.red {{ background:{SEMANTIC['danger_50']}; color:{SEMANTIC['danger_700']}; }}
/* Ícone (?) com tooltip CSS (instantâneo) — usado em stat-cards e títulos de card */
.help-dot {{ position:relative; display:inline-flex; align-items:center; justify-content:center;
  cursor:help; width:15px; height:15px; border-radius:50%; border:1px solid {P['border2']};
  font-size:10px; font-weight:700; color:{P['muted']}; flex-shrink:0; margin-left:2px; }}
.help-dot:hover {{ border-color:{P['muted']}; color:{P['label']}; }}
.help-dot[data-tip]:hover::after {{
  content: attr(data-tip);
  position:absolute; bottom:135%; left:50%; transform:translateX(-50%);
  background:{P['text']}; color:#fff; padding:8px 11px; border-radius:8px;
  font-size:11px; font-weight:400; line-height:1.45; width:max-content; max-width:260px;
  white-space:normal; text-align:left; z-index:1000; box-shadow:0 6px 18px rgba(0,0,0,.18);
  pointer-events:none; }}
.help-dot[data-tip]:hover::before {{
  content:''; position:absolute; bottom:135%; left:50%; transform:translate(-50%,100%);
  border:5px solid transparent; border-top-color:{P['text']}; z-index:1000; pointer-events:none; }}

.card-hd {{ display:flex; flex-direction:column; justify-content:center; padding:4px 8px 2px; margin-bottom:4px; min-height:42px; }}
.card-title {{ font-size:15px; font-weight:700; color:{P['text']}; }}
.card-sub {{ font-size:12px; color:{P['muted']}; margin-top:1px; }}

.bt-badge {{ display:inline-flex; align-items:center; gap:5px; padding:3px 10px;
  border-radius:99px; font-size:11.5px; font-weight:600; white-space:nowrap; }}
.bt-badge.green {{ background:{BRAND['50']}; color:{BRAND['700']}; border:1px solid {BRAND['100']}; }}
.bt-badge.red   {{ background:{SEMANTIC['danger_50']}; color:{SEMANTIC['danger_700']}; border:1px solid #fecaca; }}
.bt-badge.amber {{ background:{SEMANTIC['warning_50']}; color:{SEMANTIC['warning_700']}; border:1px solid #fde68a; }}
.bt-badge.blue  {{ background:{SEMANTIC['info_50']}; color:{SEMANTIC['info_700']}; border:1px solid #bfdbfe; }}
.bt-badge.gray  {{ background:{P['neutral_bg']}; color:{P['muted']}; border:1px solid {P['border2']}; }}

/* ── Hero band ─────────────────────────────────────────────── */
.hero {{ position:relative; border-radius:18px; overflow:hidden; margin-bottom:18px;
  background: linear-gradient(120deg, {BRAND['700']} 0%, {BRAND['600']} 45%, {BRAND['800']} 100%);
  box-shadow: 0 12px 34px rgba(15,51,23,.25); animation: fadeUp .5s cubic-bezier(.4,0,.2,1) both; }}
.hero::after {{ content:''; position:absolute; left:0; top:0; bottom:0; width:5px;
  background: linear-gradient(180deg,#fff7cc,#ffd700,#b8860b); }}
.hero-inner {{ position:relative; padding:24px 30px; }}
.hero-label {{ font-size:12.5px; font-weight:700; letter-spacing:1.4px; text-transform:uppercase; color: rgba(255,255,255,.72); }}
.hero-value {{ font-family:var(--font-num); font-size:clamp(26px,3vw,40px); font-weight:800; letter-spacing:-.4px;
  line-height:1.05; color:#fff; margin-top:3px; text-shadow:0 2px 10px rgba(0,0,0,.28); }}

/* ── Page header (.ph) — cabeçalho com logo (design system Milhão) ── */
.ph {{ display:flex; align-items:center; justify-content:space-between; gap:16px; margin:0 0 22px;
  animation: fadeUp .45s cubic-bezier(.4,0,.2,1) both; }}
.ph-l {{ display:flex; align-items:center; gap:0; }}
.ph-logo-box {{ display:flex; align-items:center; justify-content:center; height:60px; flex-shrink:0; }}
.ph-logo-img {{ height:46px; width:auto; object-fit:contain; display:block; }}
.ph-sep {{ width:1px; height:40px; background:{P['border2']}; flex-shrink:0; margin:0 18px; }}
.ph-title {{ font-size:22px; font-weight:800; color:{P['text']}; letter-spacing:-.3px; line-height:1.2; }}
.ph-sub {{ font-size:12.5px; color:{P['muted']}; margin-top:3px; }}
.ph-stamp {{ font-size:12px; color:{P['muted']}; white-space:nowrap; display:inline-flex; align-items:center;
  gap:6px; background:{P['surface']}; border:1px solid {P['border']}; padding:7px 12px; border-radius:99px;
  box-shadow:{P['shadow']}; }}
.ph-stamp i {{ color:{BRAND['500']}; }}

/* ── Animação de entrada ───────────────────────────────────── */
@keyframes fadeUp {{ from {{ opacity:0; transform:translateY(12px); }} to {{ opacity:1; transform:none; }} }}
@keyframes fadeIn {{ from {{ opacity:0; transform:translateY(8px); }} to {{ opacity:1; transform:translateY(0); }} }}
@media (prefers-reduced-motion: reduce) {{ * {{ animation:none !important; }} }}

/* ── Responsivo: celular (≤640px) ──────────────────────────────
   Empilha colunas, reduz paddings/fontes, aperta linhas de barra
   e cabeçalho. Tabelas/matriz mantêm scroll horizontal próprio. */
@media (max-width: 640px) {{
  /* colunas lado a lado passam a empilhar (gráficos, KPIs, tabelas) */
  [data-testid="stHorizontalBlock"] {{ flex-direction: column !important; }}
  [data-testid="stColumn"] {{ width: 100% !important; flex: 1 1 100% !important; min-width: 0 !important; }}

  /* margens da página menores */
  .block-container, [data-testid="stMainBlockContainer"] {{
    padding-left: 8px !important; padding-right: 8px !important; }}

  /* KPI tiles menores */
  div[data-testid="stMetric"] {{ padding: 12px 14px !important; min-height: 76px !important; }}
  div[data-testid="stMetricValue"], div[data-testid="stMetricValue"] > div {{ font-size: 20px !important; }}

  /* cards e gráficos com padding menor */
  .pub-card {{ padding: 14px 14px 10px !important; }}
  [data-testid="stElementContainer"]:has([data-testid="stPlotlyChart"]) {{ padding: 12px 10px 8px !important; }}

  /* linhas de barra: encolhe nome/valor p/ caber a barra */
  .pub-bar-row {{ grid-template-columns: minmax(0,110px) 1fr 56px !important; gap: 8px !important; }}

  /* tabs roláveis na horizontal em vez de quebrar */
  .stTabs [data-baseweb="tab-list"] {{ overflow-x: auto !important; flex-wrap: nowrap !important; }}
  .stTabs [data-baseweb="tab"] {{ padding: 8px 10px !important; font-size: 13px !important; white-space: nowrap; }}

  /* cabeçalho com logo: empilha e diminui */
  .ph {{ flex-direction: column; align-items: flex-start; gap: 10px; margin-bottom: 16px; }}
  .ph-title {{ font-size: 18px; }}
  h1 {{ font-size: 21px !important; }}

  /* ── Funis HTML (trapézio): caber em tela estreita ──
     inline styles vencem por especificidade → !important. */
  .fn-journey {{ flex-direction: column !important; }}        /* funil + cards empilham */
  .fn-stages {{ padding-right: 28px !important; }}            /* menos gutter p/ o % */
  .fn-num {{ font-size: 15px !important; }}                   /* número não estoura o trapézio */
  .fn-pct {{ font-size: 10px !important; right: 2px !important; }}
  .fn-tip {{ left: 1px !important; width: 14px !important; height: 14px !important; font-size: 9px !important; }}
  .fn-tip .fn-tipbox {{ left: 18px !important; width: 170px !important; }}
  /* "Venda Perdida" / "Acompanhamento" saem do absoluto e fluem abaixo do funil (sem sobrepor) */
  .fn-loss, .fn-acomp {{ position: static !important; bottom: auto !important; left: auto !important;
    right: auto !important; margin-top: 12px !important; margin-right: 8px !important;
    display: inline-flex !important; }}
}}
</style>
"""


def _registrar_template_plotly() -> None:
    """Registra o template Plotly 'milhao' (claro) e o define como default."""
    tpl = go.layout.Template()
    tpl.layout = go.Layout(
        font=dict(family=FONT, color=P["label"], size=13),
        colorway=COLORWAY,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=20, t=10, b=10),
        xaxis=dict(gridcolor=P["grid"], linecolor=P["border2"], zeroline=False),
        yaxis=dict(gridcolor=P["grid"], linecolor=P["border2"], zeroline=False),
        legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h", y=-.18),
        hoverlabel=dict(font=dict(family=FONT)),
        colorscale=dict(sequential=[[0, BRAND["100"]], [1, BRAND["600"]]]),
    )
    pio.templates["milhao"] = tpl
    pio.templates.default = "plotly_white+milhao"


def aplicar_tema() -> None:
    """Injeta o CSS global (Painel do Milhão · claro) e registra o template Plotly. Chamar 1x."""
    _registrar_template_plotly()
    st.markdown(_css(), unsafe_allow_html=True)
