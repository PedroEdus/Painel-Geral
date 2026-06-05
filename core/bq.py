import os
import streamlit as st
from google.cloud import bigquery
from google.oauth2 import service_account

PROJECT_ID = "buriti-marketing-analytics"
_KEY_FALLBACK = r"C:/Users/pedro.moura/Documents/Big Query Teste/keys/buriti-marketing-analytics-8466b517c505.json"

def get_client() -> bigquery.Client:
    """
    Retorna o cliente do BigQuery seguindo a ordem de prioridades:
    1. st.secrets["gcp_service_account"] (Streamlit Cloud)
    2. Variável de ambiente GOOGLE_APPLICATION_CREDENTIALS
    3. Arquivo de chave local fallback (desenvolvimento)
    """
    try:
        if "gcp_service_account" in st.secrets:
            creds = service_account.Credentials.from_service_account_info(
                st.secrets["gcp_service_account"]
            )
            return bigquery.Client(credentials=creds, project=PROJECT_ID)
    except Exception:
        pass

    if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        return bigquery.Client(project=PROJECT_ID)

    if os.path.exists(_KEY_FALLBACK):
        try:
            creds = service_account.Credentials.from_service_account_file(_KEY_FALLBACK)
            return bigquery.Client(credentials=creds, project=PROJECT_ID)
        except Exception:
            pass

    return bigquery.Client(project=PROJECT_ID)
