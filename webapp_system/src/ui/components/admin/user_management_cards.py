from __future__ import annotations

import secrets

import flet as ft

from bll.admin.user_management import delete_user, reset_password as change_password, update_user
from ui.theme import (
    PRIMARY,
    SECONDARY,
    WARNING,
    button_style,
    fmt_dt,
    open_bottom_sheet,
    overflow_action_button,
    status_badge,
)

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


def _state_badge(user: dict) -> ft.Control:
    status = (user.get("trang_thai") or "active").lower()
    if status in {"inactive", "locked", "disabled"}:
        return status_badge("Tam khoa", "danger")
    if status in {"new", "pending"}:
        return status_badge("Moi", "warning")
    return status_badge("Hoat dong", "primary")


def build_user_card(user: dict, on_refresh) -> ft.Control:
    user_id = user.get("id_user")
    role = user.get("vai_tro", "farmer")
    full_name = user.get("ho_ten", "")
    username = user.get("ten_dang_nhap", "")
    created_at = user.get("created_at", "")
    role_label, role_kind = ROLE_MAP.get(role, ("Khac", "warning"))

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
                if edit_msg.page:
                    edit_msg.update()
                return
            change_password(user_id, new_pwd)
            e_new_pwd.value = ""
            if e_new_pwd.page:
                e_new_pwd.update()

        edit_msg.value = "Da luu thay doi"
        edit_msg.color = ft.Colors.GREEN_300
        if edit_msg.page:
            edit_msg.update()
        on_refresh()

    def _delete(e):
        delete_user(user_id)
        on_refresh()

    def _reset_quick(e):
        temp_password = secrets.token_hex(4)
        change_password(user_id, temp_password)
        edit_msg.value = f"Da reset mat khau tam: {temp_password}"
        edit_msg.color = ft.Colors.AMBER_300
        if edit_msg.page:
            edit_msg.update()
        on_refresh()

    def _open_detail(e):
        if not e.page:
            return
        detail = ft.Column(
            spacing=8,
            controls=[
                ft.Row(
                    spacing=8,
                    controls=[
                        ft.Container(
                            padding=ft.padding.symmetric(horizontal=8, vertical=4),
                            border_radius=8,
                            bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
                            content=ft.Text(f"ID: {user_id}", size=10, color=ft.Colors.WHITE54),
                        ),
                        ft.Container(
                            padding=ft.padding.symmetric(horizontal=8, vertical=4),
                            border_radius=8,
                            bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
                            content=ft.Text(f"Tao: {fmt_dt(created_at)}", size=10, color=ft.Colors.WHITE54),
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
                        overflow_action_button(
                            [
                                ("Reset mat khau mac dinh", "LOCK_RESET", _reset_quick),
                                ("Xoa tai khoan", "DELETE_OUTLINE", _delete),
                            ]
                        ),
                        edit_msg,
                    ],
                ),
                *build_model_controls(role, on_refresh),
            ],
        )
        open_bottom_sheet(e.page, full_name or username or "Chi tiet tai khoan", detail)

    return ft.Container(
        ink=True,
        border_radius=12,
        padding=ft.padding.symmetric(horizontal=12, vertical=10),
        bgcolor=ft.Colors.with_opacity(0.09, ft.Colors.WHITE),
        border=ft.border.all(1, ft.Colors.with_opacity(0.10, ft.Colors.WHITE)),
        on_click=_open_detail,
        content=ft.Row(
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
                        ft.Text(
                            username,
                            size=11,
                            color=ft.Colors.WHITE54,
                            max_lines=1,
                            overflow=ft.TextOverflow.CLIP,
                        ),
                        ft.Row(
                            spacing=6,
                            tight=True,
                            controls=[
                                status_badge(role_label, role_kind),
                                _state_badge(user),
                            ],
                        ),
                    ],
                ),
                ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.END,
                    spacing=2,
                    controls=[
                        ft.Text(fmt_dt(created_at, "%d/%m"), size=10, color=ft.Colors.WHITE38),
                        ft.Icon(ft.Icons.CHEVRON_RIGHT, size=16, color=ft.Colors.WHITE38),
                    ],
                ),
            ],
        ),
    )
