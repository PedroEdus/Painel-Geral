import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import date

from core.theme import aplicar_tema
from core.ui import exibir_logo, kpis as render_kpis, botao_download_csv
from core.format import _br, _font_color_para_fundo, _rgba, VERDE
from core.charts import _LAYOUT_BASE, _titulo_layout, _tema, _html, tabela_matriz_html
from sources.funil import carregar_leads

# Apply unified design system and styles
aplicar_tema()

st.title("Funil Buriti — CRM Leads")

# ── Carregar Dados ────────────────────────────────────────────────────────────
with st.spinner("Carregando dados do CRM..."):
    df = carregar_leads()

if df.empty:
    st.info("Sem dados de leads cadastrados ou disponíveis no BigQuery.")
    st.stop()

# ── Filtros (Sidebar) ─────────────────────────────────────────────────────────
st.sidebar.header("Filtros")

# 1. Período de cadastro
if "DataCadastro" in df.columns:
    data_min = df["DataCadastro"].min()
    data_max = df["DataCadastro"].max()
    if pd.notna(data_min) and pd.notna(data_max):
        default_inicio = max(date(2026, 1, 1), data_min.date())
        periodo = st.sidebar.date_input(
            "Período de cadastro",
            value=(default_inicio, data_max.date()),
            min_value=data_min.date(),
            max_value=data_max.date(),
        )
        if isinstance(periodo, list) or isinstance(periodo, tuple):
            if len(periodo) == 2:
                df = df[
                    (df["DataCadastro"] >= pd.to_datetime(periodo[0])) &
                    (df["DataCadastro"] <= pd.to_datetime(periodo[1]))
                ]
            elif len(periodo) == 1:
                df = df[df["DataCadastro"] == pd.to_datetime(periodo[0])]

# List of filters we want to apply
FILTROS = [
    ("Funil",             "Funil"),
    ("Etapa NF",          "Etapa_NF"),
    ("On / Off",          "On_Off"),
    ("Produto",           "Produto"),
    ("Cidade",            "Cidade"),
    ("Forma de cadastro", "FormaCadastro"),
    ("Campanha",          "UtmCampaign"),
    ("Origem",            "UtmSource"),
    ("Responsável",       "Responsavel"),
]

df_filtrado = df.copy()
for label, coluna in FILTROS:
    if coluna not in df_filtrado.columns:
        continue
    serie = df_filtrado[coluna].dropna().astype(str).str.strip()
    serie = serie[serie != ""]
    opcoes = sorted(serie.unique().tolist())
    if opcoes:
        sel = st.sidebar.multiselect(label, opcoes, placeholder="Todas")
        if sel:
            df_filtrado = df_filtrado[df_filtrado[coluna].astype(str).str.strip().isin(sel)]

# ── Validar Estado Pós-Filtros ────────────────────────────────────────────────
if df_filtrado.empty:
    st.warning("Nenhum lead encontrado para os filtros selecionados.")
    st.stop()

st.caption(f"{len(df_filtrado):,} lead(s) exibido(s)")

# ── Paleta e Mapeamentos CRM ──────────────────────────────────────────────────
_VERDE_BASE   = "#008140"
_VERDE_ESCURO = "#004d26"
_VERDE_MEDIO  = "#006633"
_VERDE_CLARO  = "#00a851"
_VERDE_BRILHO = "#00cc66"
_BRANCO       = "#ffffff"

COLOR_MAP = {
    "Aguardando Atendimento": _VERDE_ESCURO,
    "Em Atendimento":         _VERDE_MEDIO,
    "Visita Agendada":        _VERDE_BASE,
    "Negociação":             _VERDE_CLARO,
    "Venda Ganha":            _VERDE_BRILHO,
    "Venda Perdida":          _BRANCO,
    "Acompanhamento":         "#335544",
    "Outros":                 "#444444",
    "On":                     _VERDE_BASE,
    "Off":                    _BRANCO,
}

ORDEM_FUNIL = [
    "Venda Ganha",
    "Negociação",
    "Visita Agendada",
    "Em Atendimento",
    "Aguardando Atendimento",
]

POR_PAGINA = 20

def _badge_html(etapa: str) -> str:
    color = COLOR_MAP.get(etapa, "#888888")
    bg    = color + "22"
    bord  = color + "55"
    return (
        f'<span class="pub-badge" style="background:{bg};border:1px solid {bord};color:{color}">'
        f'<span class="pub-badge-dot" style="background:{color}"></span>{etapa}</span>'
    )

