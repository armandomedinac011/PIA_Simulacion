---
name: cement-logistics-simulation
description: Contexto e instrucciones para implementar correctamente una simulación de inventario y abastecimiento de cemento en Streamlit, usando simulación de eventos discretos, variables aleatorias, validación del modelo, exportación de resultados y comparación de escenarios.
---

# Cement Logistics Simulator - Contexto para Antigravity

## 1. Objetivo del proyecto

Construir una aplicación en **Streamlit** para simular el proceso logístico de abastecimiento de cemento desde una planta/proveedor hacia una bodega, CEDIS o tienda.  
La app debe permitir configurar variables del modelo, ejecutar una simulación estocástica de inventario, visualizar resultados, guardar la base de datos de eventos generados y comparar múltiples escenarios.

La simulación debe servir para responder preguntas como:

- ¿Con qué frecuencia se rompe stock?
- ¿Cuál es el nivel de servicio bajo los parámetros actuales?
- ¿Qué pasa si aumenta la demanda?
- ¿Qué pasa si se modifica el punto de reorden?
- ¿Qué cantidad de reabastecimiento reduce rupturas sin saturar la bodega?
- ¿Qué escenario tiene mejor balance entre inventario promedio y servicio?

El enfoque correcto para este proyecto es una **simulación de eventos discretos** aplicada a inventarios/logística, porque el sistema cambia en eventos puntuales: llegada de demanda, disparo de pedido de reabastecimiento y llegada del reabastecimiento.

---

## 2. Fundamento metodológico que debe respetarse

La app debe seguir el ciclo básico de desarrollo de un modelo de simulación:

1. Definir objetivo del estudio.
2. Recolectar o fijar datos/parámetros del sistema real.
3. Formular modelo conceptual.
4. Codificar el modelo.
5. Verificar y validar.
6. Ejecutar escenarios.
7. Analizar resultados.
8. Repetir si el modelo no representa adecuadamente el sistema.

Para este proyecto:

- **Entradas:** parámetros del formulario.
- **Procesos:** eventos, reglas de inventario, demanda y reabastecimiento.
- **Variables de estado:** tiempo simulado, inventario actual, pedidos pendientes, rupturas, demanda atendida.
- **Salidas:** base de eventos, métricas, gráficos, recomendaciones y comparación de escenarios.

---

## 3. Tipo de simulación a implementar

Implementar el modelo como:

- **Dinámico:** cambia con el tiempo.
- **Discreto:** el estado cambia en eventos específicos.
- **Estocástico:** la demanda/llegadas pueden generarse con variables aleatorias.
- **Digital/computacional:** implementado en Python.
- **Fuera de tiempo real:** la simulación corre rápidamente aunque represente días/semanas/meses.

No usar incremento fijo como enfoque principal, salvo para gráficos o agregaciones posteriores.  
Usar **incremento variable / calendario de eventos**, donde el reloj salta directamente al próximo evento relevante.

---

## 4. Variables obligatorias del formulario

La pantalla inicial debe pedir exactamente estas variables:

| Variable | Tipo | Unidad sugerida | Significado | Validación |
|---|---:|---|---|---|
| `CAPACIDAD_BODEGA` | numérica | ton | Capacidad máxima de almacenamiento de cemento. | `> 0` |
| `STOCK_INICIAL` | numérica | ton | Inventario disponible al inicio. | `0 <= STOCK_INICIAL <= CAPACIDAD_BODEGA` |
| `PUNTO_REORDEN` | numérica | ton | Nivel de inventario/inventario-posicion que dispara un pedido. | `0 <= PUNTO_REORDEN < CAPACIDAD_BODEGA` |
| `CANTIDAD_REABASTECIMIENTO` | numérica | ton | Cantidad solicitada al proveedor cuando se activa reorden. | `> 0` |
| `TIEMPO_ENTRE_LLEGADAS` | numérica | días | Media del tiempo entre llegadas de demanda. | `> 0` |
| `TAMANO_PEDIDO` | numérica | ton | Tamaño de cada demanda/pedido del cliente/tienda. | `> 0` |
| `LEAD_TIME_PROVEEDOR` | numérica | días | Tiempo entre emitir reabastecimiento y recibirlo. | `>= 0` |
| `TIEMPO_SIMULACION` | numérica | días | Horizonte total de simulación. | `> 0` |

