import pandas as pd
import streamlit as st
import plotly.express as px

from core.theme import aplicar_tema
from core.ui import cabecalho, kpis, botao_download_csv
from core.format import _br, VERDE
from core.charts import _LAYOUT_BASE, _titulo_layout, grafico_donut, dataframe_card
from sources.clientes import carregar_clientes, fix_text_values

aplicar_tema()

cabecalho("Análise de Clientes — Buriti", "Perfil demográfico da base de clientes")

# ── Carregar Dados ────────────────────────────────────────────────────────────
with st.spinner("Carregando dados demográficos de clientes..."):
    df = carregar_clientes()

if df.empty:
    st.info("Sem dados demográficos de clientes cadastrados ou disponíveis no BigQuery.")
    st.stop()

# ── Filtros (Sidebar) ─────────────────────────────────────────────────────────
st.sidebar.header("Filtros")
df_orig = df.copy()

# 1. Ano da venda
years_list = sorted(list(df_orig['ano_venda'].dropna().unique()), reverse=True)
selected_years = st.sidebar.multiselect("Anos de Venda", options=years_list, placeholder="Todos")
if selected_years:
    df = df[df['ano_venda'].isin(selected_years)]

# 2. Gênero (Sexo)
genders_list = sorted(list(df_orig['sexo'].dropna().unique()))
selected_genders = st.sidebar.multiselect("Gênero", options=genders_list, placeholder="Todos")
if selected_genders:
    df = df[df['sexo'].isin(selected_genders)]

# 3. Finalidade da compra
purposes_list = sorted(list(df_orig['finalidade'].dropna().unique()))
selected_purposes = st.sidebar.multiselect("Finalidade da Compra", options=purposes_list, placeholder="Todas")
if selected_purposes:
    df = df[df['finalidade'].isin(selected_purposes)]

# 4. Cidade do empreendimento (Obra)
cities_list = sorted(list(df_orig['cidade_obra'].dropna().unique()))
selected_cities = st.sidebar.multiselect("Cidade do Empreendimento (Obra)", options=cities_list, placeholder="Todas")
if selected_cities:
    df = df[df['cidade_obra'].isin(selected_cities)]

# ── Download Button in Sidebar ────────────────────────────────────────────────
with st.sidebar:
    st.divider()
    botao_download_csv(df, "clientes_filtrados.csv", "📥 Baixar dados (CSV)")

# ── Validar Estado Pós-Filtros ────────────────────────────────────────────────
if df.empty:
    st.warning("Nenhum dado encontrado para a combinação de filtros selecionada.")
    st.stop()

# ── Calcular KPIs ─────────────────────────────────────────────────────────────
total_sales = len(df)
unique_clients = df['cod_cliente'].nunique()
valid_ages = df['idade_limpa'].dropna()
avg_age = int(round(valid_ages.mean())) if len(valid_ages) > 0 else 0
num_cities = df['cidade_obra'].nunique()

# Gender split percentages
m_count = len(df[df['sexo'] == 'Masculino'])
m_percent = (m_count / total_sales) * 100 if total_sales > 0 else 0
f_percent = 100 - m_percent if total_sales > 0 else 0

# Exibir KPIs
kpis({
    "Total de Vendas": f"{total_sales:,}".replace(",", "."),
    "Clientes Únicos": f"{unique_clients:,}".replace(",", "."),
    "Média de Idade": f"{avg_age} anos" if avg_age > 0 else "N/A",
    "Cidades de Obras": f"{num_cities} cidades",
    "Divisão de Gênero": f"{m_percent:.0f}% M / {f_percent:.0f}% F"
}, ajudas={
    "Total de Vendas": "Quantidade total de empreendimentos vendidos no período.",
    "Clientes Únicos": "Número de clientes distintos (sem duplicar quem comprou mais de uma vez).",
    "Divisão de Gênero": "Percentual de clientes por gênero (M/F) com base no cadastro.",
})
st.divider()

# ── Layout de Abas ────────────────────────────────────────────────────────────
tab_demographics, tab_location = st.tabs([
    "👤 Perfil Demográfico",
    "📍 Análise de Localização"
])

