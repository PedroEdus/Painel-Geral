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
    # Get sorted list of options
    opcoes = sorted(df_filtrado[coluna].dropna().unique().tolist())
    if opcoes:
        sel = st.sidebar.multiselect(label, opcoes, placeholder="Todas")
        if sel:
            df_filtrado = df_filtrado[df_filtrado[coluna].isin(sel)]

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

    render_kpis({
        "Total de Leads":  _br(total),
        "Aguardando":      _br(aguardando),
        "Em Atendimento":  _br(atendimento),
        "Visita Agendada": _br(visita),
        "Negociação":      _br(negociacao),
        "Venda Ganha":     _br(ganhas),
    })

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
        # Funil de Vendas Plotly
        contagem = df_filtrado["Etapa_NF"].value_counts().to_dict()
        funil_data = [
            {"Etapa_NF": e, "Leads": contagem.get(e, 0)}
            for e in ORDEM_FUNIL
            if contagem.get(e, 0) > 0
        ]
        if funil_data:
            funil_df = pd.DataFrame(funil_data)
            fig_funil = px.funnel(
                funil_df,
                x="Leads", y="Etapa_NF",
                title="Funil de Vendas",
                color="Etapa_NF",
                color_discrete_map=COLOR_MAP,
                template=_tema(),
            )
            fig_funil.update_traces(
                texttemplate="%{value:,.0f}",
                textposition="outside",
                textfont=dict(size=13, color="#ffffff", family="Manrope, sans-serif"),
            )
            fig_funil.update_layout(showlegend=False)
            fig_funil.update_layout(
                **_LAYOUT_BASE,
                height=440,
                title=_titulo_layout("Funil de Vendas"),
            )
            st.plotly_chart(fig_funil, use_container_width=True)
        else:
            st.info("Sem dados de funil para o período selecionado.")

    with col_b:
        # Distribuição On/Off Donut Plotly
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
                    template=_tema(), height=320,
                    margin=dict(l=10, r=10, t=50, b=10),
                    legend=dict(
                        orientation="v", x=0.65, y=0.5,
                        xanchor="left", yanchor="middle",
                        font=dict(family="Manrope, sans-serif", size=12, color="rgba(255,255,255,0.8)"),
                    ),
                    title=_titulo_layout("Distribuição On / Off"),
                )
                st.plotly_chart(fig_oo, use_container_width=True)

        st.divider()
        # Won vs Lost Cards
        if "Etapa_NF" in df_filtrado.columns:
            tot = len(df_filtrado)
            ganhas   = int(df_filtrado["Etapa_NF"].eq("Venda Ganha").sum())
            perdidas = int(df_filtrado["Etapa_NF"].eq("Venda Perdida").sum())
            p_ganhas  = f"{ganhas / tot:.1%}" if tot else "0%"
            p_perdidas= f"{perdidas / tot:.1%}" if tot else "0%"

            c_w1, c_w2 = st.columns(2)
            c_w1.metric("Venda Ganha", _br(ganhas), f"{p_ganhas} do total", delta_color="normal")
            c_w2.metric("Venda Perdida", _br(perdidas), f"{p_perdidas} do total", delta_color="inverse")

        st.divider()
        # Remarketing metric
        if "Etapa_NF" in df_filtrado.columns:
            tot = len(df_filtrado)
            qtd   = int(df_filtrado["Etapa_NF"].eq("Acompanhamento").sum())
            perc  = f"{qtd / tot:.1%}" if tot else "0%"
            st.metric(
                label="Acompanhamento (remarketing)",
                value=_br(qtd),
                delta=f"{perc} do total",
                delta_color="off",
            )
            st.caption("Leads identificados como oportunidades futuras — fora do funil ativo.")

    # Monthly evolution of leads
    if "DataCadastro" in df_filtrado.columns:
        serie = (
            df_filtrado.dropna(subset=["DataCadastro"])
            .assign(Mes=lambda d: d["DataCadastro"].dt.to_period("M").dt.to_timestamp())
            .groupby("Mes")
            .size()
            .reset_index(name="Leads")
        )
        if not serie.empty:
            serie["_label"] = serie["Leads"].apply(lambda v: _br(v))
            fig_ev = px.bar(
                serie, x="Mes", y="Leads",
                text="_label",
                title="Evolução mensal de leads",
                color_discrete_sequence=[_VERDE_BASE],
            )
            fig_ev.update_traces(
                textposition="outside",
                textfont=dict(color="#ffffff", size=12, family="JetBrains Mono, monospace"),
                marker_line_width=0,
            )
            fig_ev.update_xaxes(
                tickformat="%b %Y",
                dtick="M1",
                ticklabelmode="period",
            )
            fig_ev.update_layout(
                **_LAYOUT_BASE,
                height=360,
                title=_titulo_layout("Evolução mensal de leads"),
            )
            st.plotly_chart(fig_ev, use_container_width=True)

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
    st.subheader("Matriz de Leads (Cidade ➔ Etapa ➔ Produto ➔ Responsável ➔ Lead)")
    
    # Prepara dados para a matriz com 5 níveis
    df_mat = df_filtrado.copy()
    df_mat["Cidade"] = df_mat["Cidade"].fillna("Não Informado").astype(str).str.strip().replace({"": "Não Informado"})
    df_mat["Etapa_NF"] = df_mat["Etapa_NF"].fillna("Outros").astype(str).str.strip().replace({"": "Outros"})
    df_mat["Produto"] = df_mat["Produto"].fillna("Não Informado").astype(str).str.strip().replace({"": "Não Informado"})
    df_mat["Responsavel"] = df_mat["Responsavel"].fillna("Sem Responsável").astype(str).str.strip().replace({"": "Sem Responsável"})
    df_mat["Nome"] = df_mat["Nome"].fillna("Sem Nome").astype(str).str.strip().replace({"": "Sem Nome"})
    
    df_mat["Leads"] = 1
    df_mat["TempoTotal"] = pd.to_numeric(df_mat["TempoTotal"], errors="coerce").fillna(0.0)
    df_mat["Leads_Com_Tempo"] = (df_filtrado["TempoTotal"].notna() & (df_filtrado["TempoTotal"] > 0)).astype(int)
    
    col_specs_funil = [
        {"header": "Hierarquia (Cidade ➔ Etapa ➔ Produto ➔ Responsável ➔ Lead)", "key": "name"},
        {"header": "Leads", "key": "Leads", "dec": 0},
        {"header": "Tempo (dias)", "key": "TempoTotal", "is_text": True},
        {"header": "Responsável", "key": "Responsavel", "is_text": True},
        {"header": "Origem (Canais)", "key": "UtmSource", "is_text": True},
        {"header": "Forma de Cadastro", "key": "FormaCadastro", "is_text": True},
    ]
    
    agg_rules_funil = {
        "Leads": "sum",
        "TempoTotal": "sum",
        "Leads_Com_Tempo": "sum",
    }
    
    def derived_funil(agg, subset_df):
        # Quantidade de leads únicos no subset
        unique_leads = subset_df["Codigo"].dropna().unique()
        
        if len(unique_leads) == 1:
            # Nível de folha (Lead individual)
            row = subset_df.iloc[0]
            resp = row.get("Responsavel", "—")
            origem = row.get("UtmSource", "—")
            tempo = row.get("TempoTotal", "—")
            forma = row.get("FormaCadastro", "—")
            
            resp = resp if pd.notna(resp) and str(resp).strip() != "" else "—"
            origem = origem if pd.notna(origem) and str(origem).strip() != "" else "—"
            tempo = f"{int(tempo)} dias" if pd.notna(tempo) and float(tempo) > 0 else "—"
            forma = forma if pd.notna(forma) and str(forma).strip() != "" else "—"
            
            return {
                "Responsavel": resp,
                "UtmSource": origem,
                "TempoTotal": tempo,
                "FormaCadastro": forma,
                "Leads": 1
            }
        else:
            # Nível de agrupamento (pai)
            tempo_sum = agg.get("TempoTotal", 0)
            leads_com_tempo = agg.get("Leads_Com_Tempo", 0)
            avg = tempo_sum / leads_com_tempo if leads_com_tempo > 0 else 0
            tempo_str = f"{avg:.1f} dias (média)" if avg > 0 else "—"
            
            return {
                "Responsavel": "—",
                "UtmSource": "—",
                "TempoTotal": tempo_str,
                "FormaCadastro": "—",
                "Leads": agg.get("Leads", 0)
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
        group_cols=["Cidade", "Etapa_NF", "Produto", "Responsavel", "Nome"],
        col_specs=col_specs_funil,
        agg_rules=agg_rules_funil,
        derived_func=derived_funil,
        grid_template="minmax(380px, 3.5fr) 0.8fr 1.2fr 1.5fr 1fr 1.3fr",
        active_campaigns=None,
        key="funil_matrix_hierarquia",
        df_download=df_download,
        download_filename="leads_crm_detalhe.csv",
        download_label="📥 Baixar CSV"
    )


