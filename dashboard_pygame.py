from __future__ import annotations

import argparse
import json
import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

try:
    import pygame
except ModuleNotFoundError as exc:
    print("Falta pygame. Instala las dependencias con:")
    print("python3 -m pip install -r requirements_dashboard.txt")
    raise SystemExit(1) from exc


ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_DATA_DIR = ROOT_DIR / "data" / "dashboard_experiments"
HISTORICAL_PATH = ROOT_DIR / "data" / "simulations.csv"

TAB_DEFS = [
    ("resumen", "Resumen"),
    ("ranking", "Ranking"),
    ("riesgo", "Riesgo"),
    ("sensibilidad", "Sensibilidad"),
    ("escenario", "Escenario"),
]

SORT_OPTIONS = [
    ("Costo ($)", "Costo_Total_mean", True),
    ("Servicio (%)", "Nivel_Servicio_mean", False),
    ("CVaR 95 ($)", "Costo_Total_CVaR95", True),
    ("Ruptura (%)", "Prob_Ruptura", True),
]

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

PARAMETER_LABELS = {
    "CAPACIDAD_BODEGA": "Capacidad (ton)",
    "STOCK_INICIAL": "Stock inicial (ton)",
    "PUNTO_REORDEN": "ROP (ton)",
    "CANTIDAD_REABASTECIMIENTO": "Q reabasto (ton)",
    "TIEMPO_ENTRE_LLEGADAS": "Tiempo llegadas (dias)",
    "TAMANO_PEDIDO": "Pedido medio (ton)",
    "LEAD_TIME_PROVEEDOR": "Lead time (dias)",
    "TIEMPO_SIMULACION": "Horizonte (dias)",
}

BG = (244, 247, 251)
PANEL = (255, 255, 255)
PANEL_ALT = (248, 251, 255)
TEXT = (30, 38, 51)
MUTED = (91, 103, 120)
GRID = (221, 228, 238)
BLUE = (33, 111, 219)
BLUE_DARK = (23, 77, 154)
ORANGE = (239, 126, 49)
GREEN = (40, 153, 101)
RED = (217, 72, 77)
YELLOW = (224, 169, 48)
PURPLE = (112, 91, 214)
CYAN = (31, 151, 164)


@dataclass
class DashboardState:
    tab: str = "resumen"
    sort_metric: str = "Costo_Total_mean"
    sort_ascending: bool = True
    selected_id: str | None = None
    scroll: int = 0
    reverse_sort: bool = False


@dataclass
class DashboardData:
    summary: pd.DataFrame
    runs: pd.DataFrame
    events: pd.DataFrame
    historical: pd.DataFrame
    manifest: dict[str, Any]


