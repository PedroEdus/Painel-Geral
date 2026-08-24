"""
ETL: Extrai relatório de leituras (scans) da QRFY (GET /qrs/report, type=detailed)
e grava em buriti_marketing_silver.qrfy_scans no BigQuery.

Schema da resposta do /qrs/report NÃO está documentado oficialmente (a referência
em `QR Code/qrfyapireference.md` só lista os query params, sem exemplo de body).
Por isso: rode primeiro com --sample pra inspecionar o JSON real antes de confiar
no watermark incremental. Ver seção "Notas & inconsistências" da doc.
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta, date

import pandas as pd
import requests
from dotenv import load_dotenv
from google.cloud import bigquery
from google.oauth2 import service_account

load_dotenv()

# ── Configurações ────────────────────────────────────────────────
BASE_URL = os.getenv("QRFY_BASE_URL", "https://qrfy.com/api/public")

PROJECT_ID = os.getenv("BQ_PROJECT_ID",   "buriti-marketing-analytics")
DATASET    = os.getenv("BQ_DATASET",      "buriti_marketing_silver")
TABELA     = os.getenv("QRFY_BQ_TABELA",  "qrfy_scans")
BQ_KEY     = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

# Coluna de data candidata pra watermark — ajustar depois de ver o JSON real (--sample).
DATE_COL_CANDIDATOS = ["date", "scanDate", "createdAt", "created_at", "timestamp", "scannedAt"]

MAX_RETRIES   = 4
RETRY_BACKOFF = 3  # segundos × tentativa
# ────────────────────────────────────────────────────────────────

_KEY_FALLBACK = r"C:/Users/pedro.moura/Documents/Projetos/Transf/keys-backup/Big Query Teste/keys/buriti-marketing-analytics-8466b517c505.json"


def get_bq_client() -> bigquery.Client:
    for path in [BQ_KEY, _KEY_FALLBACK]:
        if path and os.path.exists(path):
            creds = service_account.Credentials.from_service_account_file(path)
            return bigquery.Client(credentials=creds, project=PROJECT_ID)
    if os.getenv("GOOGLE_APPLICATION_CREDENTIALS") and not os.path.exists(os.environ["GOOGLE_APPLICATION_CREDENTIALS"]):
        del os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
    return bigquery.Client(project=PROJECT_ID)


def get_api_key() -> str:
    """API-KEY estática da QRFY. Aceita o valor direto (QRFY_API_KEY) ou um
    arquivo contendo a chave (QRFY_API_KEY_FILE) — mesmo padrão do
    GOOGLE_APPLICATION_CREDENTIALS, útil pra guardar a chave fora do repo."""
    key = os.getenv("QRFY_API_KEY")
    if key:
        return key.strip()

    path = os.getenv("QRFY_API_KEY_FILE")
    if path and os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()

    raise RuntimeError(
        "API key da QRFY não encontrada. Defina QRFY_API_KEY (valor direto) "
        "ou QRFY_API_KEY_FILE (caminho pro arquivo com a chave)."
    )


def _to_unix(d: str) -> int:
    """Aceita 'YYYY-MM-DD' e devolve unix timestamp (UTC, meia-noite)."""
    return int(datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())


def buscar_report(desde_unix: int, ate_unix: int, api_key: str, tipo: str = "detailed"):
    """Chama GET /qrs/report com retry + backoff."""
    params = {"from": desde_unix, "to": ate_unix, "format": "json", "type": tipo}
    headers = {"API-KEY": api_key, "Accept": "application/json"}

    ultimo_erro = None
    for tentativa in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(f"{BASE_URL}/qrs/report", headers=headers, params=params, timeout=120)
            if resp.status_code == 200:
                return resp.json()
            ultimo_erro = f"status={resp.status_code} {resp.text[:300]}"
        except Exception as exc:
            ultimo_erro = str(exc)

        if tentativa < MAX_RETRIES:
            espera = RETRY_BACKOFF * tentativa
            print(f"  Tentativa {tentativa} falhou ({ultimo_erro[:150]}) | retry em {espera}s")
            time.sleep(espera)

    raise RuntimeError(f"GET /qrs/report falhou após {MAX_RETRIES} tentativas: {ultimo_erro}")


def _extrair_lista(data) -> list:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("data") or data.get("Data") or data.get("items") or data.get("Items") or []
    return []


def get_watermark(client: bigquery.Client) -> tuple[str | None, str | None]:
    """Retorna (coluna_usada, valor_max) testando as colunas candidatas na tabela existente."""
    table_ref = f"{PROJECT_ID}.{DATASET}.{TABELA}"
    try:
        table = client.get_table(table_ref)
    except Exception as exc:
        print(f"Tabela {table_ref} ainda não existe ({str(exc)[:100]}). Sem watermark.")
        return None, None

    cols_existentes = {f.name for f in table.schema}
    for col in DATE_COL_CANDIDATOS:
        if col in cols_existentes:
            rows = list(client.query(f"SELECT MAX(`{col}`) AS m FROM `{table_ref}`").result())
            m = rows[0].m if rows else None
            if m is not None:
                return col, str(m)
    print(f"Nenhuma das colunas candidatas {DATE_COL_CANDIDATOS} encontrada em {table_ref}.")
    return None, None


def append_bq(df: pd.DataFrame) -> None:
    client = get_bq_client()
    table_ref = f"{PROJECT_ID}.{DATASET}.{TABELA}"
    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        autodetect=True,
    )
    print(f"\nAnexando {len(df)} linhas em {table_ref} (WRITE_APPEND)…")
    job = client.load_table_from_dataframe(df, table_ref, job_config=job_config)
    job.result()
    print(f"Carga concluída. Tabela: {table_ref}")


def main():
    ap = argparse.ArgumentParser(description="ETL relatório de scans QRFY → BigQuery")
    ap.add_argument("--sample", action="store_true",
                     help="Só busca uma janela pequena e imprime/salva o JSON crú (não grava no BQ)")
    ap.add_argument("--from-date", dest="from_date", help="YYYY-MM-DD (default = watermark ou ontem)")
    ap.add_argument("--to-date", dest="to_date", help="YYYY-MM-DD (default = hoje)")
    ap.add_argument("--dry-run", action="store_true", help="Extrai e mostra o DataFrame, mas não grava no BQ")
    args = ap.parse_args()

    print("=== ETL qrfy_relatorio ===")
    api_key = get_api_key()

    hoje = date.today()
    ate = args.to_date or hoje.isoformat()

    if args.sample:
        desde = args.from_date or (hoje - timedelta(days=2)).isoformat()
        print(f"[sample] Janela {desde} → {ate} (type=detailed)")
        raw = buscar_report(_to_unix(desde), _to_unix(ate), api_key)
        out = "qrfy_sample.json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump(raw, f, ensure_ascii=False, indent=2)
        registros = _extrair_lista(raw)
        print(f"Registros: {len(registros)}. JSON salvo em {out}.")
        if registros:
            print("Campos do primeiro registro:", sorted(registros[0].keys()))
        return

    if args.from_date:
        desde = args.from_date
        print(f"Janela manual: {desde}")
    else:
        col, valor = get_watermark(get_bq_client())
        if valor is None:
            desde = (hoje - timedelta(days=1)).isoformat()
            print(f"Sem watermark; fallback ontem: {desde}")
        else:
            desde = valor[:10]  # assume ISO/data — ajustar se formato real for outro
            print(f"Watermark ({col}): {valor} → desde={desde}")

    raw = buscar_report(_to_unix(desde), _to_unix(ate), api_key)
    registros = _extrair_lista(raw)
    print(f"Registros extraídos: {len(registros)} ({desde} → {ate})")

    if not registros:
        print("Nada novo no período. Nada a gravar.")
        return

    df = pd.json_normalize(registros)
    df["data_carga"] = datetime.now(tz=timezone.utc).isoformat()
    antes = len(df)
    df = df.drop_duplicates().reset_index(drop=True)
    if antes != len(df):
        print(f"Dedup exato: {antes} -> {len(df)} linhas")

    if args.dry_run:
        print(f"[dry-run] {len(df)} linhas — sem gravação.")
        print(df.head(5).to_string(index=False))
        return

    append_bq(df)
    print("\nETL finalizado.")


if __name__ == "__main__":
    main()
