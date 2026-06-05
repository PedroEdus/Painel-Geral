import pandas as pd
import streamlit as st
from core.bq import get_client, PROJECT_ID

DATASET = "buriti_marketing_silver"
TABELA  = "dados_clientes_mkt"

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
        
    val = val.replace('\ufffd', 'a')
    return val

@st.cache_data(ttl=3600)
def carregar_clientes() -> pd.DataFrame:
    """Carrega e limpa os dados demográficos de clientes do BigQuery."""
    client = get_client()
    query = f"SELECT * FROM `{PROJECT_ID}.{DATASET}.{TABELA}`"
    
    try:
        df = client.query(query).to_dataframe()
    except Exception as e:
        st.warning(f"Erro ao carregar dados de clientes do BigQuery: {e}")
        return pd.DataFrame()
        
    if df.empty:
        return df

    # Standardize string values
    string_cols = ['sexo', 'faixa_etaria', 'estado_civil', 'grau_instrucao', 'divulgacao', 'finalidade', 'cidade_cli', 'cidade_obra', 'bairro_cli', 'profissao_cliente']
    for col in string_cols:
        if col in df.columns:
            df[col] = df[col].fillna('Não Informado').astype(str).apply(fix_text_values)

    # Normalize gender
    if 'sexo' in df.columns:
        df['sexo'] = df['sexo'].str.replace('Sexo Masculino', 'Masculino', regex=False)
        df['sexo'] = df['sexo'].str.replace('Sexo Feminino', 'Feminino', regex=False)
        # Filter to individual clients (Pessoa Física) as per the original dashboard
        df = df[df['sexo'].isin(['Masculino', 'Feminino'])]

    # Standardize casing
    if 'cidade_cli' in df.columns:
        df['cidade_cli'] = df['cidade_cli'].str.title().str.strip()
    if 'cidade_obra' in df.columns:
        df['cidade_obra'] = df['cidade_obra'].str.title().str.strip()
    if 'nome_ven' in df.columns:
        df['nome_ven'] = df['nome_ven'].fillna('Não Informado').astype(str).str.title().str.strip()

    # Clean age (filter realistic human range 18-100)
    if 'idade' in df.columns:
        df['idade_limpa'] = pd.to_numeric(df['idade'], errors='coerce')
        # Filter ages: set out-of-range or PJ to NaN
        df.loc[(df['sexo'] == 'Pessoa Jurídica') | (df['idade_limpa'] < 18) | (df['idade_limpa'] > 100), 'idade_limpa'] = pd.NA

    # Month translation mapping
    month_translation = {
        1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
        7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
    }
    if 'mes_venda' in df.columns:
        df['nome_mes_venda'] = df['mes_venda'].map(month_translation)

    return df