# ==============================================================================
# ABA 1: PERFIL DEMOGRÁFICO
# ==============================================================================
with tab_demographics:
    st.subheader("Perfil dos Compradores (Pessoa Física)")
    
    col_g, col_f = st.columns(2)
    
    with col_g:
        df_gender = df.copy()
        df_gender['quantidade'] = 1
        PALETTE_GENDER = {"Masculino": "#3B82F6", "Feminino": "#EC4899"}
        
        grafico_donut(
            df_gender,
            dim='sexo',
            valor='quantidade',
            titulo='Distribuição por Gênero',
            color_map=PALETTE_GENDER,
            total_centro=True,
            altura=320,
        )
        
    with col_f:
        df_purpose = df.copy()
        df_purpose['quantidade'] = 1
        PALETTE_PURPOSE = {
            "INVESTIMENTO": "#2a9d45",       # verde principal
            "MORADIA": "#8f8f96",            # azul-petróleo
            "SEGUNDA RESIDÊNCIA": "#008274",  # teal-verde
            "ALUGUEL": "#5BD9CC",            # teal claro
            "Não Informado": "#888888"       # cinza
        }
        
        grafico_donut(
            df_purpose,
            dim='finalidade',
            valor='quantidade',
            titulo='Finalidade de Compra dos Clientes',
            color_map=PALETTE_PURPOSE,
            total_centro=True,
            altura=320,
        )
        
    st.divider()
    col_a, col_hist = st.columns(2)
    
    with col_a:
        fe_order = [
            "De 0 a 10 anos", "De 11 a 20 anos", "De 21 a 30 anos", "De 31 a 40 anos",
            "De 41 a 50 anos", "De 51 a 60 anos", "De 61 a 70 anos", "De 71 a 80 anos",
            "De 81 a 90 anos", "De 91 a 100 anos", "Não Informado"
        ]
        fe_counts = df['faixa_etaria'].value_counts().reset_index()
        fe_counts.columns = ['faixa_etaria', 'vendas']
        
        fig_fe = px.bar(
            fe_counts,
            y='faixa_etaria',
            x='vendas',
            orientation='h',
            color_discrete_sequence=[VERDE],
            category_orders={"faixa_etaria": fe_order[::-1]}
        )
        fig_fe.update_layout(
            **{
                **_LAYOUT_BASE,
                **dict(
                    height=350,
                    title=_titulo_layout("Distribuição por Faixa Etária"),
                    xaxis=dict(title="Número de Contratos", gridcolor="#eef1f5", griddash="dot"),
                    yaxis=dict(title=None)
                )
            }
        )
        fig_fe.update_traces(marker_cornerradius=8, selector=dict(type="bar"))
        st.plotly_chart(fig_fe, use_container_width=True)
        
    with col_hist:
        if len(valid_ages) > 0:
            fig_hist = px.histogram(
                df.dropna(subset=['idade_limpa']), 
                x="idade_limpa",
                nbins=35,
                color_discrete_sequence=[VERDE]
            )
            fig_hist.update_layout(
                **{
                    **_LAYOUT_BASE,
                    **dict(
                        height=350,
                        title=_titulo_layout("Distribuição Detalhada de Idades"),
                        xaxis=dict(title="Idade do Cliente (anos)", gridcolor="#eef1f5", griddash="dot"),
                        yaxis=dict(title="Quantidade de Clientes", gridcolor="#eef1f5", griddash="dot")
                    )
                }
            )
            fig_hist.update_traces(marker_cornerradius=8, selector=dict(type="bar"))
            st.plotly_chart(fig_hist, use_container_width=True)
        else:
            st.info("Sem dados de idades válidos para exibir no histograma.")

    st.divider()
    col_ec, col_prof = st.columns([1, 1.8])

    with col_ec:
        ec_df = df[['estado_civil']].copy()
        _merge = {"Viúvo": "Solteiro", "Separado": "Solteiro"}
        _keep  = {"Solteiro", "Casado", "Divorciado"}
        ec_df['estado_civil'] = ec_df['estado_civil'].map(lambda v: _merge.get(v, v))
        ec_df = ec_df[ec_df['estado_civil'].isin(_keep)]
        ec_counts = ec_df['estado_civil'].value_counts().reset_index()
        ec_counts.columns = ['Estado Civil', 'vendas']
        grafico_donut(ec_counts, "Estado Civil", "vendas", "Estado Civil dos Clientes", altura=440)

    with col_prof:
        prof_df = df[~df['profissao_cliente'].isna()]
        prof_df = prof_df[~prof_df['profissao_cliente'].isin(['Não Informado', 'Nao Informada', 'nan', ''])]
        prof_counts = prof_df['profissao_cliente'].value_counts().reset_index().head(15)
        prof_counts.columns = ['profissao_cliente', 'vendas']
        prof_counts['profissao_cliente'] = prof_counts['profissao_cliente'].astype(str).str.title()
        fig_prof = px.bar(
            prof_counts, y='profissao_cliente', x='vendas',
            orientation='h', color_discrete_sequence=[VERDE],
        )
        fig_prof.update_layout(**{**_LAYOUT_BASE, **dict(
            height=450,
            title=_titulo_layout("Top 15 Profissões dos Clientes"),
            xaxis=dict(title="Número de Contratos", gridcolor="#eef1f5", griddash="dot"),
            yaxis=dict(title=None, categoryorder="total ascending"),
        )})
        fig_prof.update_traces(marker_cornerradius=8, selector=dict(type="bar"))
        st.plotly_chart(fig_prof, use_container_width=True)

