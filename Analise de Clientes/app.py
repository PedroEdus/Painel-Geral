import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

# 1. Page Configuration
st.set_page_config(
    page_title="Analytics Clientes | Demográfico e Vendas",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Custom CSS for Premium Design & Fonts
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Outfit', sans-serif;
}

/* Metric card glassmorphism style */
.kpi-container {
    display: flex;
    gap: 15px;
    margin-bottom: 20px;
}

.kpi-card {
    flex: 1;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(128, 128, 128, 0.15);
    border-left: 5px solid #6366f1;
    border-radius: 12px;
    padding: 16px 20px;
    box-shadow: 0 4px 15px rgba(0,0,0,0.05);
    transition: transform 0.2s, box-shadow 0.2s;
}

.kpi-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(99, 102, 241, 0.1);
    border-left-color: #818cf8;
}

.kpi-title {
    font-size: 11px;
    font-weight: 700;
    color: #888888;
    text-transform: uppercase;
    letter-spacing: 1px;
}

.kpi-value {
    font-size: 26px;
    font-weight: 700;
    color: #4f46e5;
    margin-top: 5px;
    line-height: 1.1;
}

.kpi-subtitle {
    font-size: 11px;
    color: #64748b;
    margin-top: 6px;
}

/* Tab styling and spacing */
.stTabs [data-baseweb="tab-list"] {
    gap: 24px;
}

.stTabs [data-baseweb="tab"] {
    height: 50px;
    white-space: pre-wrap;
    background-color: transparent;
    border-radius: 4px 4px 0px 0px;
    gap: 1px;
    padding-top: 10px;
    padding-bottom: 10px;
    font-size: 16px;
    font-weight: 600;
}

.stTabs [aria-selected="true"] {
    color: #6366f1 !important;
    border-bottom: 2px solid #6366f1 !important;
}

/* Custom cards for layout */
.content-card {
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid rgba(128, 128, 128, 0.08);
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 20px;
}

