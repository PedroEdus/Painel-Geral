"""
ETL: Extrai leads do CRM ClickMenos e faz write-truncate na tabela
buriti_marketing_silver.funil_leads no BigQuery.
"""
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import requests
from dotenv import load_dotenv
from google.cloud import bigquery
from google.oauth2 import service_account
from unidecode import unidecode

load_dotenv()

# ── Configurações ────────────────────────────────────────────────
BASE_URL   = os.environ["CLICKMENOS_BASE_URL"]
LOGIN      = os.environ["CLICKMENOS_LOGIN"]
SENHA      = os.environ["CLICKMENOS_SENHA"]

PROJECT_ID = os.getenv("BQ_PROJECT_ID", "buriti-marketing-analytics")
DATASET    = os.getenv("BQ_DATASET",    "buriti_marketing_silver")
TABELA     = os.getenv("BQ_TABELA",     "funil_leads")
BQ_KEY     = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

PAGE_SIZE   = 50
MAX_WORKERS = 15
BATCH_PAGES = 30
# ────────────────────────────────────────────────────────────────


_KEY_FALLBACK = r"C:/Users/pedro.moura/Documents/Projetos/Transf/keys-backup/Big Query Teste/keys/buriti-marketing-analytics-8466b517c505.json"

def get_bq_client() -> bigquery.Client:
    for path in [BQ_KEY, _KEY_FALLBACK]:
        if path and os.path.exists(path):
            creds = service_account.Credentials.from_service_account_file(path)
            return bigquery.Client(credentials=creds, project=PROJECT_ID)

    # Se GOOGLE_APPLICATION_CREDENTIALS aponta pra arquivo inexistente, remove antes de tentar ADC
    if os.getenv("GOOGLE_APPLICATION_CREDENTIALS") and not os.path.exists(os.environ["GOOGLE_APPLICATION_CREDENTIALS"]):
        del os.environ["GOOGLE_APPLICATION_CREDENTIALS"]

    return bigquery.Client(project=PROJECT_ID)


def login() -> dict:
    resp = requests.post(
        f"{BASE_URL}/auth/login",
        json={"Login": LOGIN, "Senha": SENHA},
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        timeout=60,
    )
    resp.raise_for_status()
    data  = resp.json()
    token = data["Token"]
    tipo  = data.get("Tipo", "Bearer")
    return {
        "Authorization": f"{tipo} {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


_CAMPOS_DICT_NOME = [
    "FormaCadastro", "Funil", "Etapa", "Status",
    "Responsavel", "OrigemContato", "FinalidadeCompra",
]

def _flatten_lead(lead: dict) -> dict:
    """Extrai .Nome de campos dict; popula Cidade a partir de Produto."""
    lead = lead.copy()

    for campo in _CAMPOS_DICT_NOME:
        val = lead.get(campo)
        if isinstance(val, dict):
            lead[campo] = val.get("Nome")

    produto = lead.get("Produto")
    if isinstance(produto, dict):
        lead["Cidade"]  = produto.get("Cidade")
        lead["Produto"] = produto.get("Nome")

    return lead


def _extrair_lista(data) -> list:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return (
            data.get("Data")
            or data.get("data")
            or data.get("Items")
            or data.get("items")
            or []
        )
    return []


def buscar_pagina(page: int, headers: dict) -> dict:
    try:
        resp = requests.get(
            f"{BASE_URL}/lead",
            headers=headers,
            params={"query.page": page, "query.pageSize": PAGE_SIZE},
            timeout=120,
        )
        if resp.status_code != 200:
            return {"page": page, "ok": False, "status": resp.status_code,
                    "leads": [], "erro": resp.text[:2000]}
        leads = _extrair_lista(resp.json())
        return {"page": page, "ok": True, "status": 200, "leads": leads, "qtd": len(leads)}
    except Exception as exc:
        return {"page": page, "ok": False, "status": None, "leads": [], "erro": str(exc)}


def processar_lote(paginas, headers: dict) -> list:
    resultados = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(buscar_pagina, p, headers): p for p in paginas}
        for future in as_completed(futures):
            res = future.result()
            resultados.append(res)
            if res["ok"]:
                print(f"  Página {res['page']} | OK | {res['qtd']} registros")
            else:
                print(f"  Página {res['page']} | ERRO | status={res['status']} | {res.get('erro','')[:120]}")
    return sorted(resultados, key=lambda x: x["page"])


