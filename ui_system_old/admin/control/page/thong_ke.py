"""
Thống Kê Admin — Dark Theme
Thống Kê — Con Bò Cười Design System
"""
import flet as ft

from src.ui.theme import (
    BG_MAIN, BG_PANEL, PRIMARY, SECONDARY, ACCENT,
    TEXT_MAIN, TEXT_SUB, TEXT_MUTED,
    WARNING, DANGER, BORDER,
    GRAD_TEAL, GRAD_CYAN, GRAD_WARN, GRAD_DANGER, GRAD_PURPLE,
    RADIUS_CARD, SIZE_H1, SIZE_H2, SIZE_H3, SIZE_BODY, SIZE_CAPTION,
    SHADOW_CARD_GLOW,
    kpi_card, panel, primary_button, status_badge,
)


class ThongKePage(ft.Column):
    def __init__(self):
        super().__init__(expand=True, scroll=ft.ScrollMode.AUTO, spacing=0)
        self._build()

    def _build(self):
        # ── KPI tóm tắt ──
        kpi_row = ft.Row([
            kpi_card(ft.Icons.BAR_CHART_ROUNDED,
                     "Tổng Lượt Nhận Diện", "14,320",
                     "7 ngày gần nhất",
                     grad_colors=GRAD_TEAL),
            kpi_card(ft.Icons.PEOPLE_ALT_ROUNDED,
                     "Khách Hàng Hoạt Động", "38",
                     "Trên tổng 42",
                     grad_colors=GRAD_PURPLE),
            kpi_card(ft.Icons.WARNING_AMBER_ROUNDED,
                     "Tổng Cảnh Báo", "89",
                     "7 ngày",
                     grad_colors=GRAD_WARN),
            kpi_card(ft.Icons.CHECK_CIRCLE_ROUNDED,
                     "Tỉ Lệ Thành Công", "97.2%",
                     "Accuracy nhận diện",
                     grad_colors=GRAD_CYAN),
        ], spacing=14)

        # ── Bar chart: nhận diện 7 ngày ──
        week_data = [
            ("T2", 1820), ("T3", 2150), ("T4", 1940), ("T5", 2380),
            ("T6", 2210), ("T7", 2600), ("CN", 1820),
        ]
        bar_chart = ft.BarChart(
            bar_groups=[
                ft.BarChartGroup(x=i, bar_rods=[
                    ft.BarChartRod(
                        from_y=0, to_y=val / 100, width=28,
                        gradient=ft.LinearGradient(
                            begin=ft.alignment.bottom_center,
                            end=ft.alignment.top_center,
                            colors=[SECONDARY, PRIMARY],
                        ),
                        tooltip=f"{label}: {val:,} lượt",
                        border_radius=ft.BorderRadius(5, 5, 0, 0),
                    )
                ])
                for i, (label, val) in enumerate(week_data)
            ],
            left_axis=ft.ChartAxis(labels_size=36),
            bottom_axis=ft.ChartAxis(labels=[
                ft.ChartAxisLabel(
                    value=i,
                    label=ft.Text(label, size=10, color=TEXT_SUB),
                )
                for i, (label, _) in enumerate(week_data)
            ]),
            horizontal_grid_lines=ft.ChartGridLines(
                color=ft.Colors.with_opacity(0.06, ft.Colors.WHITE), width=1,
            ),
            tooltip_bgcolor=ft.Colors.with_opacity(0.85, BG_PANEL),
            max_y=28, expand=True,
            bgcolor=ft.Colors.TRANSPARENT,
            interactive=True,
        )

        main_chart_panel = panel(
            content=bar_chart,
            title="Tổng Lượt Nhận Diện — 7 Ngày Gần Nhất",
            icon=ft.Icons.SHOW_CHART_ROUNDED,
            action_widget=ft.Dropdown(
                options=[
                    ft.dropdown.Option("7 ngày"),
                    ft.dropdown.Option("30 ngày"),
                    ft.dropdown.Option("3 tháng"),
                ],
                value="7 ngày",
                bgcolor=BG_PANEL,
                border_color=BORDER,
                focused_border_color=PRIMARY,
                text_style=ft.TextStyle(color=TEXT_MAIN, size=11),
                width=120,
            ),
            expand=True,
        )

        # ── Top 5 khách hàng ──
        top_kh = [
            ("Lê Quang Minh",   5, 4820, PRIMARY),
            ("Hoàng Thu Hương", 4, 3910, SECONDARY),
            ("Nguyễn Văn An",   3, 3240, ACCENT),
            ("Đỗ Văn Tuấn",     2, 2180, WARNING),
            ("Trần Thị Bình",   2, 1950, DANGER),
        ]

        def _kh_bar(rank, name, farms, count, color):
            max_count = top_kh[0][2]
            pct = count / max_count
            return ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text(f"#{rank}", size=11, color=color,
                                weight=ft.FontWeight.BOLD, width=24),
                        ft.Text(name, size=SIZE_BODY, color=TEXT_MAIN, expand=True),
                        ft.Text(f"{count:,}", size=SIZE_BODY, color=TEXT_SUB),
                    ]),
                    ft.Row([
                        ft.Container(width=24),
                        ft.Container(
                            width=None, height=4,
                            bgcolor=color, border_radius=2,
                            expand=True,
                        ),
                    ]),
                ], spacing=4),
                padding=ft.padding.symmetric(vertical=6),
            )

        top_kh_content = ft.Column([
            _kh_bar(i+1, name, farms, count, color)
            for i, (name, farms, count, color) in enumerate(top_kh)
        ], spacing=2)

        top_kh_panel = panel(
            content=top_kh_content,
            title="Top 5 KH Nhiều Lượt Nhận Diện",
            icon=ft.Icons.LEADERBOARD_ROUNDED,
            width=340,
        )

        # ── Bảng chi tiết ──
        def _detail_row(name, farms, scans, alerts, model, success_pct):
            return ft.Container(
                content=ft.Row([
                    ft.Text(name, size=SIZE_BODY, color=TEXT_MAIN, expand=True),
                    ft.Text(str(farms), size=SIZE_BODY, color=TEXT_SUB, width=70),
                    ft.Text(f"{scans:,}", size=SIZE_BODY, color=TEXT_SUB, width=90),
                    ft.Text(str(alerts), size=SIZE_BODY,
                            color=DANGER if alerts > 10 else TEXT_SUB, width=70),
                    ft.Container(
                        content=ft.Text(model, size=9, color=PRIMARY,
                                        weight=ft.FontWeight.BOLD),
                        border=ft.border.all(1, PRIMARY), border_radius=6,
                        padding=ft.padding.symmetric(horizontal=8, vertical=2),
                        width=90,
                    ),
                    ft.Text(f"{success_pct}%", size=SIZE_BODY,
                            color=PRIMARY if success_pct >= 95 else WARNING, width=65),
                ], spacing=10),
                bgcolor=ft.Colors.with_opacity(0.02, ft.Colors.WHITE),
                border_radius=6,
                padding=ft.padding.symmetric(horizontal=12, vertical=8),
                border=ft.border.all(1, ft.Colors.with_opacity(0.04, ft.Colors.WHITE)),
            )

        detail_header = ft.Container(
            content=ft.Row([
                ft.Text("Trang Trại", size=10, color=TEXT_MUTED,
                        weight=ft.FontWeight.BOLD, expand=True),
                ft.Text("Số Farm", size=10, color=TEXT_MUTED,
                        weight=ft.FontWeight.BOLD, width=70),
                ft.Text("Lượt Scan", size=10, color=TEXT_MUTED,
                        weight=ft.FontWeight.BOLD, width=90),
                ft.Text("Alert", size=10, color=TEXT_MUTED,
                        weight=ft.FontWeight.BOLD, width=70),
                ft.Text("Model", size=10, color=TEXT_MUTED,
                        weight=ft.FontWeight.BOLD, width=90),
                ft.Text("Thành Công", size=10, color=TEXT_MUTED,
                        weight=ft.FontWeight.BOLD, width=65),
            ], spacing=10),
            bgcolor=ft.Colors.with_opacity(0.04, ft.Colors.WHITE),
            border_radius=ft.BorderRadius(8, 8, 0, 0),
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
        )

        detail_rows = ft.Column([
            _detail_row("Nguyễn Văn An",   3, 3240, 8,  "YOLOv9", 97.2),
            ft.Divider(color=BORDER, height=1),
            _detail_row("Trần Thị Bình",   2, 1950, 5,  "YOLOv8", 95.8),
            ft.Divider(color=BORDER, height=1),
            _detail_row("Lê Quang Minh",   5, 4820, 18, "Custom", 93.1),
            ft.Divider(color=BORDER, height=1),
            _detail_row("Phạm Hoàng Nam",  1,  420, 2,  "YOLOv8", 98.5),
            ft.Divider(color=BORDER, height=1),
            _detail_row("Hoàng Thu Hương", 4, 3910, 12, "YOLOv9", 96.4),
            ft.Divider(color=BORDER, height=1),
            _detail_row("Đỗ Văn Tuấn",     2, 2180, 7,  "YOLOv8", 97.9),
        ], spacing=0)

        detail_panel = panel(
            content=ft.Column([
                detail_header,
                detail_rows,
            ], spacing=0),
            title="Chi Tiết Theo Khách Hàng",
            icon=ft.Icons.TABLE_CHART_ROUNDED,
            action_widget=ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.DOWNLOAD_ROUNDED, size=14, color=PRIMARY),
                    ft.Text("Xuất Excel", size=SIZE_CAPTION, color=PRIMARY),
                ], spacing=4),
                ink=True, border_radius=8,
                border=ft.border.all(1, PRIMARY),
                padding=ft.padding.symmetric(horizontal=10, vertical=4),
            ),
            expand=True,
        )

        # ── Assemble ──
        self.controls = [
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Column([
                            ft.Text("Thống Kê Hệ Thống",
                                    size=SIZE_H1, weight=ft.FontWeight.BOLD,
                                    color=TEXT_MAIN),
                            ft.Text("Phân tích dữ liệu nhận diện toàn bộ hệ thống Con Bò Cười",
                                    size=SIZE_CAPTION, color=TEXT_SUB),
                        ], spacing=2),
                        ft.Container(expand=True),
                        primary_button("Xuất Báo Cáo PDF",
                                       icon=ft.Icons.PICTURE_AS_PDF_ROUNDED),
                    ]),
                    ft.Container(height=16),
                    kpi_row,
                    ft.Container(height=16),
                    ft.Row([
                        main_chart_panel,
                        ft.Container(width=12),
                        top_kh_panel,
                    ], expand=True, vertical_alignment=ft.CrossAxisAlignment.START),
                    ft.Container(height=16),
                    detail_panel,
                    ft.Container(height=16),
                ], spacing=0),
                padding=ft.padding.symmetric(horizontal=4, vertical=4),
            )
        ]
