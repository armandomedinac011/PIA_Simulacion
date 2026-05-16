# Escrito final del proyecto

# Simulacion estocastica de inventario y abastecimiento para un centro de distribucion de materiales de construccion

## Integrantes y division sugerida

Este escrito esta dividido para una exposicion de 4 personas. Cada integrante puede estudiar y presentar una seccion, aunque todas las partes estan conectadas dentro del mismo proyecto.

| Integrante | Tema principal | Archivos que domina | Enfoque de exposicion |
|---|---|---|---|
| Persona 1 | Contexto del problema, modelo conceptual y Semana 3 | `Entregable1_Documento.md`, `Instrucciones_Simulacion.txt`, `SKILL.md` | Explicar el problema logistico, las variables, la aleatoriedad y las distribuciones. |
| Persona 2 | Motor de simulacion en SimPy y estructura del codigo original | `src/simulation_engine.py`, `src/database.py`, `src/charts.py`, `app.py` | Explicar como se ejecutan los eventos, como se calculan KPIs y como se guardan datos. |
| Persona 3 | Experimentacion, optimizacion y analisis actuarial | `Sem1.2.0.py`, `dashboard_experiments.py`, archivos de `data/` | Explicar DOE, replicas, reduccion de varianza, costos, riesgo, sensibilidad y resultados. |
| Persona 4 | Visualizacion final, Streamlit, Pygame y presentacion | `src/ui_components.py`, `app.py`, `dashboard_pygame.py`, `DASHBOARD_PYGAME_README.md` | Explicar las interfaces, dashboards, flujo amigable y propuesta de video/exposicion. |

---

# 1. Descripcion general del proyecto

El proyecto consiste en una simulacion de eventos discretos aplicada a un centro de distribucion de materiales de construccion, inspirado en una operacion tipo Construrama/Cemex. El objetivo central es estudiar el comportamiento del inventario de cemento ante demanda incierta y tiempos variables de reabastecimiento.

En terminos practicos, el modelo responde a una pregunta operativa:

> ¿Cuando conviene pedir material al proveedor y cuanto se debe pedir para evitar desabasto sin mantener inventario excesivo?

El sistema simula la llegada de clientes, el consumo de inventario, la emision de pedidos al proveedor, el tiempo de entrega del proveedor y la recepcion del material. Cada corrida genera eventos y metricas como nivel de servicio, ventas perdidas, inventario final, unidades vendidas y ordenes al proveedor.

El proyecto combina tres capas:

1. **Motor de simulacion:** construido con SimPy para modelar eventos discretos.
2. **Interfaz principal Streamlit:** permite capturar parametros, ejecutar una simulacion y visualizar resultados.
3. **Dashboard Pygame:** permite explorar muchos escenarios generados de forma independiente, con ranking, riesgo, sensibilidad y detalle por escenario.

La version final conserva el codigo original y agrega componentes independientes para experimentacion y dashboard, evitando romper la aplicacion base.

---

# 2. Contexto del problema logistico

Un centro de distribucion de cemento enfrenta incertidumbre diaria:

- Los clientes no llegan en intervalos exactos.
- Cada cliente puede pedir cantidades distintas.
- El proveedor no siempre entrega exactamente en el mismo tiempo.
- Si el inventario se agota, hay ventas perdidas.
- Si se mantiene demasiado inventario, suben los costos de almacenamiento y capital inmovilizado.

Por eso se usa una politica de inventario tipo `(s, Q)`:

- `s` es el punto de reorden o `PUNTO_REORDEN`.
- `Q` es la cantidad que se solicita cada vez o `CANTIDAD_REABASTECIMIENTO`.

La regla es:

> Cuando el inventario cae a un nivel menor o igual al punto de reorden, y no existe ya un pedido en transito, se emite una orden al proveedor por una cantidad fija de reabastecimiento.

Este sistema es adecuado para simulacion de eventos discretos porque los cambios importantes ocurren en momentos puntuales:

- Llega un cliente.
- Se surte o se pierde una venta.
- Se emite una orden al proveedor.
- Llega el reabastecimiento.

---

# 3. Variables principales del modelo

## 3.1 Variables de entrada

| Variable | Significado | Unidad conceptual | Rol en el modelo |
|---|---|---|---|
| `CAPACIDAD_BODEGA` | Capacidad maxima de almacenamiento | Toneladas o unidades | Limita el inventario maximo que puede entrar. |
| `STOCK_INICIAL` | Inventario disponible al inicio | Toneladas o unidades | Define el estado inicial del sistema. |
| `PUNTO_REORDEN` | Nivel que dispara una orden | Toneladas o unidades | Controla que tan temprano se pide al proveedor. |
| `CANTIDAD_REABASTECIMIENTO` | Cantidad solicitada al proveedor | Toneladas o unidades | Controla el tamano de cada reposicion. |
| `TIEMPO_ENTRE_LLEGADAS` | Tiempo promedio entre clientes | Dias | Controla la frecuencia de demanda. |
| `TAMANO_PEDIDO` | Pedido promedio de cliente | Toneladas o unidades | Controla la intensidad de consumo por cliente. |
| `LEAD_TIME_PROVEEDOR` | Tiempo medio de entrega | Dias | Controla el retraso entre pedir y recibir. |
| `TIEMPO_SIMULACION` | Horizonte de la corrida | Dias | Define cuanto tiempo se simula. |

