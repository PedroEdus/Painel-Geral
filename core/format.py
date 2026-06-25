import streamlit as st

# ════════════════════════════════════════════════════════════════════════════
# PALETAS DE COR
# ════════════════════════════════════════════════════════════════════════════

# Paleta alinhada ao design system do Painel do Milhão (verde #2a9d45).
PALETTE = [
    "#2a9d45",  # brand verde (primária)
    "#7dd190",  # brand verde claro
    "#8fa399",  # cinza-verde
    "#3b82f6",  # azul (info)
    "#1e7d34",  # brand verde escuro
    "#4ab861",  # brand verde médio
    "#1a6229",  # brand verde profundo
]

VERDE = "#2a9d45"

# Estoque / Lançamento (Google Ads, Meta, Publya)
LANCAMENTO_COLOR_MAP = {
    "Lançamento": "#2a9d45",
    "Estoque":    "#4ab861",
    "Outros":     "#8fa399",
}

# Canais de tráfego (GA4)
CANAL_COLORS = {
    "Orgânico":   "#2a9d45",
    "Pago":       "#1a6229",
    "Direto":     "#8fa399",
    "Social":     "#7dd190",
    "Referência": "#4ab861",
    "Outros":     "#4e4e57",
}

# Tipo de mídia (Publya)
COLOR_MAP_MIDIA = {
    "Display": "#2a9d45",
    "Vídeo":   "#4ab861",
    "Áudio":   "#7dd190",
    "Misto":   "#8fa399",
}

# Canais Google Ads (advertising_channel_type)
CHANNEL_LABELS_GADS = {
    "SEARCH": "Pesquisa", 
    "PERFORMANCE_MAX": "Performance Max", 
    "DISPLAY": "Display",
    "SHOPPING": "Shopping", 
    "VIDEO": "Vídeo", 
    "SMART": "Smart",
}

CHANNEL_COLORS_GADS = {
    "Pesquisa": PALETTE[0], 
    "Performance Max": PALETTE[4], 
    "Display": PALETTE[3],
    "Shopping": PALETTE[5], 
    "Vídeo": PALETTE[6], 
    "Smart": PALETTE[2],
}

# Objetivos Meta
OBJECTIVE_COLOR_MAP = {
    "OUTCOME_LEADS": "#2a9d45",
    "OUTCOME_AWARENESS": "#4ab861",
    "OUTCOME_ENGAGEMENT": "#7dd190",
    "OUTCOME_TRAFFIC": "#1a6229",
    "OUTCOME_SALES": "#1e7d34",
    "OUTCOME_APP_PROMOTION": "#8fa399",
    "CONVERSIONS": "#174f23",
    "LINK_CLICKS": "#b3e6bc",
    "REACH": "#4ab861",
    "VIDEO_VIEWS": "#d8f3de",
}

OBJECTIVE_LABELS = {
    "OUTCOME_AWARENESS": "Alcance", 
    "OUTCOME_TRAFFIC": "Tráfego",
    "OUTCOME_ENGAGEMENT": "Engajamento", 
    "OUTCOME_LEADS": "Leads",
    "OUTCOME_APP_PROMOTION": "App", 
    "OUTCOME_SALES": "Vendas",
    "CONVERSIONS": "Conversões", 
    "LINK_CLICKS": "Cliques",
    "REACH": "Alcance", 
    "VIDEO_VIEWS": "Visualizações",
}

# Cores fixas para cada canal na Visão Geral
CANAL_BRAND_COLORS = {
    "Google Ads": "#4285F4",  # Azul Google
    "Meta Ads":   "#1877F2",  # Azul Facebook / Meta
    "Publya":     "#ffcc00",  # Amarelo/Laranja Publya
    "GA4":        "#e67e22",  # Laranja Google Analytics
}

def label_obj(obj: str) -> str:
    """Retorna o rótulo amigável para objetivos de campanha Meta."""
    return OBJECTIVE_LABELS.get(str(obj), str(obj).replace("OUTCOME_", "").replace("_", " ").title())

def _br(valor, decimais: int = 0, prefixo: str = "") -> str:
    """Formatação numérica brasileira: 1.234,56."""
    try:
        if valor is None or (isinstance(valor, float) and (valor != valor)):  # NaN check
            return "—"
        fmt = f"{float(valor):,.{decimais}f}"
    except Exception:
        return "—"
    fmt = fmt.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{prefixo}{fmt}"

def _font_color_para_fundo(hex_color: str) -> str:
    """Calcula cor da fonte (preto/branco) ideal com base na luminância do fundo."""
    r, g, b = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)
    lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return "black" if lum > 0.55 else "white"

def _rgba(hex_color: str, alpha: float) -> str:
    """Converte hexadecimal para RGBA."""
    r, g, b = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)
    return f"rgba({r},{g},{b},{alpha})"
