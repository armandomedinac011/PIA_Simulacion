from __future__ import annotations

import argparse
import itertools
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.simulation_engine import ejecutar_simulacion_parametrizada


ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = ROOT_DIR / "data" / "dashboard_experiments"


PARAMETER_COLUMNS = [
    "CAPACIDAD_BODEGA",
    "STOCK_INICIAL",
    "PUNTO_REORDEN",
    "CANTIDAD_REABASTECIMIENTO",
    "TIEMPO_ENTRE_LLEGADAS",
    "TAMANO_PEDIDO",
    "LEAD_TIME_PROVEEDOR",
    "TIEMPO_SIMULACION",
]


COMPACT_LEVELS = {
    "CAPACIDAD_BODEGA": [8000, 12000],
    "STOCK_INICIAL_RATIO": [0.18, 0.35],
    "PUNTO_REORDEN_RATIO": [0.10, 0.22],
    "CANTIDAD_REABASTECIMIENTO_RATIO": [0.22, 0.45],
    "TIEMPO_ENTRE_LLEGADAS": [0.9, 1.8],
    "TAMANO_PEDIDO": [120, 220],
    "LEAD_TIME_PROVEEDOR": [1.0, 3.0],
    "TIEMPO_SIMULACION": [120, 240],
}


EXTENDED_LEVELS = {
    "CAPACIDAD_BODEGA": [8000, 10000, 12000],
    "STOCK_INICIAL_RATIO": [0.18, 0.28, 0.38],
    "PUNTO_REORDEN_RATIO": [0.10, 0.18, 0.26],
    "CANTIDAD_REABASTECIMIENTO_RATIO": [0.22, 0.34, 0.46],
    "TIEMPO_ENTRE_LLEGADAS": [0.9, 1.4, 1.9],
    "TAMANO_PEDIDO": [120, 170, 220],
    "LEAD_TIME_PROVEEDOR": [1.0, 2.0, 3.0],
    "TIEMPO_SIMULACION": [120, 180, 240],
}


def rounded_lot(value: float, lot_size: int = 10) -> int:
    return int(round(value / lot_size) * lot_size)


def build_parameter_grid(profile: str) -> list[dict[str, Any]]:
    levels = EXTENDED_LEVELS if profile == "extended" else COMPACT_LEVELS
    keys = list(levels.keys())
    scenarios: list[dict[str, Any]] = []

    for scenario_number, combo in enumerate(itertools.product(*(levels[key] for key in keys)), start=1):
        raw = dict(zip(keys, combo, strict=True))
        capacity = int(raw["CAPACIDAD_BODEGA"])
        stock_initial = max(1, rounded_lot(capacity * raw["STOCK_INICIAL_RATIO"]))
        reorder_point = max(1, rounded_lot(capacity * raw["PUNTO_REORDEN_RATIO"]))
        reorder_quantity = max(1, rounded_lot(capacity * raw["CANTIDAD_REABASTECIMIENTO_RATIO"]))

        time_between_arrivals = float(raw["TIEMPO_ENTRE_LLEGADAS"])
        order_size = int(raw["TAMANO_PEDIDO"])
        lead_time = float(raw["LEAD_TIME_PROVEEDOR"])
        horizon = int(raw["TIEMPO_SIMULACION"])
        expected_daily_demand = order_size / time_between_arrivals

        coverage_initial = stock_initial / expected_daily_demand
        coverage_reorder = reorder_point / expected_daily_demand
        supply_cycle_cover = reorder_quantity / expected_daily_demand
        lead_time_gap = coverage_reorder - lead_time

        demand_band = "Alta" if expected_daily_demand >= 175 else "Media" if expected_daily_demand >= 100 else "Baja"
        supplier_band = "Lento" if lead_time >= 3 else "Normal" if lead_time >= 2 else "Rapido"
        policy_band = "Conservadora" if raw["PUNTO_REORDEN_RATIO"] >= 0.20 and raw["CANTIDAD_REABASTECIMIENTO_RATIO"] >= 0.40 else "Ajustada"
        risk_band = "Alto" if lead_time_gap < 0 else "Medio" if lead_time_gap < 1.5 else "Bajo"

        parameters = {
            "CAPACIDAD_BODEGA": capacity,
            "STOCK_INICIAL": stock_initial,
            "PUNTO_REORDEN": reorder_point,
            "CANTIDAD_REABASTECIMIENTO": reorder_quantity,
            "TIEMPO_ENTRE_LLEGADAS": time_between_arrivals,
            "TAMANO_PEDIDO": order_size,
            "LEAD_TIME_PROVEEDOR": lead_time,
            "TIEMPO_SIMULACION": horizon,
        }

        scenarios.append(
            {
                "Scenario_ID": f"SCN-{scenario_number:04d}",
                "Escenario": f"{demand_band} demanda / {supplier_band} proveedor / {policy_band}",
                "STOCK_INICIAL_RATIO": raw["STOCK_INICIAL_RATIO"],
                "PUNTO_REORDEN_RATIO": raw["PUNTO_REORDEN_RATIO"],
                "CANTIDAD_REABASTECIMIENTO_RATIO": raw["CANTIDAD_REABASTECIMIENTO_RATIO"],
                "Demanda_Diaria_Esperada": round(expected_daily_demand, 4),
                "Cobertura_Inicial_Dias": round(coverage_initial, 4),
                "Cobertura_ROP_Dias": round(coverage_reorder, 4),
                "Cobertura_Q_Dias": round(supply_cycle_cover, 4),
                "Brecha_LeadTime_Dias": round(lead_time_gap, 4),
                "Categoria_Riesgo": risk_band,
                "Parametros": parameters,
            }
        )

    return scenarios