def load_optional_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def make_numeric_where_possible(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    for column in result.columns:
        converted = pd.to_numeric(result[column], errors="coerce")
        original_non_null = result[column].notna().sum()
        if original_non_null and converted.notna().sum() >= original_non_null * 0.9:
            result[column] = converted
    return result


def load_dashboard_data(data_dir: Path) -> DashboardData:
    summary_path = data_dir / "scenario_summary.csv"
    runs_path = data_dir / "scenario_runs.csv"
    events_path = data_dir / "scenario_events.csv"
    manifest_path = data_dir / "manifest.json"

    if not summary_path.exists() or not runs_path.exists():
        raise FileNotFoundError(
            "No encontre scenario_summary.csv y scenario_runs.csv. "
            "Ejecuta primero: python3 dashboard_experiments.py"
        )

    summary = make_numeric_where_possible(pd.read_csv(summary_path))
    runs = make_numeric_where_possible(pd.read_csv(runs_path))
    events = make_numeric_where_possible(load_optional_csv(events_path))
    historical = make_numeric_where_possible(load_optional_csv(HISTORICAL_PATH))
    manifest = {}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    return DashboardData(summary=summary, runs=runs, events=events, historical=historical, manifest=manifest)


def compact_number(value: float | int | None, decimals: int = 1) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "-"
    value = float(value)
    sign = "-" if value < 0 else ""
    value = abs(value)
    if value >= 1_000_000:
        return f"{sign}{value / 1_000_000:.{decimals}f}M"
    if value >= 1_000:
        return f"{sign}{value / 1_000:.{decimals}f}K"
    if value == int(value):
        return f"{sign}{int(value):,}"
    return f"{sign}{value:.{decimals}f}"


def money(value: float | int | None) -> str:
    return f"${compact_number(value, 1)}"


def pct(value: float | int | None, decimals: int = 1) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "-"
    return f"{float(value):.{decimals}f}%"


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def lerp_color(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    t = clamp(t, 0, 1)
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def risk_color(probability: float) -> tuple[int, int, int]:
    if probability <= 0:
        return GREEN
    if probability < 35:
        return lerp_color(GREEN, YELLOW, probability / 35)
    return lerp_color(YELLOW, RED, min(1, (probability - 35) / 65))


def truncate_text(text: Any, font: pygame.font.Font, max_width: int) -> str:
    text = str(text)
    if font.size(text)[0] <= max_width:
        return text
    ellipsis = "..."
    while text and font.size(text + ellipsis)[0] > max_width:
        text = text[:-1]
    return text + ellipsis if text else ellipsis


def draw_text(
    surface: pygame.Surface,
    text: Any,
    font: pygame.font.Font,
    color: tuple[int, int, int],
    rect: pygame.Rect,
    align: str = "left",
    valign: str = "top",
) -> None:
    rect = pygame.Rect(rect)
    rendered_text = truncate_text(text, font, rect.width)
    image = font.render(rendered_text, True, color)
    x = rect.x
    if align == "center":
        x = rect.x + (rect.width - image.get_width()) // 2
    elif align == "right":
        x = rect.right - image.get_width()

    y = rect.y
    if valign == "center":
        y = rect.y + (rect.height - image.get_height()) // 2
    elif valign == "bottom":
        y = rect.bottom - image.get_height()

    previous_clip = surface.get_clip()
    surface.set_clip(rect)
    surface.blit(image, (x, y))
    surface.set_clip(previous_clip)


def draw_card(surface: pygame.Surface, rect: pygame.Rect, fill: tuple[int, int, int] = PANEL) -> None:
    pygame.draw.rect(surface, fill, rect, border_radius=8)
    pygame.draw.rect(surface, (227, 233, 243), rect, width=1, border_radius=8)


def draw_button(
    surface: pygame.Surface,
    rect: pygame.Rect,
    label: str,
    font: pygame.font.Font,
    active: bool = False,
    accent: tuple[int, int, int] = BLUE,
) -> None:
    fill = accent if active else PANEL
    stroke = accent if active else (211, 220, 232)
    color = (255, 255, 255) if active else TEXT
    pygame.draw.rect(surface, fill, rect, border_radius=7)
    pygame.draw.rect(surface, stroke, rect, width=1, border_radius=7)
    draw_text(surface, label, font, color, rect.inflate(-12, 0), align="center", valign="center")


def draw_metric_card(
    surface: pygame.Surface,
    rect: pygame.Rect,
    title: str,
    value: str,
    detail: str,
    fonts: dict[str, pygame.font.Font],
    accent: tuple[int, int, int],
) -> None:
    draw_card(surface, rect)
    pygame.draw.rect(surface, accent, pygame.Rect(rect.x, rect.y, 5, rect.height), border_radius=4)
    draw_text(surface, title, fonts["small"], MUTED, pygame.Rect(rect.x + 16, rect.y + 12, rect.width - 24, 18))
    draw_text(surface, value, fonts["metric"], TEXT, pygame.Rect(rect.x + 16, rect.y + 36, rect.width - 24, 38))
    draw_text(surface, detail, fonts["tiny"], MUTED, pygame.Rect(rect.x + 16, rect.y + 76, rect.width - 24, 18))


def draw_axes(surface: pygame.Surface, rect: pygame.Rect, title: str, fonts: dict[str, pygame.font.Font]) -> pygame.Rect:
    draw_card(surface, rect)
    draw_text(surface, title, fonts["section"], TEXT, pygame.Rect(rect.x + 16, rect.y + 12, rect.width - 32, 24))
    chart = pygame.Rect(rect.x + 48, rect.y + 58, rect.width - 76, rect.height - 88)
    for i in range(5):
        y = chart.y + round(chart.height * i / 4)
        pygame.draw.line(surface, GRID, (chart.x, y), (chart.right, y), 1)
    pygame.draw.line(surface, (185, 197, 213), chart.bottomleft, chart.bottomright, 1)
    pygame.draw.line(surface, (185, 197, 213), chart.bottomleft, chart.topleft, 1)
    return chart


def draw_scatter(
    surface: pygame.Surface,
    rect: pygame.Rect,
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    color_col: str,
    title: str,
    fonts: dict[str, pygame.font.Font],
    selected_id: str | None,
) -> None:
    chart = draw_axes(surface, rect, title, fonts)
    if df.empty:
        draw_text(surface, "Sin datos", fonts["body"], MUTED, chart, align="center", valign="center")
        return

    x_values = df[x_col].astype(float)
    y_values = df[y_col].astype(float)
    x_min, x_max = float(x_values.min()), float(x_values.max())
    y_min, y_max = float(y_values.min()), float(y_values.max())
    if math.isclose(x_min, x_max):
        x_max = x_min + 1
    if math.isclose(y_min, y_max):
        y_max = y_min + 1

    for _, row in df.iterrows():
        x = chart.x + int((float(row[x_col]) - x_min) / (x_max - x_min) * chart.width)
        y = chart.bottom - int((float(row[y_col]) - y_min) / (y_max - y_min) * chart.height)
        prob = float(row.get(color_col, 0))
        color = risk_color(prob)
        radius = 7 if row["Scenario_ID"] == selected_id else 4
        pygame.draw.circle(surface, color, (x, y), radius)
        if row["Scenario_ID"] == selected_id:
            pygame.draw.circle(surface, TEXT, (x, y), radius + 3, 2)

    draw_text(surface, money(x_min), fonts["tiny"], MUTED, pygame.Rect(chart.x, chart.bottom + 8, 80, 16))
    draw_text(surface, money(x_max), fonts["tiny"], MUTED, pygame.Rect(chart.right - 80, chart.bottom + 8, 80, 16), align="right")
    draw_text(surface, pct(y_max), fonts["tiny"], MUTED, pygame.Rect(chart.x - 44, chart.y, 40, 16), align="right")
    draw_text(surface, pct(y_min), fonts["tiny"], MUTED, pygame.Rect(chart.x - 44, chart.bottom - 14, 40, 16), align="right")


def draw_histogram(
    surface: pygame.Surface,
    rect: pygame.Rect,
    values: pd.Series,
    title: str,
    fonts: dict[str, pygame.font.Font],
    color: tuple[int, int, int] = BLUE,
) -> None:
    chart = draw_axes(surface, rect, title, fonts)
    values = pd.to_numeric(values, errors="coerce").dropna()
    if values.empty:
        draw_text(surface, "Sin datos", fonts["body"], MUTED, chart, align="center", valign="center")
        return

    bins = min(18, max(5, int(math.sqrt(len(values)))))
    counts, edges = np.histogram(values, bins=bins)
    max_count = max(1, int(counts.max()))
    gap = 3
    bar_width = max(2, int((chart.width - gap * (bins - 1)) / bins))
    for index, count in enumerate(counts):
        height = int((count / max_count) * chart.height)
        x = chart.x + index * (bar_width + gap)
        bar = pygame.Rect(x, chart.bottom - height, bar_width, height)
        pygame.draw.rect(surface, color, bar, border_radius=3)

    draw_text(surface, compact_number(values.min(), 1), fonts["tiny"], MUTED, pygame.Rect(chart.x, chart.bottom + 8, 90, 16))
    draw_text(surface, compact_number(values.max(), 1), fonts["tiny"], MUTED, pygame.Rect(chart.right - 90, chart.bottom + 8, 90, 16), align="right")


def draw_horizontal_bars(
    surface: pygame.Surface,
    rect: pygame.Rect,
    rows: list[tuple[str, float, tuple[int, int, int]]],
    title: str,
    fonts: dict[str, pygame.font.Font],
    value_formatter=compact_number,
) -> None:
    draw_card(surface, rect)
    draw_text(surface, title, fonts["section"], TEXT, pygame.Rect(rect.x + 16, rect.y + 12, rect.width - 32, 24))
    if not rows:
        draw_text(surface, "Sin datos", fonts["body"], MUTED, rect.inflate(-32, -64), align="center", valign="center")
        return

    plot = pygame.Rect(rect.x + 16, rect.y + 52, rect.width - 32, rect.height - 68)
    max_abs = max(abs(value) for _, value, _ in rows) or 1
    row_h = max(22, min(34, plot.height // max(1, len(rows))))
    zero_x = plot.x + int(plot.width * 0.44)
    pygame.draw.line(surface, GRID, (zero_x, plot.y), (zero_x, plot.bottom), 1)

    for index, (label, value, color) in enumerate(rows):
        y = plot.y + index * row_h
        label_rect = pygame.Rect(plot.x, y, int(plot.width * 0.36), row_h)
        draw_text(surface, label, fonts["tiny"], MUTED, label_rect, valign="center")
        width = int(abs(value) / max_abs * (plot.width * 0.48))
        if value >= 0:
            bar = pygame.Rect(zero_x, y + 6, width, row_h - 12)
        else:
            bar = pygame.Rect(zero_x - width, y + 6, width, row_h - 12)
        pygame.draw.rect(surface, color, bar, border_radius=4)
        value_rect = pygame.Rect(plot.right - 94, y, 92, row_h)
        draw_text(surface, value_formatter(value), fonts["tiny"], TEXT, value_rect, align="right", valign="center")


class Dashboard:
    def __init__(self, screen: pygame.Surface, data: DashboardData):
        self.screen = screen
        self.data = data
        self.state = DashboardState()
        first_id = str(data.summary.iloc[0]["Scenario_ID"]) if not data.summary.empty else None
        self.state.selected_id = first_id
        self.zones: list[tuple[pygame.Rect, str, Any]] = []
        self.fonts = {
            "title": pygame.font.SysFont("Arial", 28, bold=True),
            "section": pygame.font.SysFont("Arial", 18, bold=True),
            "body": pygame.font.SysFont("Arial", 15),
            "small": pygame.font.SysFont("Arial", 13),
            "tiny": pygame.font.SysFont("Arial", 12),
            "metric": pygame.font.SysFont("Arial", 28, bold=True),
            "table": pygame.font.SysFont("Arial", 13),
        }

    def add_zone(self, rect: pygame.Rect, action: str, value: Any) -> None:
        self.zones.append((pygame.Rect(rect), action, value))

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.QUIT:
            return False
        if event.type == pygame.KEYDOWN:
            self.handle_key(event.key)
        elif event.type == pygame.MOUSEWHEEL:
            self.move_selection(-event.y)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                for rect, action, value in reversed(self.zones):
                    if rect.collidepoint(event.pos):
                        self.activate(action, value)
                        break
            elif event.button == 4:
                self.move_selection(-1)
            elif event.button == 5:
                self.move_selection(1)
        return True

    def handle_key(self, key: int) -> None:
        if key in (pygame.K_DOWN, pygame.K_j):
            self.move_selection(1)
        elif key in (pygame.K_UP, pygame.K_k):
            self.move_selection(-1)
        elif key == pygame.K_PAGEDOWN:
            self.move_selection(10)
        elif key == pygame.K_PAGEUP:
            self.move_selection(-10)
        elif key == pygame.K_r:
            self.state.reverse_sort = not self.state.reverse_sort
        elif pygame.K_1 <= key <= pygame.K_5:
            index = key - pygame.K_1
            if index < len(TAB_DEFS):
                self.state.tab = TAB_DEFS[index][0]

    def activate(self, action: str, value: Any) -> None:
        if action == "tab":
            self.state.tab = value
        elif action == "sort":
            label, metric, ascending = value
            if self.state.sort_metric == metric:
                self.state.reverse_sort = not self.state.reverse_sort
            else:
                self.state.sort_metric = metric
                self.state.sort_ascending = ascending
                self.state.reverse_sort = False
        elif action == "select":
            self.state.selected_id = value
            self.state.tab = "escenario" if self.state.tab == "ranking" else self.state.tab

    def sorted_summary(self) -> pd.DataFrame:
        metric = self.state.sort_metric
        if metric not in self.data.summary.columns:
            metric = "Costo_Total_mean"
        ascending = self.state.sort_ascending
        if self.state.reverse_sort:
            ascending = not ascending
        return self.data.summary.sort_values(metric, ascending=ascending).reset_index(drop=True)

    def selected_row(self) -> pd.Series | None:
        df = self.sorted_summary()
        if df.empty:
            return None
        if self.state.selected_id in set(df["Scenario_ID"].astype(str)):
            return df[df["Scenario_ID"].astype(str) == str(self.state.selected_id)].iloc[0]
        self.state.selected_id = str(df.iloc[0]["Scenario_ID"])
        return df.iloc[0]

    def move_selection(self, delta: int) -> None:
        df = self.sorted_summary()
        if df.empty:
            return
        ids = df["Scenario_ID"].astype(str).tolist()
        current = ids.index(str(self.state.selected_id)) if self.state.selected_id in ids else 0
        current = int(clamp(current + delta, 0, len(ids) - 1))
        self.state.selected_id = ids[current]
        visible_rows = 14
        if current < self.state.scroll:
            self.state.scroll = current
        elif current >= self.state.scroll + visible_rows:
            self.state.scroll = current - visible_rows + 1

    def draw(self) -> None:
        self.zones.clear()
        width, height = self.screen.get_size()
        self.screen.fill(BG)
        self.draw_header(width)
        self.draw_tabs(width)
        content = pygame.Rect(24, 132, width - 48, height - 156)
        if self.state.tab == "resumen":
            self.draw_summary(content)
        elif self.state.tab == "ranking":
            self.draw_ranking(content)
        elif self.state.tab == "riesgo":
            self.draw_risk(content)
        elif self.state.tab == "sensibilidad":
            self.draw_sensitivity(content)
        else:
            self.draw_scenario(content)

    def draw_header(self, width: int) -> None:
        title_rect = pygame.Rect(24, 18, width - 48, 34)
        draw_text(self.screen, "Dashboard actuarial de inventarios", self.fonts["title"], TEXT, title_rect)

        manifest = self.data.manifest
        created = manifest.get("created_at", "-")
        scenario_count = len(self.data.summary)
        run_count = len(self.data.runs)
        subtitle = f"{scenario_count:,} escenarios | {run_count:,} corridas | Datos generados: {created}"
        draw_text(self.screen, subtitle, self.fonts["small"], MUTED, pygame.Rect(24, 54, width - 48, 22))

    def draw_tabs(self, width: int) -> None:
        x = 24
        y = 88
        for key, label in TAB_DEFS:
            rect = pygame.Rect(x, y, 136, 32)
            active = self.state.tab == key
            draw_button(self.screen, rect, label, self.fonts["small"], active=active, accent=BLUE_DARK)
            self.add_zone(rect, "tab", key)
            x += 146

        sort_label = next((label for label, metric, _ in SORT_OPTIONS if metric == self.state.sort_metric), "Costo ($)")
        direction = "asc" if (self.state.sort_ascending ^ self.state.reverse_sort) else "desc"
        draw_text(
            self.screen,
            f"Orden: {sort_label} ({direction})",
            self.fonts["small"],
            MUTED,
            pygame.Rect(width - 280, y + 6, 256, 20),
            align="right",
        )

    def draw_summary(self, content: pygame.Rect) -> None:
        summary = self.data.summary
        selected = self.selected_row()
        if selected is None:
            return

        card_gap = 12
        card_w = (content.width - card_gap * 3) // 4
        top = content.y
        metrics = [
            (
                "Escenarios evaluados",
                compact_number(len(summary), 0),
                f"{len(self.data.runs):,} replicas simuladas",
                BLUE,
            ),
            (
                "Servicio promedio (%)",
                pct(summary["Nivel_Servicio_mean"].mean(), 1),
                "media entre politicas",
                GREEN,
            ),
            (
                "Costo medio global ($)",
                money(self.data.runs["Costo_Total"].mean()),
                "inventario, escasez y ordenes",
                ORANGE,
            ),
            (
                "Escenarios con ruptura (%)",
                pct((summary["Prob_Ruptura"] > 0).mean() * 100, 1),
                "con ventas perdidas",
                RED,
            ),
        ]
        for index, (title, value, detail, color) in enumerate(metrics):
            rect = pygame.Rect(content.x + index * (card_w + card_gap), top, card_w, 106)
            draw_metric_card(self.screen, rect, title, value, detail, self.fonts, color)

        chart_top = top + 122
        left = pygame.Rect(content.x, chart_top, int(content.width * 0.62), content.height - 122)
        right = pygame.Rect(left.right + 14, chart_top, content.right - left.right - 14, content.height - 122)
        draw_scatter(
            self.screen,
            left,
            summary,
            "Costo_Total_mean",
            "Nivel_Servicio_mean",
            "Prob_Ruptura",
            "Costo total ($) vs nivel de servicio (%)",
            self.fonts,
            str(selected["Scenario_ID"]),
        )
        self.draw_frontier_panel(right)

    def draw_frontier_panel(self, rect: pygame.Rect) -> None:
        draw_card(self.screen, rect)
        draw_text(self.screen, "Mejores politicas", self.fonts["section"], TEXT, pygame.Rect(rect.x + 16, rect.y + 14, rect.width - 32, 24))
        candidates = self.data.summary[self.data.summary["Nivel_Servicio_mean"] >= 95].copy()
        if candidates.empty:
            candidates = self.data.summary.copy()
        candidates = candidates.sort_values(["Costo_Total_mean", "Prob_Ruptura"], ascending=[True, True]).head(8)
        y = rect.y + 52
        headers = [("ID", 68), ("Serv (%)", 62), ("Costo ($)", 92), ("Rupt (%)", 62)]
        x = rect.x + 16
        for label, width in headers:
            draw_text(self.screen, label, self.fonts["tiny"], MUTED, pygame.Rect(x, y, width, 18))
            x += width
        y += 20
        for _, row in candidates.iterrows():
            row_rect = pygame.Rect(rect.x + 10, y - 2, rect.width - 20, 30)
            active = str(row["Scenario_ID"]) == str(self.state.selected_id)
            if active:
                pygame.draw.rect(self.screen, (233, 241, 255), row_rect, border_radius=6)
            self.add_zone(row_rect, "select", str(row["Scenario_ID"]))
            x = rect.x + 16
            values = [
                str(row["Scenario_ID"]),
                pct(row["Nivel_Servicio_mean"], 1),
                money(row["Costo_Total_mean"]),
                pct(row["Prob_Ruptura"], 0),
            ]
            widths = [68, 62, 92, 62]
            for value, width in zip(values, widths, strict=True):
                draw_text(self.screen, value, self.fonts["table"], TEXT, pygame.Rect(x, y, width, 22), valign="center")
                x += width
            y += 32

        if not self.data.historical.empty:
            hist = self.data.historical
            hist_rect = pygame.Rect(rect.x + 16, rect.bottom - 104, rect.width - 32, 84)
            pygame.draw.rect(self.screen, PANEL_ALT, hist_rect, border_radius=8)
            draw_text(self.screen, "Historico original", self.fonts["small"], TEXT, pygame.Rect(hist_rect.x + 12, hist_rect.y + 10, hist_rect.width - 24, 18))
            draw_text(
                self.screen,
                f"{len(hist):,} corridas | Servicio medio {hist['Nivel Servicio'].mean():.1f}%",
                self.fonts["tiny"],
                MUTED,
                pygame.Rect(hist_rect.x + 12, hist_rect.y + 36, hist_rect.width - 24, 18),
            )
            draw_text(
                self.screen,
                f"Ventas perdidas acumuladas: {int(hist['Ventas Perdidas'].sum())} eventos",
                self.fonts["tiny"],
                MUTED,
                pygame.Rect(hist_rect.x + 12, hist_rect.y + 56, hist_rect.width - 24, 18),
            )

    def draw_ranking(self, content: pygame.Rect) -> None:
        y = content.y
        x = content.x
        for label, metric, ascending in SORT_OPTIONS:
            rect = pygame.Rect(x, y, 124, 32)
            draw_button(self.screen, rect, label, self.fonts["tiny"], active=self.state.sort_metric == metric, accent=BLUE)
            self.add_zone(rect, "sort", (label, metric, ascending))
            x += 132

        table = pygame.Rect(content.x, content.y + 46, int(content.width * 0.64), content.height - 46)
        detail = pygame.Rect(table.right + 14, content.y + 46, content.right - table.right - 14, content.height - 46)
        self.draw_ranking_table(table)
        self.draw_selected_detail(detail)

    def draw_ranking_table(self, rect: pygame.Rect) -> None:
        draw_card(self.screen, rect)
        draw_text(self.screen, "Ranking de escenarios", self.fonts["section"], TEXT, pygame.Rect(rect.x + 16, rect.y + 12, rect.width - 32, 24))
        df = self.sorted_summary()
        visible_rows = max(5, (rect.height - 78) // 34)
        max_scroll = max(0, len(df) - visible_rows)
        self.state.scroll = int(clamp(self.state.scroll, 0, max_scroll))
        start = self.state.scroll
        end = min(len(df), start + visible_rows)

        headers = [
            ("ID", 74),
            ("Serv (%)", 82),
            ("Costo ($)", 104),
            ("CVaR95 ($)", 104),
            ("Rupt (%)", 76),
            ("Dem. ton/dia", 92),
            ("Categoria", 90),
        ]
        y = rect.y + 48
        x = rect.x + 16
        for label, width in headers:
            draw_text(self.screen, label, self.fonts["tiny"], MUTED, pygame.Rect(x, y, width, 18))
            x += width

        y += 24
        for _, row in df.iloc[start:end].iterrows():
            row_rect = pygame.Rect(rect.x + 10, y - 3, rect.width - 20, 31)
            active = str(row["Scenario_ID"]) == str(self.state.selected_id)
            fill = (232, 241, 255) if active else PANEL_ALT if (_ % 2 == 0) else PANEL
            pygame.draw.rect(self.screen, fill, row_rect, border_radius=6)
            self.add_zone(row_rect, "select", str(row["Scenario_ID"]))
            values = [
                str(row["Scenario_ID"]),
                pct(row["Nivel_Servicio_mean"], 1),
                money(row["Costo_Total_mean"]),
                money(row["Costo_Total_CVaR95"]),
                pct(row["Prob_Ruptura"], 0),
                compact_number(row["Demanda_Diaria_Esperada"], 1),
                str(row["Categoria_Riesgo"]),
            ]
            widths = [74, 82, 104, 104, 76, 92, 90]
            x = rect.x + 16
            for value, width in zip(values, widths, strict=True):
                color = risk_color(float(row["Prob_Ruptura"])) if value == pct(row["Prob_Ruptura"], 0) else TEXT
                draw_text(self.screen, value, self.fonts["table"], color, pygame.Rect(x, y, width, 24), valign="center")
                x += width
            y += 34

    def draw_selected_detail(self, rect: pygame.Rect) -> None:
        selected = self.selected_row()
        if selected is None:
            return
        draw_card(self.screen, rect)
        draw_text(self.screen, f"Detalle {selected['Scenario_ID']}", self.fonts["section"], TEXT, pygame.Rect(rect.x + 16, rect.y + 14, rect.width - 32, 24))
        draw_text(self.screen, selected["Escenario"], self.fonts["small"], MUTED, pygame.Rect(rect.x + 16, rect.y + 40, rect.width - 32, 20))

        metric_rows = [
            ("Servicio medio (%)", pct(selected["Nivel_Servicio_mean"], 2), GREEN),
            ("Costo medio ($)", money(selected["Costo_Total_mean"]), ORANGE),
            ("CVaR 95 ($)", money(selected["Costo_Total_CVaR95"]), RED),
            ("Prob. ruptura (%)", pct(selected["Prob_Ruptura"], 1), risk_color(float(selected["Prob_Ruptura"]))),
            ("Inventario prom. (ton)", compact_number(selected["Inventario_Promedio_mean"], 1), BLUE),
            ("Ordenes prom. (eventos)", compact_number(selected["Ordenes_Proveedor_mean"], 1), PURPLE),
        ]
        y = rect.y + 76
        for index, (label, value, color) in enumerate(metric_rows):
            row_rect = pygame.Rect(rect.x + 16, y + index * 34, rect.width - 32, 28)
            pygame.draw.rect(self.screen, PANEL_ALT, row_rect, border_radius=6)
            pygame.draw.circle(self.screen, color, (row_rect.x + 11, row_rect.centery), 4)
            draw_text(self.screen, label, self.fonts["tiny"], MUTED, pygame.Rect(row_rect.x + 24, row_rect.y, 156, row_rect.height), valign="center")
            draw_text(self.screen, value, self.fonts["table"], TEXT, pygame.Rect(row_rect.right - 126, row_rect.y, 118, row_rect.height), align="right", valign="center")

        runs = self.data.runs[self.data.runs["Scenario_ID"].astype(str) == str(selected["Scenario_ID"])]
        spark_rect = pygame.Rect(rect.x + 16, rect.y + 306, rect.width - 32, max(120, rect.height - 328))
        self.draw_replica_sparkline(spark_rect, runs)

    def draw_replica_sparkline(self, rect: pygame.Rect, runs: pd.DataFrame) -> None:
        draw_card(self.screen, rect, fill=PANEL_ALT)
        draw_text(self.screen, "Variabilidad por replica: costo total ($)", self.fonts["small"], TEXT, pygame.Rect(rect.x + 14, rect.y + 10, rect.width - 28, 20))
        if runs.empty:
            return
        chart = pygame.Rect(rect.x + 38, rect.y + 44, rect.width - 58, rect.height - 68)
        for i in range(4):
            y = chart.y + round(chart.height * i / 3)
            pygame.draw.line(self.screen, GRID, (chart.x, y), (chart.right, y), 1)
        values = runs.sort_values("Replica")["Costo_Total"].astype(float).tolist()
        min_v, max_v = min(values), max(values)
        if math.isclose(min_v, max_v):
            max_v = min_v + 1
        points = []
        for index, value in enumerate(values):
            x = chart.x + int(index / max(1, len(values) - 1) * chart.width)
            y = chart.bottom - int((value - min_v) / (max_v - min_v) * chart.height)
            points.append((x, y))
        if len(points) >= 2:
            pygame.draw.lines(self.screen, ORANGE, False, points, 2)
        for point in points:
            pygame.draw.circle(self.screen, ORANGE, point, 4)
        draw_text(self.screen, money(max_v), self.fonts["tiny"], MUTED, pygame.Rect(chart.x - 34, chart.y, 32, 16), align="right")
        draw_text(self.screen, money(min_v), self.fonts["tiny"], MUTED, pygame.Rect(chart.x - 34, chart.bottom - 14, 32, 16), align="right")

    def draw_risk(self, content: pygame.Rect) -> None:
        runs = self.data.runs
        selected = self.selected_row()
        if selected is None:
            return
        selected_runs = runs[runs["Scenario_ID"].astype(str) == str(selected["Scenario_ID"])]

        card_gap = 12
        card_w = (content.width - card_gap * 3) // 4
        risk_metrics = [
            ("VaR 95 global ($)", money(runs["Costo_Total"].quantile(0.95)), "percentil de costo", RED),
            ("CVaR 95 global ($)", money(runs.loc[runs["Costo_Total"] >= runs["Costo_Total"].quantile(0.95), "Costo_Total"].mean()), "cola superior de costo", RED),
            ("Peor ruptura media (%)", pct(self.data.summary["Prob_Ruptura"].max(), 1), "por escenario", YELLOW),
            ("Fill rate medio (%)", pct(runs["Fill_Rate_Unidades"].mean(), 1), "ton surtidas", GREEN),
        ]
        for index, (title, value, detail, color) in enumerate(risk_metrics):
            rect = pygame.Rect(content.x + index * (card_w + card_gap), content.y, card_w, 102)
            draw_metric_card(self.screen, rect, title, value, detail, self.fonts, color)

        top = content.y + 118
        left = pygame.Rect(content.x, top, (content.width - 14) // 2, content.height - 118)
        right = pygame.Rect(left.right + 14, top, content.right - left.right - 14, content.height - 118)
        draw_histogram(self.screen, left, runs["Costo_Total"], "Distribucion de costo total ($)", self.fonts, ORANGE)
        draw_histogram(self.screen, right, selected_runs["Costo_Total"], f"Costo total ($) - {selected['Scenario_ID']}", self.fonts, BLUE)

    def draw_sensitivity(self, content: pygame.Rect) -> None:
        top = pygame.Rect(content.x, content.y, content.width, 80)
        draw_card(self.screen, top)
        draw_text(self.screen, "Sensibilidad de variables operables", self.fonts["section"], TEXT, pygame.Rect(top.x + 16, top.y + 14, top.width - 32, 24))
        draw_text(
            self.screen,
            "Efecto promedio al pasar del nivel bajo al alto de cada parametro dentro del DOE.",
            self.fonts["small"],
            MUTED,
            pygame.Rect(top.x + 16, top.y + 42, top.width - 32, 20),
        )

        left = pygame.Rect(content.x, content.y + 96, (content.width - 14) // 2, content.height - 96)
        right = pygame.Rect(left.right + 14, content.y + 96, content.right - left.right - 14, content.height - 96)
        cost_rows = self.sensitivity_rows("Costo_Total_mean", lower_is_better=True)
        service_rows = self.sensitivity_rows("Nivel_Servicio_mean", lower_is_better=False)
        draw_horizontal_bars(self.screen, left, cost_rows, "Impacto en costo medio ($)", self.fonts, money)
        draw_horizontal_bars(self.screen, right, service_rows, "Impacto en nivel de servicio (puntos %)", self.fonts, lambda v: pct(v, 2))

    def sensitivity_rows(self, metric: str, lower_is_better: bool) -> list[tuple[str, float, tuple[int, int, int]]]:
        rows: list[tuple[str, float, tuple[int, int, int]]] = []
        for parameter in PARAMETER_COLUMNS:
            if parameter not in self.data.summary.columns:
                continue
            grouped = self.data.summary.groupby(parameter)[metric].mean().sort_index()
            if len(grouped) < 2:
                continue
            effect = float(grouped.iloc[-1] - grouped.iloc[0])
            good = effect < 0 if lower_is_better else effect > 0
            color = GREEN if good else RED
            rows.append((PARAMETER_LABELS.get(parameter, parameter), effect, color))
        rows.sort(key=lambda item: abs(item[1]), reverse=True)
        return rows[:8]

    def draw_scenario(self, content: pygame.Rect) -> None:
        selected = self.selected_row()
        if selected is None:
            return
        runs = self.data.runs[self.data.runs["Scenario_ID"].astype(str) == str(selected["Scenario_ID"])]

        left = pygame.Rect(content.x, content.y, int(content.width * 0.38), content.height)
        right = pygame.Rect(left.right + 14, content.y, content.right - left.right - 14, content.height)
        self.draw_parameter_panel(left, selected)

        top = pygame.Rect(right.x, right.y, right.width, int((right.height - 14) * 0.48))
        bottom = pygame.Rect(right.x, top.bottom + 14, right.width, right.bottom - top.bottom - 14)
        draw_histogram(self.screen, top, runs["Nivel_Servicio"], f"Nivel de servicio (%) por replica - {selected['Scenario_ID']}", self.fonts, GREEN)
        self.draw_event_mix(bottom, selected)

    def draw_parameter_panel(self, rect: pygame.Rect, selected: pd.Series) -> None:
        draw_card(self.screen, rect)
        draw_text(self.screen, f"Escenario {selected['Scenario_ID']}", self.fonts["section"], TEXT, pygame.Rect(rect.x + 16, rect.y + 14, rect.width - 32, 24))
        draw_text(self.screen, selected["Escenario"], self.fonts["small"], MUTED, pygame.Rect(rect.x + 16, rect.y + 40, rect.width - 32, 20))

        rows = [
            ("Capacidad bodega (ton)", compact_number(selected["CAPACIDAD_BODEGA"], 0)),
            ("Stock inicial (ton)", compact_number(selected["STOCK_INICIAL"], 0)),
            ("Punto reorden ROP (ton)", compact_number(selected["PUNTO_REORDEN"], 0)),
            ("Cantidad reabasto Q (ton)", compact_number(selected["CANTIDAD_REABASTECIMIENTO"], 0)),
            ("Tiempo entre llegadas (dias)", f"{selected['TIEMPO_ENTRE_LLEGADAS']:.1f}"),
            ("Tamano pedido medio (ton)", compact_number(selected["TAMANO_PEDIDO"], 0)),
            ("Lead time proveedor (dias)", f"{selected['LEAD_TIME_PROVEEDOR']:.1f}"),
            ("Horizonte simulacion (dias)", f"{int(selected['TIEMPO_SIMULACION'])}"),
            ("Cobertura ROP (dias)", f"{selected['Cobertura_ROP_Dias']:.1f}"),
            ("Brecha lead time (dias)", f"{selected['Brecha_LeadTime_Dias']:.1f}"),
        ]
        y = rect.y + 78
        for label, value in rows:
            row_rect = pygame.Rect(rect.x + 16, y, rect.width - 32, 30)
            pygame.draw.rect(self.screen, PANEL_ALT, row_rect, border_radius=6)
            draw_text(self.screen, label, self.fonts["tiny"], MUTED, pygame.Rect(row_rect.x + 10, row_rect.y, 230, row_rect.height), valign="center")
            draw_text(self.screen, value, self.fonts["table"], TEXT, pygame.Rect(row_rect.right - 118, row_rect.y, 108, row_rect.height), align="right", valign="center")
            y += 34

        rec_rect = pygame.Rect(rect.x + 16, rect.bottom - 116, rect.width - 32, 96)
        pygame.draw.rect(self.screen, PANEL_ALT, rec_rect, border_radius=8)
        draw_text(self.screen, "Lectura actuarial", self.fonts["small"], TEXT, pygame.Rect(rec_rect.x + 12, rec_rect.y + 10, rec_rect.width - 24, 18))
        recommendation = self.recommendation(selected)
        draw_text(self.screen, recommendation[0], self.fonts["tiny"], recommendation[1], pygame.Rect(rec_rect.x + 12, rec_rect.y + 36, rec_rect.width - 24, 18))
        draw_text(self.screen, recommendation[2], self.fonts["tiny"], MUTED, pygame.Rect(rec_rect.x + 12, rec_rect.y + 58, rec_rect.width - 24, 18))

    def recommendation(self, selected: pd.Series) -> tuple[str, tuple[int, int, int], str]:
        service = float(selected["Nivel_Servicio_mean"])
        rupture = float(selected["Prob_Ruptura"])
        inventory = float(selected["Inventario_Promedio_mean"])
        reorder = float(selected["PUNTO_REORDEN"])
        if service < 95 or rupture > 25:
            return (
                "Riesgo de escasez relevante.",
                RED,
                "Conviene subir ROP, Q o reducir lead time.",
            )
        if inventory > reorder * 2.8 and rupture == 0:
            return (
                "Servicio estable con inventario alto.",
                ORANGE,
                "Hay margen para reducir Q o stock inicial.",
            )
        return (
            "Politica balanceada.",
            GREEN,
            "Buen servicio sin sobrecargar inventario.",
        )

    def draw_event_mix(self, rect: pygame.Rect, selected: pd.Series) -> None:
        draw_card(self.screen, rect)
        draw_text(self.screen, "Mezcla de eventos (conteo)", self.fonts["section"], TEXT, pygame.Rect(rect.x + 16, rect.y + 12, rect.width - 32, 24))
        if self.data.events.empty:
            draw_text(self.screen, "Eventos no cargados", self.fonts["body"], MUTED, rect.inflate(-32, -64), align="center", valign="center")
            return
        events = self.data.events[self.data.events["Scenario_ID"].astype(str) == str(selected["Scenario_ID"])]
        if events.empty or "Tipo_Evento" not in events.columns:
            draw_text(self.screen, "Sin eventos para este escenario", self.fonts["body"], MUTED, rect.inflate(-32, -64), align="center", valign="center")
            return
        counts = events["Tipo_Evento"].value_counts().head(6)
        max_count = int(counts.max()) or 1
        plot = pygame.Rect(rect.x + 18, rect.y + 52, rect.width - 36, rect.height - 72)
        row_h = max(26, plot.height // max(1, len(counts)))
        colors = [BLUE, GREEN, ORANGE, RED, PURPLE, CYAN]
        for index, (label, count) in enumerate(counts.items()):
            y = plot.y + index * row_h
            draw_text(self.screen, label, self.fonts["tiny"], MUTED, pygame.Rect(plot.x, y, int(plot.width * 0.38), row_h), valign="center")
            bar_x = plot.x + int(plot.width * 0.40)
            bar_w = int((count / max_count) * (plot.width * 0.42))
            pygame.draw.rect(self.screen, colors[index % len(colors)], pygame.Rect(bar_x, y + 7, bar_w, row_h - 14), border_radius=4)
            draw_text(self.screen, compact_number(count, 0), self.fonts["tiny"], TEXT, pygame.Rect(plot.right - 70, y, 68, row_h), align="right", valign="center")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Dashboard interactivo Pygame para el DOE de simulacion.")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--width", type=int, default=1360)
    parser.add_argument("--height", type=int, default=820)
    parser.add_argument("--smoke-test", action="store_true", help="Carga datos, renderiza un frame y termina.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data = load_dashboard_data(args.data_dir)

    if args.smoke_test:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

    pygame.init()
    pygame.display.set_caption("Dashboard actuarial de simulaciones")
    flags = pygame.RESIZABLE
    if args.smoke_test and hasattr(pygame, "HIDDEN"):
        flags |= pygame.HIDDEN
    screen = pygame.display.set_mode((args.width, args.height), flags)
    clock = pygame.time.Clock()
    dashboard = Dashboard(screen, data)

    if args.smoke_test:
        dashboard.draw()
        pygame.display.flip()
        pygame.quit()
        print("Smoke test OK: datos cargados y frame renderizado.")
        return

    running = True
    while running:
        for event in pygame.event.get():
            running = dashboard.handle_event(event)
        dashboard.draw()
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
