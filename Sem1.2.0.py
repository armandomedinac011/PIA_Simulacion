"""
PROYECTO INTEGRADOR ACADÉMICO (PIA) — SIMULACIÓN DE SISTEMAS
Fase Avanzada (Semanas 3 y 4): Simulación Estocástica, Experimentación y Optimización

Sistema: Gestión de Inventarios y Logística para Centro de Distribución
         de Materiales de Construcción (Modelo Construrama / Cemex)

Este script implementa:
1. Variables aleatorias (Exponencial, Poisson, Triangular).
2. Uso de Common Random Numbers (CRN) para reducción de varianza.
3. Diseño de experimentos variando ROP y Cantidad de Reabastecimiento (Q).
4. Recolección de datos, cálculo de intervalos de confianza y análisis estadístico.
"""

import simpy
import random
import numpy as np
import pandas as pd
import scipy.stats as stats

# Parámetros Base del Sistema
CAPACIDAD_BODEGA = 500
STOCK_INICIAL = 200

# Parámetros para distribuciones
MEDIA_ENTRE_LLEGADAS = 1.0   # Días (Exponencial)
MEDIA_PEDIDO = 25            # Unidades (Poisson)
LEAD_TIME_MIN = 2.0          # Días
LEAD_TIME_MODA = 3.0         # Días
LEAD_TIME_MAX = 5.0          # Días
TIEMPO_SIMULACION = 365      # Horizonte de simulación en días (1 año)


class CentroDistribucion:
    def __init__(self, env, rop, q):
        self.env = env
        self.rop = rop
        self.q = q
        
        self.inventario = simpy.Container(env, capacity=CAPACIDAD_BODEGA, init=STOCK_INICIAL)
        self.pedido_en_transito = False
        
        # Métricas
        self.pedidos_surtidos = 0
        self.pedidos_perdidos = 0
        self.unidades_vendidas = 0
        self.ordenes_al_proveedor = 0
        
        # Costos (Simplificados para análisis)
        self.costo_ordenar = 1000 # Costo fijo por orden
        self.costo_mantener = 2   # Costo por unidad por día
        self.costo_escasez = 50   # Costo por unidad faltante
        
        self.costo_total_ordenar = 0
        self.costo_total_escasez = 0
        self.area_bajo_inventario = 0 # Para inventario promedio
        self.ultimo_tiempo = 0

    def actualizar_area_inventario(self):
        tiempo_transcurrido = self.env.now - self.ultimo_tiempo
        self.area_bajo_inventario += tiempo_transcurrido * self.inventario.level
        self.ultimo_tiempo = self.env.now

    def proceso_reabastecimiento(self):
        self.actualizar_area_inventario()
        self.pedido_en_transito = True
        self.ordenes_al_proveedor += 1
        self.costo_total_ordenar += self.costo_ordenar
        
        # Distribución Triangular para el Lead Time
        lead_time_real = random.triangular(LEAD_TIME_MIN, LEAD_TIME_MAX, LEAD_TIME_MODA)
        yield self.env.timeout(lead_time_real)
        
        self.actualizar_area_inventario()
        yield self.inventario.put(self.q)
        self.pedido_en_transito = False

def proceso_clientes(env, centro):
    id_cliente = 0
    while True:
        # Llegadas de clientes: Proceso de Poisson (Tiempo entre llegadas Exponencial)
        intervalo = random.expovariate(1.0 / MEDIA_ENTRE_LLEGADAS)
        yield env.timeout(intervalo)
        id_cliente += 1
        
        centro.actualizar_area_inventario()
        
        # Tamaño del pedido: Distribución de Poisson
        tamano_pedido = max(1, np.random.poisson(lam=MEDIA_PEDIDO))
        
        if centro.inventario.level >= tamano_pedido:
            yield centro.inventario.get(tamano_pedido)
            centro.pedidos_surtidos += 1
            centro.unidades_vendidas += tamano_pedido
            
            if centro.inventario.level <= centro.rop and not centro.pedido_en_transito:
                env.process(centro.proceso_reabastecimiento())
        else:
            centro.pedidos_perdidos += 1
            faltante = tamano_pedido - centro.inventario.level
            centro.costo_total_escasez += faltante * centro.costo_escasez