def time_weighted_average_inventory(df_history: pd.DataFrame, horizon: float) -> float:
    if df_history.empty or horizon <= 0:
        return 0.0

    ordered = df_history[["Dia", "Inventario"]].dropna().sort_values("Dia")
    points = list(ordered.itertuples(index=False, name=None))
    if not points:
        return 0.0

    cleaned: list[tuple[float, float]] = []
    for day, inventory in points:
        day_float = max(0.0, min(float(day), horizon))
        inventory_float = max(0.0, float(inventory))
        if cleaned and math.isclose(day_float, cleaned[-1][0]):
            cleaned[-1] = (day_float, inventory_float)
        else:
            cleaned.append((day_float, inventory_float))

    if cleaned[0][0] > 0.0:
        cleaned.insert(0, (0.0, cleaned[0][1]))
    if cleaned[-1][0] < horizon:
        cleaned.append((horizon, cleaned[-1][1]))

    area = 0.0
    previous_day, previous_inventory = cleaned[0]
    for current_day, current_inventory in cleaned[1:]:
        delta = max(0.0, current_day - previous_day)
        area += delta * previous_inventory
        previous_day, previous_inventory = current_day, current_inventory

    return area / horizon if horizon else 0.0


def percentile(series: pd.Series, q: float) -> float:
    return float(series.quantile(q)) if not series.empty else 0.0


def safe_std(series: pd.Series) -> float:
    value = float(series.std(ddof=1)) if len(series) > 1 else 0.0
    return 0.0 if math.isnan(value) else value


def cvar(series: pd.Series, q: float = 0.95) -> float:
    if series.empty:
        return 0.0
    threshold = series.quantile(q)
    tail = series[series >= threshold]
    return float(tail.mean()) if not tail.empty else float(threshold)


def build_summary(df_runs: pd.DataFrame) -> pd.DataFrame:
    summary_rows: list[dict[str, Any]] = []
    group_keys = [
        "Scenario_ID",
        "Escenario",
        *PARAMETER_COLUMNS,
        "STOCK_INICIAL_RATIO",
        "PUNTO_REORDEN_RATIO",
        "CANTIDAD_REABASTECIMIENTO_RATIO",
        "Demanda_Diaria_Esperada",
        "Cobertura_Inicial_Dias",
        "Cobertura_ROP_Dias",
        "Cobertura_Q_Dias",
        "Brecha_LeadTime_Dias",
        "Categoria_Riesgo",
    ]

    for keys, group in df_runs.groupby(group_keys, dropna=False):
        row = dict(zip(group_keys, keys, strict=True))
        row["Replicas"] = int(group["Replica"].nunique())

        row["Nivel_Servicio_mean"] = round(float(group["Nivel_Servicio"].mean()), 4)
        row["Nivel_Servicio_std"] = round(safe_std(group["Nivel_Servicio"]), 4)
        row["Nivel_Servicio_min"] = round(float(group["Nivel_Servicio"].min()), 4)
        row["Nivel_Servicio_p05"] = round(percentile(group["Nivel_Servicio"], 0.05), 4)
        row["Nivel_Servicio_p95"] = round(percentile(group["Nivel_Servicio"], 0.95), 4)

        row["Fill_Rate_Unidades_mean"] = round(float(group["Fill_Rate_Unidades"].mean()), 4)
        row["Ventas_Perdidas_mean"] = round(float(group["Ventas_Perdidas"].mean()), 4)
        row["Ventas_Perdidas_max"] = int(group["Ventas_Perdidas"].max())
        row["Unidades_Perdidas_mean"] = round(float(group["Unidades_Perdidas"].mean()), 4)
        row["Prob_Ruptura"] = round(float((group["Ventas_Perdidas"] > 0).mean() * 100), 4)

        row["Costo_Total_mean"] = round(float(group["Costo_Total"].mean()), 4)
        row["Costo_Total_std"] = round(safe_std(group["Costo_Total"]), 4)
        row["Costo_Total_p50"] = round(percentile(group["Costo_Total"], 0.50), 4)
        row["Costo_Total_p95"] = round(percentile(group["Costo_Total"], 0.95), 4)
        row["Costo_Total_CVaR95"] = round(cvar(group["Costo_Total"], 0.95), 4)

        row["Inventario_Promedio_mean"] = round(float(group["Inventario_Promedio"].mean()), 4)
        row["Ordenes_Proveedor_mean"] = round(float(group["Ordenes_Proveedor"].mean()), 4)
        row["Unidades_Vendidas_mean"] = round(float(group["Unidades_Vendidas"].mean()), 4)
        row["Total_Solicitudes_mean"] = round(float(group["Total_Solicitudes"].mean()), 4)
        summary_rows.append(row)

    summary = pd.DataFrame(summary_rows)
    return summary.sort_values(["Costo_Total_mean", "Nivel_Servicio_mean"], ascending=[True, False])


