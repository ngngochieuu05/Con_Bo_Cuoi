"""
Thống Kê User — Dark Theme với Export Popup
Con Bò Cười Design System
"""
import flet as ft
from datetime import datetime
import os

from src.ui.theme import (
    BG_MAIN, BG_PANEL, PRIMARY, SECONDARY, ACCENT,
    TEXT_MAIN, TEXT_SUB, TEXT_MUTED,
    WARNING, DANGER, SUCCESS, BORDER,
    GRAD_TEAL, GRAD_CYAN, GRAD_WARN, GRAD_DANGER,
    RADIUS_CARD, RADIUS_BTN,
    SIZE_H1, SIZE_H2, SIZE_H3, SIZE_BODY, SIZE_CAPTION,
    SHADOW_CARD_GLOW,
    kpi_card, panel, primary_button,
)


class ThongKePage(ft.Column):
    def __init__(self):
        super().__init__(expand=True, scroll=ft.ScrollMode.AUTO, spacing=0)
        self._page_ref = None   # set bởi main_user sau khi được thêm vào page
        self._build()

    # ─── Export dialog ───────────────────────────────────────────────────────
    def _open_export_dialog(self, e):
        """Popup chọn định dạng xuất dữ liệu."""
        page = e.page if hasattr(e, "page") else None

        # ── State refs ──
        fmt_selected = ft.Ref[str]()
        fmt_selected.current = "excel"

        chart_type      = ft.Ref[str]()
        chart_type.current = "bar"

        report_title = ft.TextField(
            label="Tên báo cáo",
            value=f"Báo cáo thống kê trang trại — {datetime.now().strftime('%d/%m/%Y')}",
            border_radius=8,
            border_color=BORDER,
            focused_border_color=PRIMARY,
            text_style=ft.TextStyle(color=TEXT_MAIN, size=SIZE_BODY),
            bgcolor=ft.Colors.with_opacity(0.06, ft.Colors.WHITE),
            content_padding=ft.padding.symmetric(horizontal=12, vertical=10),
        )
        date_from = ft.TextField(
            label="Từ ngày",
            value="01/03/2026",
            border_radius=8,
            border_color=BORDER,
            focused_border_color=PRIMARY,
            text_style=ft.TextStyle(color=TEXT_MAIN, size=SIZE_BODY),
            bgcolor=ft.Colors.with_opacity(0.06, ft.Colors.WHITE),
            content_padding=ft.padding.symmetric(horizontal=12, vertical=10),
            width=160,
        )
        date_to = ft.TextField(
            label="Đến ngày",
            value=datetime.now().strftime("%d/%m/%Y"),
            border_radius=8,
            border_color=BORDER,
            focused_border_color=PRIMARY,
            text_style=ft.TextStyle(color=TEXT_MAIN, size=SIZE_BODY),
            bgcolor=ft.Colors.with_opacity(0.06, ft.Colors.WHITE),
            content_padding=ft.padding.symmetric(horizontal=12, vertical=10),
            width=160,
        )

        data_choices = {
            "Số bò nhận diện theo ngày": True,
            "Số cảnh báo theo camera":   True,
            "Phân loại cảnh báo":        False,
            "Thống kê theo tuần":        False,
        }
        data_cbs = {
            k: ft.Checkbox(
                label=k, value=v,
                check_color=ft.Colors.WHITE,
                active_color=PRIMARY,
                label_style=ft.TextStyle(color=TEXT_MAIN, size=SIZE_BODY),
            )
            for k, v in data_choices.items()
        }

        # ── Format radio group ──
        fmt_status_text = ft.Text("", size=10, color=TEXT_SUB)

        def _make_fmt_btn(label, icon, fmt_key, desc):
            def _click(e):
                fmt_selected.current = fmt_key
                fmt_status_text.value = f"Xuất dưới dạng: {label}"
                # Show/hide chart selector
                chart_section.visible = fmt_key == "chart"
                try:
                    chart_section.update()
                    fmt_status_text.update()
                except Exception:
                    pass
                # Highlight selected
                for k, c in fmt_btns.items():
                    c.bgcolor = ft.Colors.with_opacity(0.15, PRIMARY) if k == fmt_key \
                        else ft.Colors.with_opacity(0.04, ft.Colors.WHITE)
                    c.border = ft.border.all(
                        2 if k == fmt_key else 1,
                        PRIMARY if k == fmt_key else BORDER
                    )
                    try:
                        c.update()
                    except Exception:
                        pass

            return ft.Container(
                content=ft.Column([
                    ft.Icon(icon, size=28, color=PRIMARY),
                    ft.Text(label, size=SIZE_BODY, color=TEXT_MAIN,
                            weight=ft.FontWeight.W_600),
                    ft.Text(desc, size=9, color=TEXT_SUB, text_align=ft.TextAlign.CENTER),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
                bgcolor=ft.Colors.with_opacity(0.04, ft.Colors.WHITE),
                border_radius=10,
                border=ft.border.all(1, BORDER),
                padding=ft.padding.all(14),
                ink=True, on_click=_click,
                width=110,
                alignment=ft.alignment.center,
            )

        fmt_btns = {}
        fmt_configs = [
            ("Excel",       ft.Icons.TABLE_VIEW_ROUNDED,        "excel", "Bảng tính\n.xlsx"),
            ("Biểu đồ",     ft.Icons.INSERT_CHART_ROUNDED,        "chart", "PNG/SVG\ncột / tròn"),
            ("Word",        ft.Icons.DESCRIPTION_ROUNDED,         "word",  "Văn bản\n.docx"),
            ("Văn bản",     ft.Icons.TEXT_SNIPPET_ROUNDED,        "txt",   "Thuần văn\nbản .txt"),
        ]
        for label, icon, key, desc in fmt_configs:
            btn = _make_fmt_btn(label, icon, key, desc)
            fmt_btns[key] = btn

        # Highlight excel (mặc định)
        fmt_btns["excel"].bgcolor = ft.Colors.with_opacity(0.15, PRIMARY)
        fmt_btns["excel"].border  = ft.border.all(2, PRIMARY)

        fmt_row = ft.Row(list(fmt_btns.values()), spacing=10)

        # ── Chart sub-options (chỉ hiện khi chọn Biểu đồ) ──
        def _chart_click(e, ct):
            chart_type.current = ct
            bar_btn.bgcolor  = ft.Colors.with_opacity(0.15, PRIMARY) if ct == "bar"  else None
            pie_btn.bgcolor  = ft.Colors.with_opacity(0.15, PRIMARY) if ct == "pie"  else None
            bar_btn.border   = ft.border.all(1, PRIMARY if ct == "bar"  else BORDER)
            pie_btn.border   = ft.border.all(1, PRIMARY if ct == "pie"  else BORDER)
            try:
                bar_btn.update()
                pie_btn.update()
            except Exception:
                pass

        bar_btn = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.BAR_CHART_ROUNDED, color=PRIMARY, size=16),
                ft.Text("Biểu đồ Cột", size=SIZE_BODY, color=TEXT_MAIN),
            ], spacing=8),
            bgcolor=ft.Colors.with_opacity(0.15, PRIMARY),
            border=ft.border.all(1, PRIMARY),
            border_radius=8,
            padding=ft.padding.symmetric(horizontal=14, vertical=8),
            ink=True,
            on_click=lambda e: _chart_click(e, "bar"),
        )
        pie_btn = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.DONUT_LARGE_ROUNDED, color=SECONDARY, size=16),
                ft.Text("Biểu đồ Tròn", size=SIZE_BODY, color=TEXT_MAIN),
            ], spacing=8),
            bgcolor=None,
            border=ft.border.all(1, BORDER),
            border_radius=8,
            padding=ft.padding.symmetric(horizontal=14, vertical=8),
            ink=True,
            on_click=lambda e: _chart_click(e, "pie"),
        )

        chart_section = ft.Container(
            visible=False,
            content=ft.Column([
                ft.Text("Loại biểu đồ:", size=10, color=TEXT_SUB,
                        weight=ft.FontWeight.BOLD),
                ft.Container(height=6),
                ft.Row([bar_btn, pie_btn], spacing=10),
            ], spacing=0),
            bgcolor=ft.Colors.with_opacity(0.05, PRIMARY),
            border_radius=10,
            padding=ft.padding.all(12),
            border=ft.border.all(1, ft.Colors.with_opacity(0.2, PRIMARY)),
        )

        # ── Export result ──
        export_result = ft.Text("", size=SIZE_CAPTION, color=SUCCESS)

        def _do_export(e):
            fmt = fmt_selected.current
            title = report_title.value or "Báo cáo"
            df   = date_from.value
            dt   = date_to.value
            selected_data = [k for k, cb in data_cbs.items() if cb.value]
            chart = chart_type.current

            if not selected_data:
                export_result.value = "⚠️ Vui lòng chọn ít nhất 1 loại dữ liệu"
                export_result.color = WARNING
                try:
                    export_result.update()
                except Exception:
                    pass
                return

            # Demo export logic
            fmt_labels = {"excel": "Excel (.xlsx)", "chart": f"Biểu đồ {chart}",
                          "word": "Word (.docx)", "txt": "Văn bản (.txt)"}
            export_result.value = (
                f"✅ Xuất thành công!\n"
                f"📄 {fmt_labels.get(fmt, fmt)} — «{title}»\n"
                f"📅 {df} → {dt} · {len(selected_data)} loại dữ liệu\n"
                f"💾 Đã lưu vào thư mục Downloads"
            )
            export_result.color = SUCCESS
            try:
                export_result.update()
            except Exception:
                pass

        def _close(e):
            if page:
                for d in page.overlay:
                    if isinstance(d, ft.AlertDialog):
                        d.open = False
                try:
                    page.update()
                except Exception:
                    pass

        dialog = ft.AlertDialog(
            modal=True,
            bgcolor=BG_PANEL,
            title=ft.Row([
                ft.Icon(ft.Icons.DOWNLOAD_ROUNDED, color=PRIMARY, size=22),
                ft.Text("Xuất Dữ Liệu", size=SIZE_H2,
                        color=TEXT_MAIN, weight=ft.FontWeight.BOLD),
            ], spacing=10),
            content=ft.Container(
                width=580,
                content=ft.Column([
                    # Tên báo cáo
                    ft.Text("Tên báo cáo & khoảng thời gian",
                            size=10, color=TEXT_SUB, weight=ft.FontWeight.BOLD),
                    ft.Container(height=6),
                    report_title,
                    ft.Container(height=8),
                    ft.Row([date_from, ft.Container(width=10), date_to], spacing=0),

                    ft.Container(height=14),
                    ft.Divider(color=BORDER, height=1),
                    ft.Container(height=10),

                    # Chọn dữ liệu
                    ft.Text("Dữ liệu muốn xuất",
                            size=10, color=TEXT_SUB, weight=ft.FontWeight.BOLD),
                    ft.Container(height=6),
                    ft.Row(list(data_cbs.values())[:2], spacing=20),
                    ft.Container(height=4),
                    ft.Row(list(data_cbs.values())[2:], spacing=20),

                    ft.Container(height=14),
                    ft.Divider(color=BORDER, height=1),
                    ft.Container(height=10),

                    # Định dạng
                    ft.Text("Định dạng xuất",
                            size=10, color=TEXT_SUB, weight=ft.FontWeight.BOLD),
                    ft.Container(height=8),
                    fmt_row,
                    ft.Container(height=8),
                    chart_section,

                    ft.Container(height=10),
                    export_result,
                ], spacing=0, scroll=ft.ScrollMode.AUTO),
                padding=ft.padding.symmetric(horizontal=2, vertical=4),
            ),
            actions=[
                ft.TextButton(
                    "Huỷ", on_click=_close,
                    style=ft.ButtonStyle(color=TEXT_SUB),
                ),
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.DOWNLOAD_ROUNDED, color=ft.Colors.WHITE, size=16),
                        ft.Text("Xuất ngay", color=ft.Colors.WHITE,
                                size=SIZE_BODY, weight=ft.FontWeight.W_600),
                    ], spacing=6),
                    bgcolor=PRIMARY, border_radius=RADIUS_BTN,
                    padding=ft.padding.symmetric(horizontal=16, vertical=8),
                    ink=True, on_click=_do_export,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        if page:
            page.overlay.append(dialog)
            dialog.open = True
            try:
                page.update()
            except Exception:
                pass

    # ─── Main build ──────────────────────────────────────────────────────────
    def _build(self):
        # KPI row
        kpi_row = ft.Row([
            kpi_card(ft.Icons.PETS_ROUNDED,
                     "Trung Bình Bò/Ngày", "84",
                     "7 ngày gần đây",
                     grad_colors=GRAD_TEAL),
            kpi_card(ft.Icons.WARNING_AMBER_ROUNDED,
                     "Cảnh Báo Tuần Này", "12",
                     "Giảm 20% so với tuần trước",
                     grad_colors=GRAD_WARN),
            kpi_card(ft.Icons.VIDEOCAM_ROUNDED,
                     "Thời Gian Online", "98.6%",
                     "Camera uptime tuần này",
                     grad_colors=GRAD_CYAN),
            kpi_card(ft.Icons.CHECK_CIRCLE_ROUNDED,
                     "Nhận Diện Thành Công", "97.1%",
                     "Accuracy tuần này",
                     grad_colors=["#00C897", "#009E7A"]),
        ], spacing=14)

        # Bar chart
        week_data = [
            ("T2", 82), ("T3", 85), ("T4", 80), ("T5", 88),
            ("T6", 84), ("T7", 90), ("CN", 87),
        ]
        bar_chart = ft.BarChart(
            bar_groups=[
                ft.BarChartGroup(x=i, bar_rods=[
                    ft.BarChartRod(
                        from_y=0, to_y=val, width=26,
                        gradient=ft.LinearGradient(
                            begin=ft.alignment.bottom_center,
                            end=ft.alignment.top_center,
                            colors=[SECONDARY, PRIMARY],
                        ),
                        tooltip=f"{label}: {val} bò",
                        border_radius=ft.BorderRadius(5, 5, 0, 0),
                    )
                ])
                for i, (label, val) in enumerate(week_data)
            ],
            left_axis=ft.ChartAxis(labels_size=32),
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
            max_y=100, expand=True, bgcolor=ft.Colors.TRANSPARENT, interactive=True,
        )

        range_dd = ft.Dropdown(
            options=[
                ft.dropdown.Option("7 ngày"),
                ft.dropdown.Option("30 ngày"),
                ft.dropdown.Option("3 tháng"),
            ],
            value="7 ngày",
            bgcolor=BG_PANEL, border_color=BORDER,
            focused_border_color=PRIMARY,
            text_style=ft.TextStyle(color=TEXT_MAIN, size=11),
            width=120,
        )

        # Export button — cần lấy page từ event
        export_btn = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.DOWNLOAD_ROUNDED, color=ft.Colors.WHITE, size=14),
                ft.Text("Xuất Dữ Liệu", color=ft.Colors.WHITE,
                        size=SIZE_CAPTION, weight=ft.FontWeight.W_600),
            ], spacing=6),
            bgcolor=PRIMARY, border_radius=8,
            padding=ft.padding.symmetric(horizontal=12, vertical=7),
            ink=True, on_click=self._open_export_dialog,
        )

        chart_panel = panel(
            content=bar_chart,
            title="Số Bò Nhận Diện Theo Ngày — 7 Ngày",
            icon=ft.Icons.SHOW_CHART_ROUNDED,
            action_widget=ft.Row([range_dd, ft.Container(width=8), export_btn], spacing=0),
            expand=True,
        )

        # Alert by camera
        cam_alerts = [
            ("CAM-01 · Chuồng A", 8,  PRIMARY),
            ("CAM-02 · Chuồng B", 3,  SECONDARY),
            ("CAM-03 · Chuồng C", 1,  ACCENT),
            ("CAM-04 · Bãi Thả",  13, DANGER),
        ]
        max_c = max(a[1] for a in cam_alerts)

        def _cam_bar(name, count, color):
            return ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text(name, size=SIZE_BODY, color=TEXT_MAIN, expand=True),
                        ft.Text(str(count), size=SIZE_BODY, color=color,
                                weight=ft.FontWeight.BOLD, width=30),
                    ]),
                    ft.ProgressBar(
                        value=count / max_c,
                        color=color,
                        bgcolor=ft.Colors.with_opacity(0.1, color),
                        height=4,
                        border_radius=2,
                    ),
                ], spacing=5),
                padding=ft.padding.symmetric(vertical=6),
            )

        cam_panel = panel(
            content=ft.Column([_cam_bar(n, c, col) for n, c, col in cam_alerts], spacing=2),
            title="Cảnh Báo Theo Camera",
            icon=ft.Icons.VIDEOCAM_ROUNDED,
            width=310,
        )

        # History table
        def _hist_row(time_str, camera, msg, severity):
            sev_color = DANGER if severity == "Cao" else WARNING if severity == "TB" else PRIMARY
            return ft.Container(
                content=ft.Row([
                    ft.Text(time_str, size=10, color=TEXT_MUTED, width=120),
                    ft.Text(camera, size=SIZE_BODY, color=TEXT_MAIN, expand=True),
                    ft.Text(msg, size=SIZE_BODY, color=TEXT_SUB, expand=True),
                    ft.Container(
                        content=ft.Text(severity, size=9, color=ft.Colors.WHITE,
                                        weight=ft.FontWeight.BOLD),
                        bgcolor=sev_color, border_radius=6,
                        padding=ft.padding.symmetric(horizontal=8, vertical=3),
                        width=55,
                    ),
                ], spacing=10),
                bgcolor=ft.Colors.with_opacity(0.02, ft.Colors.WHITE),
                border_radius=6,
                padding=ft.padding.symmetric(horizontal=12, vertical=8),
                border=ft.border.all(1, ft.Colors.with_opacity(0.04, ft.Colors.WHITE)),
            )

        hist_data = [
            ("12/03 05:12", "CAM-01", "Bò #B042 bất thường", "Cao"),
            ("12/03 04:38", "CAM-02", "Bò #B017 bỏ ăn",     "TB"),
            ("12/03 03:15", "CAM-04", "Bò ra ngoài khu vực", "Cao"),
            ("11/03 22:40", "CAM-03", "Camera mất kết nối",  "Cao"),
            ("11/03 18:05", "CAM-01", "Bò #B031 bất động",   "TB"),
        ]
        history_rows = ft.Column(
            [r for d in hist_data
             for r in [_hist_row(*d), ft.Divider(color=BORDER, height=1)]],
            spacing=0,
        )

        history_panel = panel(
            content=history_rows,
            title="Lịch Sử Cảnh Báo",
            icon=ft.Icons.HISTORY_ROUNDED,
            action_widget=ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.DOWNLOAD_ROUNDED, size=14, color=PRIMARY),
                    ft.Text("Xuất", size=SIZE_CAPTION, color=PRIMARY),
                ], spacing=4),
                ink=True, border_radius=8,
                border=ft.border.all(1, PRIMARY),
                padding=ft.padding.symmetric(horizontal=10, vertical=4),
                on_click=self._open_export_dialog,
            ),
            expand=True,
        )

        self.controls = [
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Column([
                            ft.Text("Thống Kê Trang Trại",
                                    size=SIZE_H1, weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
                            ft.Text("Phân tích chi tiết nhận diện và cảnh báo",
                                    size=SIZE_CAPTION, color=TEXT_SUB),
                        ], spacing=2),
                        ft.Container(expand=True),
                        ft.Container(
                            content=ft.Row([
                                ft.Icon(ft.Icons.DOWNLOAD_ROUNDED, color=ft.Colors.WHITE, size=16),
                                ft.Text("Xuất Báo Cáo", color=ft.Colors.WHITE,
                                        size=SIZE_BODY, weight=ft.FontWeight.W_600),
                            ], spacing=8),
                            bgcolor=PRIMARY, border_radius=RADIUS_BTN,
                            padding=ft.padding.symmetric(horizontal=16, vertical=10),
                            ink=True, on_click=self._open_export_dialog,
                        ),
                    ]),
                    ft.Container(height=16),
                    kpi_row,
                    ft.Container(height=16),
                    ft.Row([
                        chart_panel,
                        ft.Container(width=12),
                        cam_panel,
                    ], vertical_alignment=ft.CrossAxisAlignment.START, expand=True),
                    ft.Container(height=16),
                    history_panel,
                    ft.Container(height=20),
                ], spacing=0),
                padding=ft.padding.symmetric(horizontal=4, vertical=4),
            )
        ]
