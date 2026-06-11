"""
Extrai tabela meta_ads do BigQuery para DataFrame (e CSV opcional).
Uso:
    python etl/extrair_meta_ads.py                  # imprime shape + head
    python etl/extrair_meta_ads.py --csv            # salva meta_ads.csv
    python etl/extrair_meta_ads.py --desde 2025-01-01
"""
import argparse
import os
import sys

import pandas as pd
from dotenv import load_dotenv
from google.cloud import bigquery
from google.oauth2 import service_account

load_dotenv()

PROJECT_ID = os.getenv("BQ_PROJECT_ID", "buriti-marketing-analytics")
DATASET    = "buriti_marketing_silver"
TABELA     = "meta_ads"
_KEY_FALLBACK = r"C:/Users/pedro.moura/Documents/Projetos/Transf/keys-backup/Big Query Teste/keys/buriti-marketing-analytics-8466b517c505.json"


def get_bq_client() -> bigquery.Client:
    key = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    for path in [key, _KEY_FALLBACK]:
        if path and os.path.exists(path):
            creds = service_account.Credentials.from_service_account_file(path)
            return bigquery.Client(credentials=creds, project=PROJECT_ID)
    return bigquery.Client(project=PROJECT_ID)


def extrair(desde: str = "2024-01-01") -> pd.DataFrame:
    client = get_bq_client()
    query = f"""
        SELECT *
        FROM `{PROJECT_ID}.{DATASET}.{TABELA}`
        WHERE date_start >= '{desde}'
        ORDER BY date_start DESC
    """
    print(f"Consultando {PROJECT_ID}.{DATASET}.{TABELA} (desde {desde})…")
    df = client.query(query).to_dataframe()
    print(f"Retornado: {df.shape[0]:,} linhas × {df.shape[1]} colunas")
    return df


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv",    action="store_true", help="Salva meta_ads.csv")
    parser.add_argument("--desde",  default="2024-01-01", help="Data inicial (YYYY-MM-DD)")
    args = parser.parse_args()

    df = extrair(desde=args.desde)

    print("\nPrimeiras linhas:")
    print(df.head(10).to_string(index=False))

    if args.csv:
        out = "meta_ads.csv"
        df.to_csv(out, index=False, encoding="utf-8-sig")
        print(f"\nCSV salvo: {out}")

    return df


if __name__ == "__main__":
    main()
