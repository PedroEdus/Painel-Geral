import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import date

from core.theme import aplicar_tema
from core.ui import cabecalho, exibir_logo, kpis as render_kpis, botao_download_csv
from core.format import _br, _font_color_para_fundo, _rgba, VERDE
from core.charts import _LAYOUT_BASE, _titulo_layout, _tema, _html, dataframe_card, tabela_matriz_html, trapezio_svg, grafico_donut, grafico_evolucao, PLOTLY_CONFIG
from sources.funil import carregar_leads

# Apply unified design system and styles
aplicar_tema()

cabecalho("Funil BTSA — CRM Leads", "CRM · jornada de leads")

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
    ("Origem de Contato", "OrigemContato"),
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
_VERDE_BASE   = "#2a9d45"
_VERDE_ESCURO = "#174f23"
_VERDE_MEDIO  = "#1a6229"
_VERDE_CLARO  = "#4ab861"
_VERDE_BRILHO = "#7dd190"
_BRANCO       = "#8f8f96"

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

def _fmt_h(v) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    return f"{float(v):.1f}".replace(".", ",") + " h"

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

    _t_all_kpi = df_in.loc[
        df_in["TempoCiclo_h"].notna() & (df_in["TempoCiclo_h"] > 0), "TempoCiclo_h"
    ] if "TempoCiclo_h" in df_in.columns else pd.Series(dtype=float)
    _t_ganhas_kpi = df_in.loc[
        df_in["Etapa_NF"].eq("Venda Ganha") & df_in["TempoCiclo_h"].notna() & (df_in["TempoCiclo_h"] > 0), "TempoCiclo_h"
    ] if "TempoCiclo_h" in df_in.columns else pd.Series(dtype=float)
    _tm_geral = round(float(_t_all_kpi.mean()), 1) if not _t_all_kpi.empty else None
    _tm_fech  = round(float(_t_ganhas_kpi.mean()), 1) if not _t_ganhas_kpi.empty else None

    cols = st.columns(7)
    cols[0].metric("Total de Leads", _br(total))
    cols[1].metric("Aguardando", _br(aguardando))
    cols[2].metric("Em Atendimento", _br(atendimento))
    cols[3].metric("Visita Agendada", _br(visita))
    cols[4].metric("Negociação", _br(negociacao))
    cols[5].metric("Venda Ganha", _br(ganhas), delta=p_ganhas, delta_color="normal")
    cols[6].metric("Venda Perdida", _br(perdidas), delta=p_perdidas, delta_color="inverse")

exibir_kpis(df_filtrado)
st.divider()