Parámetros opcionales recomendados:

| Variable | Tipo | Default | Uso |
|---|---:|---:|---|
| `RANDOM_SEED` | entero | 42 | Reproducibilidad. |
| `PERMITIR_BACKORDER` | booleano | false | Si true, registra demanda pendiente; si false, pérdida de venta. |
| `GUARDAR_RESULTADOS` | booleano | true | Guarda eventos y resumen de escenario. |
| `NOMBRE_ESCENARIO` | texto | "Escenario base" | Identificación de la corrida. |

---

## 5. Interpretación logística del modelo

Usar una política de inventario tipo **(s, Q)**:

- `s = PUNTO_REORDEN`
- `Q = CANTIDAD_REABASTECIMIENTO`

Regla base:

> Si el inventario-posicion es menor o igual al punto de reorden, se emite un pedido de reabastecimiento por `CANTIDAD_REABASTECIMIENTO`, que llegará después de `LEAD_TIME_PROVEEDOR`.

Definir:

```text
inventario_posicion = stock_actual + cantidad_en_pedidos_pendientes - backorders
```

Esto evita emitir reabastecimientos duplicados cuando ya hay pedidos pendientes.

---

## 6. Aleatoriedad y generación de demanda

El modelo debe permitir aleatoriedad para representar incertidumbre real.

### Llegadas de demanda

Usar como base una distribución **exponencial** para los tiempos entre llegadas:

```python
interarrival = rng.exponential(scale=TIEMPO_ENTRE_LLEGADAS)
```

Equivalente por transformada inversa:

```python
U = rng.uniform(0, 1)
interarrival = -TIEMPO_ENTRE_LLEGADAS * log(1 - U)
```

Motivo: en simulación de llegadas, la exponencial es útil para modelar tiempos entre eventos cuando los arribos son irregulares.

### Tamaño de demanda

Implementación base:

```python
demanda = TAMANO_PEDIDO
```

Extensión opcional:

```python
demanda = max(1, rng.poisson(lam=TAMANO_PEDIDO))
```

Para el proyecto actual, usar demanda fija como default para mantener la app clara y controlable; permitir estocástica solo como opción avanzada.

### Lead time

Implementación base:

```python
lead_time = LEAD_TIME_PROVEEDOR
```

No volver aleatorio el lead time a menos que el usuario lo pida o existan datos históricos.

---

## 7. Motor de simulación recomendado

Usar Python puro con `heapq` para el calendario de eventos.  
No es obligatorio usar SimPy, aunque se puede si el proyecto crece. Para Streamlit es más transparente implementar un motor propio simple y trazable.

### Entidades principales

Crear dataclasses:

```python
@dataclass
class SimulationParams:
    capacidad_bodega: float
    stock_inicial: float
    punto_reorden: float
    cantidad_reabastecimiento: float
    tiempo_entre_llegadas: float
    tamano_pedido: float
    lead_time_proveedor: float
    tiempo_simulacion: float
    random_seed: int = 42
    permitir_backorder: bool = False
    guardar_resultados: bool = True
    nombre_escenario: str = "Escenario base"

@dataclass(order=True)
class Event:
    time: float
    priority: int
    event_type: str
    payload: dict = field(default_factory=dict, compare=False)
```

### Tipos de evento

Usar estos eventos:

```text
DEMANDA
LLEGADA_REABASTECIMIENTO
FIN_SIMULACION
```

Opcional:

```text
EMISION_REABASTECIMIENTO
```

Aunque puede registrarse como acción derivada dentro del evento `DEMANDA`.

### Estado de simulación

Mantener un objeto/dict de estado:

```python
state = {
    "time": 0.0,
    "stock": STOCK_INICIAL,
    "backorders": 0.0,
    "pending_orders": [],  # lista de pedidos pendientes
    "next_order_id": 1,
    "total_demand": 0.0,
    "fulfilled_demand": 0.0,
    "lost_demand": 0.0,
    "orders_total": 0,
    "orders_fulfilled_full": 0,
    "stockouts": 0,
    "replenishments_requested": 0,
    "replenishments_received": 0,
    "area_inventory": 0.0,
    "last_event_time": 0.0,
    "stock_min": STOCK_INICIAL,
    "stock_max": STOCK_INICIAL,
}
```

