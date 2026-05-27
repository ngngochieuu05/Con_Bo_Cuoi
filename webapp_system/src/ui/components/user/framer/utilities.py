from __future__ import annotations

from datetime import datetime

import flet as ft

from bll.services.monitor_service import load_cache, load_config
from bll.services.system_overview_service import get_system_overview
from ui.theme import DANGER, PRIMARY, WARNING, glass_container, status_badge


_FEATURED_POSTS = [
    {
        "title": "Kiểm tra đàn bò đầu ngày",
        "summary": "Mở Giám sát trực tiếp, kiểm tra camera chính, nước uống và trạng thái cảnh báo trước khi cho ăn.",
        "tag": "Quy trình sáng",
        "color": ft.Colors.CYAN_300,
    },
    {
        "title": "Khi nào nên chuyển sang Tư vấn AI",
        "summary": "Dùng ngay khi bò có biểu hiện bỏ ăn, sưng vùng da, nằm lâu hoặc có bất thường trong hành vi.",
        "tag": "Chẩn đoán nhanh",
        "color": ft.Colors.GREEN_300,
    },
    {
        "title": "Khi nào nên gọi chuyên gia",
        "summary": "Nếu cảnh báo lặp lại nhiều lần hoặc AI nghi ngờ bệnh, gửi ảnh và chuyển ngay sang Tư vấn chuyên gia.",
        "tag": "Can thiệp sớm",
        "color": ft.Colors.AMBER_300,
    },
]

_CARE_TIPS = [
    ("Nước uống", "Đảm bảo máng nước sạch, không thiếu nước trong các khung giờ nóng."),
    ("Chuồng trại", "Giữ nền khô, thông thoáng, giảm tụ khí và vùng ẩm kéo dài."),
    ("Quan sát ăn uống", "Nếu bò bỏ ăn liên tục, cần kết hợp ảnh chụp và lịch sử cảnh báo để kiểm tra."),
    ("Theo dõi nằm lâu", "Bò nằm quá ngưỡng là dấu hiệu cần xem lại Giám sát và hỏi AI."),
]


