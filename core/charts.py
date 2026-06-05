import pandas as pd
import plotly.express as px
import streamlit as st

from core.format import (
    VERDE,
    LANCAMENTO_COLOR_MAP,
    _br,
    _rgba,
    _font_color_para_fundo,
)

# ════════════════════════════════════════════════════════════════════════════
# CONSTANTES E LAYOUT
# ════════════════════════════════════════════════════════════════════════════

POR_PAGINA = 20

# CSS dos componentes HTML (cards, barras, tabelas, badges)
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

/* Hierarchical Matrix Grid Styles */
.pub-matrix-wrap { background:#1c1c1c; border-radius:8px; overflow-x:auto; font-family:'Manrope',sans-serif; margin-bottom:15px; border: 1px solid #2a2a2a; }
.pub-matrix-header { display:grid; border-bottom:2px solid #2a2a2a; padding:10px 12px; color:rgba(255,255,255,0.5); font-size:12px; font-weight:500; gap:10px; min-width: 900px; }
.pub-matrix-row { display:grid; align-items:center; padding:9px 12px; border-bottom:1px solid #1f1f1f; font-size:13px; color:#fff; gap:10px; min-width: 900px; }
.pub-matrix-row:hover { background:rgba(255,255,255,0.02); }
.pub-matrix-col { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.pub-matrix-col.num { text-align:right; font-family:'JetBrains Mono',monospace; font-variant-numeric:tabular-nums; font-size:12px; }
.pub-matrix-details { display:block; }
.pub-matrix-details > summary { list-style:none; cursor:pointer; outline:none; }
.pub-matrix-details > summary::-webkit-details-marker { display:none; }
.pub-matrix-toggle { display:inline-flex; align-items:center; justify-content:center; width:14px; height:14px; margin-right:6px; color:#00b359; transition:transform 0.15s; font-size:10px; font-weight:bold; }
.pub-matrix-details[open] > summary .pub-matrix-toggle { transform:rotate(90deg); }
.pub-matrix-children { padding-left:0px; background:rgba(0,0,0,0.12); border-left:1px dashed rgba(255,255,255,0.05); }
.pub-matrix-total { display:grid; align-items:center; padding:10px 12px; font-weight:700; background:rgba(0,129,64,0.07); border-top:1px solid #3a3a3a; font-size:13px; gap:10px; min-width: 900px; }
.stDownloadButton { display: flex; justify-content: flex-end; }
</style>
"""


_LAYOUT_BASE = dict(
    plot_bgcolor="#1c1c1c", paper_bgcolor="#1c1c1c",
    font=dict(family="Manrope, sans-serif", color="#ffffff"),
    margin=dict(l=20, r=20, t=50, b=20),
    xaxis=dict(title=None, gridcolor="#2a2a2a", linecolor="#2a2a2a"),
    yaxis=dict(title=None, gridcolor="#2a2a2a"),
    separators=",.",
)

# Layout específico para gráficos de rosca
_DONUT_LAYOUT = dict(
    plot_bgcolor="#1c1c1c", paper_bgcolor="#1c1c1c",
    separators=",.", height=340,
    margin=dict(l=10, r=10, t=50, b=10),
    legend=dict(
        orientation="v", x=0.65, y=0.5, xanchor="left", yanchor="middle",
        font=dict(family="Manrope, sans-serif", size=12, color="rgba(255,255,255,0.8)"),
    ),
    font=dict(family="Manrope, sans-serif", color="#ffffff"),
)

def _html(content: str) -> None:
    """Renderiza conteúdo HTML."""
    if hasattr(st, "html"):
        st.html(_CSS + content)
    else:
        st.markdown(_CSS + content, unsafe_allow_html=True)

def _tema() -> str:
    return "plotly_dark" if st.get_option("theme.base") == "dark" else "plotly_white"

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
# PLOTLY & HTML CHARTS
# ════════════════════════════════════════════════════════════════════════════

def grafico_evolucao(df: pd.DataFrame, date_col: str, value_col: str, titulo: str,
                     cor: str = VERDE, fmt=None, key: str = "") -> None:
    """Gera gráfico temporal com toggle Diário (Área) / Mensal (Barras)."""
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

    st.plotly_chart(fig, use_container_width=True)


def grafico_barras_mensais(df: pd.DataFrame, x: str, y: str, titulo: str,
                           color: str | None = None, color_map: dict | None = None,
                           fmt=None) -> None:
    """Gráfico de barras mensais com empilhamento opcional por cor e rótulos."""
    if fmt is None:
        if any(w in y.lower() for w in ["investimento", "spend", "cost", "budget", "valor", "gasto"]):
            fmt = lambda v: _br(v, 2, "R$ ")
        else:
            fmt = lambda v: _br(v)

    df = df.copy()
    if pd.api.types.is_datetime64_any_dtype(df[x]):
        df = df.sort_values(x)
        df[x] = df[x].dt.strftime("%b/%Y")

    # Create formatted labels for traces
    df["text_label"] = df[y].apply(lambda v: fmt(v) if v > 0 else "")

    kwargs = dict(
        x=x, y=y, title=titulo, 
        barmode="stack" if color else "relative",
        text="text_label"
    )
    if color:
        kwargs["color"] = color
    if color_map:
        kwargs["color_discrete_map"] = color_map
    fig = px.bar(df, **kwargs)

    if color:
        totals = df.groupby(x)[y].sum().reset_index()
        y_max = float(totals[y].max()) if not totals.empty else 1
        y_range = [0, y_max * 1.25]  # slightly higher range for annotation clearance
    else:
        y_max = float(df[y].max()) if not df.empty else 1
        y_range = [0, y_max * 1.22]

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

    if color:
        # Show labels inside the segments
        fig.update_traces(
            textposition="inside",
            insidetextanchor="middle",
            textfont=dict(size=10, family="JetBrains Mono, monospace"),
            cliponaxis=False,
        )
        # Add total sums on top of each stacked bar
        for _, row in totals.iterrows():
            total_val = row[y]
            if total_val > 0:
                fig.add_annotation(
                    x=row[x],
                    y=total_val,
                    text=fmt(total_val),
                    showarrow=False,
                    yshift=10,
                    xanchor="center",
                    yanchor="bottom",
                    font=dict(size=11, color="rgba(255,255,255,0.85)", family="JetBrains Mono, monospace")
                )
    else:
        fig.update_traces(
            marker_color=VERDE,
            textposition="outside",
            textfont=dict(size=11, color="rgba(255,255,255,0.75)", family="JetBrains Mono, monospace"),
            cliponaxis=False,
        )

    st.plotly_chart(fig, use_container_width=True)


def grafico_barras_h_card(df: pd.DataFrame, x_col: str, y_col: str, titulo: str,
                          top_n: int = 15, color: str = VERDE, fmt=None) -> None:
    """Gráfico de barras horizontais embutido em um HTML Card."""
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


def grafico_donut(df: pd.DataFrame, dim: str, valor: str, titulo: str,
                  color_map: dict | None = None, total_centro: bool = False,
                  fmt=None, label_func=None, pct_min: float = 5.0) -> None:
    """Gráfico de rosca/donut estilizado com totalizador no centro opcional."""
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
    st.plotly_chart(fig, use_container_width=True)


def grafico_barras_campanha(df: pd.DataFrame, coluna: str, titulo: str, key: str,
                            fmt=None, cor_por: str = "Tipo_Lancamento",
                            color_map: dict | None = None, nome_col: str = "campaign_name") -> None:
    """Gráfico de barras horizontais de campanhas paginado (20 por página) e colorido por categoria."""
    fmt = fmt or (lambda v: _br(v))
    color_map = color_map or LANCAMENTO_COLOR_MAP
    if df.empty or coluna not in df.columns or nome_col not in df.columns:
        st.info("Sem dados para esta métrica.")
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
# TABELAS E SEMÁFOROS
# ════════════════════════════════════════════════════════════════════════════

COR_BOM, COR_MEDIO, COR_RUIM = "#008140", "#d4a017", "#c0392b"

def _dot(color: str) -> str:
    return (f'<span style="display:inline-block;width:7px;height:7px;border-radius:50%;'
            f'background:{color};flex-shrink:0;margin-right:5px"></span>')

def cor_cpc(cpc: float, media: float) -> str:
    """Retorna cor do semáforo: Verde < 90% da média | Amarelo 90-120% | Vermelho > 120%."""
    if media <= 0:
        return COR_MEDIO
    ratio = cpc / media
    return COR_BOM if ratio <= 0.90 else (COR_MEDIO if ratio <= 1.20 else COR_RUIM)

def cor_aproveitamento(pct: float) -> str:
    """Retorna cor do semáforo: Verde >= 80% | Amarelo 50-79% | Vermelho < 50%."""
    return COR_BOM if pct >= 80 else (COR_MEDIO if pct >= 50 else COR_RUIM)

def badge_html(texto: str, color_map: dict | None = None, label_func=None) -> str:
    """Renderiza uma pílula HTML colorida para uma determinada categoria."""
    color = (color_map or {}).get(texto, "#888888")
    label = label_func(texto) if label_func else str(texto)
    return (f'<span class="pub-badge" style="background:{color}22;border:1px solid {color}55;color:{color}">'
            f'<span class="pub-badge-dot" style="background:{color}"></span>{label}</span>')

def tabela(df: pd.DataFrame) -> None:
    """Tabela nativa simples."""
    st.dataframe(df, hide_index=True, use_container_width=True)

def tabela_html(df: pd.DataFrame, col_specs: list[dict], com_total: bool = True,
                 badge_col: str | None = None, badge_map: dict | None = None,
                 badge_label=None) -> None:
    """Tabela HTML estilizada (pub-table) com linha TOTAL opcional."""
    header = "<tr>" + "".join(
        f'<th class="num">{c["header"]}</th>' if c.get("num") else f'<th>{c["header"]}</th>'
        for c in col_specs
    ) + "</tr>"

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


def tabela_matriz_html(df: pd.DataFrame, group_cols: list[str], col_specs: list[dict],
                       agg_rules: dict, derived_func=None, grid_template: str = "", active_campaigns=None, key: str = "",
                       df_download=None, download_filename: str = "", download_label: str = "") -> None:
    """Renders a collapsible matrix tree-grid matching the Power BI layout with Drill controls.
    
    Levels are dynamically grouped:
    - Google Ads: Conta -> UF -> Cidade -> Campanha
    - Meta Ads: UF -> Cidade -> Objetivo -> Campanha
    """
    if df.empty:
        _html('<div class="pub-card"><div style="color:#888">Sem dados para exibir.</div></div>')
        return

    grid_style = f"grid-template-columns: {grid_template};"

    # ── State of Expand Level ───────────────────────────────────────────────────
    state_key = f"matrix_expand_level_{key}"
    if state_key not in st.session_state:
        st.session_state[state_key] = 0

    expand_level = st.session_state[state_key]
    max_level = len(group_cols) - 1

    # Render Drill Controls (Power BI style)
    c1, c2, c3, c4, c5 = st.columns([0.8, 0.9, 1.1, 6.0, 1.2])
    with c1:
        if st.button("↑ Drill Up", key=f"btn_up_{key}", disabled=(expand_level == 0)):
            st.session_state[state_key] = max(0, expand_level - 1)
            st.rerun()
    with c2:
        if st.button("↓ Drill Down", key=f"btn_down_{key}", disabled=(expand_level >= max_level)):
            st.session_state[state_key] = min(max_level, expand_level + 1)
            st.rerun()
    with c3:
        if expand_level > 0:
            if st.button("▲ Recolher", key=f"btn_reset_{key}"):
                st.session_state[state_key] = 0
                st.rerun()
        else:
            if st.button("▼ Expandir", key=f"btn_all_{key}"):
                st.session_state[state_key] = max_level
                st.rerun()
    # c4 is empty spacing
    with c5:
        if df_download is not None and download_filename:
            from core.ui import botao_download_csv
            botao_download_csv(df_download, download_filename, download_label)

    # Build Header HTML
    header_cols = ""
    for spec in col_specs:
        cls = "pub-matrix-col num" if (spec["key"] != "name" and not spec.get("is_text")) else "pub-matrix-col"
        header_cols += f'<div class="{cls}">{spec["header"]}</div>'
    header_html = f'<div class="pub-matrix-header" style="{grid_style}">{header_cols}</div>'

    # Recursive builder
    def build_tree_node_html(sub_df, current_level, current_filters):
        col = group_cols[current_level]
        
        # Apply filters to subset
        filtered_sub = sub_df
        for f_col, f_val in current_filters.items():
            filtered_sub = filtered_sub[filtered_sub[f_col] == f_val]
            
        if filtered_sub.empty:
            return ""
            
        is_leaf = (current_level == len(group_cols) - 1)
        
        # Unique values sorted
        if col in ["UF", "Cidade"]:
            # Handle NaN or Non-identified nicely
            unique_vals = sorted(
                filtered_sub[col].dropna().unique(),
                key=lambda x: (x == "Não identificado", str(x))
            )
        else:
            unique_vals = sorted(filtered_sub[col].dropna().unique())
            
        html = ""
        for val in unique_vals:
            val_df = filtered_sub[filtered_sub[col] == val]
            
            # Compute aggregations for current node
            agg_vals = {}
            for metric, rule in agg_rules.items():
                if rule == "sum":
                    agg_vals[metric] = val_df[metric].sum()
                elif rule == "nunique":
                    agg_vals[metric] = val_df[metric].nunique()
                    
            if derived_func:
                try:
                    derived_vals = derived_func(agg_vals, val_df)
                except TypeError:
                    derived_vals = derived_func(agg_vals)
            else:
                derived_vals = {}

            
            # Label & Toggle Icon
            indent = current_level * 14
            label = str(val)
            if col == "objective":
                from core.format import label_obj
                label = label_obj(val)
                
            label_html = f'<span style="padding-left:{indent}px; display:inline-flex; align-items:center;">'
            if not is_leaf:
                label_html += f'<span class="pub-matrix-toggle">▶</span><b>{label}</b>'
            else:
                # Leaf level (Campaign). Show an active campaign dot indicator.
                is_act = False
                if active_campaigns and val in active_campaigns:
                    is_act = True
                
                dot_color = "#00b359" if is_act else "rgba(255,255,255,0.3)"
                label_html += (
                    f'<span style="display:inline-block; width:6px; height:6px; border-radius:50%; '
                    f'background:{dot_color}; margin-right:8px; margin-left:6px; flex-shrink:0;"></span>'
                    f'<span title="{label}" style="overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">{label}</span>'
                )
            label_html += '</span>'
            
            # Build Row Columns
            cell_html = f'<div class="pub-matrix-col">{label_html}</div>'
            for spec in col_specs[1:]:
                key = spec["key"]
                val_num = derived_vals.get(key) if key in derived_vals else agg_vals.get(key, 0)
                if spec.get("is_text"):
                    formatted = str(val_num)
                else:
                    formatted = _br(val_num, spec.get("dec", 0), spec.get("pref", ""))
                    if spec.get("is_pct"):
                        formatted += "%"
                cls = "pub-matrix-col num" if not spec.get("is_text") else "pub-matrix-col"
                cell_html += f'<div class="{cls}">{formatted}</div>'

                
            row_class = "pub-matrix-row leaf" if is_leaf else f"pub-matrix-row parent level-{current_level}"
            
            if is_leaf:
                html += f'<div class="{row_class}" style="{grid_style}">{cell_html}</div>'
            else:
                new_filters = {**current_filters, col: val}
                child_html = build_tree_node_html(val_df, current_level + 1, new_filters)
                
                is_open = current_level < expand_level
                open_attr = " open" if is_open else ""
                
                html += (
                    f'<details class="pub-matrix-details"{open_attr}>'
                    f'<summary>'
                    f'<div class="{row_class}" style="{grid_style}">{cell_html}</div>'
                    f'</summary>'
                    f'<div class="pub-matrix-children">{child_html}</div>'
                    f'</details>'
                )
        return html

    rows_html = build_tree_node_html(df, 0, {})

    # Global Totals
    global_agg = {}
    for metric, rule in agg_rules.items():
        if rule == "sum":
            global_agg[metric] = df[metric].sum()
        elif rule == "nunique":
            global_agg[metric] = df[metric].nunique()
            
    if derived_func:
        try:
            global_derived = derived_func(global_agg, df)
        except TypeError:
            global_derived = derived_func(global_agg)
    else:
        global_derived = {}
    
    total_cells = '<div class="pub-matrix-col"><b>TOTAL GLOBAL</b></div>'
    for spec in col_specs[1:]:
        key = spec["key"]
        val_num = global_derived.get(key) if key in global_derived else global_agg.get(key, 0)
        if spec.get("is_text"):
            formatted = str(val_num)
        else:
            formatted = _br(val_num, spec.get("dec", 0), spec.get("pref", ""))
            if spec.get("is_pct"):
                formatted += "%"
        cls = "pub-matrix-col num" if not spec.get("is_text") else "pub-matrix-col"
        total_cells += f'<div class="{cls}">{formatted}</div>'

        
    total_html = f'<div class="pub-matrix-total" style="{grid_style}">{total_cells}</div>'

    _html(f'<div class="pub-matrix-wrap">{header_html}{rows_html}{total_html}</div>')