## 3.2 Variables de estado

| Variable | Archivo | Funcion |
|---|---|---|
| `inventario` | `src/simulation_engine.py` | Contenedor SimPy que almacena el nivel actual de producto. |
| `pedido_en_transito` | `src/simulation_engine.py` | Evita duplicar ordenes mientras una orden sigue pendiente. |
| `historial_inventario` | `src/simulation_engine.py` | Guarda pares `(dia, inventario)` para graficar el diente de sierra. |
| `registro_eventos` | `src/simulation_engine.py` | Guarda cada evento de la simulacion en forma tabular. |

## 3.3 Variables de salida y KPIs

| KPI | Formula o interpretacion |
|---|---|
| `Inventario Final` | Nivel de inventario al terminar la corrida. |
| `Total Solicitudes` | `Pedidos Surtidos + Ventas Perdidas`. |
| `Pedidos Surtidos` | Solicitudes atendidas correctamente. |
| `Ventas Perdidas` | Solicitudes no atendidas por falta de inventario. |
| `Nivel Servicio` | `Pedidos Surtidos / Total Solicitudes * 100`. |
| `Unidades Vendidas` | Total de unidades realmente despachadas. |
| `Ordenes Proveedor` | Numero de ordenes emitidas al proveedor. |
| `Inventario Promedio` | Promedio ponderado por tiempo del inventario. |
| `Costo Total` | Costo de ordenar + costo de escasez + costo de inventario. |
| `Fill Rate Unidades` | Porcentaje de unidades surtidas respecto a unidades demandadas. |
| `VaR/CVaR 95` | Medidas de riesgo usadas en el dashboard actuarial. |

---

# 4. Semana 3: Aleatoriedad y analisis

## 4.1 Implementacion de variables aleatorias

El proyecto incorpora aleatoriedad en tres partes del sistema:

1. **Llegadas de clientes**
   - Archivo: `src/simulation_engine.py`
   - Funcion: `proceso_clientes`
   - Implementacion: `random.expovariate(tasa_llegada)`
   - Interpretacion: el tiempo entre clientes no es fijo, sino aleatorio.

2. **Tamano del pedido**
   - Archivo: `src/simulation_engine.py`
   - Funcion: `proceso_clientes`
   - Implementacion: `random.gauss(media_pedido, desviacion)`
   - Desviacion usada: 20% de la media.
   - Interpretacion: cada cliente pide alrededor del promedio, pero con variacion.

3. **Lead time del proveedor**
   - Archivo: `src/simulation_engine.py`
   - Funcion: `proceso_reabastecimiento`
   - Implementacion: `random.uniform(max(0.1, lead_time_base - 0.5), lead_time_base + 0.5)`
   - Interpretacion: el proveedor puede llegar medio dia antes o medio dia despues del tiempo base.

## 4.2 Seleccion y justificacion de distribuciones

### Distribucion exponencial para llegadas

La distribucion exponencial se usa para tiempos entre llegadas porque representa un proceso donde los eventos ocurren de forma irregular. En simulacion, esto equivale a modelar la llegada de clientes como un proceso de Poisson.

En el codigo:

```python
tasa_llegada = 1.0 / centro.parametros['TIEMPO_ENTRE_LLEGADAS']
tiempo_siguiente_llegada = random.expovariate(tasa_llegada)
```

Si `TIEMPO_ENTRE_LLEGADAS` baja, llegan clientes mas frecuentemente. Si sube, llegan menos clientes.

### Distribucion normal para tamano de pedido

El tamano de pedido se modela con una normal alrededor de `TAMANO_PEDIDO`:

```python
desviacion = media_pedido * 0.2
tamano_pedido_real = max(1, int(random.gauss(media_pedido, desviacion)))
```

La justificacion es que muchos pedidos se concentran alrededor de un valor promedio, pero existen pedidos menores y mayores. Se usa `max(1, ...)` para evitar pedidos negativos o cero.

### Distribucion uniforme para lead time

El tiempo de entrega del proveedor se modela como uniforme en un rango de mas/menos 0.5 dias:

```python
lead_time_real = random.uniform(max(0.1, lead_time_base - 0.5), lead_time_base + 0.5)
```

La justificacion es que no se asume una forma compleja de retrasos, sino una variabilidad operativa simple alrededor del valor esperado.

### Distribuciones usadas en el prototipo `Sem1.2.0.py`

