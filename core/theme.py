import streamlit as st

_GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

/* ── Typography & Fonts ── */
body, p, label, input, select, textarea, h1, h2, h3, h4, h5, h6,
[data-testid="stMarkdownContainer"] *, [data-testid="stCaptionContainer"] *,
[data-testid="stMetricLabel"] *, [data-testid="stMetricValue"] *,
[data-testid="stSidebarContent"] label, [data-testid="stSidebarContent"] p {
    font-family: 'Manrope', -apple-system, sans-serif !important;
}

/* ── KPIs Metric Tiles ── */
div[data-testid="stMetric"], div[data-testid="metric-container"] {
    background: #1c1c1c !important; 
    border-radius: 8px !important; 
    padding: 16px 18px !important; 
    border: none !important;
    min-height: 115px !important;
    animation: fadeIn 0.45s ease-out;
}
div[data-testid="stMetricLabel"] > div, div[data-testid="stMetricLabel"] label, div[data-testid="stMetricLabel"] p {
    font-size: 13px !important; 
    font-weight: 400 !important; 
    color: rgba(255,255,255,0.72) !important;
}
div[data-testid="stMetricValue"], div[data-testid="stMetricValue"] > div {
    font-family: 'JetBrains Mono', monospace !important; 
    font-size: 26px !important; 
    font-weight: 600 !important;
    letter-spacing: -0.01em !important; 
    font-variant-numeric: tabular-nums !important; 
    color: #ffffff !important;
}

/* ── Multiselect Tags ── */
span[data-baseweb="tag"] { background-color: #008140 !important; }
span[data-baseweb="tag"] span[role="img"] svg path { fill: rgba(255,255,255,0.8) !important; }

/* ── Sidebar ── */
section[data-testid="stSidebar"], section[data-testid="stSidebar"] > div { 
    background-color: #1c1c1c !important; 
}
section[data-testid="stSidebar"] label { 
    font-size: 13px !important; 
    color: rgba(255,255,255,0.72) !important; 
    font-weight: 400 !important; 
}
section[data-testid="stSidebar"] .stMultiSelect > div, 
section[data-testid="stSidebar"] .stSelectbox > div,
section[data-testid="stSidebar"] input[type="text"], 
section[data-testid="stSidebar"] input[type="date"] {
    background: #262626 !important; 
    border-color: #3a3a3a !important; 
    border-radius: 8px !important; 
    font-size: 14px !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] { 
    background: transparent !important; 
    border-bottom: 1px solid #2a2a2a !important; 
    gap: 20px !important; 
}
.stTabs [data-baseweb="tab"] { 
    font-size: 14px !important; 
    color: rgba(255,255,255,0.60) !important; 
    background: transparent !important; 
    border: none !important; 
    padding: 10px 4px !important; 
}
.stTabs [data-baseweb="tab"]:hover { color: #ffffff !important; background: transparent !important; }
.stTabs [aria-selected="true"],
.stTabs [data-baseweb="tab"][aria-selected="true"] { 
    color: #ffffff !important; 
    font-weight: 600 !important; 
    background: transparent !important; 
}
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { 
    background-color: #008140 !important; 
    height: 2px !important; 
}

/* ── Headers & Dividers ── */
h1, h2, h3, h4 { font-weight: 700 !important; letter-spacing: -0.005em !important; }
hr { border-color: #2a2a2a !important; }
div[data-testid="stCaptionContainer"] p { color: rgba(255,255,255,0.50) !important; font-size: 13px !important; }

/* ── Radio buttons ── */
[data-testid="stRadio"] label [data-testid="stMarkdownContainer"] p { color: rgba(255,255,255,0.72) !important; }
div[role="radiogroup"] div[data-baseweb="radio"] div:first-child { 
    border-color: rgba(255,255,255,0.4) !important; 
    background-color: transparent !important; 
}
div[role="radiogroup"] div[data-baseweb="radio"] input:checked + div div:first-child { 
    border-color: rgba(255,255,255,0.9) !important; 
    background-color: rgba(255,255,255,0.9) !important; 
}

/* ── Plotly Charts ── */
[data-testid="stPlotlyChart"] > div, 
[data-testid="stPlotlyChart"] .js-plotly-plot, 
[data-testid="stPlotlyChart"] .plotly { 
    border-radius: 8px !important; 
    overflow: hidden !important; 
    background: #1c1c1c !important;
}
[data-testid="stPlotlyChart"] {
    border-radius: 8px !important;
    overflow: hidden !important;
    background: #1c1c1c !important;
    animation: fadeIn 0.45s ease-out;
}

/* ── Dataframes ── */
[data-testid="stDataFrameResizable"] th {
    color: rgba(255,255,255,0.50) !important;
    font-size: 12px !important;
    font-weight: 500 !important;
}
[data-testid="stDataFrameResizable"] td { font-size: 13px !important; }

/* ── CSS Animations for smooth element loading ── */
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(8px); }
    to { opacity: 1; transform: translateY(0); }
}
.pub-card {
    animation: fadeIn 0.45s ease-out;
}
</style>
"""

def aplicar_tema() -> None:
    """Injeta o CSS global (verde Buriti) com animações de transição. Chamar 1x."""
    st.markdown(_GLOBAL_CSS, unsafe_allow_html=True)
