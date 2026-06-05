"""
Biblioteca de componentes padrão — Painel Buriti.

Consolida o melhor de cada dashboard (Google Ads, GA4, Publya, Meta) num único
módulo reutilizável. Design system dark Buriti: Manrope + JetBrains Mono, verde #008140.

Organização:
  - Paletas de cor (por dimensão de cada canal)
  - Tema global (aplicar_tema) + CSS dos cards/barras/tabelas
  - Logo
  - Helpers (_br, cores)
  - KPIs (genérico, recebe dict)
  - Gráficos: evolução, barras mensais, barras horizontais, donut, barras por campanha, CPL
  - Tabelas (simples + HTML genérica)
  - Semáforo / badges
"""
import base64
import os

import pandas as pd
import plotly.express as px
import streamlit as st

# ════════════════════════════════════════════════════════════════════════════
# PALETAS DE COR
# ════════════════════════════════════════════════════════════════════════════

# Paleta oficial Buriti
PALETTE = [
    "#008347",  # verde principal
    "#f0f0f0",  # branco
    "#888888",  # cinza
    "#006682",  # azul-petróleo
    "#008274",  # teal-verde
    "#5BD9CC",  # teal claro
    "#1E3436",  # teal escuro
]

VERDE = "#008140"

# Estoque / Lançamento (Google Ads, Meta)
LANCAMENTO_COLOR_MAP = {
    "Lançamento": "#008140",
    "Estoque":    "#00b359",
    "Outros":     "#888888",
}

# Canais de tráfego (GA4)
CANAL_COLORS = {
    "Orgânico":   "#008140",
    "Pago":       "#004d26",
    "Direto":     "#888888",
    "Social":     "#33aa77",
    "Referência": "#00b359",
    "Outros":     "#444444",
}

# Tipo de mídia (Publya)
COLOR_MAP_MIDIA = {
    "Display": "#008140",
    "Vídeo":   "#00b359",
    "Áudio":   "#ffffff",
    "Misto":   "#aaaaaa",
}

# Canais Google Ads (advertising_channel_type)
CHANNEL_LABELS_GADS = {
    "SEARCH": "Pesquisa", "PERFORMANCE_MAX": "Performance Max", "DISPLAY": "Display",
    "SHOPPING": "Shopping", "VIDEO": "Vídeo", "SMART": "Smart",
}
CHANNEL_COLORS_GADS = {
    "Pesquisa": PALETTE[0], "Performance Max": PALETTE[4], "Display": PALETTE[3],
    "Shopping": PALETTE[5], "Vídeo": PALETTE[6], "Smart": PALETTE[2],
}

# Objetivos Meta
OBJECTIVE_COLOR_MAP = {
    "OUTCOME_LEADS": "#008140", "OUTCOME_AWARENESS": "#00b359",
    "OUTCOME_ENGAGEMENT": "#66cc99", "OUTCOME_TRAFFIC": "#004d26",
    "OUTCOME_SALES": "#33aa77", "OUTCOME_APP_PROMOTION": "#888888",
    "CONVERSIONS": "#005c2e", "LINK_CLICKS": "#99ddbb",
    "REACH": "#00b359", "VIDEO_VIEWS": "#cceedb",
}
OBJECTIVE_LABELS = {
    "OUTCOME_AWARENESS": "Alcance", "OUTCOME_TRAFFIC": "Tráfego",
    "OUTCOME_ENGAGEMENT": "Engajamento", "OUTCOME_LEADS": "Leads",
    "OUTCOME_APP_PROMOTION": "App", "OUTCOME_SALES": "Vendas",
    "CONVERSIONS": "Conversões", "LINK_CLICKS": "Cliques",
    "REACH": "Alcance", "VIDEO_VIEWS": "Visualizações",
}


def label_obj(obj: str) -> str:
    return OBJECTIVE_LABELS.get(str(obj), str(obj).replace("OUTCOME_", "").replace("_", " ").title())


POR_PAGINA = 20

# ════════════════════════════════════════════════════════════════════════════
# CSS
# ════════════════════════════════════════════════════════════════════════════

