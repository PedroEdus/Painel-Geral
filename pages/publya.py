import pandas as pd
import streamlit as st
from datetime import date, timedelta

from core.theme import aplicar_tema
from core.ui import cabecalho, exibir_logo, kpis, botao_download_csv
from core.format import (
    _br, 
    _font_color_para_fundo,
    VERDE, 
    LANCAMENTO_COLOR_MAP, 
    COLOR_MAP_MIDIA
)
from core.charts import (
    _html,
    _tema,
    _titulo_layout,
    grafico_donut
)
from sources.publya import carregar_publya

# Apply visual theme
aplicar_tema()

cabecalho("Campanhas Publya", "Performance de mídia programática")

# ── Carregar Dados ────────────────────────────────────────────────────────────
with st.spinner("Carregando dados da Publya..."):
    df = carregar_publya()

if df.empty:
    st.info("Sem dados da Publya cadastrados ou disponíveis no BigQuery.")
    st.stop()

# ── Filtros (Sidebar) ─────────────────────────────────────────────────────────
st.sidebar.header("Filtros")

# 1. Tipo de Mídia
tipos = ["Todos"] + sorted(df["Tipo_Midia"].dropna().unique().tolist())
tipo_sel = st.sidebar.selectbox("Tipo de mídia", tipos)

# 2. Campanhas
campanhas_opcoes = sorted(df["campaign_name"].dropna().unique().tolist())
campanhas_sel = st.sidebar.multiselect("Campanhas", campanhas_opcoes, placeholder="Todas")

st.sidebar.divider()

# 3. Filtros de Data
tem_datas = "data_inicio" in df.columns and "data_fim" in df.columns
if tem_datas and df["data_inicio"].notna().any():
    data_min_global = df["data_inicio"].dropna().min().date()
    data_max_global = df["data_fim"].dropna().max().date()
else:
    data_max_global = date.today()
    data_min_global = data_max_global - timedelta(days=90)

data_inicio_sel = st.sidebar.date_input(
    "Data início (a partir de)",
    value=max(date(2026, 1, 1), data_min_global),
    min_value=data_min_global,
    max_value=data_max_global,
    format="DD/MM/YYYY",
)
data_fim_sel = st.sidebar.date_input(
    "Data fim (até)",
    value=data_max_global,
    min_value=data_min_global,
    max_value=data_max_global,
    format="DD/MM/YYYY",
)

# ── Aplicar Filtros ───────────────────────────────────────────────────────────
df_filtrado = df.copy()

if tipo_sel != "Todos":
    df_filtrado = df_filtrado[df_filtrado["Tipo_Midia"] == tipo_sel]

if campanhas_sel:
    df_filtrado = df_filtrado[df_filtrado["campaign_name"].isin(campanhas_sel)]

if data_inicio_sel and "data_inicio" in df_filtrado.columns:
    df_filtrado = df_filtrado[
        df_filtrado["data_inicio"].isna() |
        (df_filtrado["data_inicio"].dt.date >= data_inicio_sel)
    ]

if data_fim_sel and "data_fim" in df_filtrado.columns:
    df_filtrado = df_filtrado[
        df_filtrado["data_fim"].isna() |
        (df_filtrado["data_fim"].dt.date <= data_fim_sel)
    ]

st.caption(f"{len(df_filtrado)} campanha(s) exibida(s)")

# ── KPIs ──────────────────────────────────────────────────────────────────────
imp_t  = df_filtrado["impressions"].sum()
clk_t  = df_filtrado["clicks"].sum()
bud_t  = df_filtrado["budget"].sum()
conv_t = df_filtrado["conversions"].sum()
ctr_t  = (clk_t / imp_t * 100) if imp_t else 0
cpc_t  = (bud_t / clk_t) if clk_t else 0

kpis({
    "Impressões":  _br(imp_t),
    "Cliques":     _br(clk_t),
    "CTR médio":   _br(ctr_t, 2) + "%",
    "Valor gasto": _br(bud_t, 2, "R$ "),
    "CPC médio":   _br(cpc_t, 2, "R$ "),
    "Conversões":  _br(conv_t),
})
st.divider()


# ════════════════════════════════════════════════════════════════════════════
# HELPERS DE COMPONENTES EXCLUSIVOS DA PUBLYA (BARRAS EMPILHADAS HTML)
# ════════════════════════════════════════════════════════════════════════════

POR_PAGINA = 20