---

## 8. Algoritmo de simulación

Pseudocódigo principal:

```text
validar parámetros
crear rng con semilla
inicializar reloj t = 0
inicializar stock = STOCK_INICIAL
crear calendario de eventos

programar primera DEMANDA en t + exponencial(TIEMPO_ENTRE_LLEGADAS)
programar FIN_SIMULACION en TIEMPO_SIMULACION

mientras calendario no esté vacío:
    tomar siguiente evento ordenado por tiempo
    si evento.time > TIEMPO_SIMULACION:
        romper

    actualizar área de inventario:
        area_inventory += stock * (evento.time - last_event_time)
        last_event_time = evento.time
        time = evento.time

    si evento == DEMANDA:
        procesar demanda
        registrar evento
        si inventario_posicion <= PUNTO_REORDEN:
            emitir reabastecimiento si regla lo permite
        programar próxima demanda

    si evento == LLEGADA_REABASTECIMIENTO:
        recibir inventario
        respetar CAPACIDAD_BODEGA
        registrar evento

    si evento == FIN_SIMULACION:
        cerrar simulación
        romper

calcular métricas finales
devolver eventos_df, inventory_df, summary_df, metrics
```

---

## 9. Reglas de procesamiento de demanda

Cuando ocurre una demanda:

```python
stock_before = state["stock"]
demanda = params.tamano_pedido
state["orders_total"] += 1
state["total_demand"] += demanda

if state["stock"] >= demanda:
    fulfilled = demanda
    shortage = 0
    state["stock"] -= demanda
    state["orders_fulfilled_full"] += 1
else:
    fulfilled = state["stock"]
    shortage = demanda - fulfilled
    state["stock"] = 0
    state["stockouts"] += 1
    state["lost_demand"] += shortage

    if params.permitir_backorder:
        state["backorders"] += shortage

state["fulfilled_demand"] += fulfilled
```

Después de procesar la demanda, evaluar reorden:

```python
inventory_position = stock + pending_qty - backorders

if inventory_position <= PUNTO_REORDEN:
    emitir pedido por CANTIDAD_REABASTECIMIENTO
    arrival_time = current_time + LEAD_TIME_PROVEEDOR
    agregar evento LLEGADA_REABASTECIMIENTO
```

---

## 10. Reglas de reabastecimiento

Cuando llega un reabastecimiento:

```python
stock_before = stock
received_qty = CANTIDAD_REABASTECIMIENTO

if permitir_backorder and backorders > 0:
    qty_to_backorders = min(received_qty, backorders)
    backorders -= qty_to_backorders
    fulfilled_demand += qty_to_backorders
    received_qty -= qty_to_backorders

stock = min(CAPACIDAD_BODEGA, stock + received_qty)
overflow = max(0, stock_before + received_qty - CAPACIDAD_BODEGA)
```

Registrar si hubo inventario excedente por capacidad.

---

## 11. Base de datos de eventos a exportar

Cada corrida debe generar una tabla `events_df` con una fila por evento. Columnas recomendadas:

```text
simulation_id
scenario_name
event_id
time
calendar_date_optional
event_type
stock_before
demand_qty
fulfilled_qty
shortage_qty
stock_after
inventory_position
reorder_triggered
replenishment_order_id
replenishment_qty
replenishment_arrival_time
pending_orders_qty
backorders
overflow_qty
random_seed
notes
```

Tabla de serie de inventario `inventory_df`:

```text
simulation_id
time
stock
inventory_position
backorders
pending_orders_qty
event_type
```

Tabla resumen `summary_df`:

```text
simulation_id
scenario_name
run_timestamp
CAPACIDAD_BODEGA
STOCK_INICIAL
PUNTO_REORDEN
CANTIDAD_REABASTECIMIENTO
TIEMPO_ENTRE_LLEGADAS
TAMANO_PEDIDO
LEAD_TIME_PROVEEDOR
TIEMPO_SIMULACION
random_seed
nivel_servicio
fill_rate
rupturas_stock
inventario_promedio
stock_min
stock_max
demanda_total
demanda_atendida
demanda_perdida
pedidos_totales
pedidos_atendidos_completos
reabastecimientos_emitidos
reabastecimientos_recibidos
overflow_total
```

