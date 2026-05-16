import plotly.express as px
import plotly.graph_objects as go

def graficar_evolucion_inventario(df_historial, punto_reorden):
    """
    Genera un gráfico de líneas tipo 'diente de sierra' para el inventario.
    """
    # Usar scatter con líneas mode='lines+markers' para mejor visibilidad de caídas
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df_historial['Dia'], 
        y=df_historial['Inventario'],
        mode='lines',
        name='Nivel de Inventario',
        line=dict(color='#0057FF', width=2),
        fill='tozeroy',
        fillcolor='rgba(0, 87, 255, 0.1)'
    ))
    
    # Agregar línea de Punto de Reorden
    fig.add_hline(
        y=punto_reorden, 
        line_dash="dash", 
        line_color="#FF5A1F", 
        annotation_text="Punto de Reorden (ROP)",
        annotation_position="bottom right",
        annotation_font_color="#FF5A1F"
    )
    
    fig.update_layout(
        plot_bgcolor='white',
        paper_bgcolor='white',
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis=dict(
            title='Tiempo simulado (días)',
            showgrid=True, 
            gridcolor='#E8EDF5'
        ),
        yaxis=dict(
            title='Inventario disponible (ton)',
            showgrid=True, 
            gridcolor='#E8EDF5',
            rangemode='tozero'
        ),
        hovermode="x unified"
    )
    
    return fig
