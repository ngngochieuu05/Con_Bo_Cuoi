from __future__ import annotations

import flet as ft

from bll.admin.user_management import delete_user, reset_password as change_password, update_user
from ui.theme import PRIMARY, SECONDARY, WARNING, button_style, fmt_dt, status_badge

from .user_management_model_controls import build_model_controls

ROLE_MAP = {
    "admin": ("Quan tri", "secondary"),
    "expert": ("Chuyen gia", "primary"),
    "farmer": ("Nong dan", "warning"),
}
ROLE_OPTIONS = [
    ft.dropdown.Option("admin", "Quan tri"),
    ft.dropdown.Option("expert", "Chuyen gia"),
    ft.dropdown.Option("farmer", "Nong dan"),
]
ROLE_COLOR = {"admin": SECONDARY, "expert": PRIMARY, "farmer": WARNING}


def _role_dot(role: str) -> ft.Container:
    return ft.Container(
        width=8,
        height=8,
        border_radius=4,
        bgcolor=ROLE_COLOR.get(role, ft.Colors.WHITE38),
        margin=ft.margin.only(right=6, top=4),
    )


def build_user_card(user: dict, on_refresh) -> ft.Control:
    user_id = user.get("id_user")
    role = user.get("vai_tro", "farmer")
    full_name = user.get("ho_ten", "")
    username = user.get("ten_dang_nhap", "")
    created_at = user.get("created_at", "")
    role_label, role_kind = ROLE_MAP.get(role, ("Khac", "warning"))

    detail_ref = ft.Ref[ft.Container]()
    edit_msg = ft.Text("", size=11, color=ft.Colors.GREEN_300)

    e_full_name = ft.TextField(
        value=full_name,
        label="Ho ten",
        border_radius=10,
        expand=True,
        bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
        border_color=ft.Colors.with_opacity(0.25, ft.Colors.WHITE),
        focused_border_color=PRIMARY,
        label_style=ft.TextStyle(color=ft.Colors.WHITE60, size=11),
        text_style=ft.TextStyle(color=ft.Colors.WHITE, size=12),
        cursor_color=ft.Colors.WHITE,
        content_padding=ft.padding.symmetric(horizontal=10, vertical=8),
    )
    e_role = ft.Dropdown(
        value=role,
        label="Vai tro",
        options=ROLE_OPTIONS,
        border_radius=10,
        width=130,
        bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
        border_color=ft.Colors.with_opacity(0.25, ft.Colors.WHITE),
        focused_border_color=PRIMARY,
        label_style=ft.TextStyle(color=ft.Colors.WHITE60, size=11),
        text_style=ft.TextStyle(color=ft.Colors.WHITE, size=12),
    )
    e_new_pwd = ft.TextField(
        label="Mat khau moi (de trong neu giu nguyen)",
        password=True,
        can_reveal_password=True,
        border_radius=10,
        expand=True,
        bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
        border_color=ft.Colors.with_opacity(0.25, ft.Colors.WHITE),
        focused_border_color=WARNING,
        label_style=ft.TextStyle(color=ft.Colors.WHITE60, size=11),
        text_style=ft.TextStyle(color=ft.Colors.WHITE, size=12),
        cursor_color=ft.Colors.WHITE,
        content_padding=ft.padding.symmetric(horizontal=10, vertical=8),
    )

    def _toggle_detail(e):
        detail_ref.current.visible = not detail_ref.current.visible
        detail_ref.current.update()

    def _save_edit(e):
        updates = {}
        new_full_name = (e_full_name.value or "").strip()
        if new_full_name != full_name:
            updates["ho_ten"] = new_full_name
        new_role = e_role.value or role
        if new_role != role:
            updates["vai_tro"] = new_role
        if updates:
            update_user(user_id, updates)

        new_pwd = (e_new_pwd.value or "").strip()
        if new_pwd:
            if len(new_pwd) < 6:
                edit_msg.value = "Mat khau phai tu 6 ky tu"
                edit_msg.color = ft.Colors.AMBER_300
                edit_msg.update()
                return
            change_password(user_id, new_pwd)
            e_new_pwd.value = ""
            e_new_pwd.update()

        edit_msg.value = "Da luu thay doi"
        edit_msg.color = ft.Colors.GREEN_300
        edit_msg.update()
        on_refresh()

    def _delete(e):
        delete_user(user_id)
        on_refresh()

    detail_panel = ft.Container(
        ref=detail_ref,
        visible=False,
        padding=ft.padding.only(top=8),
        content=ft.Column(
            spacing=8,
            controls=[
                ft.Divider(color=ft.Colors.with_opacity(0.12, ft.Colors.WHITE), height=1),
                ft.Row(
                    spacing=8,
                    tight=True,
                    controls=[
                        ft.Container(
                            padding=ft.padding.symmetric(horizontal=8, vertical=4),
                            border_radius=8,
                            bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
                            content=ft.Row(
                                tight=True,
                                spacing=4,
                                controls=[
                                    ft.Icon(ft.Icons.TAG, size=11, color=ft.Colors.WHITE38),
                                    ft.Text(f"ID: {user_id}", size=10, color=ft.Colors.WHITE54),
                                ],
                            ),
                        ),
                        ft.Container(
                            padding=ft.padding.symmetric(horizontal=8, vertical=4),
                            border_radius=8,
                            bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
                            content=ft.Row(
                                tight=True,
                                spacing=4,
                                controls=[
                                    ft.Icon(
                                        ft.Icons.CALENDAR_TODAY,
                                        size=11,
                                        color=ft.Colors.WHITE38,
                                    ),
                                    ft.Text(
                                        f"Tao: {fmt_dt(created_at)}",
                                        size=10,
                                        color=ft.Colors.WHITE54,
                                    ),
                                ],
                            ),
                        ),
                    ],
                ),
                ft.Row(spacing=8, controls=[e_full_name, e_role]),
                e_new_pwd,
                ft.Row(
                    spacing=8,
                    controls=[
                        ft.ElevatedButton(
                            "Luu thay doi",
                            icon=ft.Icons.SAVE,
                            style=button_style("primary"),
                            height=32,
                            on_click=_save_edit,
                        ),
                        ft.OutlinedButton(
                            "Xoa tai khoan",
                            icon=ft.Icons.DELETE_OUTLINE,
                            height=32,
                            style=ft.ButtonStyle(
                                color=ft.Colors.RED_300,
                                side=ft.BorderSide(1, ft.Colors.RED_300),
                                shape=ft.RoundedRectangleBorder(radius=8),
                            ),
                            on_click=_delete,
                        ),
                        edit_msg,
                    ],
                ),
                *build_model_controls(role, on_refresh),
            ],
        ),
    )

    return ft.Container(
        ink=True,
        border_radius=12,
        padding=ft.padding.symmetric(horizontal=12, vertical=10),
        bgcolor=ft.Colors.with_opacity(0.09, ft.Colors.WHITE),
        border=ft.border.all(1, ft.Colors.with_opacity(0.10, ft.Colors.WHITE)),
        on_click=_toggle_detail,
        content=ft.Column(
            spacing=0,
            controls=[
                ft.Row(
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        _role_dot(role),
                        ft.Column(
                            expand=True,
                            tight=True,
                            spacing=2,
                            controls=[
                                ft.Text(
                                    full_name or username,
                                    size=14,
                                    weight=ft.FontWeight.W_600,
                                    max_lines=1,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                ),
                                ft.Row(
                                    spacing=6,
                                    tight=True,
                                    controls=[
                                        ft.Text(
                                            username,
                                            size=11,
                                            color=ft.Colors.WHITE54,
                                            max_lines=1,
                                            overflow=ft.TextOverflow.CLIP,
                                        ),
                                        ft.Text("·", size=11, color=ft.Colors.WHITE24),
                                        status_badge(role_label, role_kind),
                                    ],
                                ),
                            ],
                        ),
                        ft.Row(
                            spacing=4,
                            tight=True,
                            controls=[
                                ft.Text(
                                    fmt_dt(created_at, "%d/%m"),
                                    size=10,
                                    color=ft.Colors.WHITE38,
                                ),
                                ft.Icon(
                                    ft.Icons.EXPAND_MORE,
                                    size=16,
                                    color=ft.Colors.WHITE38,
                                ),
                            ],
                        ),
                    ],
                ),
                detail_panel,
            ],
        ),
    )