El archivo `Sem1.2.0.py` usa una version academica anterior con:

- Exponencial para tiempos entre llegadas.
- Poisson para tamano de pedido.
- Triangular para lead time.

Este archivo demuestra el avance conceptual de Semanas 3 y 4, mientras que `src/simulation_engine.py` es el motor integrado en la app Streamlit.

## 4.3 Simulacion de escenarios base

El escenario base se configura desde `app.py` en la pantalla de formulario. Los valores por defecto son:

| Variable | Valor base en Streamlit |
|---|---:|
| `CAPACIDAD_BODEGA` | 10000 |
| `STOCK_INICIAL` | 2000 |
| `PUNTO_REORDEN` | 1500 |
| `CANTIDAD_REABASTECIMIENTO` | 5000 |
| `TIEMPO_ENTRE_LLEGADAS` | 1.5 |
| `TAMANO_PEDIDO` | 150 |
| `LEAD_TIME_PROVEEDOR` | 2.0 |
| `TIEMPO_SIMULACION` | 180 |

Cuando el usuario presiona "Iniciar simulacion", `app.py` llama a:

```python
ejecutar_simulacion_parametrizada(st.session_state.parametros_actuales)
```

El resultado se guarda en tres objetos:

- `df_eventos`: eventos individuales.
- `df_historial`: evolucion del inventario.
- `kpis`: metricas finales.

## 4.4 Recoleccion de datos de salida

La recoleccion se realiza en dos niveles:

1. **Eventos individuales**
   - Cada llegada, venta perdida, emision de pedido y recepcion se registra con dia, tipo, cantidad, inventario previo y posterior.

2. **Resumen de corrida**
   - Se registran parametros y KPIs en `data/simulations.csv`.

La funcion responsable es `guardar_simulacion` en `src/database.py`.

Archivos generados:

- `data/events_YYYYMMDD_HHMMSS.csv`: eventos de una corrida.
- `data/simulations.csv`: resumen historico de corridas.
- `data/all_events.csv`: archivo maestro de eventos si se siguen ejecutando simulaciones desde Streamlit.

## 4.5 Analisis estadistico preliminar

El analisis preliminar se hace con:

- Nivel de servicio.
- Ventas perdidas.
- Inventario promedio.
- Ordenes al proveedor.
- Unidades vendidas.

En la pantalla de resultados, Streamlit muestra:

- Tarjetas de KPIs.
- Grafica de inventario tipo diente de sierra.
- Recomendacion automatica:
  - Si hay ventas perdidas, se sugiere ajustar el punto de reorden.
  - Si el inventario promedio es muy alto, se sugiere reducir cantidad de reabastecimiento.
  - Si no hay rupturas y el inventario no es excesivo, se considera buen nivel de servicio.

---

# 5. Semana 4: Experimentacion y optimizacion

## 5.1 Diseno de experimentos dentro de Streamlit

El motor original incluye la funcion `ejecutar_doe` en `src/simulation_engine.py`.

Esta funcion compara cuatro escenarios:

| Escenario | Cambio aplicado |
|---|---|
| Base | Usa `PUNTO_REORDEN` y `CANTIDAD_REABASTECIMIENTO` originales. |
| Aumento ROP | Incrementa el punto de reorden 50%. |
| Aumento Q | Incrementa la cantidad de reabastecimiento 20%. |
| ROP+Q Alto | Incrementa ambos parametros. |

Cada escenario se ejecuta con 10 replicas. Para cada replica se usa una semilla controlada:

```python
_, _, kpis = ejecutar_simulacion_parametrizada(parametros, semilla=rep + 42)
```

Esto aplica Common Random Numbers, una tecnica de reduccion de varianza.

## 5.2 Comparacion de escenarios

En cada escenario se calculan:

- Promedio de nivel de servicio.
- Promedio de ventas perdidas.
- Costo medio.
- Intervalo de confianza de 95% para el costo.

El costo simplificado del DOE original es:

```python
costo = kpis['Ordenes Proveedor'] * 1000 + kpis['Ventas Perdidas'] * 500
```

La tabla se muestra en la vista `doe` de `app.py`, y Streamlit identifica el escenario con menor `Costo_Medio`.

## 5.3 Experimentacion ampliada en `dashboard_experiments.py`

Para la version final se agrego un generador independiente de escenarios, sin modificar el codigo original.

Este archivo genera un diseno factorial que cruza todas las variables operables:

- Capacidad de bodega.
- Stock inicial.
- Punto de reorden.
- Cantidad de reabastecimiento.
- Tiempo entre llegadas.
- Tamano de pedido.
- Lead time.
- Horizonte de simulacion.

En perfil `compact`, cada variable tiene 2 niveles. Por lo tanto:

```text
2^8 = 256 escenarios
```

Con 3 replicas por escenario:

```text
256 * 3 = 768 corridas
```

