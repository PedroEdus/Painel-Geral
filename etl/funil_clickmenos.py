"""
ETL: Extrai leads do CRM ClickMenos e faz write-truncate na tabela
buriti_marketing_silver.funil_leads no BigQuery.
"""
import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta, date

import re
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

PAGE_SIZE     = 50
MAX_RETRIES   = 4      # tentativas por página antes de abortar
RETRY_BACKOFF = 3      # segundos × tentativa (3, 6, 9…)
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

def _safe_nome(val) -> str | None:
    """Extrai .Nome de dict com segurança; retorna None se inválido."""
    if isinstance(val, dict):
        nome = val.get("Nome")
        return str(nome).strip() if nome is not None else None
    if isinstance(val, str):
        v = val.strip()
        return v if v else None
    return None


def _flatten_lead(lead: dict) -> dict:
    lead = lead.copy()

    # Campos simples: extrai .Nome do dict
    for campo in _CAMPOS_DICT_NOME:
        lead[campo] = _safe_nome(lead.get(campo))

    # Produto: extrai Cidade e Nome separadamente
    produto = lead.get("Produto")
    if isinstance(produto, dict):
        lead["Cidade"]  = _safe_nome(produto.get("Cidade") or produto.get("cidade"))
        if lead["Cidade"] is None:
            # fallback: campo Cidade pode ser string direto
            lead["Cidade"] = str(produto.get("Cidade", "")).strip() or None
        lead["Produto"] = _safe_nome(produto.get("Nome"))
    else:
        lead.setdefault("Cidade", None)

    # TempoTotalLead: converte para horas (ignora datas tipo '13/04/2026')
    tempo = lead.get("TempoTotalLead")
    lead["TempoTotalLead"] = None
    if tempo is not None:
        s = str(tempo).strip()
        m = re.search(r"^(\d+)\s*(Dia|Hora|Minuto)", s, re.IGNORECASE)
        if m:
            n, unit = int(m.group(1)), m.group(2).lower()
            if unit.startswith("dia"):
                lead["TempoTotalLead"] = n * 24
            elif unit.startswith("hora"):
                lead["TempoTotalLead"] = n
            elif unit.startswith("minuto"):
                lead["TempoTotalLead"] = round(n / 60, 2)

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


def buscar_pagina(page: int, headers: dict, extra_params: dict | None = None) -> dict:
    """Busca uma página com retry + backoff. Volume pequeno → sequencial, sem workers."""
    params = {"query.page": page, "query.pageSize": PAGE_SIZE}
    if extra_params:
        params.update(extra_params)  # ex.: query.dataModificacaoInicio/Fim

    ultimo_erro = None
    for tentativa in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(f"{BASE_URL}/lead", headers=headers, params=params, timeout=120)
            if resp.status_code == 200:
                leads = _extrair_lista(resp.json())
                return {"page": page, "ok": True, "status": 200, "leads": leads, "qtd": len(leads)}
            ultimo_erro = f"status={resp.status_code} {resp.text[:300]}"
        except Exception as exc:
            ultimo_erro = str(exc)

        if tentativa < MAX_RETRIES:
            espera = RETRY_BACKOFF * tentativa
            print(f"  Página {page} | tentativa {tentativa} falhou ({ultimo_erro[:120]}) | retry em {espera}s")
            time.sleep(espera)

    return {"page": page, "ok": False, "status": None, "leads": [], "erro": ultimo_erro}


