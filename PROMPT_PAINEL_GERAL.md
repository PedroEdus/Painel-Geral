# Prompt — Painel Geral Buriti (Streamlit multipágina)

> Cole este arquivo inteiro como prompt inicial numa sessão do Claude Code aberta em
> `C:\Users\pedro.moura\Documents\Painel Geral`. É a especificação completa para
> construir o painel unificado. Execute em fases (ver § 10).

---

## 1. Objetivo

Construir um **único app Streamlit multipágina** que consolida os 4 dashboards de
marketing que já existem, todos lendo do **BigQuery** (`buriti-marketing-analytics`),
com **design system unificado** e deploy no **Streamlit Community Cloud**.

Duas coisas são o coração do projeto:
1. Uma página **Visão Geral** que soma/compara os canais (investimento, cliques,
   impressões, leads, sessões) **e serve de porta de entrada**: a partir dela o
   usuário navega ("drill-through") para o dashboard detalhado de cada canal.
2. **Core compartilhado**: cliente BigQuery, tema e componentes ficam num módulo
   `core/` único; cada canal vira uma página "fina". Sem duplicação de tema/cliente.

Idioma da UI: **pt-BR**. Formatação de números/moeda em padrão BR (1.234,56 / R$).

---

## 2. Fontes a portar (repos já existentes, no mesmo disco)

Reaproveite a lógica destes projetos — **não reescreva do zero**, porte e unifique:

| Canal | Pasta local (origem) | Repo GitHub | O que aproveitar |
|---|---|---|---|
| Google Ads | `..\Ext Google Ads\` | `Ext-GADS-BTSA-` | `app.py`, `components.py`, `data.py` |
| GA4 | `..\Ext GA4\ga4_buriti\` | `ga4_btsa` | `app.py`, `components.py`, `data.py`, **`style.py` (tema base)** |
| Publya | `..\Publya\dashboard\` | `publya` | `app.py`, `components.py`, `data.py` |
| Meta Ads | *(clonar do GitHub¹)* | `meta_ads` | `app.py`, `components.py`, `data.py`, `style.py` — **dashboard já pronto** |

¹ A pasta local `..\Extração Face\` só tem a extração bruta antiga. O dashboard real
está no GitHub `https://github.com/PedroEdus/meta_ads` (clone temporário em
`..\_meta_clone\`). Ele já está em paridade total com os outros — abas, filtros e
métricas prontas (ver § 8). O repo ainda traz `etl/load_meta_ads_silver.py` +
GitHub Actions (`.github/workflows/etl_meta_ads.yml`) — fora do escopo do painel, mas
é o que alimenta `silver.meta_ads`.

Os **4 dashboards** já seguem o mesmo padrão modular
(`app.py` + `components.py` + `data.py` + `style.py`), mesma autenticação BQ e mesmo
visual. O `style.py` do **GA4** é o mais completo → use como base do tema unificado.

**Lógica duplicada a centralizar:** `_tipo_lancamento()` (Estoque/Lançamento/Outros) e
`_extrair_cidade_uf()` (regex `Cidade/UF` no nome da campanha) aparecem **iguais** em
Google Ads, Publya e Meta → mover para um util único `core/taxonomia.py`.

> ⚠️ Há pastas duplicadas no disco (`publya-dashboard/`, `publya-etl/`, `Painel Publya/`).
> A fonte canônica do Publya é `..\Publya\dashboard\`. Ignore as demais.

Assets de logo para copiar: `..\Ext Google Ads\assets\logo_branca.png` e `logo_preta.png`.

---

## 3. Dados — BigQuery (`buriti-marketing-analytics`)

**Autenticação** (idêntica à dos projetos atuais):
- Local: variável `GOOGLE_APPLICATION_CREDENTIALS` apontando para a service account.
  SA com leitura no projeto inteiro: `acesso-python@buriti-marketing-analytics.iam.gserviceaccount.com`
  (key em `..\Big Query Teste\keys\buriti-marketing-analytics-8466b517c505.json`).
- Cloud: `st.secrets["gcp_service_account"]`.
- O `get_client()` tenta `st.secrets` e cai para `GOOGLE_APPLICATION_CREDENTIALS`
  (envolto em try/except para não quebrar quando não há `secrets.toml`).

**Tabelas** (colunas reais conferidas no BQ):

### `buriti_marketing_silver.meta_ads` — particionada por `date_start` (DAY)
33.519 linhas · range 2024-01-01 → 2026-06-01. **Sempre filtre `date_start` no WHERE
para usar a partição.**
```
date_start DATE, date_stop DATE, account_id, account_name,
campaign_id, campaign_name, adset_id, adset_name, objective,
spend FLOAT, impressions INT, reach INT, clicks INT, inline_link_clicks INT,
cpc FLOAT, cpm FLOAT, ctr FLOAT,
action__lead, action__purchase, action__complete_registration,
action__landing_page_view, action__view_content, action__add_to_cart,
action__initiate_checkout,   (todas FLOAT)
_loaded_at TIMESTAMP, _source STRING
```

### `buriti_marketing_silver.google_ads`
```
date, customer_id, customer_name, campaign_id, campaign_name, campaign_status,
advertising_channel_type, impressions, clicks, cost, conversions,
conversions_value, _loaded_at
```
> ⚠️ **Tabela está com 0 linhas no momento** (ETL repovoa). Toda a UI precisa tratar
> DataFrame vazio sem quebrar (mensagem "Sem dados no período", não exception).
> Dedup por `date, customer_id, campaign_id` via `ROW_NUMBER() ... ORDER BY _loaded_at DESC`.

### `buriti_marketing_silver.publya_campanhas`
```
campaign_id, campaign_name, data_inicio, data_fim, budget, impressions, clicks,
reach, frequency, conversions, videoStarts, videoCompletions, audioStarts,
audioCompletions, Tipo_Midia, data_carga, origem_fonte
```
> ⚠️ **Sem granularidade diária** — só `data_inicio`/`data_fim` por campanha. Não dá
> para colocar Publya numa série temporal diária junto com os outros (ver § 6).

### `buriti_marketing_raw.ga4_overview_raw` (21,6k linhas)
```
property_id, property_name, date (STRING YYYYMMDD), sessions, totalUsers, newUsers,
engagedSessions, engagementRate, bounceRate, screenPageViews,
averageSessionDuration, _loaded_at
```
### `buriti_marketing_raw.ga4_utm_raw` (215k linhas)
```
property_id, property_name, date (STRING YYYYMMDD), landingPage, sessionSource,
sessionMedium, sessionCampaignName, sessionManualAdContent, sessions, totalUsers,
engagedSessions, screenPageViews, _loaded_at
```
> GA4 `date` é string `YYYYMMDD` → converter com `format="%Y%m%d"`. Dedup por
> `property_id, date` (overview) e pela chave UTM completa (utm).

Todas as queries em `@st.cache_data(ttl=3600)`.

---

## 4. Arquitetura alvo (monorepo nesta pasta)

```
painel-geral/
├── streamlit_app.py          # entrypoint: st.navigation + st.Page; aplica tema e logo 1x
├── core/
│   ├── __init__.py
│   ├── bq.py                 # get_client(), PROJECT_ID, constantes de dataset
│   ├── theme.py              # aplicar_tema()  (base = style.py do GA4)
│   ├── ui.py                 # exibir_logo(), kpis(), botao_download_csv(), _br()/_limpo()/_nome_curto()
│   ├── charts.py             # Plotly unificado: barras_h_card, barras_mensais, rosca, evolucao, etc.
│   └── format.py             # moeda/num BR; paleta de cores por canal (CANAL_COLORS)
├── sources/                  # 1 módulo de dados por canal (os data.py consolidados)
│   ├── google_ads.py         # carregar_google_ads()  + regex Tipo_Lancamento/Cidade/UF
│   ├── ga4.py                # carregar_overview(), carregar_utm(), classificar_canal()
│   ├── publya.py             # carregar_publya()  + métricas derivadas (CTR/CPM/CPC/VCR/ACR)
│   └── meta.py               # carregar_dados() + agregar_por_campanha() (porta do repo meta_ads)
├── pages/
│   ├── visao_geral.py        # consolidado + drill-through (página inicial)
│   ├── google_ads.py
│   ├── meta_ads.py           # portado do repo meta_ads
│   ├── ga4.py
│   └── publya.py
├── assets/                   # logo_branca.png, logo_preta.png
├── .streamlit/
│   ├── config.toml           # tema dark base do Streamlit
│   └── secrets.toml          # (GITIGNORED) [gcp_service_account]
├── requirements.txt
├── .gitignore                # keys/, *.json de credencial, secrets.toml, .venv, __pycache__
└── README.md
```

**Navegação** — use a API moderna `st.navigation` (Streamlit ≥ 1.36) no `streamlit_app.py`:
```python
import streamlit as st
from core.theme import aplicar_tema
from core.ui import exibir_logo