---

## 12. Métricas finales obligatorias

Calcular:

```python
nivel_servicio = orders_fulfilled_full / orders_total
fill_rate = fulfilled_demand / total_demand
rupturas_stock = stockouts
inventario_promedio = area_inventory / TIEMPO_SIMULACION
stock_min = min(stock registrado)
stock_max = max(stock registrado)
demanda_total = total_demand
demanda_atendida = fulfilled_demand
demanda_perdida = lost_demand
pedidos_totales = orders_total
pedidos_atendidos = orders_fulfilled_full
```

Cuidar división entre cero:

```python
if orders_total == 0:
    nivel_servicio = 1.0

if total_demand == 0:
    fill_rate = 1.0
```

---

## 13. Validaciones antes de ejecutar

La app no debe iniciar simulación si existen errores críticos.

### Errores críticos

- `CAPACIDAD_BODEGA <= 0`
- `STOCK_INICIAL < 0`
- `STOCK_INICIAL > CAPACIDAD_BODEGA`
- `PUNTO_REORDEN < 0`
- `PUNTO_REORDEN >= CAPACIDAD_BODEGA`
- `CANTIDAD_REABASTECIMIENTO <= 0`
- `TIEMPO_ENTRE_LLEGADAS <= 0`
- `TAMANO_PEDIDO <= 0`
- `LEAD_TIME_PROVEEDOR < 0`
- `TIEMPO_SIMULACION <= 0`

### Advertencias inteligentes

Generar advertencias, pero permitir ejecutar:

1. Riesgo de ruptura:
   ```text
   demanda_esperada_durante_lead_time =
   (LEAD_TIME_PROVEEDOR / TIEMPO_ENTRE_LLEGADAS) * TAMANO_PEDIDO
   ```
   Si `PUNTO_REORDEN < demanda_esperada_durante_lead_time`, mostrar:
   > El punto de reorden parece bajo frente a la demanda esperada durante el lead time.

2. Riesgo de saturación:
   Si `PUNTO_REORDEN + CANTIDAD_REABASTECIMIENTO > CAPACIDAD_BODEGA`, mostrar:
   > El reabastecimiento podría exceder la capacidad de bodega.

3. Horizonte muy corto:
   Si `TIEMPO_SIMULACION < 5 * TIEMPO_ENTRE_LLEGADAS`, mostrar:
   > El horizonte puede ser corto para obtener resultados estables.

4. Falta de reproducibilidad:
   Si no hay semilla, recomendar usar `RANDOM_SEED`.

---

## 14. Estructura recomendada del proyecto

```text
project/
├─ app.py
├─ requirements.txt
├─ README.md
├─ src/
│  ├─ simulation/
│  │  ├─ __init__.py
│  │  ├─ engine.py
│  │  ├─ models.py
│  │  ├─ validation.py
│  │  └─ metrics.py
│  ├─ ui/
│  │  ├─ __init__.py
│  │  ├─ theme.py
│  │  ├─ components.py
│  │  └─ pages.py
│  └─ data/
│     ├─ storage.py
│     └─ export.py
├─ data/
│  ├─ simulations_summary.csv
│  └─ simulation_events/
└─ exports/
```

`requirements.txt` mínimo:

```text
streamlit
pandas
numpy
plotly
openpyxl
```

Opcional:

```text
simpy
scipy
```

---

## 15. Pantallas que debe tener la app

### Pantalla 1 - Nueva simulación

Objetivo: capturar parámetros.

Secciones:

- Inventario:
  - `CAPACIDAD_BODEGA`
  - `STOCK_INICIAL`
  - `PUNTO_REORDEN`
- Reabastecimiento:
  - `CANTIDAD_REABASTECIMIENTO`
  - `TAMANO_PEDIDO`
- Demanda:
  - `TIEMPO_ENTRE_LLEGADAS`
  - `LEAD_TIME_PROVEEDOR`