def _segmentos_html(df_camp: pd.DataFrame, coluna: str, total_camp: float, max_val: float, fmt_func) -> str:
    html = ""
    for tipo, color in COLOR_MAP_MIDIA.items():
        rows = df_camp[df_camp["Tipo_Midia"] == tipo]
        if rows.empty:
            continue
        val = float(rows[coluna].iloc[0])
        if val <= 0:
            continue

        seg_w   = val / max_val * 100
        pct_int = val / total_camp * 100
        label   = f"{pct_int:.0f}%" if pct_int >= 8 else ""
        fc      = _font_color_para_fundo(color)
        tooltip = f"{tipo}: {pct_int:.0f}% ({fmt_func(val)})"

        html += (
            f'<div title="{tooltip}" style="width:{seg_w:.2f}%;height:100%;background:{color};flex-shrink:0;'
            f'display:inline-flex;align-items:center;justify-content:center;overflow:hidden;cursor:default;'
            f'font-family:Roboto Condensed,sans-serif;font-size:10px;font-weight:500;color:{fc}">'
            f'{label}</div>'
        )
    return html

def exibir_grafico_barras_paginado(df_plot: pd.DataFrame, coluna: str, titulo: str, fmt_func, key: str) -> None:
    if key not in st.session_state:
        st.session_state[key] = 0

    totais = df_plot.groupby("campaign_name")[coluna].sum().sort_values(ascending=False)
    campanhas_ord = totais.index.tolist()
    n_total  = len(campanhas_ord)
    n_pages  = max(1, -(-n_total // POR_PAGINA))
    page     = min(st.session_state[key], n_pages - 1)
    st.session_state[key] = page

    campanhas_pag = sorted(campanhas_ord[page * POR_PAGINA:(page + 1) * POR_PAGINA], key=lambda x: totais[x], reverse=True)
    _max = totais.max()
    max_val = 1 if pd.isna(_max) or _max == 0 else _max

    # Helper de legenda
    def _legenda_midia_html(df_leg):
        presentes = df_leg["Tipo_Midia"].dropna().unique()
        return "".join(
            f'<span class="pub-legend-item">'
            f'<span class="pub-legend-dot" style="background:{COLOR_MAP_MIDIA.get(t, "#888")}"></span>{t}</span>'
            for t in COLOR_MAP_MIDIA if t in presentes
        )

    rows_html = ""
    for camp in campanhas_pag:
        total_camp = totais[camp]
        df_camp    = df_plot[df_plot["campaign_name"] == camp]
        segs       = _segmentos_html(df_camp, coluna, total_camp, max_val, fmt_func)
        name_trunc = (camp[:38] + "…") if len(camp) > 38 else camp

        rows_html += (
            f'<div class="pub-bar-row">'
            f'<div class="pub-bar-name" title="{camp}">{name_trunc}</div>'
            f'<div class="pub-bar-track" style="display:flex;overflow:hidden;border-radius:3px">{segs}</div>'
            f'<div class="pub-bar-value">{fmt_func(total_camp)}</div>'
            f'</div>'
        )

    _html(f"""
        <div class="pub-card">
            <div class="pub-card-title">{titulo}</div>
            <div class="pub-bar-list">{rows_html}</div>
            <div class="pub-bar-legend">{_legenda_midia_html(df_plot)}</div>
        </div>
    """)

    if n_pages > 1:
        c1, c2, c3 = st.columns([1, 5, 1])
        with c1:
            if st.button("← Ant.", key=f"prev_{key}", disabled=page == 0):
                st.session_state[key] -= 1
                st.rerun()
        with c2:
            st.caption(f"Página {page + 1} de {n_pages}  ·  {n_total} campanhas")
        with c3:
            if st.button("Próx. →", key=f"next_{key}", disabled=page >= n_pages - 1):
                st.session_state[key] += 1
                st.rerun()

def _badge_html(tipo: str) -> str:
    color = COLOR_MAP_MIDIA.get(tipo, "#888888")
    return (
        f'<span class="pub-badge" style="background:{color}22;border:1px solid {color}55;color:{color}">'
        f'<span class="pub-badge-dot" style="background:{color}"></span>{tipo}</span>'
    )

def exibir_tabela_resumo_publya(df_tab):
    resumo = (
        df_tab.groupby("Tipo_Midia", as_index=False)
        .agg(
            Campanhas=("campaign_name", "count"),
            Impressões=("impressions", "sum"),
            Cliques=("clicks", "sum"),
            Valor_Gasto=("budget", "sum"),
            Conversões=("conversions", "sum"),
            Video_Starts=("videoStarts", "sum"),
            Video_Completions=("videoCompletions", "sum"),
            Audio_Starts=("audioStarts", "sum"),
            Audio_Completions=("audioCompletions", "sum"),
        )
    )
    total = resumo.select_dtypes("number").sum()
    total_row = pd.DataFrame([["TOTAL"] + total.tolist()], columns=resumo.columns)
    resumo = pd.concat([resumo, total_row], ignore_index=True)

    for col in resumo.columns[1:]:
        resumo[col] = pd.to_numeric(resumo[col], errors="coerce")

    resumo["CTR (%)"]  = (resumo["Cliques"] / resumo["Impressões"].replace(0, float("nan")) * 100).round(2)
    resumo["VCR (%)"]  = (resumo["Video_Completions"] / resumo["Video_Starts"].replace(0, float("nan")) * 100).round(2)
    resumo["ACR (%)"]  = (resumo["Audio_Completions"] / resumo["Audio_Starts"].replace(0, float("nan")) * 100).round(2)
    resumo["CPM (R$)"] = (resumo["Valor_Gasto"] / resumo["Impressões"].replace(0, float("nan")) * 1000).round(2)
    resumo["CPC (R$)"] = (resumo["Valor_Gasto"] / resumo["Cliques"].replace(0, float("nan"))).round(2)

    header = ("<tr><th>Tipo</th><th class='num'>Campanhas</th><th class='num'>Impressões</th>"
              "<th class='num'>Cliques</th><th class='num'>CTR (%)</th><th class='num'>Valor Gasto (R$)</th>"
              "<th class='num'>Conversões</th><th class='num'>VCR (%)</th><th class='num'>ACR (%)</th>"
              "<th class='num'>CPM (R$)</th><th class='num'>CPC (R$)</th></tr>")

    rows_html = ""
    for _, row in resumo.iterrows():
        is_total = str(row["Tipo_Midia"]) == "TOTAL"
        tipo_cell = "<b>TOTAL</b>" if is_total else _badge_html(str(row["Tipo_Midia"]))
        row_cls = "total" if is_total else ""

        def fmt(val, dec=0, pref=""):
            return _br(val, dec, pref) if pd.notna(val) else "—"

        rows_html += (
            f'<tr class="{row_cls}">'
            f'<td>{tipo_cell}</td>'
            f'<td class="num">{fmt(row["Campanhas"])}</td>'
            f'<td class="num">{fmt(row["Impressões"])}</td>'
            f'<td class="num">{fmt(row["Cliques"])}</td>'
            f'<td class="num">{fmt(row["CTR (%)"], 2)}</td>'
            f'<td class="num">{fmt(row["Valor_Gasto"], 2, "R$ ")}</td>'
            f'<td class="num">{fmt(row["Conversões"])}</td>'
            f'<td class="num">{fmt(row.get("VCR (%)"), 2)}</td>'
            f'<td class="num">{fmt(row.get("ACR (%)"), 2)}</td>'
            f'<td class="num">{fmt(row["CPM (R$)"], 2, "R$ ")}</td>'
            f'<td class="num">{fmt(row["CPC (R$)"], 2, "R$ ")}</td>'
            f'</tr>'
        )

    _html(f'<div class="pub-card"><div class="pub-table-wrap">'
          f'<table class="pub-table"><thead>{header}</thead><tbody>{rows_html}</tbody></table>'
          f'</div></div>')

def exibir_tabela_campanhas_publya(df_tab):
    df_exibir = df_tab.sort_values("impressions", ascending=False)
    avg_cpc = df_exibir["CPC (R$)"].replace(0, pd.NA).dropna().mean() if "CPC (R$)" in df_exibir.columns else None

    # Helper de bolinha colorida do semáforo
    def _dot(color: str) -> str:
        return f'<span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:{color};margin-right:5px"></span>'

    def _aproveitamento_html(row):
        tipo = str(row.get("Tipo_Midia", ""))
        mapa = {"Display": ("CTR (%)", "CTR"), "Vídeo": ("VCR (%)", "VCR"), "Áudio": ("ACR (%)", "ACR")}
        col, label = mapa.get(tipo, (None, None))
        if col and col in row.index and pd.notna(row[col]):
            val = float(row[col])
            # Semáforo de aproveitamento (verde >= 80, amarelo 50-79, vermelho < 50)
            cor = "#2a9d45" if val >= 80 else ("#f59e0b" if val >= 50 else "#ef4444")
            return (f'<span style="display:inline-flex;align-items:center">{_dot(cor)}'
                    f'<span style="font-family:Roboto Condensed,sans-serif;font-size:12px">{_br(val, 2)}%</span>'
                    f'<span style="font-size:10px;color:#8f8f96;margin-left:4px">{label}</span></span>')
        return "—"

    header = ("<tr><th>Campanha</th><th>Tipo</th><th class='num'>Impressões</th><th class='num'>Cliques</th>"
              "<th class='num'>Aproveitamento</th><th class='num'>Valor Gasto (R$)</th>"
              "<th class='num'>CPM (R$)</th><th class='num'>CPC (R$)</th><th class='num'>Conversões</th></tr>")

    rows_html = ""
    for _, row in df_exibir.iterrows():
        # CPC com semáforo
        cpc_html = "—"
        if "CPC (R$)" in row.index and pd.notna(row["CPC (R$)"]) and float(row["CPC (R$)"]) > 0:
            cpc_val = float(row["CPC (R$)"])
            # Semáforo de CPC (verde < 90% da média, amarelo 90-120%, vermelho > 120%)
            cpc_ratio = cpc_val / avg_cpc if avg_cpc else 1.0
            cor_c = "#2a9d45" if cpc_ratio <= 0.90 else ("#f59e0b" if cpc_ratio <= 1.20 else "#ef4444")
            cpc_html = (f'<span style="display:inline-flex;align-items:center">{_dot(cor_c)}'
                        f'<span style="font-family:Roboto Condensed,sans-serif;font-size:12px">{_br(cpc_val, 2, "R$ ")}</span></span>')

        rows_html += (
            f'<tr>'
            f'<td>{row["campaign_name"]}</td>'
            f'<td>{_badge_html(str(row.get("Tipo_Midia", "")))}</td>'
            f'<td class="num">{_br(row.get("impressions"))}</td>'
            f'<td class="num">{_br(row.get("clicks"))}</td>'
            f'<td class="num">{_aproveitamento_html(row)}</td>'
            f'<td class="num">{_br(row.get("budget"), 2, "R$ ")}</td>'
            f'<td class="num">{_br(row.get("CPM (R$)"), 2, "R$ ")}</td>'
            f'<td class="num">{cpc_html}</td>'
            f'<td class="num">{_br(row.get("conversions"))}</td>'
            f'</tr>'
        )

    _html(f'<div class="pub-card"><div class="pub-table-wrap">'
          f'<table class="pub-table"><thead>{header}</thead><tbody>{rows_html}</tbody></table>'
          f'</div></div>')


# ── Abas ──────────────────────────────────────────────────────────────────────
aba_imp, aba_clk, aba_val, aba_tab = st.tabs([
    "📢 Impressões", "🖱️ Cliques", "💰 Valores", "📋 Tabela"
])

with aba_imp:
    col1, col2 = st.columns([2, 1])
    with col1:
        exibir_grafico_barras_paginado(df_filtrado, "impressions", "Impressões por campanha", lambda v: _br(v), "pag_imp")
    with col2:
        grafico_donut(df_filtrado, "Tipo_Midia", "impressions", "Distribuição por tipo de mídia — Impressões", color_map=COLOR_MAP_MIDIA)

with aba_clk:
    col1, col2 = st.columns([2, 1])
    with col1:
        exibir_grafico_barras_paginado(df_filtrado, "clicks", "Cliques por campanha", lambda v: _br(v), "pag_clk")
    with col2:
        grafico_donut(df_filtrado, "Tipo_Midia", "clicks", "Distribuição por tipo de mídia — Cliques", color_map=COLOR_MAP_MIDIA)

with aba_val:
    col1, col2 = st.columns([2, 1])
    with col1:
        exibir_grafico_barras_paginado(df_filtrado, "budget", "Valor gasto por campanha (R$)", lambda v: _br(v, 2, "R$ "), "pag_bud")
    with col2:
        grafico_donut(df_filtrado, "Tipo_Midia", "budget", "Distribuição por tipo de mídia — Gasto", color_map=COLOR_MAP_MIDIA)

with aba_tab:
    st.subheader("Resumo por tipo de mídia")
    exibir_tumo = df_filtrado.copy()
    exibir_tabela_resumo_publya(exibir_tumo)

    st.divider()
    st.subheader("Detalhe por campanha")

    # Exportação CSV
    csv_df = df_filtrado.copy().rename(columns={
        "campaign_name": "Campanha",
        "Tipo_Midia":    "Tipo",
        "impressions":   "Impressões",
        "clicks":        "Cliques",
        "budget":        "Valor Gasto (R$)",
        "conversions":   "Conversões",
    })
    botao_download_csv(csv_df, f"publya_campanhas_{date.today():%Y%m%d}.csv", "📥 Baixar dados da Tabela (CSV)")
    
    exibir_tabela_campanhas_publya(df_filtrado)