def _obter_estado_ddd(tel) -> str:
    if not tel or pd.isna(tel):
        return "Não Informado"
    digits = "".join(filter(str.isdigit, str(tel)))
    if len(digits) >= 12 and digits.startswith("55"):
        ddd = digits[2:4]
    elif len(digits) in (10, 11):
        ddd = digits[0:2]
    elif len(digits) >= 2:
        ddd = digits[0:2]
    else:
        return "Não Informado"
    
    DDD_TO_STATE = {
        '11': 'SP', '12': 'SP', '13': 'SP', '14': 'SP', '15': 'SP', '16': 'SP', '17': 'SP', '18': 'SP', '19': 'SP',
        '21': 'RJ', '22': 'RJ', '24': 'RJ',
        '27': 'ES', '28': 'ES',
        '31': 'MG', '32': 'MG', '33': 'MG', '34': 'MG', '35': 'MG', '37': 'MG', '38': 'MG',
        '41': 'PR', '42': 'PR', '43': 'PR', '44': 'PR', '45': 'PR', '46': 'PR',
        '47': 'SC', '48': 'SC', '49': 'SC',
        '51': 'RS', '53': 'RS', '54': 'RS', '55': 'RS',
        '61': 'DF',
        '62': 'GO', '64': 'GO',
        '63': 'TO',
        '65': 'MT', '66': 'MT',
        '67': 'MS',
        '68': 'AC',
        '69': 'RO',
        '71': 'BA', '73': 'BA', '74': 'BA', '75': 'BA', '77': 'BA',
        '79': 'SE',
        '81': 'PE', '82': 'AL', '83': 'PB', '84': 'RN', '85': 'CE', '86': 'PI', '87': 'PE', '88': 'CE', '89': 'PI',
        '91': 'PA', '92': 'AM', '93': 'PA', '94': 'PA', '95': 'RR', '96': 'AP', '97': 'AM', '98': 'MA', '99': 'MA'
    }
    return DDD_TO_STATE.get(ddd, "Não Informado")

def _resolver_origem(df_in: pd.DataFrame) -> pd.Series:
    source = df_in["UtmSource"].astype(str).str.strip().copy()
    nulo   = source.isin(["", "None", "nan", "NaN"])

    forma = df_in.get("FormaCadastro", pd.Series([""] * len(df_in), index=df_in.index))
    forma = forma.fillna("").astype(str).str.lower()

    source.loc[nulo & forma.str.contains("meta",   na=False)] = "Meta"
    source.loc[nulo & forma.str.contains("google", na=False)] = "Google"
    source.loc[nulo & ~forma.str.contains("meta|google", na=False)] = "Não Informado"

    return source

def _agrupar(df_in: pd.DataFrame, coluna: str, top: int | None = None) -> pd.DataFrame:
    resumo = (
        df_in[coluna]
        .dropna()
        .loc[lambda s: s.astype(str).str.strip() != ""]
        .value_counts()
        .reset_index()
    )
    resumo.columns = [coluna, "Leads"]
    if top:
        resumo = resumo.head(top)
    return resumo