def extrair_todos(extra_params: dict | None = None) -> tuple[list, list]:
    """Pagina sequencialmente até a última página (página < PAGE_SIZE).
    Falha de página esgota retries → aborta sem mascarar (evita gap silencioso)."""
    headers     = login()
    todos_leads = []
    erros       = []
    pagina      = 1

    while True:
        res = buscar_pagina(pagina, headers, extra_params)
        if not res["ok"]:
            erros.append({"page": pagina, "status": res["status"], "erro": res.get("erro")})
            print(f"Página {pagina} | ERRO definitivo | {str(res.get('erro',''))[:160]}")
            break

        leads = res["leads"]
        todos_leads.extend(leads)
        print(f"Página {pagina} | OK | {len(leads)} registros | acumulado {len(todos_leads)}")

        if len(leads) < PAGE_SIZE:
            print("Última página detectada.")
            break
        pagina += 1

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
        ((etapa_n == "FECHAMENTO") & (status_n == "VENDA GANHA")) | (etapa_n == "VENDA GANHA"),
        etapa_n == "VENDA PERDIDA",
        etapa_n.isin(["FECHAMENTO", "NEGOCIACAO", "POS - ATENDIMENTO", "PASTA COMPLETA"]),
        status_n.str.contains(r"VISITA|AGENDAMENTO|AGENDADO", na=False)
        | etapa_n.str.contains(r"AGENDAMENTO", na=False),
        etapa_n == "AGUARDANDO ATENDIMENTO SDR",
        etapa_n.isin(["EM ATENDIMENTO COM SDR", "ATENDIMENTO SDR"]),
        etapa_n == "PROSPECT",
        etapa_n.isin(["ACOMPANHAMENTO", "NUTRICAO", "REMARKETING"]),
        etapa_n.isin(["PROSPECCAO", "ATENDIMENTO", "EM ATENDIMENTO", "QUALIFICACAO",
                      "MARKETING DIGITAL", "LEAD", "PARA ATENDIMENTO DO CORRETOR"]),
    ]
    choices = [
        "Venda Ganha",
        "Venda Perdida",
        "Negociação",
        "Visita Agendada",
        "Aguardando atendimento SDR",
        "Em atendimento com SDR",
        "Aguardando contato do corretor",
        "Acompanhamento",
        "Em atendimento com corretor",
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


def get_watermark(client: bigquery.Client) -> str | None:
    """Maior DataAlteracao já carregada (ISO 8601 ordena lexicograficamente).
    Lido ANTES da extração → se uma run falhou, a próxima recupera o gap."""
    table_ref = f"{PROJECT_ID}.{DATASET}.{TABELA}"
    try:
        rows = list(client.query(f"SELECT MAX(DataAlteracao) AS m FROM `{table_ref}`").result())
    except Exception as exc:
        print(f"Sem watermark ({str(exc)[:120]}). Usando fallback.")
        return None
    m = rows[0].m if rows else None
    return str(m) if m is not None else None


def dedup_recente(df: pd.DataFrame) -> pd.DataFrame:
    """Remove duplicatas por Codigo, mantendo a DataAlteracao mais recente.
    Obrigatório antes do MERGE (BigQuery exige ≤1 linha-fonte por chave)."""
    if df.empty or "Codigo" not in df.columns:
        return df
    if "DataAlteracao" in df.columns:
        df = df.sort_values("DataAlteracao")  # ISO asc → a mais nova fica por último
    antes = len(df)
    df = df.drop_duplicates("Codigo", keep="last").reset_index(drop=True)
    if antes != len(df):
        print(f"Dedup: {antes} -> {len(df)} linhas (Codigo unico, alteracao mais recente)")
    return df


def _merge_sql(df: pd.DataFrame, staging: str, target: str) -> str:
    """MERGE (upsert) por Codigo. Só atualiza se a fonte for mais recente
    (mantém a cópia com DataAlteracao mais nova mesmo em reprocessamento)."""
    cols = list(df.columns)
    if "Codigo" not in cols:
        raise ValueError("Coluna 'Codigo' ausente — necessária como chave do MERGE.")
    set_clause = ", ".join(f"T.`{c}` = S.`{c}`" for c in cols if c != "Codigo")
    ins_cols   = ", ".join(f"`{c}`" for c in cols)
    ins_vals   = ", ".join(f"S.`{c}`" for c in cols)
    guard = ""
    if "DataAlteracao" in cols:
        guard = " AND (T.DataAlteracao IS NULL OR S.DataAlteracao > T.DataAlteracao)"
    return (
        f"MERGE `{target}` T USING `{staging}` S ON T.Codigo = S.Codigo\n"
        f"WHEN MATCHED{guard} THEN UPDATE SET {set_clause}\n"
        f"WHEN NOT MATCHED THEN INSERT ({ins_cols}) VALUES ({ins_vals})"
    )


def upsert_bq(df: pd.DataFrame) -> None:
    """Carga incremental: stage do delta + MERGE por Codigo na tabela final.
    # ponytail: staging autodetect; se uma coluna do delta vier 100% nula o
    # tipo pode divergir do target e o MERGE falha. Se acontecer, fixar schema
    # explícito no LoadJobConfig em vez de autodetect."""
    df = dedup_recente(df)  # garante ≤1 linha-fonte por Codigo (exigência do MERGE)
    client  = get_bq_client()
    target  = f"{PROJECT_ID}.{DATASET}.{TABELA}"
    staging = f"{PROJECT_ID}.{DATASET}.{TABELA}_staging"

    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        autodetect=True,
    )
    print(f"\nStaging {len(df)} linhas em {staging}…")
    client.load_table_from_dataframe(df, staging, job_config=job_config).result()

    sql = _merge_sql(df, staging, target)
    print(f"MERGE em {target}…")
    job = client.query(sql)
    job.result()
    print(f"Upsert concluído. Linhas afetadas: {job.num_dml_affected_rows}")