# CSS dos componentes HTML (cards, barras, tabelas, badges) — injetado junto com cada bloco
_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');
.pub-card { background:#1c1c1c; border-radius:8px; padding:18px 20px 14px; margin-bottom:4px; }
.pub-card-title { font-family:'Manrope',sans-serif; font-size:15px; font-weight:600; color:#fff; margin-bottom:16px; }
.pub-bar-list { display:flex; flex-direction:column; gap:9px; }
.pub-bar-row { display:grid; grid-template-columns:minmax(0,240px) 1fr 130px; align-items:center; gap:12px; }
.pub-bar-name { font-family:'Manrope',sans-serif; font-size:12px; color:#fff; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; min-width:0; }
.pub-bar-track { height:16px; background:#262626; border-radius:3px; overflow:hidden; }
.pub-bar-fill { height:100%; border-radius:3px; }
.pub-bar-value { font-family:'JetBrains Mono',monospace; font-size:12px; color:rgba(255,255,255,0.72); text-align:right; font-variant-numeric:tabular-nums; }
.pub-bar-legend { display:flex; gap:14px; margin-top:14px; padding-top:12px; border-top:1px solid #2a2a2a; flex-wrap:wrap; }
.pub-legend-item { display:inline-flex; align-items:center; gap:6px; font-family:'Manrope',sans-serif; font-size:12px; color:rgba(255,255,255,0.72); }
.pub-legend-dot { width:8px; height:8px; border-radius:50%; display:inline-block; flex-shrink:0; }
.pub-table-wrap { overflow-x:auto; }
.pub-table { width:100%; border-collapse:collapse; font-family:'Manrope',sans-serif; font-size:13px; }
.pub-table th { padding:9px 12px; text-align:left; border-bottom:1px solid #2a2a2a; color:rgba(255,255,255,0.50); font-size:12px; font-weight:500; white-space:nowrap; }
.pub-table td { padding:9px 12px; border-bottom:1px solid #1f1f1f; color:#fff; white-space:nowrap; }
.pub-table th.num, .pub-table td.num { text-align:right; font-family:'JetBrains Mono',monospace; font-variant-numeric:tabular-nums; font-size:12px; }
.pub-table tbody tr:hover td { background:rgba(255,255,255,0.025); }
.pub-table tr.total td { border-top:1px solid #3a3a3a; border-bottom:none; font-weight:700; background:rgba(0,129,64,0.07); }
.pub-badge { display:inline-flex; align-items:center; gap:5px; border-radius:9999px; padding:2px 9px; font-size:11px; font-weight:500; white-space:nowrap; }
.pub-badge-dot { width:7px; height:7px; border-radius:50%; display:inline-block; flex-shrink:0; }
</style>
"""

# CSS global — aplicado 1x no app; troca o vermelho do Streamlit pelo verde Buriti
_GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');
body, p, label, input, select, textarea, h1, h2, h3, h4, h5, h6,
[data-testid="stMarkdownContainer"] *, [data-testid="stCaptionContainer"] *,
[data-testid="stMetricLabel"] *, [data-testid="stMetricValue"] *,
[data-testid="stSidebarContent"] label, [data-testid="stSidebarContent"] p {
    font-family: 'Manrope', -apple-system, sans-serif !important;
}
div[data-testid="stMetric"], div[data-testid="metric-container"] {
    background:#1c1c1c !important; border-radius:8px !important; padding:16px 18px !important; border:none !important;
}
div[data-testid="stMetricLabel"] > div, div[data-testid="stMetricLabel"] label, div[data-testid="stMetricLabel"] p {
    font-size:13px !important; font-weight:400 !important; color:rgba(255,255,255,0.72) !important;
}
div[data-testid="stMetricValue"], div[data-testid="stMetricValue"] > div {
    font-family:'JetBrains Mono',monospace !important; font-size:26px !important; font-weight:600 !important;
    letter-spacing:-0.01em !important; font-variant-numeric:tabular-nums !important; color:#fff !important;
}
span[data-baseweb="tag"] { background-color:#008140 !important; }
span[data-baseweb="tag"] span[role="img"] svg path { fill:rgba(255,255,255,0.8) !important; }
section[data-testid="stSidebar"], section[data-testid="stSidebar"] > div { background-color:#1c1c1c !important; }
section[data-testid="stSidebar"] label { font-size:13px !important; color:rgba(255,255,255,0.72) !important; font-weight:400 !important; }
section[data-testid="stSidebar"] .stMultiSelect > div, section[data-testid="stSidebar"] .stSelectbox > div,
section[data-testid="stSidebar"] input[type="text"], section[data-testid="stSidebar"] input[type="date"] {
    background:#262626 !important; border-color:#3a3a3a !important; border-radius:8px !important; font-size:14px !important;
}
.stTabs [data-baseweb="tab-list"] { background:transparent !important; border-bottom:1px solid #2a2a2a !important; gap:20px !important; }
.stTabs [data-baseweb="tab"] { font-size:14px !important; color:rgba(255,255,255,0.60) !important; background:transparent !important; border:none !important; padding:10px 4px !important; }
.stTabs [data-baseweb="tab"]:hover { color:#fff !important; }
.stTabs [aria-selected="true"] { color:#fff !important; font-weight:600 !important; background:transparent !important; }
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { background-color:#008140 !important; height:2px !important; }
h1, h2, h3, h4 { font-weight:700 !important; letter-spacing:-0.005em !important; }
[data-testid="stRadio"] label [data-testid="stMarkdownContainer"] p { color:rgba(255,255,255,0.72) !important; }
div[role="radiogroup"] div[data-baseweb="radio"] div:first-child { border-color:rgba(255,255,255,0.4) !important; background-color:transparent !important; }
div[role="radiogroup"] div[data-baseweb="radio"] input:checked + div div:first-child { border-color:rgba(255,255,255,0.9) !important; background-color:rgba(255,255,255,0.9) !important; }
[data-testid="stPlotlyChart"] > div, [data-testid="stPlotlyChart"] .js-plotly-plot, [data-testid="stPlotlyChart"] .plotly { border-radius:8px !important; overflow:hidden !important; }
hr { border-color:#2a2a2a !important; }
div[data-testid="stCaptionContainer"] p { color:rgba(255,255,255,0.50) !important; font-size:13px !important; }
</style>
"""


def aplicar_tema() -> None:
    """Injeta o CSS global (verde Buriti). Chamar 1x no topo do app."""
    st.markdown(_GLOBAL_CSS, unsafe_allow_html=True)


def _html(content: str) -> None:
    if hasattr(st, "html"):
        st.html(_CSS + content)
    else:
        st.markdown(_CSS + content, unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# LOGO
# ════════════════════════════════════════════════════════════════════════════

_ASSETS     = os.path.join(os.path.dirname(__file__), "assets")
LOGO_CLARA  = os.path.join(_ASSETS, "logo_preta.png")
LOGO_ESCURA = os.path.join(_ASSETS, "logo_branca.png")


def _imagem_base64(caminho: str) -> str:
    with open(caminho, "rb") as f:
        return base64.b64encode(f.read()).decode()


def exibir_logo() -> None:
    existe_clara  = os.path.exists(LOGO_CLARA)
    existe_escura = os.path.exists(LOGO_ESCURA)
    if not existe_clara and not existe_escura:
        return
    caminho_claro  = LOGO_CLARA  if existe_clara  else LOGO_ESCURA
    caminho_escuro = LOGO_ESCURA if existe_escura else LOGO_CLARA
    st.markdown(
        f"""
        <style>
            .logo-container {{ display:flex; justify-content:flex-start; margin-bottom:0.75rem; }}
            .logo-container img {{ width:min(220px,55vw); height:auto; }}
            .logo-dark {{ display:none; }}
            @media (prefers-color-scheme:dark) {{
                .logo-light {{ display:none; }}
                .logo-dark  {{ display:block; }}
            }}
        </style>
        <div class="logo-container">
            <img class="logo-light" src="data:image/png;base64,{_imagem_base64(caminho_claro)}">
            <img class="logo-dark"  src="data:image/png;base64,{_imagem_base64(caminho_escuro)}">
        </div>
        """,
        unsafe_allow_html=True,
    )


# ════════════════════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════════════════════

def _tema() -> str:
    return "plotly_dark" if st.get_option("theme.base") == "dark" else "plotly_white"


def _br(valor, decimais: int = 0, prefixo: str = "") -> str:
    """Formatação numérica brasileira: 1.234,56."""
    try:
        fmt = f"{float(valor):,.{decimais}f}"
    except Exception:
        return "—"
    fmt = fmt.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{prefixo}{fmt}"


def _font_color_para_fundo(hex_color: str) -> str:
    r, g, b = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)
    lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return "black" if lum > 0.55 else "white"


def _rgba(hex_color: str, alpha: float) -> str:
    r, g, b = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)
    return f"rgba({r},{g},{b},{alpha})"


_LAYOUT_BASE = dict(
    plot_bgcolor="#1c1c1c", paper_bgcolor="#1c1c1c",
    font=dict(family="Manrope, sans-serif", color="#ffffff"),
    margin=dict(l=20, r=20, t=50, b=20),
    xaxis=dict(title=None, gridcolor="#2a2a2a", linecolor="#2a2a2a"),
    yaxis=dict(title=None, gridcolor="#2a2a2a"),
    separators=",.",
)


def _titulo_layout(titulo: str) -> dict:
    return dict(font=dict(family="Manrope, sans-serif", size=15, color="#ffffff"),
                x=0, xanchor="left", pad=dict(l=4), text=titulo)


def _legenda_html(df: pd.DataFrame, col: str, color_map: dict) -> str:
    if col not in df.columns:
        return ""
    presentes = df[col].dropna().unique()
    return "".join(
        f'<span class="pub-legend-item">'
        f'<span class="pub-legend-dot" style="background:{color_map.get(t, "#888")}"></span>{t}</span>'
        for t in color_map if t in presentes
    )


# ════════════════════════════════════════════════════════════════════════════
# KPIs (genérico — recebe {label: valor})
# ════════════════════════════════════════════════════════════════════════════

def kpis(metricas: dict) -> None:
    """Linha de KPIs. `metricas` = {"Investimento": "R$ 1.234", ...}."""
    if not metricas:
        return
    cols = st.columns(len(metricas))
    for col, (label, valor) in zip(cols, metricas.items()):
        col.metric(label, valor)


# ════════════════════════════════════════════════════════════════════════════
# GRÁFICO — evolução temporal (área diária / barras mensais, com toggle)
# ════════════════════════════════════════════════════════════════════════════

def grafico_evolucao(df: pd.DataFrame, date_col: str, value_col: str, titulo: str,
                     cor: str = VERDE, fmt=None, key: str = "") -> None:
    fmt = fmt or (lambda v: _br(v))
    gran = st.radio("Visualização", ["Diário", "Mensal"], horizontal=True,
                    key=f"gran_{key}", label_visibility="collapsed")

    d = df.copy()
    d[date_col] = pd.to_datetime(d[date_col])
    if gran == "Mensal":
        d["periodo"] = d[date_col].dt.to_period("M").dt.to_timestamp()
    else:
        d["periodo"] = d[date_col].dt.normalize()
    agg = d.groupby("periodo", as_index=False)[value_col].sum()
    if agg.empty:
        st.info("Sem dados no período.")
        return

    titulo_full = f"{titulo} ({'mês' if gran == 'Mensal' else 'dia'})"

    if gran == "Mensal":
        agg["periodo_str"] = agg["periodo"].dt.strftime("%b/%Y")
        y_max = float(agg[value_col].max()) or 1
        fig = px.bar(agg, x="periodo_str", y=value_col)
        fig.update_traces(
            marker_color=cor, text=[fmt(v) for v in agg[value_col]],
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
        fig = px.area(agg, x="periodo", y=value_col, color_discrete_sequence=[cor])
        fig.update_traces(line=dict(width=2, color=cor), fillcolor=_rgba(cor, 0.13))
        fig.update_layout(**{**_LAYOUT_BASE, **dict(height=380, title=_titulo_layout(titulo_full))})

    st.plotly_chart(fig, width="stretch")


# ════════════════════════════════════════════════════════════════════════════
# GRÁFICO — barras mensais (genérico, aceita stack por cor)
# ════════════════════════════════════════════════════════════════════════════

def grafico_barras_mensais(df: pd.DataFrame, x: str, y: str, titulo: str,
                           color: str | None = None, color_map: dict | None = None) -> None:
    df = df.copy()
    if pd.api.types.is_datetime64_any_dtype(df[x]):
        df = df.sort_values(x)
        df[x] = df[x].dt.strftime("%b/%Y")

    kwargs = dict(x=x, y=y, title=titulo, barmode="stack" if color else "relative")
    if color:
        kwargs["color"] = color
    if color_map:
        kwargs["color_discrete_map"] = color_map
    fig = px.bar(df, **kwargs)

    y_range = None if color else [0, (float(df[y].max()) if not df.empty else 1) * 1.22]
    fig.update_layout(
        template=_tema(), height=400, margin=dict(l=20, r=20, t=40, b=20),
        xaxis=dict(title=None, type="category"),
        yaxis=dict(title=None, gridcolor="#2a2a2a", range=y_range),
        legend=dict(orientation="h", y=-0.22, title=None), bargap=0.28,
        plot_bgcolor="#1c1c1c", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Manrope, sans-serif", color="#ffffff"),
        title=dict(font=dict(family="Manrope, sans-serif", size=15, color="#fff"), x=0, xanchor="left", pad=dict(l=4)),
        separators=",.",
    )
    if not color:
        fig.update_traces(
            marker_color=VERDE, text=[_br(v) for v in df[y]], texttemplate="%{text}",
            textposition="outside", textfont=dict(size=11, color="rgba(255,255,255,0.75)"), cliponaxis=False,
        )
    st.plotly_chart(fig, width="stretch")


# ════════════════════════════════════════════════════════════════════════════
# GRÁFICO — barras horizontais top-N (card HTML)
# ════════════════════════════════════════════════════════════════════════════

def grafico_barras_h_card(df: pd.DataFrame, x_col: str, y_col: str, titulo: str,
                          top_n: int = 15, color: str = VERDE, fmt=None) -> None:
    fmt = fmt or (lambda v: _br(v))
    if df.empty:
        _html(f'<div class="pub-card"><div class="pub-card-title">{titulo}</div><div style="color:#888">Sem dados.</div></div>')
        return
    df_top = df.nlargest(top_n, x_col).copy()
    max_val = float(df_top[x_col].max()) or 1
    rows_html = ""
    for _, row in df_top.sort_values(x_col, ascending=False).iterrows():
        val, name = float(row[x_col]), str(row[y_col])
        bar_w = val / max_val * 100
        name_tr = (name[:38] + "…") if len(name) > 38 else name
        rows_html += (
            f'<div class="pub-bar-row"><div class="pub-bar-name" title="{name}">{name_tr}</div>'
            f'<div class="pub-bar-track"><div class="pub-bar-fill" style="width:{bar_w:.2f}%;background:{color};"></div></div>'
            f'<div class="pub-bar-value">{fmt(val)}</div></div>'
        )
    _html(f'<div class="pub-card"><div class="pub-card-title">{titulo}</div><div class="pub-bar-list">{rows_html}</div></div>')


# ════════════════════════════════════════════════════════════════════════════
# GRÁFICO — donut (unificado: color_map, total no centro, label_func, show_cpl)
# ════════════════════════════════════════════════════════════════════════════

def grafico_donut(df: pd.DataFrame, dim: str, valor: str, titulo: str,
                  color_map: dict | None = None, total_centro: bool = False,
                  fmt=None, label_func=None, pct_min: float = 5.0) -> None:
    if dim not in df.columns or valor not in df.columns:
        return
    fmt = fmt or (lambda v: _br(v))
    d = df.copy()
    d["_lbl"] = d[dim].map(label_func) if label_func else d[dim].astype(str)
    resumo = d.groupby("_lbl", as_index=False)[valor].sum()
    total = resumo[valor].sum()
    resumo["_pct"] = (resumo[valor] / total * 100).round(1) if total else 0
    resumo["_text"] = resumo.apply(
        lambda r: f"{fmt(r[valor])}<br>{r['_pct']:.1f}%" if r["_pct"] >= pct_min else "", axis=1)
    font_colors = [_font_color_para_fundo((color_map or {}).get(t, "#888888")) for t in resumo["_lbl"]]

    fig = px.pie(resumo, names="_lbl", values=valor, hole=0.58, title=titulo,
                 color="_lbl", color_discrete_map=color_map or {})
    fig.update_traces(
        text=resumo["_text"].tolist(), textposition="inside", textinfo="text",
        insidetextfont=dict(family="JetBrains Mono, monospace", size=11, color=font_colors),
        hovertemplate="%{label}: %{value:,.0f} (%{percent})",
        domain=dict(x=[0, 0.62], y=[0, 1]),
    )
    if total_centro:
        fig.add_annotation(
            text=f"<b>{fmt(total)}</b><br><span style='font-size:11px;opacity:0.6'>total</span>",
            x=0.31, y=0.5, showarrow=False, xanchor="center", yanchor="middle",
            font=dict(family="JetBrains Mono, monospace", size=14, color="#fff"),
        )
    fig.update_layout(
        template=_tema(), separators=",.", height=340, margin=dict(l=10, r=10, t=50, b=10),
        legend=dict(orientation="v", x=0.65, y=0.5, xanchor="left", yanchor="middle",
                    font=dict(family="Manrope, sans-serif", size=12, color="rgba(255,255,255,0.8)")),
        font=dict(family="Manrope, sans-serif", color="#fff"),
        title=_titulo_layout(titulo),
    )
    st.plotly_chart(fig, width="stretch")


# ════════════════════════════════════════════════════════════════════════════
# GRÁFICO — barras por campanha (paginado, colorido por categoria)
# ════════════════════════════════════════════════════════════════════════════

def grafico_barras_campanha(df: pd.DataFrame, coluna: str, titulo: str, key: str,
                            fmt=None, cor_por: str = "Tipo_Lancamento",
                            color_map: dict | None = None, nome_col: str = "campaign_name") -> None:
    fmt = fmt or (lambda v: _br(v))
    color_map = color_map or LANCAMENTO_COLOR_MAP
    if df.empty or coluna not in df.columns or nome_col not in df.columns:
        st.info("Sem dados.")
        return

    totais = df.groupby(nome_col)[coluna].sum().sort_values(ascending=False)
    cor_por_nome = df.groupby(nome_col)[cor_por].first() if cor_por in df.columns else {}

    nomes_ord = totais.index.tolist()
    n_total = len(nomes_ord)
    n_pages = max(1, -(-n_total // POR_PAGINA))
    if key not in st.session_state:
        st.session_state[key] = 0
    page = min(st.session_state[key], n_pages - 1)
    st.session_state[key] = page

    nomes_pag = nomes_ord[page * POR_PAGINA:(page + 1) * POR_PAGINA]
    max_val = totais.max() or 1

    rows_html = ""
    for nome in nomes_pag:
        val = totais[nome]
        tipo = cor_por_nome.get(nome, "Outros") if hasattr(cor_por_nome, "get") else "Outros"
        color = color_map.get(tipo, "#888888")
        bar_w = (val / max_val * 100) if max_val else 0
        name_tr = (str(nome)[:42] + "…") if len(str(nome)) > 42 else nome
        rows_html += (
            f'<div class="pub-bar-row"><div class="pub-bar-name" title="{nome}">{name_tr}</div>'
            f'<div class="pub-bar-track"><div class="pub-bar-fill" style="width:{bar_w:.2f}%;background:{color};"></div></div>'
            f'<div class="pub-bar-value">{fmt(val)}</div></div>'
        )

    _html(
        f'<div class="pub-card"><div class="pub-card-title">{titulo}</div>'
        f'<div class="pub-bar-list">{rows_html}</div>'
        f'<div class="pub-bar-legend">{_legenda_html(df, cor_por, color_map)}</div></div>'
    )

    if n_pages > 1:
        c1, c2, c3 = st.columns([1, 5, 1])
        with c1:
            if st.button("← Ant.", key=f"prev_{key}", disabled=page == 0):
                st.session_state[key] -= 1
                st.rerun()
        with c2:
            st.caption(f"Página {page + 1} de {n_pages}  ·  {n_total} itens")
        with c3:
            if st.button("Próx. →", key=f"next_{key}", disabled=page >= n_pages - 1):
                st.session_state[key] += 1
                st.rerun()


# ════════════════════════════════════════════════════════════════════════════
# SEMÁFORO / BADGES
# ════════════════════════════════════════════════════════════════════════════

COR_BOM, COR_MEDIO, COR_RUIM = "#008140", "#d4a017", "#c0392b"


def _dot(color: str) -> str:
    return (f'<span style="display:inline-block;width:7px;height:7px;border-radius:50%;'
            f'background:{color};flex-shrink:0;margin-right:5px"></span>')


def cor_cpc(cpc: float, media: float) -> str:
    """Verde < 90% da média | Amarelo 90–120% | Vermelho > 120%."""
    if media <= 0:
        return COR_MEDIO
    ratio = cpc / media
    return COR_BOM if ratio <= 0.90 else (COR_MEDIO if ratio <= 1.20 else COR_RUIM)


def cor_aproveitamento(pct: float) -> str:
    """Verde ≥ 80% | Amarelo 50–79% | Vermelho < 50%."""
    return COR_BOM if pct >= 80 else (COR_MEDIO if pct >= 50 else COR_RUIM)


def badge_html(texto: str, color_map: dict | None = None, label_func=None) -> str:
    """Pílula colorida para uma categoria (objetivo, tipo de mídia, etc.)."""
    color = (color_map or {}).get(texto, "#888888")
    label = label_func(texto) if label_func else str(texto)
    return (f'<span class="pub-badge" style="background:{color}22;border:1px solid {color}55;color:{color}">'
            f'<span class="pub-badge-dot" style="background:{color}"></span>{label}</span>')


# ════════════════════════════════════════════════════════════════════════════
# TABELAS
# ════════════════════════════════════════════════════════════════════════════

def tabela(df: pd.DataFrame) -> None:
    """Tabela simples (dataframe nativo) — ideal para dado bruto."""
    st.dataframe(df, hide_index=True, width="stretch")


def tabela_html(df: pd.DataFrame, col_specs: list[dict], com_total: bool = True,
                badge_col: str | None = None, badge_map: dict | None = None,
                badge_label=None) -> None:
    """
    Tabela HTML estilizada (pub-table) com linha TOTAL opcional.

    col_specs: lista de dicts:
      {"key": <coluna>, "header": <título>, "num": True/False, "dec": 0, "pref": ""}
    badge_col: coluna renderizada como badge colorida (usa badge_map / badge_label).
    """
    header = "<tr>" + "".join(
        f'<th class="num">{c["header"]}</th>' if c.get("num") else f'<th>{c["header"]}</th>'
        for c in col_specs
    ) + "</tr>"

    # Totais (apenas colunas numéricas somáveis)
    totais = {}
    if com_total:
        for c in col_specs:
            if c.get("num") and c.get("somar", True) and c["key"] in df.columns:
                totais[c["key"]] = pd.to_numeric(df[c["key"]], errors="coerce").sum()

    def _cell(c, row):
        key = c["key"]
        if badge_col and key == badge_col:
            return f'<td>{badge_html(str(row.get(key, "")), badge_map, badge_label)}</td>'
        if c.get("num"):
            return f'<td class="num">{_br(row.get(key, 0), c.get("dec", 0), c.get("pref", ""))}</td>'
        return f'<td>{row.get(key, "")}</td>'

    rows_html = ""
    for _, row in df.iterrows():
        rows_html += "<tr>" + "".join(_cell(c, row) for c in col_specs) + "</tr>"

    if com_total and totais:
        cells = ""
        first = True
        for c in col_specs:
            if first:
                cells += '<td><b>TOTAL</b></td>'
                first = False
            elif c["key"] in totais:
                cells += f'<td class="num">{_br(totais[c["key"]], c.get("dec", 0), c.get("pref", ""))}</td>'
            else:
                cells += '<td class="num">—</td>'
        rows_html += f'<tr class="total">{cells}</tr>'

    _html(f'<div class="pub-card"><div class="pub-table-wrap">'
          f'<table class="pub-table"><thead>{header}</thead><tbody>{rows_html}</tbody></table>'
          f'</div></div>')