</style>
""", unsafe_allow_html=True)

# Colors Palette
COLOR_PRIMARY = "#6366F1"   # Indigo
COLOR_SECONDARY = "#EC4899" # Pink
COLOR_TERTIARY = "#10B981"  # Emerald
COLOR_DARK = "#1E293B"      # Slate Dark
COLOR_LIGHT = "#F8FAFC"     # Slate Light
PALETTE_GENDER = {"Masculino": "#3B82F6", "Feminino": "#EC4899", "Pessoa Jurídica": "#10B981"}
PALETTE_THEME = ["#6366F1", "#EC4899", "#10B981", "#F59E0B", "#3B82F6", "#8B5CF6", "#06B6D4"]

# Helper to fix encoding issues
def fix_text_values(val):
    if not isinstance(val, str):
        return val
    
    replacements = {
        'No Informado': 'Não Informado',
        'No Informada': 'Não Informada',
        'Pessoa jurdica': 'Pessoa Jurídica',
        'Vivo': 'Viúvo',
        'Ensino Mdio completo': 'Ensino Médio Completo',
        'Ensino Mdio incompleto': 'Ensino Médio Incompleto',
        'Educao Superior completa.': 'Superior Completo',
        'Educao Superior incompleta.': 'Superior Incompleto',
        'Da 5  8 srie do Ensino Fundamental': 'Fundamental II (5ª a 8ª)',
        'At 4 srie incompleta do Ensino Fundamental': 'Fundamental I Incompleto',
        '4 srie completa do Ensino Fundamental': 'Fundamental I Completo',
        'Mestrado Completo': 'Mestrado',
        'Doutorado Completo': 'Doutorado',
        'PROSPECO CORRETOR': 'Prospecção Corretor',
        'INDICAO': 'Indicação',
        'BURITI FACEBOOK': 'Facebook Ads',
        'BURITI GOOGLE': 'Google Ads',
        'MDIA OUTDOOR': 'Mídia Outdoor',
        'MATERIAL IMPRESSO - PANFLETAGEM': 'Panfletagem',
        'BURITI WHATSAPP': 'WhatsApp',
        'ESPONTNEO - STANDE DE VENDAS': 'Stand de Vendas (Espontâneo)',
        'MDIA DO CORRETOR': 'Mídia do Corretor',
        'JORNAL  DO TOCANTINS (CLASSIFICADOS)': 'Jornal do Tocantins',
        'REDENO': 'Redenção',
        'MARAB': 'Marabá',
        'MACEI': 'Maceió',
        'CANA DOS CARAJS': 'Canaã dos Carajás',
        'SO MIGUEL DOS CAMPOS': 'São Miguel dos Campos',
        'TUCUM': 'Tucumã',
        'CONCEIO DO ARAGUAIA': 'Conceição do Araguaia',
        'LUZIMANGUES': 'Luzimangues',
        'SO FLIX DO XINGU': 'São Félix do Xingu',
        'SO VALRIO DA NATIVIDADE': 'São Valério da Natividade',
        'SO VALERIO DA NATIVIDADE': 'São Valério da Natividade',
        'SO SEBASTIO DO TOCANTINS': 'São Sebastião do Tocantins',
        'SO BENTO DO TOCANTINS': 'São Bento do Tocantins',
        'SO FELIX DO XINGU': 'São Félix do Xingu',
        'ARAGUANA': 'Araguaína',
        'GOINIA': 'Goiânia',
        'BRASLIA': 'Brasília',
        'SO PAULO': 'São Paulo',
    }
    
    for k, v in replacements.items():
        val = val.replace(k, v)
        
    # Replace any residual replacement characters safely
    val = val.replace('\ufffd', 'a')
    return val

# 3. Data Loading function with Caching
@st.cache_data(show_spinner="Carregando e processando base de clientes...")
def load_and_process_data(file_source, file_name=None):
    # Detect file type
    is_csv = False
    if file_name:
        is_csv = file_name.lower().endswith('.csv')
    elif isinstance(file_source, str):
        is_csv = file_source.lower().endswith('.csv')
        
    if is_csv:
        # Load CSV sheet
        try:
            df = pd.read_csv(file_source, sep=';', encoding='utf-8-sig')
        except Exception:
            df = pd.read_csv(file_source, sep=';', encoding='latin-1')
    else:
        # Load Excel sheet
        df = pd.read_excel(file_source, sheet_name="Dados Clientes")
    
    # 3.1 Rename encoding issue columns
    cols_to_rename = {}
    for col in df.columns:
        if 'GrauInstru' in col:
            cols_to_rename[col] = 'GrauInstrucao'
        elif 'Divulga' in col and 'Chave' not in col:
            cols_to_rename[col] = 'Divulgacao'
    df.rename(columns=cols_to_rename, inplace=True)
    
    # 3.2 Fix string values for categorical columns
    string_cols = ['Sexo', 'FaixaEtaria', 'EstadoCivil', 'GrauInstrucao', 'Divulgacao', 'Finalidade', 'CidadeCli', 'CidadeObra']
    for col in string_cols:
        if col in df.columns:
            df[col] = df[col].fillna('Não Informado').astype(str).apply(fix_text_values)
            
    # Normalize Gender Categories
    if 'Sexo' in df.columns:
        df['Sexo'] = df['Sexo'].str.replace('Sexo Masculino', 'Masculino', regex=False)
        df['Sexo'] = df['Sexo'].str.replace('Sexo Feminino', 'Feminino', regex=False)
        # Filter only individual clients (Pessoa Física)
        df = df[df['Sexo'].isin(['Masculino', 'Feminino'])]
        
    # Standardize Cities casing
    if 'CidadeCli' in df.columns:
        df['CidadeCli'] = df['CidadeCli'].str.title()
    if 'CidadeObra' in df.columns:
        df['CidadeObra'] = df['CidadeObra'].str.title()
        
    # Standardize Salesperson Casing
    if 'NomeVen' in df.columns:
        df['NomeVen'] = df['NomeVen'].fillna('Não Informado').astype(str).str.title()
        
    # Clean ages: Create a cleaned age column (only within realistic human age 18-100)
    # Exclude PJ from age metrics (they will have NaN or invalid)
    if 'Idade' in df.columns:
        # Fill nulls first
        df['Idade_Limpa'] = pd.to_numeric(df['Idade'], errors='coerce')
        # Filter ages: set out-of-range or PJ to NaN
        df.loc[(df['Sexo'] == 'Pessoa Jurídica') | (df['Idade_Limpa'] < 18) | (df['Idade_Limpa'] > 100), 'Idade_Limpa'] = pd.NA
        
    # Sort months for charts
    month_translation = {
        1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
        7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
    }
    df['NomeMesVenda'] = df['MesVenda'].map(month_translation)
    
    return df

# 4. App Flow - Check for file
st.sidebar.image("https://img.icons8.com/isometric/100/data-configuration.png", width=70)
st.sidebar.markdown("### Configurações de Dados")

uploaded_file = st.sidebar.file_uploader("Fazer upload de nova base (.xlsx, .csv)", type=["xlsx", "csv"])
default_csv_path = "DadosClientes_MKT .csv"
default_xlsx_path = "DadosClientes_MKT (1).xlsx"
data_loaded = False
df = None

if uploaded_file is not None:
    try:
        df = load_and_process_data(uploaded_file, uploaded_file.name)
        st.sidebar.success("✅ Arquivo enviado carregado com sucesso!")
        data_loaded = True
    except Exception as e:
        st.sidebar.error(f"Erro ao ler arquivo enviado: {e}")

elif os.path.exists(default_csv_path):
    try:
        df = load_and_process_data(default_csv_path)
        st.sidebar.info("🟢 Utilizando base CSV padrão da pasta: `DadosClientes_MKT .csv`")
        data_loaded = True
    except Exception as e:
        st.sidebar.error(f"Erro ao ler base CSV padrão: {e}")

elif os.path.exists(default_xlsx_path):
    try:
        df = load_and_process_data(default_xlsx_path)
        st.sidebar.info("🟢 Utilizando base Excel padrão da pasta: `DadosClientes_MKT (1).xlsx`")
        data_loaded = True
    except Exception as e:
        st.sidebar.error(f"Erro ao ler base Excel padrão: {e}")
else:
    st.sidebar.warning("⚠️ Base de dados não encontrada.")

if not data_loaded:
    st.title("📊 Painel de Análise Demográfica de Clientes")
    st.warning("Nenhuma base de dados encontrada no diretório e nenhum arquivo foi carregado.")
    st.info("💡 Por favor, faça o upload de um arquivo Excel (.xlsx) ou CSV (.csv) na barra lateral para iniciar a análise.")
    st.stop()

# 5. Dashboard Sidebar Filters
st.sidebar.markdown("---")
st.sidebar.markdown("### 🔍 Filtros de Análise")

# Years filter
years_list = sorted(list(df['AnoVenda'].unique()), reverse=True)
selected_years = st.sidebar.multiselect("Anos de Venda", options=years_list, default=years_list[:5]) # Default to last 5 years

# Gender filter
genders_list = sorted(list(df['Sexo'].unique()))
selected_genders = st.sidebar.multiselect("Gênero", options=genders_list, default=genders_list)

# Purchase Purpose filter
purposes_list = sorted(list(df['Finalidade'].unique()))
selected_purposes = st.sidebar.multiselect("Finalidade da Compra", options=purposes_list, default=purposes_list)

# City (Obra) filter
cities_list = sorted(list(df['CidadeObra'].unique()))
selected_cities = st.sidebar.multiselect("Cidade do Empreendimento (Obra)", options=cities_list)

# Apply filters
filtered_df = df.copy()

if selected_years:
    filtered_df = filtered_df[filtered_df['AnoVenda'].isin(selected_years)]
if selected_genders:
    filtered_df = filtered_df[filtered_df['Sexo'].isin(selected_genders)]
if selected_purposes:
    filtered_df = filtered_df[filtered_df['Finalidade'].isin(selected_purposes)]
if selected_cities:
    filtered_df = filtered_df[filtered_df['CidadeObra'].isin(selected_cities)]

# If dataframe is empty after filter
if filtered_df.empty:
    st.title("📊 Painel de Análise de Clientes")
    st.error("Nenhum data encontrado para os filtros selecionados. Remova alguns filtros para exibir a análise.")
    st.stop()

# 6. HEADER
st.title("📊 Painel de Análise Demográfica de Clientes (Pessoa Física)")
st.markdown("Uma análise completa da base de vendas, demografia, perfil de clientes e evolução de mercado.")

# 7. KPI Metric Cards
col1, col2, col3, col4, col5 = st.columns(5)

# Metrics calculation
total_sales = len(filtered_df)
unique_clients = filtered_df['CodCliente'].nunique()

# Average age for PF clients with valid ages
valid_ages = filtered_df['Idade_Limpa'].dropna()
avg_age = int(round(valid_ages.mean())) if len(valid_ages) > 0 else 0

# Number of cities with active construction projects
num_cities = filtered_df['CidadeObra'].nunique()

# Gender Split percentages
m_count = len(filtered_df[filtered_df['Sexo'] == 'Masculino'])
m_percent = (m_count / total_sales) * 100 if total_sales > 0 else 0
f_percent = 100 - m_percent if total_sales > 0 else 0

with col1:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-title">Total de Vendas</div>
        <div class="kpi-value">{total_sales:,}</div>
        <div class="kpi-subtitle">Contratos assinados (PF)</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="kpi-card" style="border-left-color: #EC4899;">
        <div class="kpi-title">Clientes Únicos</div>
        <div class="kpi-value">{unique_clients:,}</div>
        <div class="kpi-subtitle">Cadastros individuais (PF)</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="kpi-card" style="border-left-color: #10B981;">
        <div class="kpi-title">Média de Idade</div>
        <div class="kpi-value">{avg_age if avg_age > 0 else 'N/A'} anos</div>
        <div class="kpi-subtitle">Excluindo idades inválidas</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="kpi-card" style="border-left-color: #F59E0B;">
        <div class="kpi-title">Cidades Atendidas</div>
        <div class="kpi-value">{num_cities} cidades</div>
        <div class="kpi-subtitle">Compreende cidades de Obras</div>
    </div>
    """, unsafe_allow_html=True)

