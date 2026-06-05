import streamlit as st

# ════════════════════════════════════════════════════════════════════════════
# PALETAS DE COR
# ════════════════════════════════════════════════════════════════════════════

PALETTE = [
    "#008347",  # verde principal
    "#f0f0f0",  # branco
    "#888888",  # cinza
    "#006682",  # azul-petróleo
    "#008274",  # teal-verde
    "#5BD9CC",  # teal claro
    "#1E3436",  # teal escuro
]

VERDE = "#008140"

# Estoque / Lançamento (Google Ads, Meta, Publya)
LANCAMENTO_COLOR_MAP = {
    "Lançamento": "#008140",
    "Estoque":    "#00b359",
    "Outros":     "#888888",
}

# Canais de tráfego (GA4)
CANAL_COLORS = {
    "Orgânico":   "#008140",
    "Pago":       "#004d26",
    "Direto":     "#888888",
    "Social":     "#33aa77",
    "Referência": "#00b359",
    "Outros":     "#444444",
}

# Tipo de mídia (Publya)
COLOR_MAP_MIDIA = {
    "Display": "#008140",
    "Vídeo":   "#00b359",
    "Áudio":   "#ffffff",
    "Misto":   "#aaaaaa",
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
    "OUTCOME_LEADS": "#008140", 
    "OUTCOME_AWARENESS": "#00b359",
    "OUTCOME_ENGAGEMENT": "#66cc99", 
    "OUTCOME_TRAFFIC": "#004d26",
    "OUTCOME_SALES": "#33aa77", 
    "OUTCOME_APP_PROMOTION": "#888888",
    "CONVERSIONS": "#005c2e", 
    "LINK_CLICKS": "#99ddbb",
    "REACH": "#00b359", 
    "VIDEO_VIEWS": "#cceedb",
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
