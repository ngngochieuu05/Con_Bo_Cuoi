import flet as ft
from ui.theme import glass_container, button_style, PRIMARY

_ACTIVITY_EVENTS = [
    {"icon": ft.Icons.MARK_EMAIL_UNREAD, "color": ft.Colors.AMBER_400,
     "text": "Case-2026-004 mới từ Trần Văn A", "time": "09:40"},
    {"icon": ft.Icons.WARNING_AMBER, "color": ft.Colors.RED_400,
     "text": "Cảnh báo: bò #12 bất thường", "time": "09:20"},
    {"icon": ft.Icons.CHECK_CIRCLE_OUTLINE, "color": ft.Colors.GREEN_400,
     "text": "Tư vấn Case-2026-002 hoàn tất", "time": "08:55"},
    {"icon": ft.Icons.BIOTECH, "color": ft.Colors.TEAL_300,
     "text": "Kết quả AI: bò #07 nghi lở mồm", "time": "08:30"},
    {"icon": ft.Icons.FACT_CHECK, "color": ft.Colors.BLUE_300,
     "text": "Kiểm duyệt ảnh dataset #0018 xong", "time": "08:10"},
]


def _stat_chip(value: str, label: str, color) -> ft.Control:
    return ft.Container(
        expand=1,
        padding=ft.padding.symmetric(horizontal=6, vertical=6),
        border_radius=10,
        bgcolor=ft.Colors.with_opacity(0.12, color),
        content=ft.Column(
            tight=True, spacing=1,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Text(value, size=14, weight=ft.FontWeight.W_700, color=color),
                ft.Text(label, size=9, color=ft.Colors.WHITE54),
            ],
        ),
    )


def _sla_stats_card() -> ft.Control:
    try:
        from bll.user.expert.kiem_duyet import get_review_summary
        s = get_review_summary()
    except Exception:
        s = {"total": 0, "pending": 0, "approved": 0, "rejected": 0}

    total    = s["total"]
    approved = s["approved"]
    pending  = s["pending"]
    rejected = s["rejected"]
    sla_pct  = approved / max(total, 1) * 100
    color    = (ft.Colors.GREEN_400 if sla_pct >= 90
                else ft.Colors.AMBER_400 if sla_pct >= 75
                else ft.Colors.RED_400)

    return glass_container(
        padding=16, radius=20,
        content=ft.Column(tight=True, spacing=10, controls=[
            ft.Text("Thống kê SLA kiểm duyệt", size=14, weight=ft.FontWeight.W_700),
            ft.ProgressBar(value=sla_pct / 100, color=color, bgcolor=ft.Colors.WHITE12),
            ft.Text(f"{sla_pct:.1f}% đúng hạn", size=13, color=color,
                    weight=ft.FontWeight.W_600),
            ft.Row(spacing=6, controls=[
                _stat_chip(str(total),    "Tổng",      ft.Colors.BLUE_300),
                _stat_chip(str(pending),  "Chờ",       ft.Colors.AMBER_400),
                _stat_chip(str(approved), "Duyệt",     ft.Colors.GREEN_400),
                _stat_chip(str(rejected), "Từ chối",   ft.Colors.RED_400),
            ]),
        ]),
    )


def _activity_feed_card() -> ft.Control:
    items = [
        ft.Container(
            padding=ft.padding.symmetric(horizontal=4, vertical=6),
            border=ft.border.only(
                bottom=ft.BorderSide(1, ft.Colors.with_opacity(0.07, ft.Colors.WHITE))
            ),
            content=ft.Row(spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                ft.Icon(ev["icon"], size=16, color=ev["color"]),
                ft.Text(ev["text"], size=12, color=ft.Colors.WHITE70, expand=True,
                        max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                ft.Text(ev["time"], size=10, color=ft.Colors.WHITE38),
            ]),
        )
        for ev in _ACTIVITY_EVENTS
    ]
    return glass_container(
        padding=16, radius=20,
        content=ft.Column(tight=True, spacing=8, controls=[
            ft.Text("Hoạt động gần đây", size=14, weight=ft.FontWeight.W_700),
            ft.ListView(height=180, spacing=0, controls=items),
        ]),
    )


