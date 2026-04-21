from __future__ import annotations

import flet as ft

from ui.theme import SECONDARY


def make_selection_screen(on_ai, on_expert):
    def _card(icon, title, subtitle, color, on_click):
        return ft.Container(
            height=190,
            padding=24,
            border_radius=20,
            bgcolor=ft.Colors.with_opacity(0.12, color),
            border=ft.border.all(1.5, ft.Colors.with_opacity(0.35, color)),
            ink=True,
            on_click=on_click,
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=12,
                controls=[
                    ft.Container(
                        width=64,
                        height=64,
                        border_radius=32,
                        bgcolor=ft.Colors.with_opacity(0.20, color),
                        alignment=ft.alignment.center,
                        content=ft.Icon(icon, size=32, color=color),
                    ),
                    ft.Text(
                        title,
                        size=16,
                        weight=ft.FontWeight.W_700,
                        color=ft.Colors.WHITE,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        subtitle,
                        size=12,
                        color=ft.Colors.WHITE60,
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
            ),
        )

    return ft.Column(
        expand=True,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=0,
        controls=[
            ft.Container(
                padding=ft.padding.symmetric(horizontal=16, vertical=18),
                content=ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=6,
                    controls=[
                        ft.Container(
                            width=52,
                            height=52,
                            border_radius=26,
                            bgcolor=ft.Colors.with_opacity(0.18, SECONDARY),
                            alignment=ft.alignment.center,
                            content=ft.Icon(
                                ft.Icons.HEALTH_AND_SAFETY,
                                size=28,
                                color=SECONDARY,
                            ),
                        ),
                        ft.Text(
                            "Tư vấn sức khỏe bò",
                            size=20,
                            weight=ft.FontWeight.W_700,
                            color=ft.Colors.WHITE,
                        ),
                        ft.Text(
                            "Chọn hình thức tư vấn phù hợp với bạn",
                            size=13,
                            color=ft.Colors.WHITE60,
                            text_align=ft.TextAlign.CENTER,
                        ),
                    ],
                ),
            ),
            ft.Container(
                expand=True,
                padding=ft.padding.symmetric(horizontal=16, vertical=8),
                content=ft.Column(
                    expand=True,
                    spacing=16,
                    controls=[
                        _card(
                            icon=ft.Icons.SMART_TOY,
                            title="Tư vấn qua AI",
                            subtitle="Gửi ảnh con bò để AI phân tích bệnh tật\n"
                            "và đưa ra lời khuyên ngay lập tức.",
                            color=SECONDARY,
                            on_click=lambda e: on_ai(),
                        ),
                        _card(
                            icon=ft.Icons.SUPPORT_AGENT,
                            title="Tư vấn chuyên gia",
                            subtitle="Chọn chuyên gia thú y để nhận tư vấn\n"
                            "trực tiếp từ người có kinh nghiệm.",
                            color=ft.Colors.TEAL_300,
                            on_click=lambda e: on_expert(),
                        ),
                    ],
                ),
            ),
        ],
    )
