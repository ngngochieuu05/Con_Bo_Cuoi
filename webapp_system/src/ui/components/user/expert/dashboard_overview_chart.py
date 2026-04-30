from __future__ import annotations

import inspect

import flet as ft

from bll.services.chat_service import get_case_overview_series
from ui.theme import DANGER, SECONDARY, glass_container, info_strip


def _resolve_chart_namespace():
    try:
        import flet_charts as fch

        return fch
    except Exception:
        pass

    required = (
        "LineChart",
        "LineChartData",
        "LineChartDataPoint",
        "ChartAxis",
        "ChartAxisLabel",
        "ChartGridLines",
    )
    if not all(hasattr(ft, name) for name in required):
        return None

    class _FletChartsShim:
        LineChart = ft.LineChart
        LineChartData = ft.LineChartData
        LineChartDataPoint = ft.LineChartDataPoint
        ChartAxis = ft.ChartAxis
        ChartAxisLabel = ft.ChartAxisLabel
        ChartGridLines = ft.ChartGridLines

    return _FletChartsShim


def _supports_param(callable_obj, param_name: str) -> bool:
    try:
        return param_name in inspect.signature(callable_obj).parameters
    except Exception:
        return False


def _build_line_data(fch, color: str, values: list[int]):
    line_kwargs = {
        "color": color,
        "stroke_width": 3,
        "curved": True,
        "point": True,
    }
    if _supports_param(fch.LineChartData, "rounded_stroke_cap"):
        line_kwargs["rounded_stroke_cap"] = True
    if _supports_param(fch.LineChartData, "stroke_cap_round"):
        line_kwargs["stroke_cap_round"] = True

    points = [fch.LineChartDataPoint(index, value) for index, value in enumerate(values)]
    if _supports_param(fch.LineChartData, "points"):
        line_kwargs["points"] = points
    elif _supports_param(fch.LineChartData, "data_points"):
        line_kwargs["data_points"] = points
    else:
        line_kwargs["points"] = points

    return fch.LineChartData(**line_kwargs)


def _build_axis(fch, *, labels: list, size: int):
    axis_kwargs = {"labels": labels}
    if _supports_param(fch.ChartAxis, "label_size"):
        axis_kwargs["label_size"] = size
    if _supports_param(fch.ChartAxis, "labels_size"):
        axis_kwargs["labels_size"] = size
    return fch.ChartAxis(**axis_kwargs)


def _build_period_chip(label: str, period: str, current_period: str, on_select) -> ft.Control:
    selected = current_period == period
    accent = SECONDARY if selected else ft.Colors.WHITE24
    return ft.Container(
        ink=True,
        on_click=lambda e, value=period: on_select(value),
        padding=ft.padding.symmetric(horizontal=12, vertical=8),
        border_radius=999,
        bgcolor=ft.Colors.with_opacity(0.22 if selected else 0.12, accent),
        border=ft.border.all(1, ft.Colors.with_opacity(0.36 if selected else 0.16, accent)),
        content=ft.Text(
            label,
            size=11,
            weight=ft.FontWeight.W_600,
            color=ft.Colors.WHITE if selected else ft.Colors.WHITE70,
        ),
    )


def _build_summary_card(label: str, value: str, ratio_text: str, accent: str) -> ft.Control:
    return ft.Container(
        padding=12,
        border_radius=16,
        bgcolor=ft.Colors.with_opacity(0.14, accent),
        border=ft.border.all(1, ft.Colors.with_opacity(0.24, accent)),
        content=ft.Column(
            tight=True,
            spacing=8,
            controls=[
                ft.Row(
                    tight=True,
                    spacing=8,
                    controls=[
                        ft.Container(width=9, height=9, border_radius=999, bgcolor=accent),
                        ft.Text(label, size=11, color=ft.Colors.WHITE70),
                    ],
                ),
                ft.Text(value, size=22, weight=ft.FontWeight.W_700, color=ft.Colors.WHITE),
                ft.Text(ratio_text, size=10, color=ft.Colors.WHITE54),
            ],
        ),
    )


def _build_bottom_labels(fch, items: list[dict]) -> list:
    if len(items) <= 7:
        visible_indexes = set(range(len(items)))
    else:
        step = 5 if len(items) >= 25 else 3
        visible_indexes = {0, len(items) - 1, *range(0, len(items), step)}

    labels = []
    for index, item in enumerate(items):
        if index not in visible_indexes:
            continue
        labels.append(
            fch.ChartAxisLabel(
                value=index,
                label=ft.Container(
                    margin=ft.margin.only(top=8),
                    content=ft.Text(item["label"], size=9, color=ft.Colors.WHITE54),
                ),
            )
        )
    return labels