Los datos generados se guardan en:

- `data/dashboard_experiments/scenario_runs.csv`
- `data/dashboard_experiments/scenario_summary.csv`
- `data/dashboard_experiments/scenario_events.csv`
- `data/dashboard_experiments/manifest.json`

## 5.4 Aplicacion de tecnicas de mejora u optimizacion

La optimizacion se aborda comparando politicas de inventario bajo multiples condiciones. No se usa un optimizador matematico cerrado, sino una optimizacion por experimentacion:

1. Se generan combinaciones de parametros.
2. Se ejecutan replicas con semillas controladas.
3. Se calcula costo, servicio y riesgo.
4. Se ordenan escenarios por costo medio, servicio, CVaR o probabilidad de ruptura.
5. Se seleccionan politicas que cumplen alto servicio con menor costo.

Esto es adecuado para simulacion porque el sistema es estocastico y la respuesta depende de interacciones dinamicas.

## 5.5 Reduccion de varianza

Se utiliza Common Random Numbers (CRN):

- La idea es que escenarios diferentes sean comparados bajo condiciones aleatorias equivalentes.
- En `ejecutar_doe`, las replicas usan semillas `rep + 42`.
- En `dashboard_experiments.py`, la semilla se construye con base en el escenario y la replica:

```python
seed = args.seed + scenario_index * 10_000 + replica
```

El objetivo es reducir ruido experimental y hacer mas justa la comparacion entre politicas.

## 5.6 Analisis de sensibilidad

El analisis de sensibilidad se implementa en `dashboard_pygame.py`, en la funcion:

```python
sensitivity_rows(self, metric, lower_is_better)
```

Esta funcion agrupa por cada parametro y compara el cambio promedio al pasar del nivel bajo al nivel alto. Se mide el impacto en:

- `Costo_Total_mean`
- `Nivel_Servicio_mean`

La vista "Sensibilidad" del dashboard muestra barras horizontales que indican que variables tienen mayor efecto sobre el costo o el servicio.

---

# 6. Semana 5: Presentacion final

## 6.1 Version final del modelo

La version final integra:

- Simulacion estocastica en SimPy.
- Interfaz Streamlit para ejecucion amigable.
- Persistencia en CSV.
- DOE integrado en Streamlit.
- Generador adicional de escenarios masivos.
- Dashboard Pygame interactivo.
- Documentacion de uso y escrito final.

El modelo final representa:

1. Llegadas aleatorias de clientes.
2. Pedidos aleatorios.
3. Reabastecimiento con lead time variable.
4. Restriccion de capacidad de bodega.
5. Politica de inventario `(s, Q)`.
6. Registro de eventos.
7. Analisis de KPIs.
8. Comparacion de escenarios.

## 6.2 Visualizacion con Streamlit

Streamlit se usa como interfaz principal. Su objetivo es que cualquier usuario pueda ejecutar la simulacion sin escribir codigo.

La app tiene cuatro vistas:

1. **Formulario**
   - Captura variables de entrada.
   - Muestra resumen del escenario.

2. **Carga**
   - Muestra progreso.
   - Ejecuta la simulacion.
   - Guarda los resultados.

3. **Resultados**
   - Muestra KPIs.
   - Grafica el inventario.
   - Da recomendaciones.
   - Permite exportar eventos.

4. **DOE**
   - Ejecuta experimentacion de Semana 4.
   - Compara escenarios.
   - Selecciona el menor costo medio.

## 6.3 Visualizacion con Pygame

Pygame se usa para un dashboard independiente, mas visual e interactivo. No reemplaza a Streamlit: lo complementa.

El dashboard Pygame tiene cinco pestañas:

| Pestaña | Funcion |
|---|---|
| Resumen | Muestra indicadores globales y grafica costo vs servicio. |
| Ranking | Ordena escenarios por costo, servicio, CVaR o ruptura. |
| Riesgo | Muestra VaR, CVaR, histogramas y fill rate. |
| Sensibilidad | Mide impacto de variables en costo y servicio. |
| Escenario | Presenta parametros, replicas, eventos y recomendacion del escenario seleccionado. |

La integracion se logra leyendo los CSV generados por `dashboard_experiments.py`. El dashboard no ejecuta el modelo directamente, sino que visualiza resultados ya generados. Esto separa computo y visualizacion, lo cual mejora la estabilidad.

## 6.4 Documentacion completa

La documentacion del proyecto esta repartida en:

- `Entregable1_Documento.md`: fundamentos, problema, objetivos y modelo base.
- `Instrucciones_Simulacion.txt`: guia de uso para ejecutar la app.
- `DASHBOARD_PYGAME_README.md`: instrucciones del dashboard Pygame.
- `ESCRITO_FINAL_PROYECTO_4_INTEGRANTES.md`: documento final integrador.

## 6.5 Video explicativo de 5 minutos

Guion sugerido:

| Tiempo | Persona | Contenido |
|---|---|---|
| 0:00 - 1:00 | Persona 1 | Presenta el problema logistico, objetivo, variables y por que se usa simulacion de eventos discretos. |
| 1:00 - 2:00 | Persona 2 | Explica el motor SimPy: clientes, inventario, reabastecimiento, KPIs y almacenamiento de datos. |
| 2:00 - 3:15 | Persona 3 | Explica aleatoriedad, distribuciones, DOE, replicas, CRN, costo, riesgo y sensibilidad. |
| 3:15 - 4:30 | Persona 4 | Muestra Streamlit y Pygame: formulario, resultados, dashboard, ranking y graficas. |
| 4:30 - 5:00 | Todos o Persona 1 | Conclusiones: mejor politica, utilidad del modelo y posibles mejoras futuras. |

## 6.6 Exposicion del proyecto

La exposicion puede seguir este orden:

1. Contexto y problema.
2. Modelo conceptual.
3. Variables y distribuciones.
4. Codigo del motor.
5. Recoleccion de datos.
6. Experimentacion y optimizacion.
7. Visualizacion Streamlit.
8. Visualizacion Pygame.
9. Conclusiones y recomendaciones.

---

# 7. Analisis archivo por archivo

## 7.1 `README.md`

Archivo breve con el nombre del proyecto:

```text
PIA_Simulacion
Proyecto final
```

Funciona como identificador general del repositorio.

## 7.2 `Entregable1_Documento.md`

Documento academico de Semanas 1 y 2. Incluye:

- Definicion del problema.
- Justificacion.
- Objetivos.
- Variables de entrada, estado y salida.
- Supuestos del modelo.
- Tipo de simulacion.
- Justificacion de SimPy.
- Modelo conceptual.
- Diagrama de flujo.
- Cronograma.

Este archivo da el marco teorico y metodologico del proyecto.

## 7.3 `Instrucciones_Simulacion.txt`

Guia de uso para usuarios. Explica:

- Que simula el proyecto.
- Como instalar dependencias.
- Como ejecutar Streamlit.
- Como usar la aplicacion.
- Como ejecutar el DOE de Semana 4.

Es util para la entrega porque demuestra que el proyecto no solo tiene codigo, sino instrucciones reproducibles.

## 7.4 `SKILL.md`

Archivo de especificacion tecnica del proyecto. Describe:

- Objetivo esperado de la app.
- Variables obligatorias.
- Interpretacion logistica.
- Reglas de inventario.
- Recomendaciones metodologicas.
- Salidas esperadas.

Aunque no es parte de la ejecucion directa, sirve como documento de requerimientos.

## 7.5 `requirements.txt`

Lista las dependencias de la app original:

```text
streamlit
pandas<3.0
plotly
simpy
numpy
scipy
```

Cada dependencia cumple un papel:

- `streamlit`: interfaz web.
- `pandas`: tablas y CSV.
- `plotly`: graficas interactivas.
- `simpy`: simulacion de eventos discretos.
- `numpy`: calculos numericos.
- `scipy`: intervalos de confianza y estadistica.

## 7.6 `Sem1.2.0.py`

Es un script independiente de consola que representa una version academica previa o alternativa para Semanas 3 y 4.

Componentes:

- Importa `simpy`, `random`, `numpy`, `pandas` y `scipy.stats`.
- Define parametros base como `CAPACIDAD_BODEGA`, `STOCK_INICIAL`, `MEDIA_ENTRE_LLEGADAS`, `MEDIA_PEDIDO` y `TIEMPO_SIMULACION`.
- Define la clase `CentroDistribucion`.
- Usa distribucion exponencial para llegadas.
- Usa Poisson para tamano de pedido.
- Usa triangular para lead time.
- Calcula costos de ordenar, mantener y escasez.
- Ejecuta un DOE con 4 escenarios.
- Calcula intervalos de confianza.

Funciones principales:

| Funcion/clase | Proposito |
|---|---|
| `CentroDistribucion` | Representa el inventario, costos y proceso de reabastecimiento. |
| `actualizar_area_inventario` | Calcula area bajo la curva del inventario para obtener inventario promedio. |
| `proceso_reabastecimiento` | Simula una orden al proveedor con lead time triangular. |
| `proceso_clientes` | Genera clientes, demanda y ventas perdidas. |
| `ejecutar_simulacion` | Corre una simulacion para un ROP y Q especificos. |
| `analisis_estadistico` | Calcula media e intervalo de confianza para costos. |
| `main` | Ejecuta los escenarios y muestra la comparacion. |

Este archivo sustenta claramente Semana 3 y Semana 4.

## 7.7 `app.py`

Es el archivo principal de la aplicacion Streamlit. Organiza la experiencia del usuario.

Importaciones:

```python
import streamlit as st
import time
from src.ui_components import aplicar_estilos, render_header
from src.simulation_engine import ejecutar_simulacion_parametrizada
from src.charts import graficar_evolucion_inventario
from src.database import guardar_simulacion
```

Funciones de navegacion:

- `ir_a_carga`
- `ir_a_resultados`
- `ir_a_formulario`
- `ir_a_doe`

Variables de estado en `st.session_state`:

- `estado_app`
- `df_eventos`
- `df_historial`
- `kpis`
- `parametros_actuales`

Vistas:

1. **Formulario**
   - Captura parametros.
   - Construye el diccionario `parametros_actuales`.

2. **Carga**
   - Simula una pantalla de progreso.
   - Ejecuta el motor.
   - Guarda resultados.

3. **Resultados**
   - Muestra KPIs.
   - Grafica inventario.
   - Muestra recomendaciones.
   - Permite descargar eventos.

4. **DOE**
   - Ejecuta `ejecutar_doe`.
   - Muestra tabla comparativa.
   - Selecciona escenario optimo por menor costo.

## 7.8 `src/ui_components.py`

Contiene elementos visuales reutilizables para Streamlit.

Funciones:

| Funcion | Proposito |
|---|---|
| `aplicar_estilos` | Inyecta CSS personalizado. |
| `render_header` | Dibuja la cabecera tipo CEMEX Logistics Simulator. |

El CSS define:

- Fondo claro.
- Tarjetas blancas.
- Azul principal.
- Naranja para botones.
- Tipografia Inter.
- Estilo de metricas.
- Estilos para botones secundarios y azules.

Su funcion es hacer que la app no parezca una salida tecnica cruda, sino una herramienta amigable.

## 7.9 `src/simulation_engine.py`

Es el motor central del proyecto.

Importaciones:

```python
import simpy
import pandas as pd
import random
```

### Clase `CentroDistribucionEstocastico`

Representa el sistema fisico simulado.

Atributos principales:

- `env`: entorno SimPy.
- `parametros`: diccionario con variables del modelo.
- `registro_eventos`: lista donde se guardan eventos.
- `inventario`: `simpy.Container`.
- `pedido_en_transito`: bandera para evitar pedidos duplicados.
- `pedidos_surtidos`: contador.
- `pedidos_perdidos`: contador.
- `unidades_vendidas`: acumulador.
- `ordenes_al_proveedor`: contador.
- `historial_inventario`: lista para graficar inventario.

Metodos:

| Metodo | Funcion |
|---|---|
| `registrar_nivel` | Guarda el nivel de inventario en el tiempo actual. |
| `registrar_evento` | Agrega un evento a la lista de eventos. |
| `proceso_reabastecimiento` | Emite orden, espera lead time y recibe inventario. |

### Funcion `proceso_clientes`

Simula la demanda:

1. Genera el tiempo hasta el siguiente cliente.
2. Genera el tamano de pedido.
3. Revisa si hay inventario.
4. Si hay inventario, surte y descuenta.
5. Si no hay inventario, registra venta perdida.
6. Si el inventario cae bajo el punto de reorden, activa reabastecimiento.

### Funcion `ejecutar_simulacion_parametrizada`

Orquesta una corrida:

1. Fija semilla si se recibe.
2. Crea ambiente SimPy.
3. Crea centro de distribucion.
4. Activa proceso de clientes.
5. Ejecuta hasta `TIEMPO_SIMULACION`.
6. Calcula KPIs.
7. Devuelve eventos, historial y KPIs.

### Funcion `ejecutar_doe`

Ejecuta experimentacion con 4 escenarios:

- Base.
- Aumento ROP.
- Aumento Q.
- ROP+Q alto.

Usa 10 replicas, calcula costo medio e intervalo de confianza.

## 7.10 `src/database.py`

Gestiona almacenamiento local.

Constante:

```python
DATA_DIR = 'data'
```

Funciones:

| Funcion | Proposito |
|---|---|
| `asegurar_directorio` | Crea `data/` si no existe. |
| `guardar_simulacion` | Guarda eventos y resumen de cada corrida. |

`guardar_simulacion` crea un ID de simulacion con fecha y hora:

```python
id_simulacion = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
```

Despues:

- Inserta `ID_Simulacion` en eventos.
- Guarda `events_ID.csv`.
- Agrega eventos a `all_events.csv`.
- Agrega resumen a `simulations.csv`.

## 7.11 `src/charts.py`

Contiene la funcion:

```python
graficar_evolucion_inventario(df_historial, punto_reorden)
```

Esta funcion usa Plotly para dibujar:

- Linea del inventario.
- Area bajo la curva.
- Linea horizontal del punto de reorden.
- Ejes con dias y unidades.

La grafica muestra el comportamiento tipo diente de sierra:

- Baja cuando se surten clientes.
- Sube cuando llega reabastecimiento.

## 7.12 `dashboard_experiments.py`

Generador independiente de pruebas masivas.