st.set_page_config(page_title="Painel Buriti", page_icon="📊", layout="wide")
aplicar_tema(); exibir_logo()

pg = st.navigation([
    st.Page("pages/visao_geral.py", title="Visão Geral", icon="📊", default=True),
    st.Page("pages/google_ads.py", title="Google Ads",  icon="🔍"),
    st.Page("pages/meta_ads.py",   title="Meta Ads",    icon="📱"),
    st.Page("pages/ga4.py",        title="GA4",          icon="🌐"),
    st.Page("pages/publya.py",     title="Publya",       icon="📺"),
])
pg.run()
```
Drill-through na Visão Geral com `st.page_link("pages/google_ads.py", ...)` (ou
`st.switch_page` em botões).

---

## 5. Design system (tema unificado)

Portar de `..\Ext GA4\ga4_buriti\style.py` para `core/theme.py`. Manter:
- Fontes: **Manrope** (texto) + **JetBrains Mono** (números/KPIs), via Google Fonts.
- Fundo escuro; cards de métrica `#1c1c1c`, raio 8px; sidebar `#1c1c1c`.
- Verde Buriti **`#008140`** como cor de destaque (abas ativas, realces).
- KPIs com `JetBrains Mono`, `tabular-nums`.
- Resolver o drift: Google Ads usa `injetar_css_global()` e GA4/Publya usam
  `aplicar_tema()` → **uma função só** (`aplicar_tema()`) aplicada 1x no entrypoint.
- `core/format.py` define `CANAL_COLORS` (cor fixa por canal: Google Ads, Meta, Publya,
  GA4) usada em todos os gráficos comparativos para consistência.

---

## 6. Página **Visão Geral** (a nova — principal entrega)

Filtro de período global no topo (date_input), aplicado a todas as fontes (cada uma
com sua coluna de data). Estrutura:

**(a) Linha de KPIs consolidados** — soma cross-channel no período:

| KPI | Google Ads | Meta | Publya | GA4 |
|---|---|---|---|---|
| Investimento (R$) | `cost` | `spend` | `budget` | — |
| Impressões | `impressions` | `impressions` | `impressions` | — |
| Cliques | `clicks` | `clicks` | `clicks` | — |
| Alcance | — | `reach` | `reach` | — |
| Leads/Conversões | `conversions` | `action__lead` | `conversions` | — |
| Sessões | — | — | — | `sessions` |
| Usuários | — | — | — | `totalUsers` |

Derivadas cross-channel: **CTR** = cliques/impressões · **CPC** = invest/cliques ·
**CPM** = invest/impressões×1000 · **CPL** = invest/leads.

**(b) Comparativo por canal** (totais do período):
- Donut/barras "Investimento por canal" (cores de `CANAL_COLORS`).
- Barras "Cliques por canal" e "Impressões por canal".
- Tabela comparativa: 1 linha por canal × (invest, impressões, cliques, CTR, CPC, leads, CPL).

**(c) Série temporal de investimento** — empilhada por canal:
- Diária/mensal somando **Google Ads (`date`) + Meta (`date_start`)** (ambos diários).
- **Publya NÃO entra na série diária** (só tem range de campanha). Mostrar Publya
  apenas nos totais/comparativo (b) e numa nota. *(Opcional, fase posterior:
  distribuir `budget` uniformemente entre `data_inicio`→`data_fim` para incluí-lo.)*
- GA4 numa série separada de sessões (não é investimento).

**(d) Drill-through** — cartões/links no fim da página, um por canal, levando à página
detalhada (`st.page_link`). Cada cartão mostra o KPI-chave do canal (ex.: invest Meta,
sessões GA4).

Sempre tratar fontes vazias (ex.: google_ads = 0 linhas hoje) sem quebrar o consolidado.

---

## 7. Páginas por canal (portar + afinar ao core)

Cada página = a lógica atual do `app.py` correspondente, mas usando `core/*` e
`sources/*` (sem tema/cliente próprios). Manter o que já existe:

- **Google Ads** — abas: 💰 Valor Gasto · 🖱️ Cliques · 💵 CPC · 📋 Tabela.
  Filtros: período, tipo (Estoque/Lançamento/Outros), conta, UF, cidade (cascata).
  Manter regex de `Tipo_Lancamento` e extração `Cidade/UF` em `sources/google_ads.py`.
- **GA4** — abas: 🏛️ Institucionais · 🏢 Empreendimentos · 🔗 UTM/Canais ·
  🏠 Landing Pages · 📋 Tabela. Manter separação institucional×empreendimento,
  `classificar_canal()` e limpeza de ruído (`(not set)` etc.).