def _tratar_erros(erros: list) -> None:
    """Em erro de extração: salva detalhe e ABORTA sem gravar.
    Watermark fica intacto → a próxima run recupera o período (cobre falhas)."""
    if not erros:
        return
    with open("erros_clickmenos.json", "w", encoding="utf-8") as f:
        json.dump(erros, f, ensure_ascii=False, indent=2)
    print(f"{len(erros)} erro(s) salvos em erros_clickmenos.json. "
          f"Abortando sem gravar (watermark preservado).")
    sys.exit(1)


def main():
    import argparse
    ap = argparse.ArgumentParser(description="ETL leads ClickMenos → BigQuery")
    ap.add_argument("--full", action="store_true",
                    help="Recarga completa (WRITE_TRUNCATE) — ignora watermark")
    ap.add_argument("--since",
                    help="Override do dataModificacaoInicio (ISO). Default = MAX(DataAlteracao) do BQ")
    ap.add_argument("--until", help="dataModificacaoFim (ISO)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Extrai e mostra params/SQL, mas não grava no BQ")
    args = ap.parse_args()

    print("=== ETL funil_clickmenos ===")

    # ── Modo FULL: recarga completa ──────────────────────────────
    if args.full:
        print("Modo FULL — recarga completa (WRITE_TRUNCATE).")
        leads, erros = extrair_todos(None)
        _tratar_erros(erros)
        if not leads:
            print("Nenhum lead extraído. Abortando.")
            return
        df = preparar_df(leads)
        if args.dry_run:
            print(f"[dry-run] {len(df)} leads (full) — sem gravação.")
            return
        write_truncate_bq(df)
        print("\nETL finalizado.")
        return

    # ── Modo INCREMENTAL (default): watermark = MAX(DataAlteracao) ─
    if args.since:
        since = args.since
        print(f"Incremental — since (manual): {since}")
    else:
        since = get_watermark(get_bq_client())
        if since is None:
            since = (date.today() - timedelta(days=1)).isoformat()
            print(f"Incremental — sem watermark; fallback ontem: {since}")
        else:
            print(f"Incremental — watermark MAX(DataAlteracao): {since}")

    extra = {"query.dataModificacaoInicio": since}
    if args.until:
        extra["query.dataModificacaoFim"] = args.until

    leads, erros = extrair_todos(extra)
    _tratar_erros(erros)

    if not leads:
        print("Nenhum lead novo/alterado no período. Nada a gravar.")
        return

    df = dedup_recente(preparar_df(leads))

    if args.dry_run:
        print(f"[dry-run] {len(df)} leads (pós-dedup) — sem gravação.")
        staging = f"{PROJECT_ID}.{DATASET}.{TABELA}_staging"
        target  = f"{PROJECT_ID}.{DATASET}.{TABELA}"
        print("\n" + _merge_sql(df, staging, target))
        return

    upsert_bq(df)
    print("\nETL finalizado.")


if __name__ == "__main__":
    main()