with col5:
    st.markdown(f"""
    <div class="kpi-card" style="border-left-color: #3B82F6;">
        <div class="kpi-title">Distribuição de Gênero</div>
        <div class="kpi-value">{m_percent:.0f}% M / {f_percent:.0f}% F</div>
        <div class="kpi-subtitle">Proporção Masculino / Feminino</div>
    </div>
    """, unsafe_allow_html=True)

# 8. Main Tabs Layout
tab_demographics, tab_sales, tab_location = st.tabs([
    "👤 Perfil Demográfico (Pessoa Física)",
    "📈 Evolução de Vendas & Canais",
    "📍 Análise de Localização"
])

# ==========================================
# TAB 1: DEMOGRAPHICS
# ==========================================
with tab_demographics:
    st.subheader("Perfil dos Compradores")
    
    col_g, col_a = st.columns(2)
    
    with col_g:
        st.markdown('<div class="content-card">', unsafe_allow_html=True)
        st.markdown("#### Distribuição por Gênero")
        # Gender split
        gender_counts = filtered_df['Sexo'].value_counts().reset_index()
        gender_counts.columns = ['Sexo', 'Quantidade']
        
        fig_gender = px.pie(
            gender_counts, 
            values='Quantidade', 
            names='Sexo',
            color='Sexo',
            color_discrete_map=PALETTE_GENDER,
            hole=0.4,
            category_orders={"Sexo": ["Masculino", "Feminino"]}
        )
        fig_gender.update_traces(textinfo='percent+label', textposition='inside')
        fig_gender.update_layout(
            margin=dict(l=20, r=20, t=10, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5),
            height=350,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig_gender, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col_a:
        st.markdown('<div class="content-card">', unsafe_allow_html=True)
        st.markdown("#### Distribuição por Faixa Etária (Todos)")
        
        # Plot Age brackets (FaixaEtaria)
        # Sort them in logical order
        fe_order = [
            "De 0 a 10 anos", "De 11 a 20 anos", "De 21 a 30 anos", "De 31 a 40 anos",
            "De 41 a 50 anos", "De 51 a 60 anos", "De 61 a 70 anos", "De 71 a 80 anos",
            "De 81 a 90 anos", "De 91 a 100 anos", "Não Informado"
        ]
        
        fe_counts = filtered_df['FaixaEtaria'].value_counts().reset_index()
        fe_counts.columns = ['FaixaEtaria', 'Vendas']
        
        # Add missing ranges with zero sales if needed, but plotting what exists is fine
        fig_fe = px.bar(
            fe_counts,
            y='FaixaEtaria',
            x='Vendas',
            orientation='h',
            color_discrete_sequence=[COLOR_PRIMARY],
            category_orders={"FaixaEtaria": fe_order[::-1]} # reverse for horizontal chart
        )
        fig_fe.update_layout(
            margin=dict(l=20, r=20, t=10, b=10),
            height=350,
            xaxis_title="Número de Contratos",
            yaxis_title="Faixa Etária",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        fig_fe.update_xaxes(showgrid=True, gridcolor='rgba(128,128,128,0.1)')
        st.plotly_chart(fig_fe, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    col_hist, col_ec = st.columns(2)
    
    with col_hist:
        st.markdown('<div class="content-card">', unsafe_allow_html=True)
        st.markdown("#### Distribuição Detalhada de Idades")
        
        if len(valid_ages) > 0:
            fig_hist = px.histogram(
                filtered_df.dropna(subset=['Idade_Limpa']), 
                x="Idade_Limpa",
                nbins=35,
                color_discrete_sequence=[COLOR_PRIMARY],
                labels={"Idade_Limpa": "Idade"}
            )
            fig_hist.update_layout(
                margin=dict(l=20, r=20, t=10, b=10),
                height=350,
                xaxis_title="Idade do Cliente (anos)",
                yaxis_title="Quantidade de Clientes",
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )
            fig_hist.update_yaxes(showgrid=True, gridcolor='rgba(128,128,128,0.1)')
            st.plotly_chart(fig_hist, use_container_width=True)
        else:
            st.info("Sem dados de idades válidos para exibir no histograma.")
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col_ec:
        st.markdown('<div class="content-card">', unsafe_allow_html=True)
        st.markdown("#### Estado Civil dos Clientes")
        
        ec_counts = filtered_df['EstadoCivil'].value_counts().reset_index()
        ec_counts.columns = ['EstadoCivil', 'Vendas']
        
        fig_ec = px.bar(
            ec_counts,
            x='EstadoCivil',
            y='Vendas',
            color='EstadoCivil',
            color_discrete_sequence=PALETTE_THEME
        )
        fig_ec.update_layout(
            margin=dict(l=20, r=20, t=10, b=10),
            height=350,
            showlegend=False,
            xaxis_title="Estado Civil",
            yaxis_title="Número de Contratos",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        fig_ec.update_yaxes(showgrid=True, gridcolor='rgba(128,128,128,0.1)')
        st.plotly_chart(fig_ec, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Secondary details: Education and Professions
    st.markdown("---")
    col_edu, col_prof = st.columns([1, 1.5])
    
    with col_edu:
        st.markdown('<div class="content-card">', unsafe_allow_html=True)
        st.markdown("#### Grau de Instrução")
        
        # User choice: exclude Não Informado
        exclude_ni_edu = st.checkbox("Excluir 'Não Informado' (Educação)", value=False)
        edu_df = filtered_df.copy()
        if exclude_ni_edu:
            edu_df = edu_df[edu_df['GrauInstrucao'] != 'Não Informado']
            
        edu_counts = edu_df['GrauInstrucao'].value_counts().reset_index()
        edu_counts.columns = ['GrauInstrucao', 'Vendas']
        
        fig_edu = px.bar(
            edu_counts,
            y='GrauInstrucao',
            x='Vendas',
            orientation='h',
            color_discrete_sequence=["#8B5CF6"]
        )
        fig_edu.update_layout(
            margin=dict(l=20, r=20, t=10, b=10),
            height=400,
            xaxis_title="Número de Contratos",
            yaxis_title="Escolaridade",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        fig_edu.update_xaxes(showgrid=True, gridcolor='rgba(128,128,128,0.1)')
        st.plotly_chart(fig_edu, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col_prof:
        st.markdown('<div class="content-card">', unsafe_allow_html=True)
        st.markdown("#### Top 15 Profissões dos Clientes")
        
        prof_df = filtered_df.copy()
        prof_df = prof_df[~prof_df['ProfissaoCliente'].isna()]
        prof_df = prof_df[~prof_df['ProfissaoCliente'].isin(['Não Informado', 'Nao Informada'])]
        
        prof_counts = prof_df['ProfissaoCliente'].value_counts().reset_index().head(15)
        prof_counts.columns = ['ProfissaoCliente', 'Vendas']
        
        # Standardize strings for display
        prof_counts['ProfissaoCliente'] = prof_counts['ProfissaoCliente'].astype(str).str.title()
        
        fig_prof = px.bar(
            prof_counts,
            x='Vendas',
            y='ProfissaoCliente',
            orientation='h',
            color='Vendas',
            color_continuous_scale=px.colors.sequential.Purples
        )
        fig_prof.update_layout(
            margin=dict(l=20, r=20, t=10, b=10),
            height=400,
            xaxis_title="Número de Contratos",
            yaxis_title="Profissão",
            coloraxis_showscale=False,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        fig_prof.update_xaxes(showgrid=True, gridcolor='rgba(128,128,128,0.1)')
        st.plotly_chart(fig_prof, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# TAB 2: SALES TRENDS & CHANNELS
# ==========================================
with tab_sales:
    st.subheader("Evolução das Vendas e Canais de Marketing")
    
    st.markdown('<div class="content-card">', unsafe_allow_html=True)
    st.markdown("#### Evolução Anual de Vendas (Quantidade de Contratos)")
    sales_yearly = filtered_df['AnoVenda'].value_counts().reset_index().sort_values('AnoVenda')
    sales_yearly.columns = ['Ano', 'Vendas']
    
    fig_yearly = px.area(
        sales_yearly,
        x='Ano',
        y='Vendas',
        color_discrete_sequence=[COLOR_PRIMARY]
    )
    fig_yearly.update_traces(mode="lines+markers", line=dict(width=3))
    fig_yearly.update_layout(
        margin=dict(l=20, r=20, t=10, b=10),
        height=300,
        xaxis_title="Ano da Venda",
        yaxis_title="Contratos Assinados",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    fig_yearly.update_xaxes(showgrid=True, gridcolor='rgba(128,128,128,0.1)')
    fig_yearly.update_yaxes(showgrid=True, gridcolor='rgba(128,128,128,0.1)')
    st.plotly_chart(fig_yearly, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    col_seas, col_fin = st.columns(2)
    
    with col_seas:
        st.markdown('<div class="content-card">', unsafe_allow_html=True)
        st.markdown("#### Sazonalidade Mensal de Vendas")
        
        # Sort months
        months_ordered = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", 
                          "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
        sales_monthly = filtered_df['NomeMesVenda'].value_counts().reindex(months_ordered).reset_index()
        sales_monthly.columns = ['Mês', 'Vendas']
        
        fig_monthly = px.bar(
            sales_monthly,
            x='Mês',
            y='Vendas',
            color_discrete_sequence=[COLOR_SECONDARY]
        )
        fig_monthly.update_layout(
            margin=dict(l=20, r=20, t=10, b=10),
            height=350,
            xaxis_title="Mês",
            yaxis_title="Vendas",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        fig_monthly.update_yaxes(showgrid=True, gridcolor='rgba(128,128,128,0.1)')
        st.plotly_chart(fig_monthly, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col_fin:
        st.markdown('<div class="content-card">', unsafe_allow_html=True)
        st.markdown("#### Finalidade de Compra dos Clientes")
        
        purpose_counts = filtered_df['Finalidade'].value_counts().reset_index()
        purpose_counts.columns = ['Finalidade', 'Quantidade']
        
        fig_purpose = px.pie(
            purpose_counts,
            values='Quantidade',
            names='Finalidade',
            color_discrete_sequence=PALETTE_THEME,
            hole=0.4
        )
        fig_purpose.update_traces(textinfo='percent+label', textposition='inside')
        fig_purpose.update_layout(
            margin=dict(l=20, r=20, t=10, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5),
            height=350,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig_purpose, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")
    col_chan, col_ven = st.columns(2)
    
    with col_chan:
        st.markdown('<div class="content-card">', unsafe_allow_html=True)
        st.markdown("#### Canais de Divulgação (Marketing)")
        
        # Option to hide "Não Informado" in marketing
        exclude_ni_mkt = st.checkbox("Excluir 'Não Informado' (Canais)", value=True)
        mkt_df = filtered_df.copy()
        if exclude_ni_mkt:
            mkt_df = mkt_df[mkt_df['Divulgacao'] != 'Não Informado']
            
        mkt_counts = mkt_df['Divulgacao'].value_counts().reset_index()
        mkt_counts.columns = ['Divulgacao', 'Vendas']
        
        fig_mkt = px.bar(
            mkt_counts,
            y='Divulgacao',
            x='Vendas',
            orientation='h',
            color_discrete_sequence=["#10B981"]
        )
        fig_mkt.update_layout(
            margin=dict(l=20, r=20, t=10, b=10),
            height=400,
            xaxis_title="Vendas",
            yaxis_title="Canal",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        fig_mkt.update_xaxes(showgrid=True, gridcolor='rgba(128,128,128,0.1)')
        st.plotly_chart(fig_mkt, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col_ven:
        st.markdown('<div class="content-card">', unsafe_allow_html=True)
        st.markdown("#### Top 15 Vendedores por Volume de Vendas")
        
        ven_df = filtered_df.copy()
        ven_df = ven_df[ven_df['NomeVen'] != 'Não Informado']
        
        ven_counts = ven_df['NomeVen'].value_counts().reset_index().head(15)
        ven_counts.columns = ['Vendedor', 'Vendas']
        
        fig_ven = px.bar(
            ven_counts,
            x='Vendas',
            y='Vendedor',
            orientation='h',
            color='Vendas',
            color_continuous_scale=px.colors.sequential.Magenta
        )
        fig_ven.update_layout(
            margin=dict(l=20, r=20, t=10, b=10),
            height=400,
            xaxis_title="Número de Contratos",
            yaxis_title="Nome do Vendedor",
            coloraxis_showscale=False,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        fig_ven.update_xaxes(showgrid=True, gridcolor='rgba(128,128,128,0.1)')
        st.plotly_chart(fig_ven, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# TAB 3: LOCATION ANALYSIS
# ==========================================
with tab_location:
    st.subheader("Análise de Localização e Comportamento Geográfico")
    
    # Calculate cross-city buying rate
    # Where CidadeCli (client residence) is different from CidadeObra (project location)
    # Filter rows where both are informed and not 'Não Informado'
    loc_clean = filtered_df[(filtered_df['CidadeCli'] != 'Não Informado') & (filtered_df['CidadeObra'] != 'Não Informado')]
    
    cross_city = loc_clean[loc_clean['CidadeCli'] != loc_clean['CidadeObra']]
    same_city = loc_clean[loc_clean['CidadeCli'] == loc_clean['CidadeObra']]
    
    cross_rate = (len(cross_city) / len(loc_clean)) * 100 if len(loc_clean) > 0 else 0
    same_rate = 100 - cross_rate
    
    st.markdown('<div class="content-card">', unsafe_allow_html=True)
    st.markdown("#### Comportamento de Compra Intermunicipal (Onde mora vs Onde compra)")
    
    col_rate, col_chart = st.columns([1, 2])
    
    with col_rate:
        st.markdown(f"""
        <div style="padding: 20px; border-radius: 8px; border: 1px solid rgba(128,128,128,0.1); background: rgba(0,0,0,0.02); height: 100%;">
            <h5 style="margin-top:0; color:#888;">Fidelidade Geográfica</h5>
            <p style="font-size:32px; font-weight:700; color:#6366F1; margin-bottom: 2px;">{cross_rate:.1f}%</p>
            <p style="font-size:12px; color:#555; margin-bottom:15px;">Dos clientes moram em uma cidade <b>diferente</b> de onde fica o empreendimento (Compradores de fora).</p>
            <hr style="opacity: 0.1; margin: 15px 0;">
            <p style="font-size:32px; font-weight:700; color:#10B981; margin-bottom: 2px;">{same_rate:.1f}%</p>
            <p style="font-size:12px; color:#555;">Dos clientes moram na <b>mesma</b> cidade do empreendimento (Demanda local).</p>
        </div>
        """, unsafe_allow_html=True)
        
    with col_chart:
        comp_df = pd.DataFrame({
            "Tipo": ["Compradores de Outras Cidades", "Compradores Locais"],
            "Contratos": [len(cross_city), len(same_city)]
        })
        fig_comp = px.pie(
            comp_df,
            values='Contratos',
            names='Tipo',
            color='Tipo',
            color_discrete_map={"Compradores de Outras Cidades": COLOR_PRIMARY, "Compradores Locais": COLOR_TERTIARY},
            hole=0.4
        )
        fig_comp.update_traces(textinfo='percent+label', textposition='inside')
        fig_comp.update_layout(
            margin=dict(l=10, r=10, t=10, b=10),
            height=280,
            showlegend=False,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig_comp, use_container_width=True)
        
    st.markdown('</div>', unsafe_allow_html=True)
    
    col_ccli, col_cobr = st.columns(2)
    
    with col_ccli:
        st.markdown('<div class="content-card">', unsafe_allow_html=True)
        st.markdown("#### Top 15 Cidades de Residência dos Clientes")
        ccli_counts = filtered_df['CidadeCli'].value_counts().reset_index().head(15)
        ccli_counts.columns = ['Cidade', 'Vendas']
        
        fig_ccli = px.bar(
            ccli_counts,
            x='Vendas',
            y='Cidade',
            orientation='h',
            color='Vendas',
            color_continuous_scale=px.colors.sequential.Teal
        )
        fig_ccli.update_layout(
            margin=dict(l=20, r=20, t=10, b=10),
            height=400,
            xaxis_title="Número de Clientes",
            yaxis_title="Cidade de Origem",
            coloraxis_showscale=False,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        fig_ccli.update_xaxes(showgrid=True, gridcolor='rgba(128,128,128,0.1)')
        st.plotly_chart(fig_ccli, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col_cobr:
        st.markdown('<div class="content-card">', unsafe_allow_html=True)
        st.markdown("#### Top 15 Cidades de Obras (Empreendimentos)")
        cobr_counts = filtered_df['CidadeObra'].value_counts().reset_index().head(15)
        cobr_counts.columns = ['Cidade', 'Vendas']
        
        fig_cobr = px.bar(
            cobr_counts,
            x='Vendas',
            y='Cidade',
            orientation='h',
            color='Vendas',
            color_continuous_scale=px.colors.sequential.Electric
        )
        fig_cobr.update_layout(
            margin=dict(l=20, r=20, t=10, b=10),
            height=400,
            xaxis_title="Número de Empreendimentos Vendidos",
            yaxis_title="Cidade da Obra",
            coloraxis_showscale=False,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        fig_cobr.update_xaxes(showgrid=True, gridcolor='rgba(128,128,128,0.1)')
        st.plotly_chart(fig_cobr, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Neighborhood analysis section when exactly 1 city is selected
    if len(selected_cities) == 1:
        st.markdown("---")
        st.markdown(f"### 🏘️ Perfil de Bairros de Residência para o Empreendimento em {selected_cities[0]}")
        
        col_b1, col_b2 = st.columns([2, 1])
        
        # 1. Filter neighborhoods, clean them
        bairro_df = filtered_df.copy()
        # Clean nulls or placeholders
        bairro_df = bairro_df[~bairro_df['BairroCli'].isna()]
        bairro_df['BairroCli_Limpo'] = bairro_df['BairroCli'].astype(str).apply(fix_text_values).str.title().str.strip()
        bairro_df = bairro_df[~bairro_df['BairroCli_Limpo'].isin(['Não Informado', 'Nao Informado', 'Outros', 'nan'])]
        
        bairro_counts = bairro_df['BairroCli_Limpo'].value_counts().reset_index().head(15)
        bairro_counts.columns = ['Bairro', 'Clientes']
        
        with col_b1:
            st.markdown('<div class="content-card">', unsafe_allow_html=True)
            st.markdown(f"#### Top 15 Bairros dos Compradores")
            if not bairro_counts.empty:
                fig_bairro = px.bar(
                    bairro_counts,
                    x='Clientes',
                    y='Bairro',
                    orientation='h',
                    color='Clientes',
                    color_continuous_scale=px.colors.sequential.Sunsetdark
                )
                fig_bairro.update_layout(
                    margin=dict(l=20, r=20, t=10, b=10),
                    height=450,
                    xaxis_title="Número de Clientes",
                    yaxis_title="Bairro",
                    coloraxis_showscale=False,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)'
                )
                fig_bairro.update_xaxes(showgrid=True, gridcolor='rgba(128,128,128,0.1)')
                st.plotly_chart(fig_bairro, use_container_width=True)
            else:
                st.info("Nenhum dado de bairro detalhado disponível para esta seleção.")
            st.markdown('</div>', unsafe_allow_html=True)
            
        with col_b2:
            st.markdown('<div class="content-card" style="height: 100%;">', unsafe_allow_html=True)
            st.markdown("#### Detalhamento de Concentração")
            
            # Show a table with the percentages
            if not bairro_counts.empty:
                total_bairros_cados = len(bairro_df)
                bairro_counts['%'] = (bairro_counts['Clientes'] / total_bairros_cados) * 100
                bairro_counts['%'] = bairro_counts['%'].round(1).astype(str) + '%'
                
                st.write(f"Total de compradores com bairros informados: **{total_bairros_cados:,}**")
                st.dataframe(
                    bairro_counts,
                    column_config={
                        "Bairro": "Bairro de Origem",
                        "Clientes": st.column_config.NumberColumn("Qtd. Clientes", format="%d"),
                        "%": "Representatividade"
                    },
                    hide_index=True,
                    use_container_width=True
                )
                st.caption("ℹ️ Representatividade calculada com base no total de clientes PF com bairro informado para esta cidade.")
            else:
                st.info("Tabela de bairros indisponível.")
            st.markdown('</div>', unsafe_allow_html=True)