- **Publya** — abas: 📢 Impressões · 🖱️ Cliques · 💰 Valores · 📋 Tabela.
  Manter métricas derivadas (CTR, CPM, CPC, VCR, ACR) e agregação por
  `campaign_name`+`Tipo_Midia`.

---

## 8. Página **Meta Ads** (PORTAR do repo `meta_ads` — já está pronta)

**Não reescrever** — o dashboard do repo `meta_ads` já está completo. Porte `app.py`,
`components.py`, `data.py`, `style.py` para a estrutura do painel (usando `core/*`).

`sources/meta.py` (porta de `data.py`): `carregar_dados()` lê `silver.meta_ads`,
converte `date_start` para date, soma todas as `action__*` em `conversions`, aplica
`Tipo_Lancamento` e `Cidade/UF` (regex — agora em `core/taxonomia.py`).
`agregar_por_campanha(df)` agrupa por `campaign_name` + `objective` +
`Tipo_Lancamento` + `Cidade/UF` e deriva **CTR**, **CPM** e **CPL** (= `spend`/`action__lead`).

Layout atual a preservar:
- **Filtros**: período (`date_start`), Tipo (Estoque/Lançamento), UF, Cidade,
  objetivo (`objective`), campanhas.
- **KPIs**: Investimento (`spend`), Impressões, Alcance, Cliques, Leads, CTR, CPM, CPL.
- **Abas**: 📢 Impressões · 🖱️ Cliques · 💰 Investimento · 🎯 Leads · 📋 Tabela.
  - Cada aba de métrica tem o gráfico principal + quebra por **objetivo** e por **tipo**.
  - 🎯 **Leads** usa `action__lead` + gráfico de **CPL** — diferencial do Meta (detalhe
    de ações que os outros canais não têm: `action__purchase`,
    `action__complete_registration`, `landing_page_view`, etc.).
  - 📋 **Tabela**: resumo por objetivo + detalhe por campanha + export CSV.
- `components.py` do Meta tem gráficos específicos (`grafico_cpl`, `grafico_objetivo`,
  `grafico_leads`, `grafico_tipo_lancamento`) → mover para `core/charts.py` ou manter
  como helpers da página.

---

## 9. Convenções e qualidade

- `@st.cache_data(ttl=3600)` em toda query.
- Formatação BR central em `core/format.py` (`_br()` para milhar, moeda R$).
- Export CSV em toda aba "Tabela" (`utf-8-sig`, separador `;`, decimal `,`).
- `exibir_logo()` lê de `assets/` (base64), igual ao atual.
- **Nunca commitar credenciais**: `.gitignore` deve cobrir `secrets.toml`, `keys/`,
  `*sa*.json`, `*credential*.json`, `.venv/`, `__pycache__/`. Conferir antes do 1º commit.
- `requirements.txt`: `streamlit>=1.36`, `pandas`, `google-cloud-bigquery`, `db-dtypes`,
  `plotly`, `python-dotenv`.
- `.streamlit/config.toml`: `[theme] base="dark"` + cor primária `#008140`.
- README com: como rodar local (`GOOGLE_APPLICATION_CREDENTIALS` + `streamlit run streamlit_app.py`)
  e como configurar `secrets.toml` no Cloud.

---

## 10. Plano de execução (fases)

1. **Scaffold** — estrutura de pastas, `requirements.txt`, `.gitignore`, `config.toml`,
   copiar logos para `assets/`, `streamlit_app.py` com `st.navigation`.
2. **Core** — `core/bq.py`, `core/theme.py` (do GA4), `core/format.py`, `core/ui.py`,
   `core/charts.py` (consolidando os 4 `components.py`).
3. **Sources** — `sources/{google_ads,ga4,publya,meta}.py` a partir dos `data.py` atuais
   (Meta vem do repo `meta_ads` clonado). Extrair o regex comum para `core/taxonomia.py`.
4. **Páginas de canal** — portar os **4** dashboards (Google Ads, GA4, Publya, Meta).
   Validar cada uma isolada antes de seguir.
5. **Visão Geral** — KPIs consolidados, comparativos, série temporal, drill-through.
6. **Polimento** — estados vazios (google_ads 0 linhas), responsividade, README,
   conferir `.gitignore`, primeiro commit.

Valide rodando `streamlit run streamlit_app.py` ao fim de cada fase com dados reais
(período recente). Lembre: `google_ads` pode estar vazia — use Meta/GA4/Publya para
validar o consolidado enquanto isso.