def run_experiments(args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    scenarios = build_parameter_grid(args.profile)
    if args.max_scenarios:
        scenarios = scenarios[: args.max_scenarios]

    run_rows: list[dict[str, Any]] = []
    event_frames: list[pd.DataFrame] = []
    total_runs = len(scenarios) * args.replicas
    current_run = 0

    for scenario_index, scenario in enumerate(scenarios, start=1):
        parameters = scenario["Parametros"]

        for replica in range(1, args.replicas + 1):
            current_run += 1
            seed = args.seed + scenario_index * 10_000 + replica
            df_events, df_history, kpis = ejecutar_simulacion_parametrizada(parameters, semilla=seed)

            horizon = float(parameters["TIEMPO_SIMULACION"])
            inventory_average = time_weighted_average_inventory(df_history, horizon)
            lost_units = 0.0
            if not df_events.empty and "Venta_Perdida" in df_events.columns:
                lost_units = float(df_events.loc[df_events["Venta_Perdida"] == 1, "Cantidad"].sum())

            sold_units = float(kpis["Unidades Vendidas"])
            demanded_units = sold_units + lost_units
            fill_rate = (sold_units / demanded_units) * 100 if demanded_units else 0.0

            order_cost = float(kpis["Ordenes Proveedor"]) * args.order_cost
            shortage_cost = float(kpis["Ventas Perdidas"]) * args.shortage_cost + lost_units * args.lost_unit_cost
            holding_cost = inventory_average * horizon * args.holding_cost
            total_cost = order_cost + shortage_cost + holding_cost

            run_id = f"{scenario['Scenario_ID']}-R{replica:02d}"
            row = {
                "Run_ID": run_id,
                "Scenario_ID": scenario["Scenario_ID"],
                "Replica": replica,
                "Semilla": seed,
                "Escenario": scenario["Escenario"],
                **parameters,
                "STOCK_INICIAL_RATIO": scenario["STOCK_INICIAL_RATIO"],
                "PUNTO_REORDEN_RATIO": scenario["PUNTO_REORDEN_RATIO"],
                "CANTIDAD_REABASTECIMIENTO_RATIO": scenario["CANTIDAD_REABASTECIMIENTO_RATIO"],
                "Demanda_Diaria_Esperada": scenario["Demanda_Diaria_Esperada"],
                "Cobertura_Inicial_Dias": scenario["Cobertura_Inicial_Dias"],
                "Cobertura_ROP_Dias": scenario["Cobertura_ROP_Dias"],
                "Cobertura_Q_Dias": scenario["Cobertura_Q_Dias"],
                "Brecha_LeadTime_Dias": scenario["Brecha_LeadTime_Dias"],
                "Categoria_Riesgo": scenario["Categoria_Riesgo"],
                "Inventario_Final": float(kpis["Inventario Final"]),
                "Total_Solicitudes": int(kpis["Total Solicitudes"]),
                "Pedidos_Surtidos": int(kpis["Pedidos Surtidos"]),
                "Ventas_Perdidas": int(kpis["Ventas Perdidas"]),
                "Nivel_Servicio": float(kpis["Nivel Servicio"]),
                "Unidades_Vendidas": sold_units,
                "Unidades_Perdidas": lost_units,
                "Fill_Rate_Unidades": round(fill_rate, 4),
                "Ordenes_Proveedor": int(kpis["Ordenes Proveedor"]),
                "Inventario_Promedio": round(inventory_average, 4),
                "Costo_Ordenes": round(order_cost, 4),
                "Costo_Escasez": round(shortage_cost, 4),
                "Costo_Inventario": round(holding_cost, 4),
                "Costo_Total": round(total_cost, 4),
            }
            run_rows.append(row)

            if args.save_events and not df_events.empty:
                events = df_events.copy()
                events.insert(0, "Run_ID", run_id)
                events.insert(1, "Scenario_ID", scenario["Scenario_ID"])
                events.insert(2, "Replica", replica)
                event_frames.append(events)

            if args.verbose and (current_run == total_runs or current_run % args.progress_every == 0):
                print(f"Corridas completadas: {current_run}/{total_runs}")

    df_runs = pd.DataFrame(run_rows)
    df_summary = build_summary(df_runs)
    df_events = pd.concat(event_frames, ignore_index=True) if event_frames else pd.DataFrame()
    return df_runs, df_summary, df_events


def write_outputs(
    output_dir: Path,
    df_runs: pd.DataFrame,
    df_summary: pd.DataFrame,
    df_events: pd.DataFrame,
    args: argparse.Namespace,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    df_runs.to_csv(output_dir / "scenario_runs.csv", index=False)
    df_summary.to_csv(output_dir / "scenario_summary.csv", index=False)
    if args.save_events:
        df_events.to_csv(output_dir / "scenario_events.csv", index=False)

    manifest = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "profile": args.profile,
        "replicas": args.replicas,
        "seed": args.seed,
        "scenario_count": int(df_summary["Scenario_ID"].nunique()),
        "run_count": int(len(df_runs)),
        "events_saved": bool(args.save_events),
        "cost_assumptions": {
            "order_cost": args.order_cost,
            "shortage_cost_per_lost_order": args.shortage_cost,
            "lost_unit_cost": args.lost_unit_cost,
            "holding_cost_per_unit_day": args.holding_cost,
        },
        "files": {
            "scenario_runs": "scenario_runs.csv",
            "scenario_summary": "scenario_summary.csv",
            "scenario_events": "scenario_events.csv" if args.save_events else None,
        },
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Genera pruebas de simulacion independientes para el dashboard actuarial."
    )
    parser.add_argument("--profile", choices=["compact", "extended"], default="compact")
    parser.add_argument("--replicas", type=int, default=3)
    parser.add_argument("--seed", type=int, default=20260515)
    parser.add_argument("--max-scenarios", type=int, default=None)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--order-cost", type=float, default=1000.0)
    parser.add_argument("--shortage-cost", type=float, default=500.0)
    parser.add_argument("--lost-unit-cost", type=float, default=8.0)
    parser.add_argument("--holding-cost", type=float, default=0.15)
    parser.add_argument("--no-events", dest="save_events", action="store_false")
    parser.add_argument("--progress-every", type=int, default=50)
    parser.add_argument("--quiet", dest="verbose", action="store_false")
    parser.set_defaults(save_events=True, verbose=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.replicas < 1:
        raise SystemExit("--replicas debe ser al menos 1")
    if args.max_scenarios is not None and args.max_scenarios < 1:
        raise SystemExit("--max-scenarios debe ser al menos 1")

    print("Generando escenarios actuariales de inventario...")
    df_runs, df_summary, df_events = run_experiments(args)
    write_outputs(args.output_dir, df_runs, df_summary, df_events, args)

    best_cost = df_summary.sort_values("Costo_Total_mean", ascending=True).iloc[0]
    best_service = df_summary.sort_values("Nivel_Servicio_mean", ascending=False).iloc[0]
    print(f"Archivos generados en: {args.output_dir}")
    print(f"Escenarios: {df_summary['Scenario_ID'].nunique()} | Corridas: {len(df_runs)}")
    print(
        "Menor costo medio: "
        f"{best_cost['Scenario_ID']} (${best_cost['Costo_Total_mean']:,.2f}, "
        f"servicio {best_cost['Nivel_Servicio_mean']:.2f}%)"
    )
    print(
        "Mayor servicio medio: "
        f"{best_service['Scenario_ID']} ({best_service['Nivel_Servicio_mean']:.2f}%, "
        f"costo ${best_service['Costo_Total_mean']:,.2f})"
    )


if __name__ == "__main__":
    main()
