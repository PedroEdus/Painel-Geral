# Painel Geral Buriti — Dashboards de Marketing Consolidados

Este projeto unifica e consolida os 4 dashboards de marketing (Google Ads, Meta Ads, GA4 e Publya) em uma única aplicação **Streamlit multipágina**, estruturada sob um design system e módulo central compartilhados.

## 🚀 Como Executar Localmente

### 1. Pré-requisitos
Certifique-se de ter o Python instalado (3.9+ recomendado) e as dependências descritas no `requirements.txt`. Instale-as via terminal:

```bash
pip install -r requirements.txt
```

### 2. Autenticação com o BigQuery (GCP)
A conexão com o BigQuery (`buriti-marketing-analytics`) tenta autenticar na seguinte ordem de prioridade:

#### Opção A (Produção / Streamlit Cloud)
Configurando o segredo no Streamlit Cloud com o nome `gcp_service_account` contendo as chaves do JSON de serviço. Localmente, você pode simular criando um arquivo `.streamlit/secrets.toml` (este arquivo está no `.gitignore`):

```toml
[gcp_service_account]
type = "service_account"
project_id = "buriti-marketing-analytics"
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "acesso-python@buriti-marketing-analytics.iam.gserviceaccount.com"
# ... restante das chaves do JSON de serviço
```

#### Opção B (Local — Variável de Ambiente)
Configurando a variável de ambiente `GOOGLE_APPLICATION_CREDENTIALS` no seu terminal ou arquivo `.env` local:

```bash
# Windows (PowerShell)
$env:GOOGLE_APPLICATION_CREDENTIALS="C:\Caminho\Para\Sua\chave.json"
```

#### Opção C (Local — Fallback Fixo)
O código buscará automaticamente a chave local no caminho padrão:
`C:/Users/pedro.moura/Documents/Big Query Teste/keys/buriti-marketing-analytics-8466b517c505.json`

### 3. Rodando o App
Inicie o servidor de desenvolvimento do Streamlit a partir do diretório raiz:

```bash
streamlit run streamlit_app.py
```

---

## 📁 Estrutura do Projeto (Arquitetura)

```
painel-geral/
├── streamlit_app.py          # Entrypoint principal: define navegação st.navigation e st.Page
├── core/
│   ├── bq.py                 # Conexão centralizada com o BigQuery (get_client)
│   ├── theme.py              # Tema visual unificado e animações CSS (aplicar_tema)
│   ├── format.py             # Formatações brasileiras (_br) e paletas de cores padrão
│   ├── ui.py                 # Elementos gráficos comuns (exibir_logo, kpis, export CSV)
│   ├── charts.py             # Componentes de gráficos unificados (evolucao, barras_mensais, HTML tables)
│   └── taxonomia.py          # Classificador Estoque/Lançamento e Cidade/UF regex unificado
├── sources/                  # Data Loaders específicos de cada canal (com TTL cache de 1 hora)
│   ├── google_ads.py
│   ├── ga4.py
│   ├── publya.py
│   └── meta.py
├── pages/                    # Views/Páginas finas de cada dashboard
│   ├── visao_geral.py        # Consolidação cross-channel e drill-through de entrada
│   ├── google_ads.py
│   ├── meta_ads.py
│   ├── ga4.py
│   └── publya.py
├── assets/                   # Logotipos do dashboard (logo_branca.png / logo_preta.png)
└── requirements.txt          # Dependências do Python
```

---

## 🛡️ Tratamento de Dados Vazios
O dashboard foi projetado defensivamente para lidar com bases de dados temporariamente vazias no BigQuery (como a tabela `google_ads` atualmente). Em vez de travar a aplicação ou lançar exceções na tela, as views exibirão mensagens explicativas ("*Sem dados no período*") e as KPIs consolidadas somarão os valores das demais fontes ignorando os canais sem dados.
