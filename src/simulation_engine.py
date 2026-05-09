import simpy
import pandas as pd
import random

class CentroDistribucionEstocastico:
    def __init__(self, env, parametros, registro_eventos):
        self.env = env
        self.parametros = parametros
        self.registro_eventos = registro_eventos
        
        self.inventario = simpy.Container(
            env,
            capacity=parametros['CAPACIDAD_BODEGA'],
            init=parametros['STOCK_INICIAL']
        )
        self.pedido_en_transito = False
        self.pedidos_surtidos = 0       
        self.pedidos_perdidos = 0       
        self.unidades_vendidas = 0      
        self.ordenes_al_proveedor = 0   
        
        # Historial de inventario para graficar el "diente de sierra"
        self.historial_inventario = [(0.0, parametros['STOCK_INICIAL'])]

    def registrar_nivel(self):
        self.historial_inventario.append((round(self.env.now, 2), self.inventario.level))

    def registrar_evento(self, tipo_evento, cantidad, inventario_previo, inventario_posterior, venta_perdida):
        self.registro_eventos.append({
            'Dia_Simulacion': round(self.env.now, 2),
            'Tipo_Evento': tipo_evento,
            'Cantidad': cantidad,
            'Inventario_Previo': inventario_previo,
            'Inventario_Posterior': inventario_posterior,
            'Venta_Perdida': venta_perdida
        })

    def proceso_reabastecimiento(self):
        self.pedido_en_transito = True
        self.ordenes_al_proveedor += 1
        
        # Registrar emisión de pedido
        self.registrar_evento(
            tipo_evento='Emisión Pedido',
            cantidad=self.parametros['CANTIDAD_REABASTECIMIENTO'],
            inventario_previo=self.inventario.level,
            inventario_posterior=self.inventario.level,
            venta_perdida=0
        )

        # Variabilidad en el Lead Time (Uniforme entre +/- 0.5 días)
        lead_time_base = self.parametros['LEAD_TIME_PROVEEDOR']
        lead_time_real = random.uniform(max(0.1, lead_time_base - 0.5), lead_time_base + 0.5)
        
        yield self.env.timeout(lead_time_real)

        inventario_antes_llegada = self.inventario.level
        
        # Asegurarnos de no sobrepasar la capacidad de la bodega
        espacio_disponible = self.inventario.capacity - self.inventario.level
        cantidad_a_ingresar = min(self.parametros['CANTIDAD_REABASTECIMIENTO'], espacio_disponible)
        
        if cantidad_a_ingresar > 0:
            yield self.inventario.put(cantidad_a_ingresar)
            self.registrar_nivel()
        
        # Registrar recepción de material
        self.registrar_evento(
            tipo_evento='Recepción Material',
            cantidad=cantidad_a_ingresar,
            inventario_previo=inventario_antes_llegada,
            inventario_posterior=self.inventario.level,
            venta_perdida=0
        )

        self.pedido_en_transito = False

def proceso_clientes(env, centro):
    while True:
        # Llegadas con distribución Exponencial (Proceso de Poisson)
        tasa_llegada = 1.0 / centro.parametros['TIEMPO_ENTRE_LLEGADAS']
        tiempo_siguiente_llegada = random.expovariate(tasa_llegada)
        yield env.timeout(tiempo_siguiente_llegada)
        
        # Tamaño de pedido con distribución Normal (Estocástico)
        media_pedido = centro.parametros['TAMANO_PEDIDO']
        desviacion = media_pedido * 0.2  # 20% de variabilidad
        tamano_pedido_real = max(1, int(random.gauss(media_pedido, desviacion)))
        
        inventario_previo = centro.inventario.level
        
        if centro.inventario.level >= tamano_pedido_real:
            # Surtido Exitoso
            yield centro.inventario.get(tamano_pedido_real)
            centro.pedidos_surtidos += 1
            centro.unidades_vendidas += tamano_pedido_real
            centro.registrar_nivel()
            
            centro.registrar_evento(
                tipo_evento='Llegada Demanda (Surtida)',
                cantidad=tamano_pedido_real,
                inventario_previo=inventario_previo,
                inventario_posterior=centro.inventario.level,
                venta_perdida=0
            )

            # Revisión Continua: Verificar si se bajó del Punto de Reorden
            if centro.inventario.level <= centro.parametros['PUNTO_REORDEN']:
                if not centro.pedido_en_transito:
                    env.process(centro.proceso_reabastecimiento())
        else:
            # Venta Perdida (Ruptura de stock)
            centro.pedidos_perdidos += 1
            centro.registrar_evento(
                tipo_evento='Llegada Demanda (No Surtida)',
                cantidad=tamano_pedido_real,
                inventario_previo=inventario_previo,
                inventario_posterior=inventario_previo,
                venta_perdida=1
            )