def _quick_action(label: str, icon_name, color: str, on_click) -> ft.Control:
    return ft.Container(
        padding=ft.padding.symmetric(horizontal=12, vertical=12),
        border_radius=16,
        bgcolor=ft.Colors.with_opacity(0.12, color),
        border=ft.border.all(1, ft.Colors.with_opacity(0.30, color)),
        ink=True,
        on_click=on_click,
        content=ft.Row(
            spacing=10,
            controls=[
                ft.Icon(icon_name, color=color, size=18),
                ft.Text(label, size=12, weight=ft.FontWeight.W_600, expand=True, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
            ],
        ),
    )


def _two_column_grid(items: list[ft.Control]) -> ft.Column:
    rows: list[ft.Control] = []
    for index in range(0, len(items), 2):
        pair = items[index:index + 2]
        rows.append(
            ft.Row(
                spacing=8,
                controls=[
                    ft.Container(expand=1, content=pair[0]),
                    ft.Container(expand=1, content=pair[1]) if len(pair) > 1 else ft.Container(expand=1),
                ],
            )
        )
    return ft.Column(spacing=8, controls=rows)


def _mini_stat(title: str, value: str, note: str, color: str = PRIMARY) -> ft.Control:
    return glass_container(
        padding=12,
        radius=16,
        content=ft.Column(
            tight=True,
            spacing=4,
            controls=[
                ft.Text(title, size=11, color=ft.Colors.WHITE70),
                ft.Text(value, size=21, weight=ft.FontWeight.W_700, color=color),
                ft.Text(note, size=10, color=ft.Colors.WHITE54),
            ],
        ),
    )


def _feeding_hours_text(config: dict) -> str:
    hours = config.get("thresholds", {}).get("feeding_hours") or []
    if not hours:
        return "--"
    return ", ".join(f"{start}:00-{end}:00" for start, end in hours)


def _daily_advice(cache: dict, config: dict) -> tuple[str, str]:
    hour = datetime.now().hour
    alert_count = int(cache.get("active_alerts", 0) or 0)
    if alert_count > 0:
        return (
            "Có cảnh báo đang mở. Ưu tiên kiểm tra camera và ảnh gần nhất trước khi xử lý đàn.",
            "warning",
        )
    if 11 <= hour <= 15:
        return (
            "Khung giờ nắng nóng. Kiểm tra nước uống, quạt, vùng bóng mát và trạng thái bò nằm lâu.",
            "warning",
        )
    if hour < 9:
        return (
            "Đầu ngày là thời điểm tốt để mở Giám sát trực tiếp và đối chiếu trạng thái camera, model, lịch sử phiên.",
            "primary",
        )
    feeding_hours = _feeding_hours_text(config)
    return (
        f"Theo dõi khung giờ cho ăn {feeding_hours} và rà lại lịch sử cảnh báo nếu có bất thường.",
        "primary",
    )


def build_farmer_utilities(page: ft.Page | None = None, on_navigate=None):
    cache = load_cache()
    config = load_config()
    user_id = int((page.client_storage.get("user_id") or 0) if page else 0)
    overview = get_system_overview(user_id=user_id, role="farmer")

    advice_text, advice_kind = _daily_advice(cache, config)
    recent_alerts = cache.get("recent_alerts", [])[-4:]

    quick_actions = _two_column_grid(
        [
            _quick_action("Mở giám sát", ft.Icons.LIVE_TV, ft.Colors.CYAN_300, lambda _e: on_navigate("monitoring") if on_navigate else None),
            _quick_action("Tư vấn với AI", ft.Icons.HEALTH_AND_SAFETY, ft.Colors.GREEN_300, lambda _e: on_navigate("consulting") if on_navigate else None),
            _quick_action("Xem thông báo", ft.Icons.NOTIFICATIONS_ACTIVE, ft.Colors.AMBER_300, lambda _e: on_navigate("notifications") if on_navigate else None),
            _quick_action("Lịch sử giám sát", ft.Icons.HISTORY, ft.Colors.TEAL_300, lambda _e: on_navigate("history") if on_navigate else None),
        ]
    )

    stat_grid = _two_column_grid(
        [
            _mini_stat(
                "Camera của tôi",
                f"{overview.get('own_cameras_online', 0)}/{overview.get('own_cameras_total', 0)}",
                "camera trực tuyến",
                ft.Colors.CYAN_300,
            ),
            _mini_stat(
                "Cảnh báo mở",
                str(overview.get("own_alerts_open", 0)),
                "cảnh báo cần xử lý",
                DANGER,
            ),
            _mini_stat(
                "Model online",
                f"{overview.get('models_online', 0)}/{overview.get('models_total', 0)}",
                "toàn hệ thống",
                PRIMARY,
            ),
            _mini_stat(
                "Hoạt động hôm nay",
                str(overview.get("activity_today", 0)),
                "sự kiện hệ thống",
                WARNING,
            ),
        ]
    )

    alert_controls: list[ft.Control] = []
    for alert in reversed(recent_alerts):
        alert_type = str(alert.get("type", "Cảnh báo"))
        is_warning = "fight" in alert_type.lower() or "bất thường" in alert_type.lower()
        alert_controls.append(
            ft.Container(
                padding=ft.padding.all(10),
                border_radius=12,
                bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                    controls=[
                        ft.Text(
                            f"{alert.get('time', '--')} • {alert_type}",
                            size=12,
                            expand=True,
                            max_lines=2,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                        status_badge("Cần xem", "danger" if is_warning else "warning"),
                    ],
                ),
            )
        )
    if not alert_controls:
        alert_controls = [ft.Text("Chưa có cảnh báo gần đây.", size=12, color=ft.Colors.WHITE60)]

    post_controls = [
        ft.Container(
            padding=ft.padding.all(12),
            border_radius=14,
            bgcolor=ft.Colors.with_opacity(0.10, post["color"]),
            border=ft.border.all(1, ft.Colors.with_opacity(0.24, post["color"])),
            content=ft.Column(
                spacing=6,
                controls=[
                    status_badge(post["tag"], "primary"),
                    ft.Text(post["title"], size=14, weight=ft.FontWeight.W_600),
                    ft.Text(post["summary"], size=12, color=ft.Colors.WHITE70),
                ],
            ),
        )
        for post in _FEATURED_POSTS
    ]

    tip_controls = [
        ft.Container(
            padding=ft.padding.all(12),
            border_radius=14,
            bgcolor=ft.Colors.with_opacity(0.08, ft.Colors.WHITE),
            content=ft.Column(
                tight=True,
                spacing=4,
                controls=[
                    ft.Text(title, size=13, weight=ft.FontWeight.W_600),
                    ft.Text(summary, size=12, color=ft.Colors.WHITE70),
                ],
            ),
        )
        for title, summary in _CARE_TIPS
    ]

    return ft.Column(
        expand=True,
        spacing=12,
        scroll=ft.ScrollMode.AUTO,
        controls=[
            ft.Column(
                spacing=4,
                controls=[
                    ft.Text("Tiện ích", size=24, weight=ft.FontWeight.W_700),
                    ft.Text(
                        "Một nơi để theo dõi nhanh trạng thái trang trại, cảnh báo và gợi ý vận hành trong ngày.",
                        size=12,
                        color=ft.Colors.WHITE70,
                    ),
                ],
            ),
            glass_container(
                padding=16,
                radius=18,
                content=ft.Column(
                    spacing=10,
                    controls=[
                        ft.Text("Điều hướng nhanh", size=15, weight=ft.FontWeight.W_600),
                        quick_actions,
                    ],
                ),
            ),
            stat_grid,
            glass_container(
                padding=16,
                radius=18,
                content=ft.Column(
                    spacing=8,
                    controls=[
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Text("Khuyến nghị hôm nay", size=15, weight=ft.FontWeight.W_600),
                                status_badge("Ưu tiên", advice_kind),
                            ],
                        ),
                        ft.Text(advice_text, size=12, color=ft.Colors.WHITE70),
                        ft.Text(f"Khung giờ cho ăn: {_feeding_hours_text(config)}", size=12, color=ft.Colors.WHITE70),
                        ft.Text(
                            f"Ngưỡng bò nằm lâu: {config.get('thresholds', {}).get('lying_duration_minutes', '--')} phút • "
                            f"Cooldown cảnh báo: {config.get('thresholds', {}).get('alert_cooldown_seconds', '--')} giây",
                            size=12,
                            color=ft.Colors.WHITE70,
                        ),
                        ft.Text(
                            f"Chế độ app: {overview.get('app_mode', '--')} • Port: {overview.get('app_port', '--')} • "
                            f"Camera máy chủ: index {overview.get('camera_index', '--')}",
                            size=12,
                            color=ft.Colors.WHITE70,
                        ),
                    ],
                ),
            ),
            glass_container(
                padding=16,
                radius=18,
                content=ft.Column(
                    spacing=10,
                    controls=[
                        ft.Text("Bài viết nổi bật", size=15, weight=ft.FontWeight.W_600),
                        ft.Column(spacing=8, controls=post_controls),
                    ],
                ),
            ),
            glass_container(
                padding=16,
                radius=18,
                content=ft.Column(
                    spacing=10,
                    controls=[
                        ft.Text("Mẹo chăn nuôi nhanh", size=15, weight=ft.FontWeight.W_600),
                        ft.Column(spacing=8, controls=tip_controls),
                    ],
                ),
            ),
            glass_container(
                padding=16,
                radius=18,
                content=ft.Column(
                    spacing=8,
                    controls=[
                        ft.Text("Cảnh báo gần đây", size=15, weight=ft.FontWeight.W_600),
                        *alert_controls,
                    ],
                ),
            ),
        ],
    )
