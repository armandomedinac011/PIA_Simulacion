import streamlit as st

def aplicar_estilos():
    """
    Inyecta CSS personalizado basado en los lineamientos visuales:
    Fondo general: #F5F7FB
    Tarjetas: #FFFFFF
    Azul principal CEMEX: #0057FF
    Naranja CTA: #FF5A1F
    Bordes suaves: #E8EDF5
    """
    css = """
    <style>
        /* Importar fuente moderna */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        
        /* Fondo general */
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
            background-color: #F5F7FB !important;
        }
        
        .stApp {
            background-color: #F5F7FB !important;
        }
        
        /* Cabecera / Header simulado */
        .header-container {
            display: flex;
            align-items: center;
            padding: 15px 0;
            border-bottom: 1px solid #E8EDF5;
            margin-bottom: 2rem;
            background-color: #FFFFFF;
            padding-left: 2rem;
            padding-right: 2rem;
            margin-left: -4rem;
            margin-right: -4rem;
            margin-top: -4rem;
        }
        .header-logo {
            font-weight: 800;
            font-size: 1.5rem;
            color: #0f172a;
            margin-right: 30px;
            display: flex;
            align-items: center;
        }
        .header-logo span {
            color: #0057FF; /* Azul Cemex */
            margin-right: 8px;
        }
        .header-nav {
            display: flex;
            gap: 25px;
            color: #64748b;
            font-weight: 500;
            font-size: 0.95rem;
        }
        .header-nav .active {
            color: #0057FF;
            border-bottom: 2px solid #0057FF;
            padding-bottom: 5px;
        }
        
        /* Tarjetas generales */
        .stCard {
            background-color: #FFFFFF;
            border-radius: 12px;
            padding: 24px;
            border: 1px solid #E8EDF5;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.02);
        }
        
        /* Títulos */
        h1, h2, h3 {
            color: #1e293b !important;
            font-weight: 600 !important;
        }
        p {
            color: #475569;
        }
        
        /* Botones principales - Naranja CTA */
        .stButton > button,
        button[kind="primary"],
        button[data-testid="baseButton-primary"],
        .primary-button,
        .orange-button,
        .cta-button {
            background-color: #EC6636 !important;
            color: #FFFFFF !important;
            border: none !important;
            font-weight: 600 !important;
            border-radius: 8px;
            padding: 10px 24px;
            transition: all 0.2s ease;
            width: 100%;
        }
        
        /* Asegurar que TODO el texto interno sea blanco */
        .stButton > button *,
        button[kind="primary"] *,
        button[data-testid="baseButton-primary"] *,
        .primary-button *,
        .orange-button *,
        .cta-button * {
            color: #FFFFFF !important;
        }
        
        .stButton > button:hover,
        .stButton > button:focus,
        .stButton > button:active,
        button[kind="primary"]:hover,
        button[kind="primary"]:focus,
        button[kind="primary"]:active,
        button[data-testid="baseButton-primary"]:hover,
        button[data-testid="baseButton-primary"]:focus,
        button[data-testid="baseButton-primary"]:active,
        .primary-button:hover,
        .orange-button:hover,
        .cta-button:hover {
            background-color: #EC6636 !important;
            color: #FFFFFF !important;
            border: none !important;
            box-shadow: 0 4px 12px rgba(236, 102, 54, 0.3);
        }
        
        .stButton > button:hover *,
        button[kind="primary"]:hover * {
            color: #FFFFFF !important;
        }
        
        /* Botones Secundarios */
        .btn-secondary>button {
            background-color: #FFFFFF !important;
            color: #1e293b !important;
            border: 1px solid #E8EDF5 !important;
            box-shadow: none !important;
        }
        .btn-secondary>button * {
            color: #1e293b !important;
        }
        .btn-secondary>button:hover,
        .btn-secondary>button:focus,
        .btn-secondary>button:active {
            background-color: #F5F7FB !important;
            border-color: #cbd5e1 !important;
            box-shadow: none !important;
        }
        .btn-secondary>button:hover *,
        .btn-secondary>button:focus *,
        .btn-secondary>button:active * {
            color: #1e293b !important;
        }
        
        /* Botón Azul */
        .btn-blue>button {
            background-color: #0057FF !important;
        }
        .btn-blue>button * {
            color: #FFFFFF !important;
        }
        .btn-blue>button:hover,
        .btn-blue>button:focus,
        .btn-blue>button:active {
            background-color: #0046d1 !important;
            box-shadow: 0 4px 12px rgba(0, 87, 255, 0.3) !important;
        }
        .btn-blue>button:hover *,
        .btn-blue>button:focus *,
        .btn-blue>button:active * {
            color: #FFFFFF !important;
        }
        
        /* Botón de Descarga CSV */
        [data-testid="stDownloadButton"] > button {
            color: #FFFFFF !important;
        }
        [data-testid="stDownloadButton"] > button * {
            color: #FFFFFF !important;
        }
        
        /* KPIs Metrics */
        [data-testid="stMetricValue"] {
            font-size: 2.2rem !important;
            font-weight: 700 !important;
            color: #0f172a !important;
        }
        [data-testid="stMetricLabel"] {
            font-size: 1rem !important;
            color: #64748b !important;
            font-weight: 500 !important;
        }
        [data-testid="stMetricDelta"] {
            font-weight: 500 !important;
        }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

def render_header():
    st.markdown("""
    <div class="header-container">
        <div class="header-logo"><span>//</span> CEMEX Logistics Simulator</div>
        <div class="header-nav">
            <div>Dashboard</div>
            <div class="active">Simulación</div>
            <div>Envíos</div>
            <div>Inventario</div>
            <div>Reportes</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
