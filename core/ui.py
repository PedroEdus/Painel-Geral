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


def cabecalho(titulo: str, sub: str = "", atualizado_em=None) -> None:
    """Cabeçalho de página (.ph do design system Milhão): logo + título + subtítulo
    e selo opcional de atualização. Substitui o st.title simples.
    """
    logo_tag = ""
    if os.path.exists(LOGO_CLARA):
        b64 = _imagem_base64(LOGO_CLARA)
        logo_tag = (
            f'<div class="ph-logo-box">'
            f'<img src="data:image/png;base64,{b64}" class="ph-logo-img" alt="logo"></div>'
            f'<div class="ph-sep"></div>'
        )
    sub_html = f'<div class="ph-sub">{sub}</div>' if sub else ""
    stamp = ""
    if atualizado_em is not None:
        try:
            stamp = (
                f'<span class="ph-stamp"><i class="fa-regular fa-clock"></i>'
                f'Atualizado {atualizado_em:%d/%m/%Y %H:%M}</span>'
            )
        except (ValueError, TypeError):
            stamp = f'<span class="ph-stamp"><i class="fa-regular fa-clock"></i>{atualizado_em}</span>'
    html = (
        f'<div class="ph"><div class="ph-l">{logo_tag}'
        f'<div><div class="ph-title">{titulo}</div>{sub_html}</div></div>'
        f'<div>{stamp}</div></div>'
    )
    if hasattr(st, "html"):
        st.html(html)
    else:
        st.markdown(html, unsafe_allow_html=True)

def exibir_logo() -> None:
    """Renderiza a logo preta no topo da sidebar (tema claro)."""
    if not os.path.exists(LOGO_CLARA):
        return
    try:
        b64 = _imagem_base64(LOGO_CLARA)
        st.markdown(
            f"""
            <style>
                .logo-container {{ display:flex; justify-content:center; padding:6px 4px 14px; }}
                .logo-container img {{ width:min(180px,80%); height:auto; }}
            </style>
            <div class="logo-container">
                <img src="data:image/png;base64,{b64}">
            </div>
            """,
            unsafe_allow_html=True,
        )
    except Exception:
        pass

# Ícones (Font Awesome) por palavra-chave do label → stat-card do design system.
_ICON_KEYWORDS = [
    (("invest", "custo", "gasto", "spend", "cost", "budget", "valor", "receita", "r$"), "fa-coins", "green"),
    (("lead", "contato", "cadastr"), "fa-user-plus", "blue"),
    (("clique", "click"), "fa-arrow-pointer", "blue"),
    (("impress", "alcance", "reach", "view", "visualiz"), "fa-eye", "amber"),
    (("convers", "venda", "compra"), "fa-bullseye", "green"),
    (("cpc", "cpl", "cpm", "cpa", "ctr", "cpv", "taxa", "%"), "fa-percent", "amber"),
    (("sess", "usu", "user", "visit"), "fa-users", "blue"),
    (("camp",), "fa-rectangle-ad", "green"),
]


def _icone_para_label(label: str) -> tuple[str, str]:
    low = str(label).lower()
    for chaves, icon, cor in _ICON_KEYWORDS:
        if any(k in low for k in chaves):
            return icon, cor
    return "fa-chart-simple", "green"


def kpis(metricas: dict, ajudas: dict | None = None) -> None:
    """Rende uma grade de KPIs como stat-cards (design system Milhão).

    `metricas` = {"Label": "Valor", ...}. Mantém a assinatura usada pelas páginas;
    o ícone/acento é escolhido por palavra-chave do label.

    `ajudas` = {"Label": "texto de ajuda", ...} (opcional). Para cada label
    presente, renderiza um ícone (?) ao lado que mostra o texto ao passar o mouse.
    """
    if not metricas:
        return
    ajudas = ajudas or {}
    cards = []
    for label, valor in metricas.items():
        icon, cor = _icone_para_label(label)
        _help = ajudas.get(label)
        _help_html = (
            f'<span class="help-dot" data-tip="{_help}">?</span>'
            if _help else ""
        )
        cards.append(
            f'<div class="stat-card {cor}">'
            f'<div class="stat-val">{valor}</div>'
            f'<div class="stat-foot">'
            f'<span class="stat-ico-sm {cor}"><i class="fa-solid {icon}"></i></span>'
            f'<span class="stat-label">{label}</span>'
            f'{_help_html}'
            f'</div></div>'
        )
    html = '<div class="stats-row">' + "".join(cards) + "</div>"
    if hasattr(st, "html"):
        st.html(html)
    else:
        st.markdown(html, unsafe_allow_html=True)

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