def extrair_todos() -> tuple[list, list]:
    headers     = login()
    todos_leads = []
    erros       = []
    pagina      = 1

    while True:
        paginas = range(pagina, pagina + BATCH_PAGES)
        print(f"\nPáginas {pagina}–{pagina + BATCH_PAGES - 1}")

        resultados = processar_lote(paginas, headers)
        parar = False

        for res in resultados:
            if res["ok"]:
                todos_leads.extend(res["leads"])
                if len(res["leads"]) < PAGE_SIZE:
                    parar = True
            else:
                erros.append({"page": res["page"], "status": res["status"], "erro": res.get("erro")})

        print(f"Acumulado: {len(todos_leads)} leads | Erros: {len(erros)}")

        if parar:
            print("Última página detectada.")
            break

        pagina += BATCH_PAGES
        time.sleep(1)

    return todos_leads, erros


def _norm(s: pd.Series) -> pd.Series:
    return s.fillna("").astype(str).apply(lambda x: unidecode(x).upper().strip())


def _derivar_campos(df: pd.DataFrame) -> pd.DataFrame:
    df["On_Off"] = np.where(
        df["FormaCadastro"].str.contains(r"Meta|Google", case=False, na=False),
        "On",
        "Off",
    )

    etapa_n  = _norm(df.get("Etapa",  pd.Series([""] * len(df), index=df.index)))
    status_n = _norm(df.get("Status", pd.Series([""] * len(df), index=df.index)))

    conds = [
        (etapa_n == "FECHAMENTO") & (status_n == "VENDA GANHA"),
        etapa_n == "VENDA PERDIDA",
        etapa_n.isin(["FECHAMENTO", "NEGOCIACAO"]),
        status_n.str.contains(r"VISITA|AGENDAMENTO|AGENDADO", na=False),
        etapa_n == "MARKETING DIGITAL",
        etapa_n.isin(["PROSPECCAO", "QUALIFICACAO", "ATENDIMENTO"]),
        etapa_n == "ACOMPANHAMENTO",
    ]
    choices = [
        "Venda Ganha",
        "Venda Perdida",
        "Negociação",
        "Visita Agendada",
        "Aguardando Atendimento",
        "Em Atendimento",
        "Acompanhamento",
    ]
    df["Etapa_NF"] = np.select(conds, choices, default="Outros")

    return df


def preparar_df(leads: list) -> pd.DataFrame:
    df = pd.DataFrame([_flatten_lead(l) for l in leads])

    # Renomear colunas da API para os nomes esperados pelo Streamlit
    df = df.rename(columns={
        "Id":              "Codigo",
        "DataAtualizacao": "DataAlteracao",
        "TempoTotalLead":  "TempoTotal",
        "FinalidadeCompra":"Finalidade",
    })

    # Campos UTM ausentes na API — criar como nulos (Cidade vem de Produto)
    for col in ("UtmSource", "UtmCampaign", "UtmMedium"):
        if col not in df.columns:
            df[col] = None

    df = _derivar_campos(df)

    df["data_carga"] = datetime.now(tz=timezone.utc).isoformat()
    print(f"DataFrame: {df.shape[0]} linhas × {df.shape[1]} colunas")
    return df


def write_truncate_bq(df: pd.DataFrame) -> None:
    client    = get_bq_client()
    table_ref = f"{PROJECT_ID}.{DATASET}.{TABELA}"

    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        autodetect=True,
    )

    print(f"\nCarregando {len(df)} linhas em {table_ref} (WRITE_TRUNCATE)…")
    job = client.load_table_from_dataframe(df, table_ref, job_config=job_config)
    job.result()
    print(f"Carga concluída. Tabela: {table_ref}")


def main():
    print("=== ETL funil_clickmenos ===")
    leads, erros = extrair_todos()

    if erros:
        with open("erros_clickmenos.json", "w", encoding="utf-8") as f:
            json.dump(erros, f, ensure_ascii=False, indent=2)
        print(f"{len(erros)} erros salvos em erros_clickmenos.json")

    if not leads:
        print("Nenhum lead extraído. Abortando carga no BQ.")
        return

    df = preparar_df(leads)
    write_truncate_bq(df)
    print("\nETL finalizado.")


if __name__ == "__main__":
    main()
