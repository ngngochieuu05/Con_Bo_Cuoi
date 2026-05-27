import flet as ft

from bll.services.monitor_service import get_monitor_sessions_by_user
from ui.theme import fmt_dt, glass_container, status_badge


_STATUS_KIND = {
    "running": ("Đang chạy", "warning"),
    "completed": ("Hoàn tất", "primary"),
    "stopped": ("Đã dừng", "secondary"),
    "failed": ("Lỗi", "danger"),
}


def _session_card(item: dict) -> ft.Control:
    status_label, kind = _STATUS_KIND.get(item.get("status", ""), ("Không rõ", "warning"))
    source_type = item.get("source_type", "camera")
    source_label = item.get("source_label") or item.get("camera_label") or "Nguồn không rõ"
    source_text = "Camera trực tiếp" if source_type == "camera" else source_label

    return ft.Container(
        expand=True,
        padding=ft.padding.symmetric(horizontal=12, vertical=12),
        border_radius=16,
        bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
        border=ft.border.all(1, ft.Colors.with_opacity(0.10, ft.Colors.WHITE)),
        content=ft.Column(
            spacing=8,
            tight=True,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Text(
                            f"Phiên #{item.get('id_session', '--')}",
                            size=13,
                            weight=ft.FontWeight.W_700,
                            expand=True,
                            max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                        status_badge(status_label, kind),
                    ],
                ),
                ft.Text(
                    item.get("camera_label", "Chưa xác định camera"),
                    size=12,
                    color=ft.Colors.WHITE70,
                    max_lines=2,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
                ft.Text(
                    f"Nguồn: {source_text}",
                    size=11,
                    color=ft.Colors.WHITE60,
                    max_lines=2,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
                ft.Column(
                    spacing=4,
                    tight=True,
                    controls=[
                        ft.Text(f"Bắt đầu: {fmt_dt(item.get('started_at', ''))}", size=10, color=ft.Colors.WHITE54),
                        ft.Text(
                            f"Kết thúc: {fmt_dt(item.get('stopped_at', '')) if item.get('stopped_at') else '--'}",
                            size=10,
                            color=ft.Colors.WHITE54,
                        ),
                        ft.Text(f"Số frame đã xử lý: {item.get('frame_count', 0)}", size=10, color=ft.Colors.WHITE54),
                    ],
                ),
            ],
        ),
    )


def build_session_history(page: ft.Page | None = None):
    user_id = int((page.client_storage.get("user_id") or 0) if page else 0)
    sessions = get_monitor_sessions_by_user(user_id) if user_id else []

    cards = [ft.Container(expand=True, content=_session_card(item)) for item in sessions]
    if not cards:
        cards = [ft.Text("Chưa có phiên giám sát nào được lưu.", size=12, color=ft.Colors.WHITE70)]

    return ft.Column(
        expand=True,
        spacing=14,
        scroll=ft.ScrollMode.AUTO,
        controls=[
            ft.Text("Lịch sử phiên giám sát", size=22, weight=ft.FontWeight.W_700),
            glass_container(
                padding=14,
                radius=18,
                content=ft.Column(
                    spacing=10,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=cards,
                ),
            ),
        ],
    )
