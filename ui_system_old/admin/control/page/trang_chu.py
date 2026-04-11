"""
Trang Chủ Admin — Dark Dashboard
Con Bò Cười Design System
"""
import flet as ft
from datetime import datetime

from src.ui.theme import (
    BG_MAIN, BG_PANEL, PRIMARY, SECONDARY, ACCENT,
    TEXT_MAIN, TEXT_SUB, TEXT_MUTED,
    WARNING, DANGER, SUCCESS,
    BORDER, GRAD_TEAL, GRAD_CYAN, GRAD_WARN, GRAD_DANGER, GRAD_PURPLE,
    RADIUS_CARD, RADIUS_BTN,
    SIZE_H1, SIZE_H2, SIZE_H3, SIZE_BODY, SIZE_CAPTION,
    PAD_CARD, SHADOW_CARD, SHADOW_CARD_GLOW,
    kpi_card, panel, primary_button, status_badge, divider,
)


def _hour_greeting() -> str:
    h = datetime.now().hour
    if h < 12:  return "Chào buổi sáng"
    if h < 18:  return "Chào buổi chiều"
    return "Chào buổi tối"


def TrangChu() -> ft.Container:
    today = datetime.now().strftime("%d/%m/%Y")

    # ─── 1. KPI Cards ────────────────────────────────────────────────────────
    kpi_row = ft.Row([
        kpi_card(ft.Icons.PEOPLE_ALT_ROUNDED,
                 "Tổng Khách Hàng", "42",
                 "Đang sử dụng hệ thống",
                 grad_colors=GRAD_TEAL),
        kpi_card(ft.Icons.SMART_TOY_ROUNDED,
                 "Model Đang Chạy", "6",
                 "Trên toàn bộ trang trại",
                 grad_colors=GRAD_PURPLE),
        kpi_card(ft.Icons.WARNING_AMBER_ROUNDED,
                 "Cảnh Báo Hôm Nay", "12",
                 "Cần xem xét ngay",
                 grad_colors=GRAD_WARN),
        kpi_card(ft.Icons.CAMPAIGN_ROUNDED,
                 "OA Bot Telegram", "Online",
                 "Kết nối ổn định",
                 grad_colors=GRAD_CYAN),
    ], spacing=14)

    # ─── 2. Line Chart (BarChart Flet built-in) ──────────────────────────────
    bar_data = [
        ("T2", 38), ("T3", 52), ("T4", 45), ("T5", 63),
        ("T6", 57), ("T7", 71), ("CN", 49),
    ]

    bar_chart = ft.BarChart(
        bar_groups=[
            ft.BarChartGroup(x=i, bar_rods=[
                ft.BarChartRod(
                    from_y=0, to_y=val, width=26,
                    color=PRIMARY,
                    gradient=ft.LinearGradient(
                        begin=ft.alignment.bottom_center,
                        end=ft.alignment.top_center,
                        colors=[SECONDARY, PRIMARY],
                    ),
                    tooltip=f"{label}: {val} lượt",
                    border_radius=ft.BorderRadius(5, 5, 0, 0),
                )
            ])
            for i, (label, val) in enumerate(bar_data)
        ],
        left_axis=ft.ChartAxis(
            labels_size=32,
            title=ft.Text("Lượt nhận diện", size=9, color=TEXT_SUB),
        ),
        bottom_axis=ft.ChartAxis(labels=[
            ft.ChartAxisLabel(
                value=i,
                label=ft.Text(label, size=10, color=TEXT_SUB),
            )
            for i, (label, _) in enumerate(bar_data)
        ]),
        horizontal_grid_lines=ft.ChartGridLines(
            color=ft.Colors.with_opacity(0.08, ft.Colors.WHITE), width=1,
        ),
        tooltip_bgcolor=ft.Colors.with_opacity(0.85, BG_PANEL),
        max_y=90, expand=True,
        bgcolor=ft.Colors.TRANSPARENT,
        interactive=True,
    )

    chart_panel = panel(
        content=bar_chart,
        title="Hoạt Động Hệ Thống — 7 Ngày Gần Nhất",
        icon=ft.Icons.SHOW_CHART_ROUNDED,
        action_widget=ft.Container(
            content=ft.Text("2026", size=11, color=TEXT_SUB),
            bgcolor=ft.Colors.with_opacity(0.06, ft.Colors.WHITE),
            border_radius=8,
            border=ft.border.all(1, BORDER),
            padding=ft.padding.symmetric(horizontal=10, vertical=4),
        ),
        expand=True,
    )

    # ─── 3. Pie Chart: Phân bổ model ─────────────────────────────────────────
    pie_data = [
        ("YOLOv8",    35, PRIMARY),
        ("YOLOv9",    28, ACCENT),
        ("Custom",    22, SECONDARY),
        ("Thử nghiệm", 15, WARNING),
    ]

    pie_chart = ft.PieChart(
        sections=[
            ft.PieChartSection(
                value=pct,
                title=f"{pct}%",
                color=color,
                radius=52,
                title_style=ft.TextStyle(
                    size=9, color=ft.Colors.WHITE,
                    weight=ft.FontWeight.BOLD,
                ),
            )
            for label, pct, color in pie_data
        ],
        sections_space=3,
        center_space_radius=32,
        expand=True,
    )

    legend = ft.Column([
        ft.Row([
            ft.Container(width=10, height=10, bgcolor=color, border_radius=3),
            ft.Text(f"{label}  {pct}%", size=11, color=TEXT_SUB),
        ], spacing=6)
        for label, pct, color in pie_data
    ], spacing=5)

    pie_panel = panel(
        content=ft.Column([
            ft.Container(content=pie_chart, height=160),
            ft.Container(height=8),
            legend,
        ]),
        title="Phân Bổ Model",
        icon=ft.Icons.DONUT_LARGE_ROUNDED,
        width=260,
    )

    # ─── 4. Bảng KH mới nhất ────────────────────────────────────────────────
    def _kh_row(stt, name, phone, farms, status):
        status_color = PRIMARY if status == "Active" else TEXT_MUTED
        return ft.Container(
            content=ft.Row([
                ft.Text(str(stt), size=SIZE_CAPTION, color=TEXT_MUTED, width=32),
                ft.Container(
                    content=ft.Text(name[0].upper(), color=ft.Colors.WHITE,
                                    size=11, weight=ft.FontWeight.BOLD),
                    width=30, height=30, border_radius=15, bgcolor=SECONDARY,
                    alignment=ft.alignment.center,
                ),
                ft.Column([
                    ft.Text(name, size=SIZE_BODY, color=TEXT_MAIN,
                            weight=ft.FontWeight.W_500),
                    ft.Text(phone, size=10, color=TEXT_SUB),
                ], spacing=0, expand=True),
                ft.Text(f"{farms} farm", size=SIZE_CAPTION, color=TEXT_SUB, width=60),
                ft.Container(
                    content=ft.Text(status, size=9, color=ft.Colors.WHITE,
                                    weight=ft.FontWeight.BOLD),
                    bgcolor=status_color, border_radius=20,
                    padding=ft.padding.symmetric(horizontal=8, vertical=3),
                ),
            ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=ft.Colors.with_opacity(0.03, ft.Colors.WHITE),
            border_radius=8,
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
            border=ft.border.all(1, ft.Colors.with_opacity(0.05, ft.Colors.WHITE)),
        )

    kh_list = ft.Column([
        _kh_row(1, "Nguyễn Văn An",   "0901234567", 3, "Active"),
        ft.Container(height=4),
        _kh_row(2, "Trần Thị Bình",   "0912345678", 2, "Active"),
        ft.Container(height=4),
        _kh_row(3, "Lê Quang Minh",   "0923456789", 5, "Active"),
        ft.Container(height=4),
        _kh_row(4, "Phạm Hoàng Nam",  "0934567890", 1, "Inactive"),
        ft.Container(height=4),
        _kh_row(5, "Hoàng Thu Hương", "0945678901", 4, "Active"),
    ], spacing=0)

    customers_panel = panel(
        content=kh_list,
        title="Khách Hàng Mới Nhất",
        icon=ft.Icons.PEOPLE_ALT_ROUNDED,
        action_widget=ft.TextButton(
            "Xem tất cả →",
            style=ft.ButtonStyle(color=PRIMARY),
        ),
        expand=True,
    )

    # ─── 5. Alert feed ──────────────────────────────────────────────────────
    def _alert_item(icon, color, title, desc, time_str):
        return ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Icon(icon, color=ft.Colors.WHITE, size=14),
                    width=32, height=32, border_radius=16,
                    bgcolor=color, alignment=ft.alignment.center,
                ),
                ft.Column([
                    ft.Text(title, size=SIZE_BODY, color=TEXT_MAIN,
                            weight=ft.FontWeight.W_500),
                    ft.Text(desc, size=10, color=TEXT_SUB),
                ], spacing=1, expand=True),
                ft.Text(time_str, size=10, color=TEXT_MUTED),
            ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=ft.Colors.with_opacity(0.03, ft.Colors.WHITE),
            border_radius=8,
            padding=ft.padding.symmetric(horizontal=10, vertical=8),
            border=ft.border.all(1, ft.Colors.with_opacity(0.05, ft.Colors.WHITE)),
        )

    alerts_list = ft.Column([
        _alert_item(ft.Icons.PETS,         DANGER,  "Bò #B042 bất thường",  "CAM-01 · Chuồng A2", "05:12"),
        ft.Container(height=4),
        _alert_item(ft.Icons.NO_MEALS_ROUNDED, WARNING, "Bò #B017 bỏ ăn",  "CAM-02 · Chuồng B1", "04:38"),
        ft.Container(height=4),
        _alert_item(ft.Icons.VIDEOCAM_OFF, DANGER,  "Camera CAM-03 mất kết nối", "Trang trại Minh",  "03:55"),
        ft.Container(height=4),
        _alert_item(ft.Icons.WARNING_AMBER_ROUNDED, WARNING, "Bò #B055 ra ngoài khu vực", "CAM-04 · Bãi thả", "03:15"),
        ft.Container(height=4),
        _alert_item(ft.Icons.CHECK_CIRCLE_ROUNDED,  PRIMARY, "Model YOLOv9 deploy thành công", "Admin · v9.1", "02:00"),
    ], spacing=0)

    alert_panel = panel(
        content=alerts_list,
        title="Cảnh Báo Gần Đây",
        icon=ft.Icons.NOTIFICATIONS_ROUNDED,
        action_widget=ft.Container(
            content=ft.Text("3 chưa đọc", size=10,
                            color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
            bgcolor=DANGER, border_radius=12,
            padding=ft.padding.symmetric(horizontal=8, vertical=3),
        ),
        width=320,
    )

    # ─── LAYOUT ─────────────────────────────────────────────────────────────
    return ft.Container(
        content=ft.Column([
            # Greeting row
            ft.Row([
                ft.Column([
                    ft.Text(
                        f"{_hour_greeting()}, Admin 👋",
                        size=SIZE_H1,
                        weight=ft.FontWeight.BOLD,
                        color=TEXT_MAIN,
                    ),
                    ft.Text(
                        f"Hôm nay: {today}  •  Tổng quan hệ thống Con Bò Cười",
                        size=SIZE_CAPTION,
                        color=TEXT_SUB,
                    ),
                ], spacing=2),
                ft.Container(expand=True),
                primary_button(
                    "Làm mới",
                    icon=ft.Icons.REFRESH_ROUNDED,
                ),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),

            ft.Container(height=16),

            # KPI row
            kpi_row,

            ft.Container(height=16),

            # Charts row
            ft.Row([
                chart_panel,
                ft.Container(width=12),
                pie_panel,
            ], expand=True, vertical_alignment=ft.CrossAxisAlignment.START),

            ft.Container(height=16),

            # Bottom row
            ft.Row([
                customers_panel,
                ft.Container(width=12),
                alert_panel,
            ], expand=True, vertical_alignment=ft.CrossAxisAlignment.START),

            ft.Container(height=16),
        ], expand=True, scroll=ft.ScrollMode.AUTO, spacing=0),
        expand=True,
    )