def _barras_card(
    df_plot: pd.DataFrame,
    x: str,
    y: str,
    titulo: str,
    key: str,
    color_map: dict | None = None,
    fmt_func=None,
) -> None:
    if df_plot.empty:
        st.info(f"Sem dados para '{titulo}'.")
        return

    if fmt_func is None:
        fmt_func = lambda v: _br(v)

    df_plot = df_plot.sort_values(x, ascending=False).reset_index(drop=True)

    if key not in st.session_state:
        st.session_state[key] = 0

    n_total = len(df_plot)
    n_pages = max(1, -(-n_total // POR_PAGINA))
    page    = min(st.session_state[key], n_pages - 1)
    st.session_state[key] = page

    df_pag  = df_plot.iloc[page * POR_PAGINA:(page + 1) * POR_PAGINA]
    max_val = df_plot[x].max() or 1

    rows_html = ""
    for _, row in df_pag.iterrows():
        label  = str(row[y])
        val    = float(row[x])
        bar_w  = val / max_val * 100
        color  = (color_map or {}).get(label, _VERDE_BASE)
        lbl_tr = (label[:38] + "…") if len(label) > 38 else label
        rows_html += (
            f'<div class="pub-bar-row">'
            f'<div class="pub-bar-name" title="{label}">{lbl_tr}</div>'
            f'<div class="pub-bar-track" style="display:flex;overflow:hidden;border-radius:3px;">'
            f'<div style="width:{bar_w:.2f}%;height:100%;background:{color};border-radius:3px;"></div>'
            f'</div>'
            f'<div class="pub-bar-value">{fmt_func(val)}</div>'
            f'</div>'
        )

    _html(f"""
        <div class="pub-card">
            <div class="pub-card-title">{titulo}</div>
            <div class="pub-bar-list">{rows_html}</div>
        </div>
    """)

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

# ── KPIs ──────────────────────────────────────────────────────────────────────
def exibir_kpis(df_in: pd.DataFrame) -> None:
    total = len(df_in)
    def _conta(etapa: str) -> int:
        if "Etapa_NF" not in df_in.columns:
            return 0
        return int(df_in["Etapa_NF"].eq(etapa).sum())

    aguardando  = _conta("Aguardando Atendimento")
    atendimento = _conta("Em Atendimento")
    visita      = _conta("Visita Agendada")
    negociacao  = _conta("Negociação")
    ganhas      = _conta("Venda Ganha")
    perdidas    = _conta("Venda Perdida")
    acompanhamento = _conta("Acompanhamento")
    
    p_ganhas = f"{ganhas / total:.1%} do total" if total else "0% do total"
    p_perdidas = f"{perdidas / total:.1%} do total" if total else "0% do total"
    p_acomp = f"{acompanhamento / total:.1%} do total" if total else "0% do total"

    cols = st.columns(8)
    cols[0].metric("Total de Leads", _br(total))
    cols[1].metric("Aguardando", _br(aguardando))
    cols[2].metric("Em Atendimento", _br(atendimento))
    cols[3].metric("Visita Agendada", _br(visita))
    cols[4].metric("Negociação", _br(negociacao))
    cols[5].metric("Venda Ganha", _br(ganhas), delta=p_ganhas, delta_color="normal")
    cols[6].metric("Venda Perdida", _br(perdidas), delta=p_perdidas, delta_color="inverse")
    cols[7].metric(
        "Acompanhamento (remarketing)",
        _br(acompanhamento),
        delta=p_acomp,
        delta_color="off",
        help="Leads identificados como oportunidades futuras — fora do funil ativo."
    )

exibir_kpis(df_filtrado)
st.divider()

# ── Abas ──────────────────────────────────────────────────────────────────────
aba1, aba2, aba3, aba4, aba5 = st.tabs([
    "Funil",
    "Origem e Campanhas",
    "Cidades e Cadastro",
    "Operação",
    "Base Analítica",
])

# ── Aba 1: Funil ──────────────────────────────────────────────────────────────
with aba1:
    col_a, col_b = st.columns([1.4, 0.9])
    
    with col_a:
        # Funil de Vendas — HTML trapezoid customizado
        FUNIL_ETAPAS = [
            ("Aguardando Atendimento", _VERDE_ESCURO),
            ("Em Atendimento",         _VERDE_MEDIO),
            ("Visita Agendada",        _VERDE_BASE),
            ("Negociação",             _VERDE_CLARO),
            ("Venda Ganha",            _VERDE_BRILHO),
        ]
        contagem     = df_filtrado["Etapa_NF"].value_counts().to_dict()
        etapas_ativas = [(e, c, contagem.get(e, 0)) for e, c in FUNIL_ETAPAS if contagem.get(e, 0) > 0]

        if etapas_ativas:
            total_base = len(df_filtrado)
            perdidas   = contagem.get("Venda Perdida", 0)
            n          = len(etapas_ativas)
            W_TOP, W_BOT = 90, 32
            step_w = (W_TOP - W_BOT) / max(n - 1, 1)

            stages_html = ""
            for i, (etapa, cor, count) in enumerate(etapas_ativas):
                w     = W_TOP - i * step_w
                w_n   = W_TOP - (i + 1) * step_w
                ml    = (100 - w) / 2
                ml_n  = (100 - w_n) / 2
                pct   = count / total_base * 100 if total_base else 0
                stages_html += f"""
                <div style="position:relative;margin-bottom:3px;">
                  <div style="
                    background:{cor};
                    clip-path:polygon({ml:.2f}% 0%,{100-ml:.2f}% 0%,{100-ml_n:.2f}% 100%,{ml_n:.2f}% 100%);
                    height:68px;display:flex;align-items:center;justify-content:center;
                    flex-direction:column;gap:3px;">
                    <span style="font-size:22px;font-weight:800;color:#fff;
                      font-family:'JetBrains Mono',monospace;">{_br(count)}</span>
                    <span style="font-size:9px;font-weight:600;color:rgba(255,255,255,0.75);
                      text-transform:uppercase;letter-spacing:1.2px;">{etapa}</span>
                  </div>
                  <div style="position:absolute;right:4px;top:50%;transform:translateY(-50%);
                    color:rgba(255,255,255,0.6);font-size:12px;font-weight:700;
                    font-family:'JetBrains Mono',monospace;">{pct:.1f}%</div>
                </div>"""

            perdidas_html = ""
            if perdidas:
                pct_p = perdidas / total_base * 100 if total_base else 0
                perdidas_html = f"""
                <div style="display:flex;align-items:center;gap:14px;margin-top:14px;
                  padding:10px 14px;border-radius:6px;
                  background:rgba(231,76,60,0.10);border:1px solid rgba(231,76,60,0.22);">
                  <span style="font-size:10px;text-transform:uppercase;letter-spacing:1.2px;
                    color:rgba(255,255,255,0.45);">Venda Perdida</span>
                  <span style="font-size:20px;font-weight:800;color:#e74c3c;
                    font-family:'JetBrains Mono',monospace;">{_br(perdidas)}</span>
                  <span style="font-size:12px;color:rgba(231,76,60,0.65);
                    font-family:'JetBrains Mono',monospace;">{pct_p:.1f}%</span>
                </div>"""

            _html(f"""
            <div class="pub-card" style="padding:22px 22px 18px;">
              <div style="font-size:10px;letter-spacing:2px;text-transform:uppercase;
                color:rgba(255,255,255,0.4);margin-bottom:4px;">Base Total</div>
              <div style="font-size:34px;font-weight:800;color:#fff;
                font-family:'JetBrains Mono',monospace;margin-bottom:20px;">{_br(total_base)}</div>
              <div style="padding-right:52px;">
                {stages_html}
              </div>
              {perdidas_html}
            </div>
            """)
        else:
            st.info("Sem dados de funil para o período selecionado.")

    with col_b:
        # Distribuição On/Off Donut Plotly (rosca)
        if "On_Off" in df_filtrado.columns:
            resumo_onoff = _agrupar(df_filtrado, "On_Off")
            if not resumo_onoff.empty:
                total_oo = resumo_onoff["Leads"].sum()
                resumo_onoff["_pct"]  = (resumo_onoff["Leads"] / total_oo * 100).round(1) if total_oo else 0
                resumo_onoff["_text"] = resumo_onoff.apply(
                    lambda r: f"{_br(r['Leads'])}<br>{r['_pct']:.1f}%" if r["_pct"] >= 5 else "",
                    axis=1,
                )
                font_colors = [
                    _font_color_para_fundo(COLOR_MAP.get(cat, "#888888"))
                    for cat in resumo_onoff["On_Off"]
                ]

                fig_oo = px.pie(
                    resumo_onoff,
                    names="On_Off", values="Leads",
                    hole=0.58, title="Distribuição On / Off",
                    color="On_Off", color_discrete_map=COLOR_MAP,
                )
                fig_oo.update_traces(
                    text=resumo_onoff["_text"].tolist(),
                    textposition="inside",
                    textinfo="text",
                    insidetextfont=dict(family="JetBrains Mono, monospace", size=11, color=font_colors),
                    hovertemplate="%{label}: %{value:,.0f} (%{percent})",
                    domain=dict(x=[0, 0.62], y=[0, 1]),
                )
                fig_oo.add_annotation(
                    text=f"<b>{_br(total_oo)}</b><br><span style='font-size:11px;opacity:0.6'>total</span>",
                    x=0.31, y=0.5,
                    xanchor="center", yanchor="middle",
                    showarrow=False,
                    font=dict(family="JetBrains Mono, monospace", size=14, color="#ffffff"),
                    align="center",
                )
                fig_oo.update_layout(
                    template=_tema(), height=440,
                    margin=dict(l=10, r=10, t=50, b=10),
                    legend=dict(
                        orientation="v", x=0.65, y=0.5,
                        xanchor="left", yanchor="middle",
                        font=dict(family="Manrope, sans-serif", size=12, color="rgba(255,255,255,0.8)"),
                    ),
                    title=_titulo_layout("Distribuição On / Off"),
                )
                st.plotly_chart(fig_oo, use_container_width=True)

    # Evolução temporal de leads (Diário e Mensal)
    if "DataCadastro" in df_filtrado.columns:
        st.subheader("Evolução Temporal de Leads")
        gran = st.radio(
            "Visualização Série Temporal", 
            ["Diário", "Mensal"], 
            horizontal=True, 
            key="funil_temporal_gran", 
            label_visibility="collapsed"
        )
        
        d = df_filtrado.copy()
        d["DataCadastro"] = pd.to_datetime(d["DataCadastro"])
        
        if gran == "Mensal":
            d["periodo"] = d["DataCadastro"].dt.to_period("M").dt.to_timestamp()
            agg = d.groupby("periodo").size().reset_index(name="Leads")
            agg = agg.sort_values("periodo")
            agg["periodo_str"] = agg["periodo"].dt.strftime("%b/%Y")
            
            y_max = float(agg["Leads"].max()) if not agg.empty else 1
            fig_ev = px.bar(
                agg, x="periodo_str", y="Leads",
                color_discrete_sequence=[_VERDE_BASE],
            )
            fig_ev.update_traces(
                text=[_br(v) for v in agg["Leads"]],
                textposition="outside",
                textfont=dict(color="#ffffff", size=12, family="Manrope, sans-serif"),
                marker_line_width=0,
                cliponaxis=False,
            )
            fig_ev.update_layout(**{**_LAYOUT_BASE, **dict(
                height=380,
                xaxis=dict(title=None, type="category"),
                yaxis=dict(title=None, gridcolor="#2a2a2a", range=[0, y_max * 1.22]),
                title=_titulo_layout("Evolução Mensal de Leads CRM"),
            )})
        else:
            d["periodo"] = d["DataCadastro"].dt.normalize()
            agg = d.groupby("periodo").size().reset_index(name="Leads")
            agg = agg.sort_values("periodo")
            
            fig_ev = px.area(
                agg, x="periodo", y="Leads",
                color_discrete_sequence=[_VERDE_BASE],
            )
            fig_ev.update_traces(
                line=dict(width=2, color=_VERDE_BASE),
                fillcolor=_rgba(_VERDE_BASE, 0.13)
            )
            fig_ev.update_layout(**{**_LAYOUT_BASE, **dict(
                height=380,
                yaxis=dict(gridcolor="#2a2a2a"),
                title=_titulo_layout("Evolução Diária de Leads CRM"),
            )})
            
        st.plotly_chart(fig_ev, use_container_width=True)

    # Motivos de Perda de Vendas (Lost Lead Analysis)
    if "Etapa_NF" in df_filtrado.columns and "Status" in df_filtrado.columns:
        df_perdidos = df_filtrado[df_filtrado["Etapa_NF"] == "Venda Perdida"]
        if not df_perdidos.empty:
            st.write("")
            st.subheader("Justificativas de Perda de Vendas")
            
            resumo_perda = df_perdidos["Status"].fillna("Não Informado").astype(str).str.strip()
            resumo_perda = resumo_perda.loc[resumo_perda != ""].value_counts().reset_index()
            resumo_perda.columns = ["Motivo", "Leads"]
            resumo_perda = resumo_perda.head(10)
            
            if not resumo_perda.empty:
                fig_perda = px.bar(
                    resumo_perda,
                    x="Leads", y="Motivo",
                    orientation="h",
                    color_discrete_sequence=["#e74c3c"],
                    template=_tema(),
                )
                fig_perda.update_layout(**{**_LAYOUT_BASE, **dict(
                    height=360,
                    xaxis=dict(title=None, gridcolor="#2a2a2a"),
                    yaxis=dict(title=None, categoryorder="total ascending"),
                    title=_titulo_layout("Principais Motivos de Perda (Top 10)"),
                )})
                fig_perda.update_traces(
                    textposition="outside",
                    texttemplate="%{value:,.0f}",
                    textfont=dict(size=11, color="#ffffff", family="Manrope, sans-serif"),
                    cliponaxis=False,
                )
                st.plotly_chart(fig_perda, use_container_width=True)

    # ── Performance Comparativa por Funil ────────────────────────────────────
    if "Funil" in df_filtrado.columns and "Etapa_NF" in df_filtrado.columns:
        st.write("")
        st.subheader("Performance Comparativa de Funil")

        df_comp = df_filtrado.copy()
        df_comp["_Grupo"] = (
            df_comp["Funil"]
            .fillna("")
            .astype(str)
            .str.upper()
            .apply(lambda f: "SDR" if "ATENDIMENTO" in f else "Outros Funis")
        )

        CORES_GRUPO = {"SDR": _VERDE_BASE, "Outros Funis": "#5b8dee"}

        def _calc_metricas_grupo(df_g: pd.DataFrame) -> dict:
            total    = len(df_g)
            ganhas   = int(df_g["Etapa_NF"].eq("Venda Ganha").sum())
            perdidas = int(df_g["Etapa_NF"].eq("Venda Perdida").sum())
            negoc    = int(df_g["Etapa_NF"].eq("Negociação").sum())
            visita   = int(df_g["Etapa_NF"].eq("Visita Agendada").sum())
            atend    = int(df_g["Etapa_NF"].eq("Em Atendimento").sum())
            aguard   = int(df_g["Etapa_NF"].eq("Aguardando Atendimento").sum())
            acomp    = int(df_g["Etapa_NF"].eq("Acompanhamento").sum())
            pipeline = atend + visita + negoc + ganhas
            visita_plus = visita + negoc + ganhas
            negoc_plus  = negoc + ganhas
            return {
                "Total":            total,
                "Aguardando":       aguard,
                "Em Atendimento":   atend,
                "Visita Agendada":  visita,
                "Negociação":       negoc,
                "Venda Ganha":      ganhas,
                "Venda Perdida":    perdidas,
                "Acompanhamento":   acomp,
                "Conv. Total (%)":  round(ganhas   / total        * 100, 1) if total        else 0.0,
                "Taxa Perda (%)":   round(perdidas / total        * 100, 1) if total        else 0.0,
                "Lead→Atend (%)":   round(pipeline / total        * 100, 1) if total        else 0.0,
                "Atend→Visita (%)": round(visita_plus / pipeline  * 100, 1) if pipeline     else 0.0,
                "Visita→Negoc (%)": round(negoc_plus / visita_plus* 100, 1) if visita_plus  else 0.0,
                "Negoc→Ganho (%)":  round(ganhas   / negoc_plus   * 100, 1) if negoc_plus   else 0.0,
            }

        grupos_dados: dict = {}
        for _g in ["SDR", "Outros Funis"]:
            _df_g = df_comp[df_comp["_Grupo"] == _g]
            if not _df_g.empty:
                grupos_dados[_g] = _calc_metricas_grupo(_df_g)

        if grupos_dados:
            # KPI cards — side by side per group
            g_cols = st.columns(len(grupos_dados))
            for _ci, (_grupo, _met) in enumerate(grupos_dados.items()):
                with g_cols[_ci]:
                    _label = "SDR — Funil de Atendimento" if _grupo == "SDR" else "Outros Funis (agrupados)"
                    st.markdown(f"**{_label}**")
                    _ka, _kb, _kc = st.columns(3)
                    _ka.metric("Total Leads",  _br(_met["Total"]),
                              help="Total de leads que entraram neste funil no período selecionado.")
                    _kb.metric("Vendas Ganhas", _br(_met["Venda Ganha"]),
                              help="Leads que chegaram à etapa Venda Ganha.")
                    _kc.metric("Conv. Total",  f"{_met['Conv. Total (%)']:.1f}%",
                              help="Taxa de conversão total: Venda Ganha ÷ Total de Leads.")
                    _kd, _ke, _kf = st.columns(3)
                    _kd.metric("Taxa Perda",   f"{_met['Taxa Perda (%)']:.1f}%",
                              help="% de leads marcados como Venda Perdida sobre o total.")
                    _ke.metric("Lead→Atend",   f"{_met['Lead→Atend (%)']:.1f}%",
                              help="% de leads que avançaram para atendimento ativo (saíram de Aguardando Atendimento).")
                    _kf.metric("Negoc→Ganho",  f"{_met['Negoc→Ganho (%)']:.1f}%",
                              help="% de leads em Negociação que fecharam como Venda Ganha.")

            st.write("")

            _df_met = pd.DataFrame([{"Grupo": g, **m} for g, m in grupos_dados.items()])

            _col_vol, _col_tx = st.columns(2)

            with _col_vol:
                _etapas_vol = ["Em Atendimento", "Visita Agendada", "Negociação", "Venda Ganha"]
                _df_vol = _df_met.melt(
                    id_vars=["Grupo"], value_vars=_etapas_vol,
                    var_name="Etapa", value_name="Leads"
                )
                _fig_vol = px.bar(
                    _df_vol, x="Etapa", y="Leads", color="Grupo",
                    barmode="group",
                    color_discrete_map=CORES_GRUPO,
                    template=_tema(),
                )
                _fig_vol.update_traces(
                    texttemplate="%{y:,.0f}", textposition="outside", cliponaxis=False,
                    textfont=dict(size=11, color="#ffffff", family="Manrope, sans-serif"),
                )
                _fig_vol.update_layout(**{**_LAYOUT_BASE, **dict(
                    height=320,
                    title=_titulo_layout("Volume por Etapa do Funil"),
                    xaxis=dict(title=None),
                    yaxis=dict(title=None, gridcolor="#2a2a2a"),
                    legend=dict(
                        orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                        font=dict(family="Manrope, sans-serif", size=11, color="rgba(255,255,255,0.8)"),
                    ),
                )})
                st.plotly_chart(_fig_vol, use_container_width=True)

            with _col_tx:
                _taxa_vars = ["Lead→Atend (%)", "Atend→Visita (%)", "Visita→Negoc (%)", "Negoc→Ganho (%)"]
                _df_tx = _df_met.melt(
                    id_vars=["Grupo"], value_vars=_taxa_vars,
                    var_name="Etapa", value_name="Taxa (%)"
                )
                _fig_tx = px.bar(
                    _df_tx, x="Etapa", y="Taxa (%)", color="Grupo",
                    barmode="group",
                    color_discrete_map=CORES_GRUPO,
                    template=_tema(),
                )
                _fig_tx.update_traces(
                    texttemplate="%{y:.1f}%", textposition="outside", cliponaxis=False,
                    textfont=dict(size=11, color="#ffffff", family="Manrope, sans-serif"),
                )
                _fig_tx.update_layout(**{**_LAYOUT_BASE, **dict(
                    height=320,
                    title=_titulo_layout("Taxa de Conversão por Etapa (%)"),
                    xaxis=dict(title=None),
                    yaxis=dict(title=None, gridcolor="#2a2a2a"),
                    legend=dict(
                        orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                        font=dict(family="Manrope, sans-serif", size=11, color="rgba(255,255,255,0.8)"),
                    ),
                )})
                st.plotly_chart(_fig_tx, use_container_width=True)

            # Resumo tabular
            st.write("")
            _display_cols = [
                "Grupo", "Total", "Venda Ganha", "Venda Perdida",
                "Conv. Total (%)", "Taxa Perda (%)",
                "Lead→Atend (%)", "Atend→Visita (%)", "Visita→Negoc (%)", "Negoc→Ganho (%)",
            ]
            st.dataframe(
                _df_met[_display_cols].set_index("Grupo"),
                use_container_width=True,
            )

# ── Aba 2: Origem e Campanhas ─────────────────────────────────────────────────
with aba2:
    col_orig, col_camp = st.columns(2)
    
    with col_orig:
        df_orig = df_filtrado.copy()
        df_orig["UtmSource"] = _resolver_origem(df_orig)
        resumo_orig = _agrupar(df_orig, "UtmSource", top=15)
        _barras_card(resumo_orig, "Leads", "UtmSource", "Top origens de leads (Canais)", "bar_origem")

    with col_camp:
        resumo_camp = _agrupar(df_filtrado, "UtmCampaign", top=15)
        _barras_card(resumo_camp, "Leads", "UtmCampaign", "Top campanhas", "bar_campanha")

    if {"UtmSource", "Etapa_NF"}.issubset(df_filtrado.columns):
        df_mat = df_filtrado.copy()
        df_mat["UtmSource"] = _resolver_origem(df_mat)
        df_mat = df_mat.dropna(subset=["Etapa_NF"])
        if not df_mat.empty:
            st.subheader("Matriz origem × etapa")
            st.dataframe(
                pd.crosstab(df_mat["UtmSource"], df_mat["Etapa_NF"]),
                use_container_width=True,
            )

# ── Aba 3: Cidades e Cadastro ─────────────────────────────────────────────────
with aba3:
    col_cid, col_cad = st.columns(2)
    
    with col_cid:
        df_cid = df_filtrado.copy()
        df_cid["Cidade"] = df_cid["Cidade"].fillna("Não Informado").astype(str).str.strip()
        df_cid = df_cid[df_cid["Cidade"] != ""]
        resumo_cid = (
            df_cid.groupby("Cidade")
            .size()
            .reset_index(name="Leads")
            .sort_values("Leads", ascending=False)
            .head(20)
        )
        _barras_card(resumo_cid, "Leads", "Cidade", "Top cidades", "bar_cidades")

    with col_cad:
        resumo_cad = _agrupar(df_filtrado, "FormaCadastro")
        _barras_card(resumo_cad, "Leads", "FormaCadastro", "Leads por forma de cadastro", "bar_forma")

    st.write("")
    col_est, col_orig_cont = st.columns(2)
    
    with col_est:
        if "Telefone" in df_filtrado.columns:
            df_est = df_filtrado.copy()
            df_est["Estado_Origem"] = df_est["Telefone"].apply(_obter_estado_ddd)
            resumo_est = _agrupar(df_est, "Estado_Origem")
            _barras_card(resumo_est, "Leads", "Estado_Origem", "Estado de Origem (via DDD do Lead)", "bar_estados")
            
    with col_orig_cont:
        if "OrigemContato" in df_filtrado.columns:
            df_origcont = df_filtrado.copy()
            df_origcont["OrigemContato"] = df_origcont["OrigemContato"].fillna("Não Informado").astype(str).str.strip()
            df_origcont = df_origcont[df_origcont["OrigemContato"] != ""]
            resumo_origcont = _agrupar(df_origcont, "OrigemContato")
            _barras_card(resumo_origcont, "Leads", "OrigemContato", "Meio de Contato (Origem Contato)", "bar_origem_contato")

    st.write("")
    col_mat1, col_mat2 = st.columns(2)
    
    with col_mat1:
        if {"Cidade", "Etapa_NF"}.issubset(df_filtrado.columns):
            df_v = df_filtrado.dropna(subset=["Cidade", "Etapa_NF"])
            if not df_v.empty:
                m = pd.crosstab(df_v["Cidade"], df_v["Etapa_NF"])
                m["Total"] = m.sum(axis=1)
                st.subheader("Matriz cidade × etapa")
                st.dataframe(m.sort_values("Total", ascending=False).head(30), use_container_width=True)

    with col_mat2:
        if {"FormaCadastro", "Etapa_NF"}.issubset(df_filtrado.columns):
            df_v = df_filtrado.dropna(subset=["FormaCadastro", "Etapa_NF"])
            if not df_v.empty:
                m = pd.crosstab(df_v["FormaCadastro"], df_v["Etapa_NF"])
                m["Total"] = m.sum(axis=1)
                st.subheader("Matriz forma de cadastro × etapa")
                st.dataframe(m.sort_values("Total", ascending=False), use_container_width=True)

# ── Aba 4: Operação ───────────────────────────────────────────────────────────
with aba4:
    col_prod, col_resp = st.columns(2)
    
    with col_prod:
        if {"Produto", "Cidade"}.issubset(df_filtrado.columns):
            df_prod = df_filtrado.copy()
            df_prod["Produto"] = df_prod["Produto"].fillna("Não Informado").astype(str).str.strip()
            df_prod["Cidade"]  = df_prod["Cidade"].fillna("Não Informado").astype(str).str.strip()
            df_prod = df_prod[(df_prod["Produto"] != "") & (df_prod["Cidade"] != "")]
            resumo_prod = (
                df_prod.groupby(["Produto", "Cidade"])
                .size()
                .reset_index(name="Leads")
                .sort_values("Leads", ascending=False)
                .head(20)
            )
            resumo_prod["Produto — Cidade"] = resumo_prod["Produto"] + "  ·  " + resumo_prod["Cidade"]
            _barras_card(resumo_prod, "Leads", "Produto — Cidade", "Leads por produto e cidade", "bar_produto")

    with col_resp:
        if {"Responsavel", "Codigo"}.issubset(df_filtrado.columns):
            df_resp = df_filtrado.dropna(subset=["Responsavel"])
            df_resp = df_resp[df_resp["Responsavel"].astype(str).str.strip() != ""]
            
            if not df_resp.empty:
                agg: dict = {"Leads": ("Codigo", "count")}
                if "TempoTotal" in df_resp.columns:
                    agg["Tempo Médio (dias)"] = ("TempoTotal", "mean")

                resumo_resp = (
                    df_resp.groupby("Responsavel")
                    .agg(**agg)
                    .reset_index()
                    .sort_values("Leads", ascending=False)
                    .head(20)
                )
                if "Tempo Médio (dias)" in resumo_resp.columns:
                    resumo_resp["Tempo Médio (dias)"] = resumo_resp["Tempo Médio (dias)"].round(1)

                _barras_card(resumo_resp, "Leads", "Responsavel", "Leads por responsável", "bar_responsavel")

                if "Tempo Médio (dias)" in resumo_resp.columns:
                    st.subheader("Resumo por responsável")
                    st.dataframe(resumo_resp, hide_index=True, use_container_width=True)
            else:
                st.info("Sem dados de responsável para o período.")

# ── Aba 5: Base Analítica ─────────────────────────────────────────────────────
with aba5:
    st.subheader("Matriz de Leads (Cidade ➔ Produto ➔ Responsável)")
    
    # Prepara dados para a matriz com 3 níveis na hierarquia
    df_mat = df_filtrado.copy()
    df_mat["Cidade"] = df_mat["Cidade"].fillna("Não Informado").astype(str).str.strip().replace({"": "Não Informado"})
    df_mat["Produto"] = df_mat["Produto"].fillna("Não Informado").astype(str).str.strip().replace({"": "Não Informado"})
    df_mat["Responsavel"] = df_mat["Responsavel"].fillna("Sem Responsável").astype(str).str.strip().replace({"": "Sem Responsável"})
    
    # Colunas com a contagem de leads por etapa do funil
    df_mat["Aguardando"] = df_mat["Etapa_NF"].eq("Aguardando Atendimento").astype(int)
    df_mat["Em_Atendimento"] = df_mat["Etapa_NF"].eq("Em Atendimento").astype(int)
    df_mat["Visita_Agendada"] = df_mat["Etapa_NF"].eq("Visita Agendada").astype(int)
    df_mat["Negociacao"] = df_mat["Etapa_NF"].eq("Negociação").astype(int)
    df_mat["Venda_Ganha"] = df_mat["Etapa_NF"].eq("Venda Ganha").astype(int)
    df_mat["Venda_Perdida"] = df_mat["Etapa_NF"].eq("Venda Perdida").astype(int)
    df_mat["Acompanhamento"] = df_mat["Etapa_NF"].eq("Acompanhamento").astype(int)
    
    df_mat["Leads"] = 1
    df_mat["TempoTotal"] = pd.to_numeric(df_mat["TempoTotal"], errors="coerce").fillna(0.0)
    df_mat["Leads_Com_Tempo"] = (df_filtrado["TempoTotal"].notna() & (df_filtrado["TempoTotal"] > 0)).astype(int)
    
    col_specs_funil = [
        {"header": "Hierarquia (Cidade ➔ Produto ➔ Responsável)", "key": "name"},
        {"header": "Leads", "key": "Leads", "dec": 0},
        {"header": "Aguardando", "key": "Aguardando", "dec": 0},
        {"header": "Em Atendimento", "key": "Em_Atendimento", "dec": 0},
        {"header": "Visita Agendada", "key": "Visita_Agendada", "dec": 0},
        {"header": "Negociação", "key": "Negociacao", "dec": 0},
        {"header": "Venda Ganha", "key": "Venda_Ganha", "dec": 0},
        {"header": "Venda Perdida", "key": "Venda_Perdida", "dec": 0},
        {"header": "Acompanhamento", "key": "Acompanhamento", "dec": 0},
        {"header": "Tempo Médio (dias)", "key": "TempoTotal", "is_text": True},
    ]
    
    agg_rules_funil = {
        "Leads": "sum",
        "Aguardando": "sum",
        "Em_Atendimento": "sum",
        "Visita_Agendada": "sum",
        "Negociacao": "sum",
        "Venda_Ganha": "sum",
        "Venda_Perdida": "sum",
        "Acompanhamento": "sum",
        "TempoTotal": "sum",
        "Leads_Com_Tempo": "sum",
    }
    
    def derived_funil(agg, subset_df):
        tempo_sum = agg.get("TempoTotal", 0)
        leads_com_tempo = agg.get("Leads_Com_Tempo", 0)
        avg = tempo_sum / leads_com_tempo if leads_com_tempo > 0 else 0
        tempo_str = f"{avg:.1f} dias" if avg > 0 else "—"
        return {
            "TempoTotal": tempo_str,
        }
            
    # Cria o dataframe de download contendo todas as colunas
    colunas_dl = [
        "Codigo", "Nome", "Produto", "Cidade", "DataCadastro",
        "FormaCadastro", "UtmCampaign", "UtmMedium", "UtmSource",
        "Etapa", "Status", "Etapa_NF", "On_Off", "Responsavel", "TempoTotal",
    ]
    df_download = df_filtrado[[c for c in colunas_dl if c in df_filtrado.columns]].copy()
        
    tabela_matriz_html(
        df=df_mat,
        group_cols=["Cidade", "Produto", "Responsavel"],
        col_specs=col_specs_funil,
        agg_rules=agg_rules_funil,
        derived_func=derived_funil,
        grid_template="minmax(320px, 3fr) 0.7fr 0.9fr 1.1fr 1.1fr 0.9fr 0.9fr 0.9fr 1.1fr 1.1fr",
        active_campaigns=None,
        key="funil_matrix_hierarquia",
        df_download=df_download,
        download_filename="leads_crm_detalhe.csv",
        download_label="📥 Baixar CSV"
    )