No modifica la app original. Usa el motor `ejecutar_simulacion_parametrizada` y genera nuevos CSV.

Elementos principales:

| Elemento | Proposito |
|---|---|
| `PARAMETER_COLUMNS` | Lista de variables operables. |
| `COMPACT_LEVELS` | Niveles para DOE compacto. |
| `EXTENDED_LEVELS` | Niveles para DOE extendido. |
| `rounded_lot` | Redondea cantidades a lotes. |
| `build_parameter_grid` | Construye todos los escenarios. |
| `time_weighted_average_inventory` | Calcula inventario promedio ponderado por tiempo. |
| `percentile` | Calcula percentiles. |
| `safe_std` | Calcula desviacion estandar sin fallar con una replica. |
| `cvar` | Calcula CVaR, riesgo promedio en cola. |
| `build_summary` | Agrega resultados por escenario. |
| `run_experiments` | Ejecuta todos los escenarios y replicas. |
| `write_outputs` | Guarda CSV y manifest. |
| `parse_args` | Lee argumentos de consola. |
| `main` | Ejecuta el flujo completo. |

Metricas nuevas:

- `Costo_Ordenes`
- `Costo_Escasez`
- `Costo_Inventario`
- `Costo_Total`
- `Costo_Total_p95`
- `Costo_Total_CVaR95`
- `Prob_Ruptura`
- `Fill_Rate_Unidades`
- `Cobertura_ROP_Dias`
- `Brecha_LeadTime_Dias`

## 7.13 `dashboard_pygame.py`

Dashboard interactivo final.

Importa:

- `pygame` para ventana e interaccion.
- `pandas` para leer CSV.
- `numpy` para histogramas.
- `dataclasses` para estado.

Clases:

| Clase | Proposito |
|---|---|
| `DashboardState` | Guarda pestaña actual, ordenamiento, escenario seleccionado y scroll. |
| `DashboardData` | Guarda tablas cargadas: summary, runs, events, historical y manifest. |
| `Dashboard` | Controla eventos, dibujo y logica visual. |

Funciones de carga:

- `load_optional_csv`
- `make_numeric_where_possible`
- `load_dashboard_data`

Funciones de formato:

- `compact_number`
- `money`
- `pct`
- `clamp`
- `risk_color`

Funciones de dibujo:

- `draw_text`
- `draw_card`
- `draw_button`
- `draw_metric_card`
- `draw_axes`
- `draw_scatter`
- `draw_histogram`
- `draw_horizontal_bars`

Metodos principales de `Dashboard`:

| Metodo | Proposito |
|---|---|
| `handle_event` | Procesa teclado, mouse y cierre de ventana. |
| `activate` | Cambia pestañas, ordenamientos o escenario seleccionado. |
| `sorted_summary` | Ordena la tabla segun metrica elegida. |
| `selected_row` | Obtiene el escenario seleccionado. |
| `move_selection` | Navega por escenarios con teclado o scroll. |
| `draw` | Decide que vista dibujar. |
| `draw_summary` | Vista global de resumen. |
| `draw_ranking` | Tabla ordenable de escenarios. |
| `draw_risk` | VaR, CVaR e histogramas. |
| `draw_sensitivity` | Sensibilidad de variables. |
| `draw_scenario` | Detalle del escenario seleccionado. |
| `recommendation` | Genera lectura actuarial automatica. |

Controles:

- Click en pestañas.
- Click en ranking.
- Rueda del mouse.
- Flechas.
- PageUp/PageDown.
- Teclas 1 a 5.
- `R` invierte orden.

## 7.14 `requirements_dashboard.txt`

Dependencias para el dashboard Pygame:

```text
pandas<3.0
numpy
simpy
pygame>=2.5
```

Se separo de `requirements.txt` para no alterar la app original.

## 7.15 `DASHBOARD_PYGAME_README.md`

Explica:

- Como generar pruebas:

```bash
python3 dashboard_experiments.py
```

- Como instalar Pygame:

```bash
venv/bin/python -m pip install -r requirements_dashboard.txt
```

- Como abrir el dashboard:

```bash
venv/bin/python dashboard_pygame.py
```

Tambien lista los controles interactivos.

## 7.16 Carpeta `data/`

Contiene datos historicos y generados:

| Archivo | Contenido |
|---|---|
| `simulations.csv` | Historico de corridas ejecutadas desde Streamlit. |
| `events_*.csv` | Eventos detallados de corridas individuales. |
| `dashboard_experiments/scenario_runs.csv` | Cada replica generada para el dashboard. |
| `dashboard_experiments/scenario_summary.csv` | Resumen por escenario. |
| `dashboard_experiments/scenario_events.csv` | Eventos de corridas masivas. |
| `dashboard_experiments/manifest.json` | Metadatos de generacion y supuestos de costo. |

En la corrida actual del dashboard se generaron:

- 256 escenarios.
- 768 corridas.
- Mas de 128 mil eventos.

## 7.17 Carpeta `PIA_Simulacion/`

Contiene un repositorio/placeholder interno con README. No participa directamente en la ejecucion actual, pero forma parte de la estructura del proyecto.

---

# 8. Explicacion del flujo completo del sistema

1. El usuario abre Streamlit con:

```bash
python -m streamlit run app.py
```

2. Captura parametros.
3. `app.py` guarda parametros en `st.session_state.parametros_actuales`.
4. Se llama a `ejecutar_simulacion_parametrizada`.
5. SimPy avanza de evento en evento.
6. Los clientes llegan con tiempos aleatorios.
7. Cada cliente genera un pedido aleatorio.
8. Si hay inventario, se surte.
9. Si no hay inventario, se registra venta perdida.
10. Si el inventario cae bajo ROP, se emite orden.
11. El proveedor llega despues de un lead time aleatorio.
12. Se actualiza inventario.
13. Al final se calculan KPIs.
14. Streamlit muestra resultados.
15. `src/database.py` guarda CSV.
16. Para Semana 4 se ejecuta DOE desde Streamlit.
17. Para Semana 5 se generan escenarios masivos con `dashboard_experiments.py`.
18. El dashboard Pygame lee los CSV y permite analizar ranking, riesgo y sensibilidad.

---

# 9. Conclusiones del proyecto

El proyecto cumple con los objetivos de Semanas 3, 4 y 5 porque:

- Implementa aleatoriedad realista en llegadas, pedidos y tiempos de entrega.
- Justifica distribuciones con base en el comportamiento logistico.
- Simula escenarios base desde una interfaz amigable.
- Recolecta datos de salida en CSV para trazabilidad.
- Calcula KPIs operativos y estadisticos.
- Implementa DOE con replicas y Common Random Numbers.
- Compara escenarios por costo, servicio y riesgo.
- Realiza analisis de sensibilidad.
- Integra visualizacion en Streamlit y Pygame.
- Mantiene separada la ampliacion final para no romper el codigo original.

La utilidad practica del modelo es que permite experimentar con politicas de inventario antes de aplicarlas en una operacion real. Esto reduce riesgo, mejora la toma de decisiones y permite justificar recomendaciones con evidencia cuantitativa.

---

# 10. Recomendaciones para exposicion por integrante

## Persona 1: Contexto, variables y Semana 3

Debe explicar:

- Que problema se esta resolviendo.
- Por que se usa simulacion.
- Que variables existen.
- Que distribuciones se usan.
- Como se recolectan datos de salida.

Frase clave:

> Nuestro modelo representa un centro de distribucion con demanda incierta. Usamos simulacion de eventos discretos porque el sistema cambia cuando ocurren eventos especificos, como la llegada de clientes o la recepcion de reabastecimiento.

## Persona 2: Codigo original y motor SimPy

Debe explicar:

- Clase `CentroDistribucionEstocastico`.
- Funcion `proceso_clientes`.
- Funcion `proceso_reabastecimiento`.
- Funcion `ejecutar_simulacion_parametrizada`.
- Como se calculan KPIs.
- Como se guardan CSV.

Frase clave:

> El motor usa SimPy para avanzar el reloj directamente al siguiente evento. Esto hace eficiente la simulacion y permite modelar clientes y proveedor como procesos concurrentes.

## Persona 3: DOE, optimizacion y sensibilidad

Debe explicar:

- DOE de 4 escenarios en Streamlit.
- DOE ampliado de 256 escenarios.
- Replicas.
- Common Random Numbers.
- Costo total.
- VaR y CVaR.
- Sensibilidad.

Frase clave:

> No buscamos una unica corrida, sino comparar politicas bajo incertidumbre. Por eso usamos replicas, semillas controladas y metricas de riesgo para seleccionar escenarios robustos.

## Persona 4: Streamlit, Pygame y entrega final

Debe explicar:

- Interfaz Streamlit.
- Estilos en `ui_components.py`.
- Grafica Plotly.
- Dashboard Pygame.
- Pestañas del dashboard.
- Controles.
- Video y documentacion.

Frase clave:

> La visualizacion convierte los resultados tecnicos en una herramienta comprensible: Streamlit sirve para ejecutar simulaciones y Pygame para explorar escenarios masivos de manera interactiva.

---

# 11. Cierre ejecutivo

Este proyecto demuestra como la simulacion puede apoyar decisiones logisticas en un sistema con incertidumbre. La aplicacion permite observar el comportamiento del inventario, medir el impacto de politicas de reabastecimiento y seleccionar alternativas que balancean costo y nivel de servicio.

El trabajo final no se limita a programar una simulacion; tambien incorpora analisis estadistico, experimentacion, visualizacion y documentacion, que son elementos esenciales para una entrega completa de Simulacion de Sistemas.