- Horizonte:
  - `TIEMPO_SIMULACION`
- Opciones:
  - `PERMITIR_BACKORDER`
  - `GUARDAR_RESULTADOS`
  - `RANDOM_SEED`

Botones:

- `Restablecer`
- `Iniciar simulación`

### Pantalla 2 - Generando simulación

Objetivo: mostrar estado visible.

Elementos:

- Barra de progreso.
- Pasos:
  1. Validando parámetros.
  2. Preparando eventos de demanda.
  3. Ejecutando simulación.
  4. Construyendo resultados y base de datos.
- Tiempo transcurrido.
- Registros generados.
- Mensaje: "No cierres la aplicación mientras la simulación está en curso."

### Pantalla 3 - Resultados de simulación

Objetivo: analizar desempeño.

Elementos:

- KPIs:
  - Nivel de servicio.
  - Rupturas de stock.
  - Inventario promedio.
  - Pedidos atendidos.
- Gráfico:
  - Evolución del inventario.
  - Línea de punto de reorden.
  - Marcadores de reabastecimiento.
- Tabla:
  - Indicadores del modelo.
- Gráfico:
  - Eventos de la simulación.
- Panel:
  - Hallazgos y recomendaciones.
- Botones:
  - Nueva simulación.
  - Guardar y comparar.
  - Exportar resultados.

### Pantalla 4 - Base de datos de simulaciones

Objetivo: comparar y exportar corridas.

Elementos:

- Historial de simulaciones.
- Filtros por escenario, fecha, estado.
- Exportar CSV.
- Exportar Excel.
- Comparar seleccionadas.
- Comparador rápido con 2 o 3 escenarios.

---

## 16. Estilo visual obligatorio

Usar diseño minimalista, profesional y consistente.

Paleta base:

```css
--app-bg: #F5F7FB;
--card-bg: #FFFFFF;
--border: #E8EDF5;
--text-main: #0F172A;
--text-muted: #64748B;
--primary-blue: #0B5FFF;
--primary-blue-dark: #064DCC;
--accent-orange: #FF5A1F;
--success-green: #16A34A;
--warning-orange: #F97316;
--danger-red: #EF4444;
--shadow-soft: rgba(15, 23, 42, 0.06);
```

Reglas de UI:

- Fondo general `#F5F7FB`.
- Tarjetas `#FFFFFF`.
- Bordes sutiles `#E8EDF5`.
- Botón principal naranja para iniciar/exportar.
- Botón azul para guardar/comparar.
- Mucho espacio en blanco.
- No saturar la pantalla.
- Usar tarjetas con `border-radius: 16px`.
- Gráficos limpios, sin exceso de colores.
- Mantener etiquetas en español.
- Variables técnicas en mayúsculas exactas.

---

## 17. Implementación en Streamlit: reglas

Usar `st.session_state` para conservar:

```python
params
is_running
events_df
inventory_df
summary_df
metrics
simulation_history
selected_simulation_id
```

Flujo:

1. Usuario llena formulario.
2. Se validan parámetros.
3. Si hay errores, mostrar `st.error` y bloquear botón.
4. Si solo hay advertencias, mostrar `st.warning` pero permitir ejecución.
5. Al iniciar, ejecutar `run_simulation(params)`.
6. Guardar resultados en `session_state`.
7. Mostrar resultados y permitir exportar.
8. Si `GUARDAR_RESULTADOS`, persistir CSV/Excel.

No recalcular la simulación automáticamente cada vez que Streamlit recargue.  
Usar botón explícito para ejecutar.

---

## 18. Función esperada del motor

Implementar una función principal:

```python
def run_simulation(params: SimulationParams) -> SimulationResult:
    """
    Ejecuta una simulación de inventario y abastecimiento de cemento con eventos discretos.

    Returns:
        SimulationResult con:
        - events_df
        - inventory_df
        - summary_df
        - metrics
        - warnings
    """
```

Crear objeto de resultado:

```python
@dataclass
class SimulationResult:
    simulation_id: str
    events_df: pd.DataFrame
    inventory_df: pd.DataFrame
    summary_df: pd.DataFrame
    metrics: dict
    warnings: list[str]
```

---

## 19. Recomendaciones automáticas

