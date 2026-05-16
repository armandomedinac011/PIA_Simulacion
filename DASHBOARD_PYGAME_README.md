# Dashboard Pygame de Simulaciones

Estos archivos son una capa nueva sobre el proyecto. No modifican `app.py`, `src/` ni el historico original de `data/simulations.csv`.

## 1. Generar pruebas de simulacion

```bash
python3 dashboard_experiments.py
```

Salida esperada:

- `data/dashboard_experiments/scenario_runs.csv`: cada replica simulada.
- `data/dashboard_experiments/scenario_summary.csv`: resumen actuarial por escenario.
- `data/dashboard_experiments/scenario_events.csv`: eventos de las corridas generadas.
- `data/dashboard_experiments/manifest.json`: supuestos de costo y trazabilidad.

El perfil `compact` varia todas las variables operables del modelo con dos niveles por variable: capacidad, stock inicial, punto de reorden, cantidad de reabasto, tiempo entre llegadas, tamano de pedido, lead time y horizonte. Genera 256 escenarios por defecto, con 3 replicas cada uno.

Para un experimento mas grande:

```bash
python3 dashboard_experiments.py --profile extended --replicas 5
```

## 2. Abrir el dashboard interactivo

Instala la dependencia visual si hace falta:

```bash
venv/bin/python -m pip install -r requirements_dashboard.txt
```

Despues ejecuta:

```bash
venv/bin/python dashboard_pygame.py
```

El dashboard carga por defecto los CSV de `data/dashboard_experiments`. Tambien lee `data/simulations.csv` como referencia historica, sin modificarlo.

## Controles

- Click en las pestanas superiores para cambiar de vista.
- Click en metricas de ordenamiento para cambiar ranking.
- Click en una fila del ranking para inspeccionar ese escenario.
- Rueda del mouse, flechas, PageUp/PageDown para navegar escenarios.
- Teclas `1` a `5` cambian de vista.
- `R` invierte el orden actual.
