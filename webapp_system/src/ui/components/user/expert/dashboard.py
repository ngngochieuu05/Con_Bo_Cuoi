import flet as ft

from bll.services.system_overview_service import get_system_overview
from ui.theme import glass_container, metric_card, status_badge


def _metric_grid(items: list[ft.Control]) -> ft.Column:
    rows: list[ft.Control] = []
    for i in range(0, len(items), 2):
        pair = items[i:i + 2]
        rows.append(
            ft.Row(
                spacing=10,
                controls=[
                    ft.Container(expand=1, content=pair[0]),
                    ft.Container(expand=1, content=pair[1]) if len(pair) > 1 else ft.Container(expand=1),
                ],
            )
        )
    return ft.Column(spacing=10, controls=rows)


def build_expert_dashboard(page: ft.Page | None = None):
    expert_id = int((page.client_storage.get("user_id") or 0) if page else 0)
    overview = get_system_overview(user_id=expert_id, role="expert")

    metric_wrap = _metric_grid([
        metric_card("Hội thoại", str(overview.get("own_conversations_total", 0)), ft.Icons.MARK_EMAIL_UNREAD),
        metric_card("Chưa đọc", str(overview.get("own_conversations_unread", 0)), ft.Icons.NOTIFICATIONS),
        metric_card("Cảnh báo hệ thống", str(overview.get("alerts_open", 0)), ft.Icons.WARNING_AMBER),
        metric_card("Model online", f"{overview.get('models_online', 0)}/{overview.get('models_total', 0)}", ft.Icons.SMART_TOY),
    ])

    system_rows = [
        ft.Text(f"Máy chủ: {overview.get('server_url', '--')}", size=12, color=ft.Colors.WHITE70),
        ft.Text(f"Chế độ app: {overview.get('app_mode', '--')} | Port: {overview.get('app_port', '--')}", size=12, color=ft.Colors.WHITE70),
        ft.Text(f"Camera toàn hệ thống: {overview.get('cameras_online', 0)}/{overview.get('cameras_total', 0)} online", size=12, color=ft.Colors.WHITE70),
        ft.Text(f"Nhật ký hôm nay: {overview.get('activity_today', 0)} | Người dùng: {overview.get('users_total', 0)}", size=12, color=ft.Colors.WHITE70),
    ]

    convos = []
    from bll.services import chat_service

    for convo in chat_service.list_conversations_for_expert(expert_id)[:6]:
        last = convo.get("messages", [])[-1] if convo.get("messages") else {}
        preview = last.get("text") or ("[Ảnh]" if (last.get("img_src") or last.get("img_b64")) else "Chưa có tin nhắn")
        convos.append(
            ft.Container(
                padding=ft.padding.symmetric(horizontal=12, vertical=10),
                border_radius=14,
                bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
                border=ft.border.all(1, ft.Colors.with_opacity(0.10, ft.Colors.WHITE)),
                content=ft.Row(
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                    controls=[
                        ft.Column(
                            expand=True,
                            spacing=3,
                            tight=True,
                            controls=[
                                ft.Text(convo.get("farmer_name", "Nông dân"), size=12, weight=ft.FontWeight.W_600),
                                ft.Text(preview, size=11, color=ft.Colors.WHITE70, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                            ],
                        ),
                        status_badge(str(convo.get("unread_expert", 0) or 0), "warning" if convo.get("unread_expert", 0) else "primary"),
                    ],
                ),
            )
        )

    if not convos:
        convos.append(ft.Text("Chưa có hội thoại thực tế từ nông dân.", size=12, color=ft.Colors.WHITE70))

    return ft.Column(
        expand=True,
        spacing=14,
        scroll=ft.ScrollMode.AUTO,
        controls=[
            ft.Text("Bảng điều khiển chuyên gia", size=22, weight=ft.FontWeight.W_700),
            metric_wrap,
            glass_container(
                padding=14,
                radius=18,
                content=ft.Column(
                    spacing=10,
                    controls=[
                        ft.Text("Thông số hệ thống", size=15, weight=ft.FontWeight.W_600),
                        *system_rows,
                    ],
                ),
            ),
            glass_container(
                padding=14,
                radius=18,
                content=ft.Column(
                    spacing=10,
                    controls=[
                        ft.Text("Hội thoại cần xử lý", size=15, weight=ft.FontWeight.W_600),
                        *convos,
                    ],
                ),
            ),
        ],
    )