def _build_left_labels(fch, max_value: int) -> list:
    marks = {0, max_value}
    if max_value > 2:
        marks.add(round(max_value / 2))
    if max_value > 4:
        marks.add(round(max_value * 0.75))
    return [
        fch.ChartAxisLabel(
            value=value,
            label=ft.Text(str(value), size=9, color=ft.Colors.WHITE54),
        )
        for value in sorted(marks)
    ]


def _build_chart(fch, series_payload: dict) -> ft.Control:
    items = series_payload["days"]
    summary = series_payload["summary"]
    if not summary["total_cases"]:
        return ft.Container(
            height=190,
            alignment=ft.alignment.center,
            content=ft.Text(
                "Chưa có dữ liệu ca bệnh trong kỳ đã chọn.",
                size=12,
                color=ft.Colors.WHITE54,
                text_align=ft.TextAlign.CENTER,
            ),
        )

    max_value = max(
        max(item["total_cases"] for item in items),
        max(item["severe_cases"] for item in items),
        1,
    )
    max_y = max(3, max_value + 1)
    max_x = max(len(items) - 1, 1)

    return ft.Container(
        height=205,
        content=fch.LineChart(
            min_x=0,
            max_x=max_x,
            min_y=0,
            max_y=max_y,
            interactive=True,
            point_line_start=0,
            data_series=[
                _build_line_data(fch, SECONDARY, [item["total_cases"] for item in items]),
                _build_line_data(fch, DANGER, [item["severe_cases"] for item in items]),
            ],
            left_axis=_build_axis(fch, labels=_build_left_labels(fch, max_value), size=26),
            bottom_axis=_build_axis(fch, labels=_build_bottom_labels(fch, items), size=32),
            horizontal_grid_lines=fch.ChartGridLines(
                color=ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
                width=1,
                dash_pattern=[4, 4],
                interval=1,
            ),
            vertical_grid_lines=fch.ChartGridLines(
                color=ft.Colors.with_opacity(0.06, ft.Colors.WHITE),
                width=1,
                dash_pattern=[4, 4],
                interval=max(1, round(len(items) / 6)),
            ),
            border=ft.border.all(1, ft.Colors.with_opacity(0.08, ft.Colors.WHITE)),
            tooltip=None,
        ),
    )


def build_case_overview_chart(page: ft.Page | None, expert_id: int) -> ft.Control:
    state = {"period": "7d"}
    chart_ref = ft.Ref[ft.Container]()
    fch = _resolve_chart_namespace()

    def _build_body() -> ft.Control:
        series_payload = get_case_overview_series(expert_id, state["period"])
        summary = series_payload["summary"]
        severe_ratio = summary["severe_ratio"] * 100

        chart_control = (
            _build_chart(fch, series_payload)
            if fch is not None
            else info_strip(
                "Runtime này chưa có chart control. Dashboard vẫn giữ summary ca bệnh.",
                tone="warning",
                icon_name="QUERY_STATS",
            )
        )

        return glass_container(
            padding=14,
            radius=18,
            content=ft.Column(
                spacing=12,
                tight=True,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Text("Tổng quan ca bệnh", size=14, weight=ft.FontWeight.W_700),
                            ft.Row(
                                tight=True,
                                spacing=8,
                                controls=[
                                    _build_period_chip("7 ngày", "7d", state["period"], _set_period),
                                    _build_period_chip("30 ngày", "30d", state["period"], _set_period),
                                ],
                            ),
                        ],
                    ),
                    chart_control,
                    ft.Row(
                        spacing=8,
                        controls=[
                            ft.Container(expand=True, content=
                                _build_summary_card(
                                    "Tổng ca",
                                    str(summary["total_cases"]),
                                    "100% trong kỳ đang xem",
                                    SECONDARY,
                                )
                            ),
                            ft.Container(expand=True, content=
                                _build_summary_card(
                                    "Ca nặng",
                                    str(summary["severe_cases"]),
                                    f"{severe_ratio:.0f}% tổng số ca",
                                    DANGER,
                                )
                            ),
                        ],
                    ),
                ],
            ),
        )

    def _set_period(period: str) -> None:
        if state["period"] == period:
            return
        state["period"] = period
        if chart_ref.current:
            chart_ref.current.content = _build_body()
            chart_ref.current.update()
        elif page:
            page.update()

    return ft.Container(ref=chart_ref, content=_build_body())