# Note: Tab 2 (Evolução de Vendas & Canais) was removed by user request to focus on Demographics and Location.

# ==============================================================================
# ABA 3: ANÁLISE DE LOCALIZAÇÃO
# ==============================================================================
with tab_location:
    st.subheader("Análise de Localização e Comportamento Geográfico")
    
    loc_clean = df[(df['cidade_cli'] != 'Não Informado') & (df['cidade_obra'] != 'Não Informado')]
    cross_city = loc_clean[loc_clean['cidade_cli'] != loc_clean['cidade_obra']]
    same_city = loc_clean[loc_clean['cidade_cli'] == loc_clean['cidade_obra']]
    
    cross_rate = (len(cross_city) / len(loc_clean)) * 100 if len(loc_clean) > 0 else 0
    same_rate = 100 - cross_rate
    
    with st.container(key="dfc_loc_geo"):
        col_rate, col_chart = st.columns([1, 2])

        with col_rate:
            st.markdown(f"""
            <div style="padding-top: 4px;">
                <h5 style="margin-top:0; margin-bottom:16px; color:#232329; font-family:'Segoe UI',sans-serif; font-size:15px; font-weight:700;">Fidelidade Geográfica</h5>
                <p style="font-size:32px; font-weight:700; color:#2a9d45; margin-bottom: 2px; font-family:'Roboto Condensed',sans-serif;">{same_rate:.1f}%</p>
                <p style="font-size:12px; color:#6b6b74; margin-bottom:15px; font-family:'Segoe UI',sans-serif; line-height:1.4;">Clientes que residem na <b>mesma</b> cidade do empreendimento (Demanda local).</p>
                <hr style="border-color:#ececed; margin:15px 0;">
                <p style="font-size:32px; font-weight:700; color:#8f8f96; margin-bottom: 2px; font-family:'Roboto Condensed',sans-serif;">{cross_rate:.1f}%</p>
                <p style="font-size:12px; color:#6b6b74; font-family:'Segoe UI',sans-serif; line-height:1.4;">Clientes que residem em cidade <b>diferente</b> da obra (Compradores de fora).</p>
            </div>
            """, unsafe_allow_html=True)

        with col_chart:
            loc_df = pd.DataFrame({
                "tipo_compra": ["Outras Cidades"] * len(cross_city) + ["Cidade Local"] * len(same_city),
                "quantidade": 1
            })
            COLOR_MAP_LOC = {"Outras Cidades": "#8f8f96", "Cidade Local": "#2a9d45"}
            grafico_donut(
                loc_df,
                dim='tipo_compra',
                valor='quantidade',
                titulo='Comportamento Geográfico',
                color_map=COLOR_MAP_LOC,
                total_centro=True,
                altura=260,
            )

    st.divider()
    col_ccli, col_cobr = st.columns(2)
    
    with col_ccli:
        ccli_counts = df['cidade_cli'].value_counts().reset_index().head(15)
        ccli_counts.columns = ['cidade', 'vendas']
        
        fig_ccli = px.bar(
            ccli_counts,
            y='cidade',
            x='vendas',
            orientation='h',
            color_discrete_sequence=["#2a9d45"],
        )
        fig_ccli.update_layout(
            **{
                **_LAYOUT_BASE,
                **dict(
                    height=400,
                    title=_titulo_layout("Top 15 Cidades de Residência dos Clientes"),
                    xaxis=dict(title="Número de Clientes", gridcolor="#eef1f5", griddash="dot"),
                    yaxis=dict(title=None, categoryorder="total ascending"),
                )
            }
        )
        fig_ccli.update_traces(marker_cornerradius=8, selector=dict(type="bar"))
        st.plotly_chart(fig_ccli, use_container_width=True)
        
    with col_cobr:
        cobr_counts = df['cidade_obra'].value_counts().reset_index().head(15)
        cobr_counts.columns = ['cidade', 'vendas']
        
        fig_cobr = px.bar(
            cobr_counts,
            y='cidade',
            x='vendas',
            orientation='h',
            color_discrete_sequence=["#2a9d45"],
        )
        fig_cobr.update_layout(
            **{
                **_LAYOUT_BASE,
                **dict(
                    height=400,
                    title=_titulo_layout("Top 15 Cidades de Obras (Empreendimentos)"),
                    xaxis=dict(title="Número de Empreendimentos Vendidos", gridcolor="#eef1f5", griddash="dot"),
                    yaxis=dict(title=None, categoryorder="total ascending"),
                )
            }
        )
        fig_cobr.update_traces(marker_cornerradius=8, selector=dict(type="bar"))
        st.plotly_chart(fig_cobr, use_container_width=True)

    # Neighborhood analysis section when exactly 1 city is selected
    if len(selected_cities) == 1:
        st.divider()
        st.subheader(f"🏘️ Perfil de Bairros de Residência para o Empreendimento em {selected_cities[0]}")
        
        col_b1, col_b2 = st.columns([2, 1])
        
        bairro_df = df.copy()
        bairro_df = bairro_df[~bairro_df['bairro_cli'].isna()]
        bairro_df['bairro_cli_limpo'] = bairro_df['bairro_cli'].astype(str).apply(fix_text_values).str.title().str.strip()
        bairro_df = bairro_df[~bairro_df['bairro_cli_limpo'].isin(['Não Informado', 'Nao Informado', 'Outros', 'nan', ''])]
        
        bairro_counts = bairro_df['bairro_cli_limpo'].value_counts().reset_index().head(15)
        bairro_counts.columns = ['bairro', 'clientes']
        total_bairros_cados = len(bairro_df)

        if not bairro_counts.empty:
            st.markdown(f"<div style='margin-bottom:10px;'>Total de compradores com bairros informados: <b>{total_bairros_cados:,}</b></div>", unsafe_allow_html=True)

        with col_b1:
            if not bairro_counts.empty:
                with st.container(key="dfc_bairros_chart"):
                    fig_bairro = px.bar(
                        bairro_counts,
                        y='bairro',
                        x='clientes',
                        orientation='h',
                        color_discrete_sequence=["#2a9d45"],
                    )
                    fig_bairro.update_layout(
                        **{
                            **_LAYOUT_BASE,
                            **dict(
                                height=450,
                                title=_titulo_layout("Top 15 Bairros dos Compradores"),
                                xaxis=dict(title="Número de Clientes", gridcolor="#eef1f5", griddash="dot"),
                                yaxis=dict(title=None, categoryorder="total ascending"),
                            )
                        }
                    )
                    fig_bairro.update_traces(marker_cornerradius=8, selector=dict(type="bar"))
                    st.plotly_chart(fig_bairro, use_container_width=True)
            else:
                st.info("Nenhum dado de bairro detalhado disponível para esta seleção.")

        with col_b2:
            if not bairro_counts.empty:
                bairro_counts['%'] = (bairro_counts['clientes'] / total_bairros_cados) * 100
                bairro_counts['%'] = bairro_counts['%'].round(1).astype(str) + '%'

                dataframe_card(
                    bairro_counts,
                    "Bairros de origem",
                    key="bairros_origem",
                    height=398,
                    column_config={
                        "bairro": "Bairro de Origem",
                        "clientes": st.column_config.NumberColumn("Qtd. Clientes", format="%d"),
                        "%": "Representatividade"
                    },
                    hide_index=True,
                )
                st.caption("ℹ️ Representatividade calculada com base no total de clientes PF com bairro informado para esta cidade.")
            else:
                st.info("Tabela de bairros indisponível.")