# ── Abas ──────────────────────────────────────────────────────────────────────
aba1, aba_perdas, aba2, aba3, aba4, aba5 = st.tabs([
    "Funil",
    "Perdas & Desempenho",
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
                <div style="position:relative;margin-bottom:3px;height:83px;">
                  {trapezio_svg(ml, ml_n, cor, h=83)}
                  <div style="position:absolute;inset:0;display:flex;align-items:center;
                    justify-content:center;flex-direction:column;gap:3px;pointer-events:none;">
                    <span class="fn-num" style="font-size:22px;font-weight:800;color:#fff;
                      font-family:'Roboto Condensed',sans-serif;">{_br(count)}</span>
                    <span style="font-size:9px;font-weight:600;color:rgba(255,255,255,0.82);
                      text-transform:uppercase;letter-spacing:1.2px;">{etapa}</span>
                  </div>
                  <div class="fn-pct" style="position:absolute;right:4px;top:50%;transform:translateY(-50%);
                    color:#6b6b74;font-size:12px;font-weight:700;
                    font-family:'Roboto Condensed',sans-serif;">{pct:.1f}%</div>
                </div>"""

                # Taxa de passagem para a próxima etapa
                if i < len(etapas_ativas) - 1:
                    prox_count = etapas_ativas[i + 1][2]
                    conv = prox_count / count * 100 if count else 0
                    stages_html += f"""
                <div style="display:flex;justify-content:center;margin:-1px 0 2px;">
                  <span style="font-size:10px;font-weight:700;color:rgba(0,204,102,0.9);
                    font-family:'Roboto Condensed',sans-serif;background:rgba(0,204,102,0.08);
                    border:1px solid rgba(0,204,102,0.22);border-radius:10px;padding:1px 9px;"
                    title="Passagem {etapa} → {etapas_ativas[i + 1][0]}">▼ {conv:.1f}%</span>
                </div>"""

            perdidas_html = ""
            if perdidas:
                pct_p = perdidas / total_base * 100 if total_base else 0
                perdidas_html = f"""
                <div class="fn-loss" style="position:absolute;bottom:22px;left:22px;
                  display:flex;flex-direction:column;align-items:flex-start;gap:2px;
                  padding:10px 14px;border-radius:6px;
                  background:rgba(231,76,60,0.10);border:1px solid rgba(231,76,60,0.22);">
                  <span style="font-size:9px;text-transform:uppercase;letter-spacing:1.2px;
                    color:#8f8f96;">Venda Perdida</span>
                  <span style="font-size:22px;font-weight:800;color:#ef4444;
                    font-family:'Roboto Condensed',sans-serif;line-height:1;">{_br(perdidas)}</span>
                  <span style="font-size:11px;color:rgba(231,76,60,0.65);
                    font-family:'Roboto Condensed',sans-serif;">{pct_p:.1f}%</span>
                </div>"""

            _html(f"""
            <div class="pub-card" style="padding:22px 22px 18px;position:relative;">
              <div style="font-size:10px;letter-spacing:2px;text-transform:uppercase;
                color:#8f8f96;margin-bottom:4px;">Base Total</div>
              <div style="font-size:34px;font-weight:800;color:#232329;
                font-family:'Roboto Condensed',sans-serif;margin-bottom:20px;">{_br(total_base)}</div>
              <div class="fn-stages" style="padding-right:52px;">
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
                grafico_donut(resumo_onoff, "On_Off", "Leads", "Distribuição On / Off", altura=340)

        # Métricas de tempo e acompanhamento abaixo do donut
        _acomp = int(df_filtrado["Etapa_NF"].eq("Acompanhamento").sum()) if "Etapa_NF" in df_filtrado.columns else 0
        _pct_acomp = f"{_acomp / len(df_filtrado):.1%}" if len(df_filtrado) else "—"
        _t_all = df_filtrado.loc[
            df_filtrado["TempoCiclo_h"].notna() & (df_filtrado["TempoCiclo_h"] > 0), "TempoCiclo_h"
        ] if "TempoCiclo_h" in df_filtrado.columns else pd.Series(dtype=float)
        _t_ganhas = df_filtrado.loc[
            df_filtrado["Etapa_NF"].eq("Venda Ganha") & df_filtrado["TempoCiclo_h"].notna() & (df_filtrado["TempoCiclo_h"] > 0), "TempoCiclo_h"
        ] if "TempoCiclo_h" in df_filtrado.columns else pd.Series(dtype=float)
        _tm = round(float(_t_all.mean()), 1) if not _t_all.empty else None
        _tf = round(float(_t_ganhas.mean()), 1) if not _t_ganhas.empty else None

        _html(f"""
        <div class="pub-card" style="padding:18px 20px 20px;">
          <div style="font-size:14px;font-weight:600;color:#6b6b74;
            font-family:'Segoe UI',sans-serif;margin-bottom:14px;">Tempos &amp; Acompanhamento</div>

          <div style="margin-bottom:4px;">
            <div style="font-size:28px;font-weight:800;color:#2a9d45;
              font-family:'Roboto Condensed',sans-serif;line-height:1.1;">{_br(_acomp)}</div>
            <div style="font-size:12px;color:#232329;margin-top:3px;
              font-family:'Segoe UI',sans-serif;">Leads em Acompanhamento — {_pct_acomp} do total.</div>
          </div>

          <div style="border-top:1px solid #ececed;margin:12px 0;"></div>

          <div style="margin-bottom:4px;">
            <div style="font-size:28px;font-weight:800;color:#8f8f96;
              font-family:'Roboto Condensed',sans-serif;line-height:1.1;">{_fmt_h(_tm)}</div>
            <div style="font-size:12px;color:#232329;margin-top:3px;
              font-family:'Segoe UI',sans-serif;">Tempo médio de todos os leads com ciclo registrado.</div>
          </div>

          <div style="border-top:1px solid #ececed;margin:12px 0;"></div>

          <div>
            <div style="font-size:28px;font-weight:800;color:#8f8f96;
              font-family:'Roboto Condensed',sans-serif;line-height:1.1;">{_fmt_h(_tf)}</div>
            <div style="font-size:12px;color:#232329;margin-top:3px;
              font-family:'Segoe UI',sans-serif;">Ciclo médio de fechamento (Venda Ganha).</div>
          </div>
        </div>
        """)

    # Evolução temporal de leads (Diário e Mensal) — card com slicer integrado
    if "DataCadastro" in df_filtrado.columns:
        _df_ev = df_filtrado[["DataCadastro"]].copy()
        _df_ev["Leads"] = 1
        grafico_evolucao(
            _df_ev, "DataCadastro", "Leads", "Evolução de Leads CRM",
            cor=_VERDE_BASE, key="funil_temporal",
        )

# ── Aba "Perdas & Desempenho" ─────────────────────────────────────────────────
with aba_perdas:
    # ── Justificativas de Perda + Leads Parados (lado a lado) ─────────────────
    if "Etapa_NF" in df_filtrado.columns:
        st.write("")
        col_perda, col_aging = st.columns(2)

        # Esquerda: motivos de perda
        with col_perda:
            df_perdidos = df_filtrado[df_filtrado["Etapa_NF"] == "Venda Perdida"]
            if not df_perdidos.empty and "Status" in df_filtrado.columns:
                resumo_perda = df_perdidos["Status"].fillna("Não Informado").astype(str).str.strip()
                resumo_perda = resumo_perda.loc[resumo_perda != ""].value_counts().reset_index()
                resumo_perda.columns = ["Motivo", "Leads"]
                resumo_perda = resumo_perda.head(10)
            else:
                resumo_perda = pd.DataFrame(columns=["Motivo", "Leads"])

            if not resumo_perda.empty:
                _maxp = float(resumo_perda["Leads"].max()) or 1.0
                fig_perda = px.bar(
                    resumo_perda,
                    x="Leads", y="Motivo",
                    orientation="h",
                    color_discrete_sequence=["#ef4444"],
                    template=_tema(),
                )
                fig_perda.update_layout(**{**_LAYOUT_BASE, **dict(
                    height=380, bargap=0.42,
                    margin=dict(l=20, r=20, t=10, b=20),
                    xaxis=dict(title=None, gridcolor="#eef1f5", griddash="dot",
                               zeroline=False, showline=False, ticks="",
                               range=[0, _maxp * 1.18]),
                    yaxis=dict(title=None, categoryorder="total ascending", showgrid=False,
                               ticks="", tickfont=dict(size=12, color="#6b6b74")),
                    title=dict(text=""),
                )})
                fig_perda.update_traces(
                    marker=dict(cornerradius=6, line_width=0),
                    textposition="outside",
                    texttemplate="%{value:,.0f}",
                    textfont=dict(size=12, color="#232329", family="Roboto Condensed, sans-serif"),
                    hovertemplate="<b>%{y}</b><br>Leads: <b>%{x:,.0f}</b><extra></extra>",
                    cliponaxis=False,
                )
                fig_perda.update_traces(marker_cornerradius=8, selector=dict(type="bar"))
                with st.container(key="dfc_motivos_perda"):
                    _html('<div class="pub-card-title">Principais Motivos de Perda (Top 10)</div>')
                    st.plotly_chart(fig_perda, use_container_width=True, config=PLOTLY_CONFIG)
            else:
                st.info("Sem motivos de perda no período.")

        # Direita: leads parados sem movimentação (aging)
        with col_aging:
            _AGING_TOOLTIP = (
                "Considera apenas leads ativos no funil (Aguardando Atendimento, "
                "Em Atendimento, Visita Agendada, Negociação). "
                "Não inclui Venda Ganha nem Venda Perdida, pois esses já estão "
                "encerrados e não fazem mais parte do funil em andamento. "
                "Dias parados = hoje − última alteração (DataAlteracao)."
            )
            _ATIVOS = ["Aguardando Atendimento", "Em Atendimento", "Visita Agendada", "Negociação"]
            if {"DataAlteracao", "Etapa_NF"}.issubset(df_filtrado.columns):
                df_ag = df_filtrado[df_filtrado["Etapa_NF"].isin(_ATIVOS)].copy()
                df_ag["DataAlteracao"] = pd.to_datetime(df_ag["DataAlteracao"], errors="coerce")
                _agora = pd.Timestamp.now()
                df_ag["DiasParado"] = (_agora - df_ag["DataAlteracao"]).dt.total_seconds() / 86400
                df_ag = df_ag[df_ag["DiasParado"].notna() & (df_ag["DiasParado"] >= 0)]

                if not df_ag.empty:
                    _bins   = [-0.01, 3, 7, 14, 30, 60, 90, 180, float("inf")]
                    _labels = ["0–3 dias", "4–7 dias", "8–14 dias", "15–30 dias",
                               "30–60 dias", "60–90 dias", "90–180 dias", "180+ dias"]
                    df_ag["Faixa"] = pd.cut(df_ag["DiasParado"], bins=_bins, labels=_labels)

                    resumo_faixa = (
                        df_ag["Faixa"].value_counts().reindex(_labels).fillna(0).reset_index()
                    )
                    resumo_faixa.columns = ["Faixa", "Leads"]
                    # Gradiente recente→antigo: verde brand → âmbar → vermelho.
                    CORES_AGING = {
                        "0–3 dias":    "#2a9d45",
                        "4–7 dias":    "#4ab861",
                        "8–14 dias":   "#7dd190",
                        "15–30 dias":  "#f59e0b",
                        "30–60 dias":  "#e67e22",
                        "60–90 dias":  "#d35400",
                        "90–180 dias": "#ef4444",
                        "180+ dias":   "#b91c1c",
                    }
                    _maxa = float(resumo_faixa["Leads"].max()) or 1.0
                    fig_ag = px.bar(
                        resumo_faixa, x="Faixa", y="Leads",
                        color="Faixa", color_discrete_map=CORES_AGING, template=_tema(),
                    )
                    fig_ag.update_traces(
                        marker=dict(cornerradius=6, line_width=0),
                        texttemplate="%{y:,.0f}", textposition="outside", cliponaxis=False,
                        textfont=dict(size=12, color="#232329", family="Roboto Condensed, sans-serif"),
                        hovertemplate="<b>%{x}</b><br>Leads: <b>%{y:,.0f}</b><extra></extra>",
                    )
                    fig_ag.update_layout(**{**_LAYOUT_BASE, **dict(
                        height=380, showlegend=False, bargap=0.45,
                        title=dict(text=""),
                        margin=dict(l=20, r=20, t=10, b=20),
                        xaxis=dict(title=None, showgrid=False, ticks="",
                                   tickfont=dict(size=12, color="#6b6b74")),
                        yaxis=dict(title=None, gridcolor="#eef1f5", griddash="dot",
                                   zeroline=False, showline=False, ticks="",
                                   range=[0, _maxa * 1.2]),
                    )})
                    fig_ag.update_traces(marker_cornerradius=8, selector=dict(type="bar"))
                    _ttl_aging = (
                        '<div class="pub-card-title" '
                        'style="display:flex;align-items:center;gap:6px;">'
                        'Distribuição por Tempo sem Movimentação'
                        f'<span class="help-dot" data-tip="{_AGING_TOOLTIP}">?</span></div>'
                    )
                    with st.container(key="dfc_aging_dist"):
                        _html(_ttl_aging)
                        st.plotly_chart(fig_ag, use_container_width=True, config=PLOTLY_CONFIG)
                else:
                    st.info("Sem dados de movimentação (DataAlteracao) para aging.")

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
                "Tempo Médio (h)":   round(float(df_g.loc[df_g["TempoCiclo_h"].notna() & (df_g["TempoCiclo_h"] > 0), "TempoCiclo_h"].mean()), 1)
                                        if "TempoCiclo_h" in df_g.columns and df_g["TempoCiclo_h"].notna().any() else None,
                "Ciclo Fecham. (h)": round(float(df_g.loc[df_g["Etapa_NF"].eq("Venda Ganha") & df_g["TempoCiclo_h"].notna() & (df_g["TempoCiclo_h"] > 0), "TempoCiclo_h"].mean()), 1)
                                        if "TempoCiclo_h" in df_g.columns and df_g.loc[df_g["Etapa_NF"].eq("Venda Ganha"), "TempoCiclo_h"].notna().any() else None,
            }

        grupos_dados: dict = {}
        for _g in ["SDR", "Outros Funis"]:
            _df_g = df_comp[df_comp["_Grupo"] == _g]
            if not _df_g.empty:
                grupos_dados[_g] = _calc_metricas_grupo(_df_g)

        if grupos_dados:
            _df_met = pd.DataFrame([{"Grupo": g, **m} for g, m in grupos_dados.items()])

            # Resumo tabular — cores reforçam a legenda dos gráficos:
            # SDR verde, Outros Funis azul.
            _display_cols = [
                "Grupo", "Total", "Venda Ganha", "Venda Perdida",
                "Conv. Total (%)", "Taxa Perda (%)",
                "Lead→Atend (%)", "Atend→Visita (%)", "Visita→Negoc (%)", "Negoc→Ganho (%)",
                "Tempo Médio (h)", "Ciclo Fecham. (h)",
            ]
            _COR_GRUPO_TXT = {"SDR": _VERDE_BASE, "Outros Funis": "#5b8dee"}

            def _estilo_linha_grupo(row):
                cor = _COR_GRUPO_TXT.get(row.name, "#232329")
                return [f"color: {cor}; font-weight: 600"] * len(row)

            def _fmt_br(v):
                # BR: ponto milhar, vírgula decimal; inteiros sem casas,
                # demais com 1 casa (sem zeros sobrando).
                if v is None or (isinstance(v, float) and pd.isna(v)):
                    return "—"
                if float(v).is_integer():
                    return f"{int(v):,}".replace(",", ".")
                return f"{v:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")

            _tabela_grupo = (
                _df_met[_display_cols].set_index("Grupo")
                .style.apply(_estilo_linha_grupo, axis=1)
                .format(_fmt_br)
            )
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
                    textfont=dict(size=11, color="#232329", family="Roboto Condensed, sans-serif"),
                )
                _fig_vol.update_layout(**{**_LAYOUT_BASE, **dict(
                    height=320,
                    title=_titulo_layout("Volume por Etapa do Funil"),
                    xaxis=dict(title=None),
                    yaxis=dict(title=None, gridcolor="#eef1f5", griddash="dot"),
                    legend=dict(
                        orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                        font=dict(family="Roboto Condensed, sans-serif", size=11, color="#6b6b74"),
                    ),
                )})
                _fig_vol.update_traces(marker_cornerradius=8, selector=dict(type="bar"))
                st.plotly_chart(_fig_vol, use_container_width=True, config=PLOTLY_CONFIG)

            with _col_tx:
                _etapas_dur = ["Aguardando Atendimento", "Em Atendimento", "Visita Agendada", "Negociação", "Venda Ganha"]
                _dur_rows = []
                for _gn, _dg in [(_g, df_comp[df_comp["_Grupo"] == _g]) for _g in grupos_dados]:
                    if "TempoCiclo_h" not in _dg.columns:
                        continue
                    for _et in _etapas_dur:
                        _sub = _dg.loc[
                            _dg["Etapa_NF"].eq(_et) & _dg["TempoCiclo_h"].notna() & (_dg["TempoCiclo_h"] > 0),
                            "TempoCiclo_h"
                        ]
                        if not _sub.empty:
                            _dur_rows.append({
                                "Grupo": _gn,
                                "Etapa": _et,
                                "Horas": round(float(_sub.mean()), 1),
                            })
                if _dur_rows:
                    _df_dur = pd.DataFrame(_dur_rows)
                    _fig_dur = px.bar(
                        _df_dur, x="Etapa", y="Horas", color="Grupo",
                        barmode="group",
                        color_discrete_map=CORES_GRUPO,
                        template=_tema(),
                    )
                    _fig_dur.update_traces(
                        texttemplate="%{y:.1f}h", textposition="outside", cliponaxis=False,
                        textfont=dict(size=11, color="#232329", family="Roboto Condensed, sans-serif"),
                    )
                    _fig_dur.update_layout(**{**_LAYOUT_BASE, **dict(
                        height=320,
                        title=_titulo_layout("Duração Média por Etapa (horas)"),
                        xaxis=dict(title=None),
                        yaxis=dict(title="Horas", gridcolor="#eef1f5", griddash="dot"),
                        legend=dict(
                            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                            font=dict(family="Roboto Condensed, sans-serif", size=11, color="#6b6b74"),
                        ),
                    )})
                    _fig_dur.update_traces(marker_cornerradius=8, selector=dict(type="bar"))
                    st.plotly_chart(_fig_dur, use_container_width=True, config=PLOTLY_CONFIG)

            st.write("")
            dataframe_card(_tabela_grupo, "Resumo por grupo", key="resumo_grupo")

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
            dataframe_card(
                pd.crosstab(df_mat["UtmSource"], df_mat["Etapa_NF"]),
                "Matriz origem × etapa",
                key="matriz_origem_etapa",
                height=460,
            )

