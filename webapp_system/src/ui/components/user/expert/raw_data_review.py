import flet as ft

from dal.dataset_repo import get_all_images
from ui.theme import collapsible_section, glass_container, page_header, status_badge

_STATUS_META = {
    "PENDING_REVIEW": ("Cho", "warning"),
    "CLEANED_DATA": ("Xong", "success"),
}


def _image_card(item: dict) -> ft.Control:
    label, kind = _STATUS_META.get(item.get("trang_thai"), ("Mo", "secondary"))
    return ft.Container(
        margin=ft.margin.only(bottom=10),
        padding=14,
        border_radius=18,
        bgcolor=ft.Colors.with_opacity(0.14, ft.Colors.WHITE),
        border=ft.border.all(1, ft.Colors.with_opacity(0.14, ft.Colors.WHITE)),
        content=ft.Column(
            spacing=8,
            tight=True,
            controls=[
                ft.Row(
                    controls=[
                        ft.Text(item.get("duong_dan", "").split("/")[-1] or "Anh dataset", size=13, weight=ft.FontWeight.W_700, expand=True),
                        status_badge(label, kind),
                    ],
                ),
                ft.Text(f"User #{item.get('id_user', '—')}  •  {item.get('created_at', '')[:16].replace('T', ' ')}", size=10, color=ft.Colors.WHITE54),
                collapsible_section(
                    "Chi tiet va thao tac",
                    ft.Column(
                        spacing=8,
                        controls=[
                            ft.Text(item.get("duong_dan", "—"), size=11, color=ft.Colors.WHITE70),
                            ft.Row(
                                spacing=8,
                                controls=[
                                    ft.ElevatedButton("Preview", icon=ft.Icons.VISIBILITY, height=34),
                                    ft.ElevatedButton("Danh dau sach", icon=ft.Icons.CHECK_CIRCLE, height=34),
                                ],
                            ),
                        ],
                    ),
                    note="An metadata va action it dung",
                ),
            ],
        ),
    )


def build_raw_data_review():
    images = sorted(get_all_images(), key=lambda item: item.get("created_at", ""), reverse=True)
    pending = [item for item in images if item.get("trang_thai") == "PENDING_REVIEW"]
    done = [item for item in images if item.get("trang_thai") == "CLEANED_DATA"]
    snapshot = pending[:4] + done[:2]

    return ft.Column(
        expand=True,
        spacing=14,
        controls=[
            page_header(
                "Review du lieu",
                "Card/detail flow cho mobile. Khong dung table desktop tren man nay.",
                icon_name="DATA_OBJECT",
            ),
            ft.Row(
                spacing=10,
                controls=[
                    glass_container(
                        expand=1,
                        padding=14,
                        radius=18,
                        content=ft.Column(tight=True, spacing=6, controls=[ft.Text("Cho review", size=11, color=ft.Colors.WHITE70), ft.Text(str(len(pending)), size=24, weight=ft.FontWeight.W_700)]),
                    ),
                    glass_container(
                        expand=1,
                        padding=14,
                        radius=18,
                        content=ft.Column(tight=True, spacing=6, controls=[ft.Text("Da lam sach", size=11, color=ft.Colors.WHITE70), ft.Text(str(len(done)), size=24, weight=ft.FontWeight.W_700)]),
                    ),
                ],
            ),
            ft.Container(
                expand=True,
                content=ft.ListView(
                    expand=True,
                    spacing=0,
                    controls=[_image_card(item) for item in snapshot]
                    if snapshot
                    else [ft.Text("Chua co du lieu cho review.", size=12, color=ft.Colors.WHITE54)],
                ),
            ),
        ],
    )
