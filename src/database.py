import pandas as pd
import os
import datetime

DATA_DIR = 'data'

def asegurar_directorio():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

def guardar_simulacion(df_eventos, parametros, kpis):
    """
    Guarda los eventos de la corrida actual y actualiza un archivo histórico.
    """
    asegurar_directorio()
    
    # Generar un ID único para la simulación
    id_simulacion = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Añadir ID a los eventos
    df_eventos_copy = df_eventos.copy()
    df_eventos_copy.insert(0, 'ID_Simulacion', id_simulacion)
    
    # Guardar detalle de eventos individual
    path_eventos = os.path.join(DATA_DIR, f'events_{id_simulacion}.csv')
    df_eventos_copy.to_csv(path_eventos, index=False)
    
    # Adjuntar al archivo maestro de eventos (all_events.csv) para Power BI
    path_all_events = os.path.join(DATA_DIR, 'all_events.csv')
    if os.path.exists(path_all_events):
        df_eventos_copy.to_csv(path_all_events, mode='a', header=False, index=False)
    else:
        df_eventos_copy.to_csv(path_all_events, index=False)
    
    # Crear registro para el historial general
    resumen = {
        'ID_Simulacion': id_simulacion,
        'Fecha': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        **parametros,
        **kpis
    }
    
    df_resumen = pd.DataFrame([resumen])
    path_simulations = os.path.join(DATA_DIR, 'simulations.csv')
    
    # Adjuntar al archivo maestro si existe
    if os.path.exists(path_simulations):
        df_historico = pd.read_csv(path_simulations)
        df_historico = pd.concat([df_historico, df_resumen], ignore_index=True)
        df_historico.to_csv(path_simulations, index=False)
    else:
        df_resumen.to_csv(path_simulations, index=False)
        
    return path_eventos