# ── Aba 3: Cidades e Cadastro ─────────────────────────────────────────────────
with aba3:
    # Listas maiores lado a lado: Top cidades + Estado de Origem
    col_cid, col_est = st.columns(2)

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

    with col_est:
        if "Telefone" in df_filtrado.columns:
            df_est = df_filtrado.copy()
            df_est["Estado_Origem"] = df_est["Telefone"].apply(_obter_estado_ddd)
            resumo_est = _agrupar(df_est, "Estado_Origem")
            _barras_card(resumo_est, "Leads", "Estado_Origem", "Estado de Origem (via DDD do Lead)", "bar_estados")

    st.write("")
    # Listas menores lado a lado: Forma de cadastro + Meio de Contato
    col_cad, col_orig_cont = st.columns(2)

    with col_cad:
        resumo_cad = _agrupar(df_filtrado, "FormaCadastro")
        if not resumo_cad.empty:
            grafico_donut(resumo_cad, "FormaCadastro", "Leads", "Leads por forma de cadastro", altura=390)
        else:
            st.info("Sem dados de forma de cadastro.")

        if "Finalidade" in df_filtrado.columns:
            df_fin = df_filtrado.copy()
            df_fin["Finalidade"] = df_fin["Finalidade"].fillna("").astype(str).str.strip()
            df_fin = df_fin[~df_fin["Finalidade"].isin(["", "Não Informado", "não informado"])]
            resumo_fin = _agrupar(df_fin, "Finalidade")
            if not resumo_fin.empty:
                _barras_card(
                    resumo_fin, "Leads", "Finalidade",
                    "Finalidade de compra &nbsp;<span style='font-size:11px;font-weight:400;color:#8f8f96'>⚠️ \"Não Informado\" excluído</span>",
                    "bar_finalidade",
                )
                _html('<div style="height:60px"></div>')

    with col_orig_cont:
        if "OrigemContato" in df_filtrado.columns:
            df_origcont = df_filtrado.copy()
            df_origcont["OrigemContato"] = df_origcont["OrigemContato"].fillna("Não Informado").astype(str).str.strip()
            df_origcont = df_origcont[df_origcont["OrigemContato"] != ""]
            resumo_origcont = _agrupar(df_origcont, "OrigemContato")
            _barras_card(resumo_origcont, "Leads", "OrigemContato", "Meio de Contato (Origem Contato)", "bar_origem_contato")

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
                if "TempoCiclo_h" in df_resp.columns:
                    agg["Tempo Médio (h)"] = ("TempoCiclo_h", "mean")

                resumo_resp = (
                    df_resp.groupby("Responsavel")
                    .agg(**agg)
                    .reset_index()
                    .sort_values("Leads", ascending=False)
                    .head(20)
                )
                if "Tempo Médio (h)" in resumo_resp.columns:
                    resumo_resp["Tempo Médio (h)"] = resumo_resp["Tempo Médio (h)"].round(1)

                _barras_card(resumo_resp, "Leads", "Responsavel", "Leads por responsável", "bar_responsavel")
            else:
                st.info("Sem dados de responsável para o período.")

    # ── Tabelas lado a lado: Resumo por responsável | Leads parados >7d ────────
    st.write("")
    _TBL_H = 460
    t_resp, t_aging = st.columns(2)

    with t_resp:
        if {"Responsavel", "Codigo"}.issubset(df_filtrado.columns):
            df_resp2 = df_filtrado.dropna(subset=["Responsavel"])
            df_resp2 = df_resp2[df_resp2["Responsavel"].astype(str).str.strip() != ""]
            if not df_resp2.empty:
                agg2: dict = {"Leads": ("Codigo", "count")}
                if "TempoCiclo_h" in df_resp2.columns:
                    agg2["Tempo Médio (h)"] = ("TempoCiclo_h", "mean")
                resumo_resp2 = (
                    df_resp2.groupby("Responsavel")
                    .agg(**agg2)
                    .reset_index()
                    .sort_values("Leads", ascending=False)
                    .head(20)
                )
                if "Tempo Médio (h)" in resumo_resp2.columns:
                    resumo_resp2["Tempo Médio (h)"] = resumo_resp2["Tempo Médio (h)"].round(1)
                dataframe_card(resumo_resp2, "Resumo por responsável",
                               key="resumo_resp", height=_TBL_H, hide_index=True)
            else:
                st.info("Sem dados de responsável para o período.")

    with t_aging:
        _AGING_HELP = (
            "Leads ativos no funil (Aguardando, Em Atendimento, Visita Agendada, "
            "Negociação) sem alteração há mais de 7 dias, agrupados por responsável. "
            "Não inclui Venda Ganha nem Venda Perdida."
        )
        _ATIVOS_OP = ["Aguardando Atendimento", "Em Atendimento", "Visita Agendada", "Negociação"]
        if {"DataAlteracao", "Etapa_NF", "Responsavel", "Codigo"}.issubset(df_filtrado.columns):
            df_ag_op = df_filtrado[df_filtrado["Etapa_NF"].isin(_ATIVOS_OP)].copy()
            df_ag_op["DataAlteracao"] = pd.to_datetime(df_ag_op["DataAlteracao"], errors="coerce")
            df_ag_op["DiasParado"] = (pd.Timestamp.now() - df_ag_op["DataAlteracao"]).dt.total_seconds() / 86400
            df_crit = df_ag_op[df_ag_op["DiasParado"].notna() & (df_ag_op["DiasParado"] > 7)]
            if not df_crit.empty:
                resumo_crit = (
                    df_crit.assign(
                        Responsavel=df_crit["Responsavel"].fillna("Sem Responsável")
                        .astype(str).str.strip().replace({"": "Sem Responsável"})
                    )
                    .groupby("Responsavel")
                    .agg(Parados=("Codigo", "count"), Dias_Medio=("DiasParado", "mean"))
                    .reset_index()
                    .sort_values("Parados", ascending=False)
                    .head(20)
                )
                resumo_crit["Dias_Medio"] = resumo_crit["Dias_Medio"].round(1)
                resumo_crit.columns = ["Responsável", "Parados >7d", "Dias Médio"]
                dataframe_card(resumo_crit, "Leads ativos parados há mais de 7 dias",
                               key="aging_parados", height=_TBL_H, help=_AGING_HELP,
                               hide_index=True)
            else:
                st.info("Nenhum lead ativo parado há mais de 7 dias.")

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
    df_mat["TempoCiclo_h"] = pd.to_numeric(df_mat["TempoCiclo_h"], errors="coerce").fillna(0.0)
    df_mat["Leads_Com_Tempo"] = (df_filtrado["TempoCiclo_h"].notna() & (df_filtrado["TempoCiclo_h"] > 0)).astype(int)
    
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
        {"header": "Tempo Médio (h)", "key": "TempoCiclo_h", "is_text": True},
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
        "TempoCiclo_h": "sum",
        "Leads_Com_Tempo": "sum",
    }
    
    def derived_funil(agg, subset_df):
        tempo_sum = agg.get("TempoCiclo_h", 0)
        leads_com_tempo = agg.get("Leads_Com_Tempo", 0)
        avg = (tempo_sum / leads_com_tempo) if leads_com_tempo > 0 else 0
        tempo_str = f"{avg:.1f}".replace(".", ",") + " h" if avg > 0 else "—"
        return {
            "TempoCiclo_h": tempo_str,
        }
            
    # Cria o dataframe de download contendo todas as colunas
    colunas_dl = [
        "Codigo", "Nome", "Produto", "Cidade", "DataCadastro",
        "FormaCadastro", "UtmCampaign", "UtmMedium", "UtmSource",
        "Etapa", "Status", "Etapa_NF", "On_Off", "Responsavel", "TempoCiclo_h",
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