def ejecutar_simulacion_parametrizada(parametros, semilla=None):
    # Inicializar semilla para tener algo de consistencia en caso de pruebas, 
    # pero manteniendo el comportamiento estocástico distinto por parametros.
    if semilla is not None:
        random.seed(semilla)
    else:
        random.seed()
    
    env = simpy.Environment()
    registro_eventos = []
    
    centro = CentroDistribucionEstocastico(env, parametros, registro_eventos)
    env.process(proceso_clientes(env, centro))
    
    env.run(until=parametros['TIEMPO_SIMULACION'])
    
    # Forzar un registro final del inventario al terminar el horizonte
    centro.historial_inventario.append((float(parametros['TIEMPO_SIMULACION']), centro.inventario.level))
    
    total_solicitudes = centro.pedidos_surtidos + centro.pedidos_perdidos
    nivel_servicio = (centro.pedidos_surtidos / total_solicitudes) * 100 if total_solicitudes > 0 else 0.0
    
    kpis = {
        'Inventario Final': centro.inventario.level,
        'Total Solicitudes': total_solicitudes,
        'Pedidos Surtidos': centro.pedidos_surtidos,
        'Ventas Perdidas': centro.pedidos_perdidos,
        'Nivel Servicio': round(nivel_servicio, 2),
        'Unidades Vendidas': centro.unidades_vendidas,
        'Ordenes Proveedor': centro.ordenes_al_proveedor,
    }
    
    df_eventos = pd.DataFrame(registro_eventos)
    if not df_eventos.empty:
        # Añadir metadatos
        for key, val in parametros.items():
            df_eventos[f'Param_{key}'] = val
            
    df_historial = pd.DataFrame(centro.historial_inventario, columns=['Dia', 'Inventario'])
    
    return df_eventos, df_historial, kpis

def ejecutar_doe(parametros_base):
    import scipy.stats as stats
    import numpy as np
    
    escenarios = [
        {"ROP": parametros_base["PUNTO_REORDEN"], "Q": parametros_base["CANTIDAD_REABASTECIMIENTO"], "Nombre": "Base"},
        {"ROP": parametros_base["PUNTO_REORDEN"] * 1.5, "Q": parametros_base["CANTIDAD_REABASTECIMIENTO"], "Nombre": "Aumento ROP"},
        {"ROP": parametros_base["PUNTO_REORDEN"], "Q": parametros_base["CANTIDAD_REABASTECIMIENTO"] * 1.2, "Nombre": "Aumento Q"},
        {"ROP": parametros_base["PUNTO_REORDEN"] * 1.5, "Q": parametros_base["CANTIDAD_REABASTECIMIENTO"] * 1.2, "Nombre": "ROP+Q Alto"}
    ]
    
    num_replicas = 10
    resultados = []
    
    for esc in escenarios:
        parametros = parametros_base.copy()
        parametros["PUNTO_REORDEN"] = esc["ROP"]
        parametros["CANTIDAD_REABASTECIMIENTO"] = esc["Q"]
        
        ns_list = []
        vp_list = []
        costo_list = []
        
        for rep in range(num_replicas):
            # Common Random Numbers (CRN)
            _, _, kpis = ejecutar_simulacion_parametrizada(parametros, semilla=rep + 42)
            
            # Simplificación de costo (1000 orden, 500 escasez)
            costo = kpis['Ordenes Proveedor']*1000 + kpis['Ventas Perdidas']*500
            
            ns_list.append(kpis['Nivel Servicio'])
            vp_list.append(kpis['Ventas Perdidas'])
            costo_list.append(costo)
            
        costo_mean = np.mean(costo_list)
        std_err = stats.sem(costo_list)
        h = std_err * stats.t.ppf((1 + 0.95) / 2., num_replicas - 1) if std_err > 0 else 0
        
        resultados.append({
            "Escenario": esc["Nombre"],
            "ROP": esc["ROP"],
            "Q": esc["Q"],
            "Nivel_Servicio": round(np.mean(ns_list), 2),
            "Ventas_Perdidas": round(np.mean(vp_list), 2),
            "Costo_Medio": round(costo_mean, 2),
            "IC_Inf": round(costo_mean - h, 2),
            "IC_Sup": round(costo_mean + h, 2)
        })
    
    return pd.DataFrame(resultados)
