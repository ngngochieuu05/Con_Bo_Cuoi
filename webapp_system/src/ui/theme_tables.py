from __future__ import annotations

import flet as ft


def _on_row_hover(e: ft.ControlEvent):
    e.control.bgcolor = (
        ft.Colors.with_opacity(0.22, ft.Colors.WHITE)
        if e.data == "true"
        else ft.Colors.with_opacity(0.09, ft.Colors.WHITE)
    )
    e.control.update()


def data_table(headers: list[str], rows: list[list[ft.Control]], col_flex: list[int] | None = None):
    count = len(headers)
    flex = col_flex if (col_flex and len(col_flex) == count) else [1] * count
    header = ft.Container(
        padding=ft.padding.symmetric(horizontal=12, vertical=9),
        border_radius=12,
        bgcolor=ft.Colors.with_opacity(0.28, ft.Colors.WHITE),
        content=ft.Row(
            controls=[
                ft.Container(
                    expand=flex[i],
                    content=ft.Text(
                        header_text,
                        weight=ft.FontWeight.W_700,
                        size=12,
                        max_lines=1,
                        overflow=ft.TextOverflow.CLIP,
                    ),
                )
                for i, header_text in enumerate(headers)
            ]
        ),
    )
    body_rows = [
        ft.Container(
            ink=True,
            bgcolor=ft.Colors.with_opacity(0.09, ft.Colors.WHITE),
            border_radius=10,
            padding=ft.padding.symmetric(horizontal=12, vertical=9),
            on_hover=_on_row_hover,
            content=ft.Row(
                controls=[
                    ft.Container(expand=flex[i], content=cell)
                    for i, cell in enumerate(row)
                ]
            ),
        )
        for row in rows
    ]
    return ft.Column(spacing=5, controls=[header, ft.Column(spacing=4, controls=body_rows)])