def ejecutar_simulacion(rop, q, semilla):
    # Uso de Common Random Numbers (CRN) para reducción de varianza
    random.seed(semilla)
    np.random.seed(semilla)
    
    env = simpy.Environment()
    centro = CentroDistribucion(env, rop, q)
    env.process(proceso_clientes(env, centro))
    env.run(until=TIEMPO_SIMULACION)
    
    centro.actualizar_area_inventario()
    
    total_solicitudes = centro.pedidos_surtidos + centro.pedidos_perdidos
    nivel_servicio = (centro.pedidos_surtidos / total_solicitudes) if total_solicitudes > 0 else 0
    
    inventario_promedio = centro.area_bajo_inventario / TIEMPO_SIMULACION
    costo_total_mantener = inventario_promedio * centro.costo_mantener * TIEMPO_SIMULACION
    
    costo_total = centro.costo_total_ordenar + costo_total_mantener + centro.costo_total_escasez
    
    return {
        "ROP": rop,
        "Q": q,
        "Nivel_Servicio": nivel_servicio * 100,
        "Costo_Total": costo_total,
        "Pedidos_Perdidos": centro.pedidos_perdidos,
        "Ordenes": centro.ordenes_al_proveedor
    }

def analisis_estadistico(resultados):
    data = [r["Costo_Total"] for r in resultados]
    n = len(data)
    media = np.mean(data)
    std_err = stats.sem(data)
    
    # Manejar caso de varianza cero
    if std_err == 0:
        return media, media, media
        
    h = std_err * stats.t.ppf((1 + 0.95) / 2., n - 1)
    return media, media - h, media + h

def main():
    print("Iniciando Experimentos (Semanas 3 y 4)....")
    
    # Diseño de Experimentos
    escenarios = [
        {"ROP": 50, "Q": 150},   # Base
        {"ROP": 80, "Q": 150},   # Aumento ROP
        {"ROP": 50, "Q": 200},   # Aumento Q
        {"ROP": 100, "Q": 200},  # Optimo propuesto
    ]
    
    num_replicas = 30 # Corridas por escenario
    
    resultados_finales = []
    
    for esc in escenarios:
        rop = esc["ROP"]
        q = esc["Q"]
        
        resultados_escenario = []
        for i in range(num_replicas):
            # Misma secuencia de semillas para cada escenario (CRN - Reducción de varianza)
            res = ejecutar_simulacion(rop, q, semilla=i+42)
            resultados_escenario.append(res)
            
        # Análisis estadístico de este escenario
        costo_medio, ic_inf, ic_sup = analisis_estadistico(resultados_escenario)
        nivel_serv_medio = np.mean([r["Nivel_Servicio"] for r in resultados_escenario])
        
        resultados_finales.append({
            "Escenario": f"ROP={rop}, Q={q}",
            "Costo Medio": round(costo_medio, 2),
            "IC 95% Inf": round(ic_inf, 2),
            "IC 95% Sup": round(ic_sup, 2),
            "Nivel Servicio (%)": round(nivel_serv_medio, 2)
        })
        
    df = pd.DataFrame(resultados_finales)
    print("\nResultados Comparativos de Escenarios:")
    print(df.to_string(index=False))
    
    # Identificación del mejor escenario (Menor Costo)
    mejor_escenario = df.loc[df['Costo Medio'].idxmin()]
    print("\nAnalisis de Optimizacion:")
    print(f"El escenario optimo es {mejor_escenario['Escenario']} con un Costo Medio de ${mejor_escenario['Costo Medio']}")

if __name__ == "__main__":
    main()
