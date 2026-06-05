import base64
import os
import streamlit as st
import pandas as pd

_ASSETS = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
LOGO_CLARA  = os.path.join(_ASSETS, "logo_preta.png")
LOGO_ESCURA = os.path.join(_ASSETS, "logo_branca.png")

def _imagem_base64(caminho: str) -> str:
    with open(caminho, "rb") as f:
        return base64.b64encode(f.read()).decode()

def exibir_logo() -> None:
    """Renderiza a logo da empresa baseada no modo claro/escuro usando Base64."""
    existe_clara  = os.path.exists(LOGO_CLARA)
    existe_escura = os.path.exists(LOGO_ESCURA)
    if not existe_clara and not existe_escura:
        return
    caminho_claro  = LOGO_CLARA  if existe_clara  else LOGO_ESCURA
    caminho_escuro = LOGO_ESCURA if existe_escura else LOGO_CLARA

    try:
        clara_b64 = _imagem_base64(caminho_claro)
        escura_b64 = _imagem_base64(caminho_escuro)
        st.markdown(
            f"""
            <style>
                .logo-container {{ display:flex; justify-content:flex-start; margin-bottom:1rem; }}
                .logo-container img {{ width:min(220px,55vw); height:auto; }}
                .logo-dark {{ display:none; }}
                @media (prefers-color-scheme:dark) {{
                    .logo-light {{ display:none; }}
                    .logo-dark  {{ display:block; }}
                }}
            </style>
            <div class="logo-container">
                <img class="logo-light" src="data:image/png;base64,{clara_b64}">
                <img class="logo-dark"  src="data:image/png;base64,{escura_b64}">
            </div>
            """,
            unsafe_allow_html=True,
        )
    except Exception:
        pass

def kpis(metricas: dict) -> None:
    """Rende uma linha horizontal de KPIs. `metricas` = {"Label": "Valor", ...}."""
    if not metricas:
        return
    cols = st.columns(len(metricas))
    for col, (label, valor) in zip(cols, metricas.items()):
        col.metric(label, valor)

def botao_download_csv(df: pd.DataFrame, filename: str, label: str = "📥 Baixar dados (CSV)") -> None:
    """Cria um botão de download para CSV no padrão brasileiro (delimitador ';' e decimal ',')."""
    if df.empty:
        return
    csv_data = df.to_csv(index=False, sep=";", decimal=",", encoding="utf-8-sig").encode("utf-8-sig")
    st.download_button(
        label=label,
        data=csv_data,
        file_name=filename,
        mime="text/csv",
    )
