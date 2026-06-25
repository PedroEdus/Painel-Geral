import streamlit as st
from core.theme import aplicar_tema

st.set_page_config(page_title="Marketing Analytics", page_icon="📊", layout="wide")

# Apply global theme and styling
aplicar_tema()

# Define the multi-page navigation links and icons
pg = st.navigation([
    st.Page("pages/visao_geral.py", title="Visão Geral", icon="📊", default=True),
    st.Page("pages/google_ads.py", title="Google Ads",  icon="🔍"),
    st.Page("pages/meta_ads.py",   title="Meta Ads",    icon="📱"),
    st.Page("pages/ga4.py",        title="GA4",          icon="🌐"),
    st.Page("pages/publya.py",     title="Publya",       icon="📺"),
    st.Page("pages/funil.py",      title="Funil BTSA", icon="📊"),
    st.Page("pages/clientes.py",   title="Análise de Clientes", icon="👤"),
])

# Run the selected page
pg.run()
