import streamlit as st
import time

# Importaciones modulares
from src.ui_components import aplicar_estilos, render_header
from src.simulation_engine import ejecutar_simulacion_parametrizada
from src.charts import graficar_evolucion_inventario
from src.database import guardar_simulacion

# Configuración inicial de la página
st.set_page_config(
    page_title="CEMEX Logistics Simulator",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Aplicar CSS global
aplicar_estilos()

# Inicializar variables de estado
if 'estado_app' not in st.session_state:
    st.session_state.estado_app = 'formulario' # formulario, carga, resultados
if 'df_eventos' not in st.session_state:
    st.session_state.df_eventos = None
if 'df_historial' not in st.session_state:
    st.session_state.df_historial = None
if 'kpis' not in st.session_state:
    st.session_state.kpis = None
if 'parametros_actuales' not in st.session_state:
    st.session_state.parametros_actuales = None

# Funciones de navegación
def ir_a_carga():
    st.session_state.estado_app = 'carga'
def ir_a_resultados():
    st.session_state.estado_app = 'resultados'
def ir_a_formulario():
    st.session_state.estado_app = 'formulario'
def ir_a_doe():
    st.session_state.estado_app = 'doe'

# Renderizar Cabecera Corporativa
render_header()

# -----------------------------------------------------------------------------
# VISTA 1: FORMULARIO
# -----------------------------------------------------------------------------
if st.session_state.estado_app == 'formulario':
    st.title("Nueva simulación")
    st.markdown("<p>Configura los parámetros del modelo antes de ejecutar la simulación estocástica de abastecimiento.</p>", unsafe_allow_html=True)
    
    col_form, col_resumen = st.columns([2, 1], gap="large")
    
    with col_form:
        st.markdown('<div class="stCard">', unsafe_allow_html=True)
        st.subheader("Inventario")
        c1, c2, c3 = st.columns(3)
        cap_bodega = c1.number_input("CAPACIDAD_BODEGA", min_value=100, value=10000, step=100, help="Capacidad máxima de almacenamiento (ton).")
        stock_ini = c2.number_input("STOCK_INICIAL", min_value=0, max_value=cap_bodega, value=2000, step=100, help="Inventario disponible al inicio (ton).")
        pto_reorden = c3.number_input("PUNTO_REORDEN", min_value=0, max_value=cap_bodega, value=1500, step=100, help="Nivel de inventario para reordenar (ton).")
        
        st.divider()
        
        st.subheader("Reabastecimiento")
        c4, c5 = st.columns(2)
        cant_reabasto = c4.number_input("CANTIDAD_REABASTECIMIENTO", min_value=10, value=5000, step=100, help="Cantidad a solicitar al reordenar (ton).")
        
        # AJUSTE CRITICO: Tamaño de pedido por cliente debe ser mucho menor al stock inicial
        tamano_pedido = c5.number_input("TAMANO_PEDIDO (Media)", min_value=1, value=150, step=10, help="Tamaño de pedido promedio por cliente (Estocástico).")
        
        st.divider()
        
        st.subheader("Demanda y Proveedor")
        c6, c7 = st.columns(2)
        t_llegadas = c6.number_input("TIEMPO_ENTRE_LLEGADAS (días)", min_value=0.1, value=1.5, step=0.1, help="Tiempo promedio entre llegadas (Poisson).")
        lead_time = c7.number_input("LEAD_TIME_PROVEEDOR (días)", min_value=0.1, value=2.0, step=0.1, help="Tiempo de entrega del proveedor (Uniforme ±0.5).")
        
        st.divider()
        
        st.subheader("Horizonte de simulación")
        t_simulacion = st.number_input("TIEMPO_SIMULACION (días)", min_value=1, value=180, step=10, help="Duración total de la simulación.")
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col_resumen:
        st.markdown('<div class="stCard">', unsafe_allow_html=True)
        st.subheader("Resumen de configuración")
        st.markdown("**(Escenario base estocástico)**")
        st.markdown(f"- **Capacidad:** {cap_bodega} ton")
        st.markdown(f"- **Stock Inicial:** {stock_ini} ton")
        st.markdown(f"- **Punto Reorden:** {pto_reorden} ton")
        st.markdown(f"- **Cant. Reabasto:** {cant_reabasto} ton")
        st.markdown(f"- **Tiempo Llegadas:** ~{t_llegadas} días")
        st.markdown(f"- **Pedido Cliente:** ~{tamano_pedido} ton")
        st.markdown(f"- **Lead Time Prov:** ~{lead_time} días")
        st.markdown(f"- **Horizonte:** {t_simulacion} días")
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.info("Todos los parámetros están completos y el modelo está listo para ejecutar.")
        
        # Guardar parametros
        st.session_state.parametros_actuales = {
            'CAPACIDAD_BODEGA': int(cap_bodega),
            'STOCK_INICIAL': int(stock_ini),
            'PUNTO_REORDEN': int(pto_reorden),
            'CANTIDAD_REABASTECIMIENTO': int(cant_reabasto),
            'TIEMPO_ENTRE_LLEGADAS': float(t_llegadas),
            'TAMANO_PEDIDO': int(tamano_pedido),
            'LEAD_TIME_PROVEEDOR': float(lead_time),
            'TIEMPO_SIMULACION': int(t_simulacion)
        }
        
        if st.button("Iniciar simulación", use_container_width=True):
            ir_a_carga()
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# VISTA 2: CARGA
# -----------------------------------------------------------------------------
elif st.session_state.estado_app == 'carga':
    st.title("Generando simulación")
    st.markdown("<p>Estamos procesando los parámetros y ejecutando el modelo estocástico de abastecimiento.</p>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1], gap="large")
    
    with col1:
        st.markdown('<div class="stCard">', unsafe_allow_html=True)
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        status_text.markdown("### 1. Validando parámetros y distribuciones...")
        time.sleep(0.3)
        progress_bar.progress(25)
        
        status_text.markdown("### 2. Construyendo motor SimPy...")
        time.sleep(0.3)
        progress_bar.progress(50)
        
        status_text.markdown("### 3. Ejecutando eventos discretos...")
        
        # EJECUCIÓN DEL MOTOR
        df_eventos, df_historial, kpis = ejecutar_simulacion_parametrizada(st.session_state.parametros_actuales)
        st.session_state.df_eventos = df_eventos
        st.session_state.df_historial = df_historial
        st.session_state.kpis = kpis
        
        # GUARDAR EN BASE DE DATOS LOCAL
        guardar_simulacion(df_eventos, st.session_state.parametros_actuales, kpis)
        
        time.sleep(0.3)
        progress_bar.progress(75)
        
        status_text.markdown("### 4. Construyendo dashboard interactivo...")
        time.sleep(0.3)
        progress_bar.progress(100)
        status_text.markdown("### ¡Completado!")
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col2:
        st.markdown('<div class="stCard">', unsafe_allow_html=True)
        st.subheader("Estado de la simulación")
        st.markdown(f"**Escenario:** Escenario con variabilidad")
        st.markdown(f"**Horizonte:** {st.session_state.parametros_actuales['TIEMPO_SIMULACION']} días")
        st.info("Guardando histórico de eventos en la base de datos CSV local.")
        st.markdown('</div>', unsafe_allow_html=True)
        
    time.sleep(0.3)
    ir_a_resultados()
    st.rerun()

# -----------------------------------------------------------------------------
# VISTA 3: RESULTADOS
# -----------------------------------------------------------------------------
elif st.session_state.estado_app == 'resultados':
    kpis = st.session_state.kpis
    parametros = st.session_state.parametros_actuales
    
    col_t1, col_t2 = st.columns([3, 1])
    with col_t1:
        st.title("Resultados de simulación")
        st.markdown("<p>Analiza el desempeño estocástico del modelo y los indicadores clave.</p>", unsafe_allow_html=True)
    with col_t2:
        st.markdown('<div style="margin-top:20px;"></div>', unsafe_allow_html=True)
        # Convertir DF a CSV para descarga de la vista actual
        csv = st.session_state.df_eventos.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Exportar eventos actuales",
            data=csv,
            file_name='eventos_simulacion_cemex.csv',
            mime='text/csv',
            use_container_width=True
        )

    # Tarjetas de KPIs Superiores
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        st.markdown('<div class="stCard">', unsafe_allow_html=True)
        st.metric("Nivel de servicio", f"{kpis['Nivel Servicio']}%")
        st.markdown('</div>', unsafe_allow_html=True)
    with kpi2:
        st.markdown('<div class="stCard">', unsafe_allow_html=True)
        st.metric("Rupturas de stock", f"{kpis['Ventas Perdidas']}", "Eventos sin surtir")
        st.markdown('</div>', unsafe_allow_html=True)
    with kpi3:
        st.markdown('<div class="stCard">', unsafe_allow_html=True)
        inv_promedio = int(st.session_state.df_historial['Inventario'].mean())
        st.metric("Inventario promedio", f"{inv_promedio} ton")
        st.markdown('</div>', unsafe_allow_html=True)
    with kpi4:
        st.markdown('<div class="stCard">', unsafe_allow_html=True)
        st.metric("Pedidos atendidos", f"{kpis['Pedidos Surtidos']}")
        st.markdown('</div>', unsafe_allow_html=True)

    # Gráfico y Hallazgos
    col_graf, col_hall = st.columns([2, 1], gap="large")
    
    with col_graf:
        st.markdown('<div class="stCard">', unsafe_allow_html=True)
        st.subheader("Evolución del inventario (Diente de Sierra)")
        
        fig = graficar_evolucion_inventario(st.session_state.df_historial, parametros['PUNTO_REORDEN'])
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col_hall:
        st.markdown('<div class="stCard">', unsafe_allow_html=True)
        st.subheader("Hallazgos y recomendaciones")
        
        if kpis['Ventas Perdidas'] > 0:
            st.error(f"**Ajustar punto de reorden:** Se detectaron {kpis['Ventas Perdidas']} rupturas de stock debido a la variabilidad del proveedor o demanda alta.")
        elif inv_promedio > parametros['PUNTO_REORDEN'] * 2.5:
             st.warning("**Reducir cantidad de reabastecimiento:** El inventario promedio es muy alto frente a la demanda.")
        else:
            st.success("**Buen nivel de servicio:** El sistema amortiguó correctamente la variabilidad sin romper stock.")
             
        st.info("**Datos Históricos:** Esta corrida ha sido guardada en la base de datos local `data/simulations.csv` para tu análisis.")
        
        st.divider()
        st.markdown("### Resumen del escenario")
        st.markdown(f"- **Órdenes al proveedor:** {kpis['Ordenes Proveedor']}")
        st.markdown(f"- **Unidades despachadas:** {kpis['Unidades Vendidas']}")
        st.markdown(f"- **Registros BD:** {len(st.session_state.df_eventos)}")
        st.markdown('</div>', unsafe_allow_html=True)
        
    # Botones inferiores
    c_btn1, c_btn2, c_btn3 = st.columns([2, 1, 1])
    with c_btn2:
        st.markdown('<div class="btn-secondary">', unsafe_allow_html=True)
        if st.button("Nueva simulación"):
            ir_a_formulario()
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with c_btn3:
        st.markdown('<div class="btn-blue">', unsafe_allow_html=True)
        if st.button("Ejecutar DOE (Semana 4)"):
            ir_a_doe()
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# VISTA 4: DOE (Semana 4)
# -----------------------------------------------------------------------------
elif st.session_state.estado_app == 'doe':
    st.title("Diseño de Experimentos (DOE)")
    st.markdown("<p>Comparativa estocástica con Common Random Numbers para Reducción de Varianza y Optimización.</p>", unsafe_allow_html=True)
    
    with st.spinner("Ejecutando múltiples réplicas estocásticas... esto puede tomar unos segundos."):
        from src.simulation_engine import ejecutar_doe
        df_doe = ejecutar_doe(st.session_state.parametros_actuales)
    
    col_1, col_2 = st.columns([3, 1])
    with col_1:
        st.markdown('<div class="stCard">', unsafe_allow_html=True)
        st.subheader("Resultados Comparativos")
        st.dataframe(df_doe, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col_2:
        st.markdown('<div class="stCard">', unsafe_allow_html=True)
        mejor_escenario = df_doe.loc[df_doe['Costo_Medio'].idxmin()]
        st.success(f"**Escenario Óptimo:**\n\n{mejor_escenario['Escenario']}")
        st.markdown(f"**Costo Medio:** ${mejor_escenario['Costo_Medio']:,.2f}")
        st.markdown(f"**Nivel Servicio:** {mejor_escenario['Nivel_Servicio']}%")
        st.markdown('</div>', unsafe_allow_html=True)
        
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Volver a Resultados", type="primary"):
        ir_a_resultados()
        st.rerun()