Generar recomendaciones simples después de cada simulación:

1. Si `rupturas_stock > 0`:
   - Sugerir aumentar `PUNTO_REORDEN`.
   - Sugerir reducir `LEAD_TIME_PROVEEDOR`.
   - Sugerir aumentar `CANTIDAD_REABASTECIMIENTO`.

2. Si `inventario_promedio` es muy alto:
   - Sugerir reducir `CANTIDAD_REABASTECIMIENTO`.
   - Sugerir reducir `STOCK_INICIAL`.
   - Sugerir revisar `PUNTO_REORDEN`.

3. Si hay `overflow_total > 0`:
   - Sugerir bajar reabastecimiento o aumentar capacidad.

4. Si `nivel_servicio >= 0.95` y `inventario_promedio` bajo:
   - Marcar escenario como eficiente.

---

## 20. Comparación de escenarios

Para comparar escenarios, usar estos criterios:

- Mejor nivel de servicio.
- Menor ruptura de stock.
- Menor inventario promedio.
- Menor demanda perdida.
- Balance general.

Score simple recomendado:

```python
score = (
    0.45 * nivel_servicio
    + 0.25 * fill_rate
    - 0.15 * normalized_stockouts
    - 0.15 * normalized_inventory_avg
)
```

No recomendar automáticamente el escenario con menor inventario si tiene muchas rupturas.

---

## 21. Pruebas mínimas

Crear pruebas o validaciones internas para:

1. Si no hay demanda, el stock no cambia.
2. Si demanda fija es menor al stock y no se llega al punto de reorden, no debe haber reabastecimiento.
3. Si stock cae debajo del punto de reorden, debe programarse reabastecimiento.
4. Si llega reabastecimiento, el stock aumenta sin exceder capacidad.
5. Si demanda excede stock, se registra ruptura.
6. Con la misma semilla, la simulación debe ser reproducible.
7. `inventario_promedio` debe calcularse como promedio ponderado por tiempo, no como promedio simple de filas.

---

## 22. Errores que se deben evitar

- No usar loops por cada día si el modelo es de eventos discretos.
- No recalcular toda la simulación al mover cualquier widget.
- No permitir valores negativos.
- No permitir `STOCK_INICIAL` mayor a `CAPACIDAD_BODEGA`.
- No duplicar pedidos si ya hay reabastecimiento pendiente y el inventario-posicion cubre la regla.
- No calcular inventario promedio como promedio simple de eventos.
- No mezclar unidades sin especificarlas.
- No sobrescribir corridas anteriores.
- No exportar solo métricas; también exportar eventos.
- No usar colores saturados ni pantallas cargadas.

---

## 23. Entregables esperados

La implementación debe producir:

1. App Streamlit ejecutable.
2. Pantalla inicial con formulario.
3. Pantalla de carga/progreso.
4. Pantalla de resultados.
5. Pantalla de base de datos/exportación.
6. Motor de simulación separado del código UI.
7. Exportación CSV y Excel.
8. Base histórica de simulaciones.
9. Gráficos:
   - Evolución de inventario.
   - Eventos por tiempo.
   - Comparación de escenarios.
10. Validaciones y recomendaciones.

---

## 24. Criterio de aceptación

La simulación se considera correcta si:

- Usa calendario de eventos.
- Genera demanda con tiempos entre llegadas.
- Disminuye stock ante demanda.
- Registra demanda atendida y no atendida.
- Dispara reabastecimiento al llegar al punto de reorden.
- Respeta lead time.
- Respeta capacidad de bodega.
- Calcula métricas de servicio, rupturas e inventario promedio.
- Guarda eventos y resumen.
- Permite comparar escenarios.
- Es reproducible con semilla.

---

## 25. Prompt interno para el agente

Cuando se pida programar o modificar esta app, actuar como desarrollador experto en simulación, Python y Streamlit.  
Antes de escribir código, revisar:

1. Variables obligatorias.
2. Validaciones.
3. Lógica de eventos discretos.
4. Separación entre motor y UI.
5. Exportación de resultados.
6. Coherencia visual del dashboard.

Priorizar claridad, trazabilidad y facilidad de explicar el modelo frente a complejidad innecesaria.