def _export_card(page) -> ft.Control:
    state: dict = {}
    format_dd = ft.Dropdown(
        label="Định dạng",
        value="CSV",
        border_radius=10,
        bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
        border_color=ft.Colors.with_opacity(0.28, ft.Colors.WHITE),
        focused_border_color=PRIMARY,
        label_style=ft.TextStyle(color=ft.Colors.WHITE70, size=12),
        options=[ft.dropdown.Option("CSV", "CSV"), ft.dropdown.Option("PDF", "PDF")],
    )
    from_field = ft.TextField(
        label="Từ ngày", hint_text="dd/mm/yyyy", expand=True,
        keyboard_type=ft.KeyboardType.DATETIME, border_radius=10,
        bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
        border_color=ft.Colors.with_opacity(0.28, ft.Colors.WHITE),
        focused_border_color=PRIMARY,
        label_style=ft.TextStyle(color=ft.Colors.WHITE70, size=12),
        text_style=ft.TextStyle(color=ft.Colors.WHITE, size=13),
        cursor_color=ft.Colors.WHITE,
        content_padding=ft.padding.symmetric(horizontal=10, vertical=8),
    )
    to_field = ft.TextField(
        label="Đến ngày", hint_text="dd/mm/yyyy", expand=True,
        keyboard_type=ft.KeyboardType.DATETIME, border_radius=10,
        bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
        border_color=ft.Colors.with_opacity(0.28, ft.Colors.WHITE),
        focused_border_color=PRIMARY,
        label_style=ft.TextStyle(color=ft.Colors.WHITE70, size=12),
        text_style=ft.TextStyle(color=ft.Colors.WHITE, size=13),
        cursor_color=ft.Colors.WHITE,
        content_padding=ft.padding.symmetric(horizontal=10, vertical=8),
    )

    def _on_save(ev: ft.FilePickerResultEvent):
        if not ev.path or not page:
            return
        try:
            from bll.user.expert.kiem_duyet import get_review_summary
            s = get_review_summary()
        except Exception:
            s = {"total": 0, "pending": 0, "approved": 0, "rejected": 0}
        lines = [
            "Chỉ số,Giá trị",
            f"Tổng ảnh dataset,{s['total']}",
            f"Chờ kiểm duyệt,{s['pending']}",
            f"Đã duyệt,{s['approved']}",
            f"Từ chối,{s['rejected']}",
            f"SLA %,{s['approved'] / max(s['total'], 1) * 100:.1f}",
        ]
        try:
            with open(ev.path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            page.show_snack_bar(ft.SnackBar(ft.Text(f"Đã xuất báo cáo: {ev.path}")))
        except Exception as ex:
            page.show_snack_bar(ft.SnackBar(ft.Text(f"Lỗi xuất file: {ex}")))
        page.update()

    def _export(e):
        if not page:
            return
        if "picker" not in state:
            state["picker"] = ft.FilePicker(on_result=_on_save)
            page.overlay.append(state["picker"])
            page.update()
        state["picker"].save_file(
            file_name="bao_cao_chuyen_gia.csv",
            allowed_extensions=["csv"],
        )

    return glass_container(
        padding=16, radius=20,
        content=ft.Column(tight=True, spacing=10, controls=[
            ft.Text("Xuất báo cáo", size=14, weight=ft.FontWeight.W_700),
            format_dd,
            ft.Row(spacing=8, controls=[from_field, to_field]),
            ft.ElevatedButton(
                "Tạo báo cáo", icon=ft.Icons.DOWNLOAD,
                style=button_style("primary"), expand=True,
                on_click=_export,
            ),
        ]),
    )


def build_expert_utilities(page: ft.Page = None):
    return ft.Column(
        expand=True, spacing=14, scroll=ft.ScrollMode.AUTO,
        controls=[
            ft.Text("Tiện ích", size=26, weight=ft.FontWeight.W_700),
            _sla_stats_card(),
            _activity_feed_card(),
            _export_card(page),
        ],
    )
