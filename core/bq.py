import glob
import os
import streamlit as st
from google.cloud import bigquery
from google.oauth2 import service_account

PROJECT_ID = "buriti-marketing-analytics"

# Pasta keys/ na raiz do projeto (gitignored). Qualquer .json de chave de
# serviço colocado aí é detectado automaticamente em desenvolvimento local.
_KEYS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "keys")


def _chave_local() -> str | None:
    """Primeiro .json encontrado em keys/ (ordem alfabética). None se vazia."""
    if not os.path.isdir(_KEYS_DIR):
        return None
    arquivos = sorted(glob.glob(os.path.join(_KEYS_DIR, "*.json")))
    return arquivos[0] if arquivos else None


def get_client() -> bigquery.Client:
    """
    Retorna o cliente do BigQuery seguindo a ordem de prioridades:
    1. st.secrets["gcp_service_account"] (Streamlit Cloud)
    2. Chave de serviço .json em keys/ (desenvolvimento local)
    3. Variável de ambiente GOOGLE_APPLICATION_CREDENTIALS / ADC
    """
    try:
        if "gcp_service_account" in st.secrets:
            creds = service_account.Credentials.from_service_account_info(
                st.secrets["gcp_service_account"]
            )
            return bigquery.Client(credentials=creds, project=PROJECT_ID)
    except Exception:
        pass

    chave = _chave_local()
    if chave:
        try:
            creds = service_account.Credentials.from_service_account_file(chave)
            return bigquery.Client(credentials=creds, project=PROJECT_ID)
        except Exception:
            pass

    if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        return bigquery.Client(project=PROJECT_ID)

    return bigquery.Client(project=PROJECT_ID)
