import base64

import flet as ft

from bll.services.auth_service import (
    get_session_value,
    get_user_by_id,
    update_profile,
    change_password_safe,
    sync_profile_session,
)
from ui.theme import button_style, glass_container, inline_field, PRIMARY


def build_profile_expert(page: ft.Page, on_back=None):
    user_id = int(get_session_value(page, "user_id", 0) or 0)
    user = get_user_by_id(user_id) or {}
    avatar_b64 = {"val": user.get("anh_dai_dien", "") or ""}

    # ── Avatar widget ──────────────────────────────────────────────────────
    avatar_img = ft.Container(
        width=96, height=96,
        border_radius=48,
        bgcolor=ft.Colors.with_opacity(0.30, PRIMARY),
        border=ft.border.all(2.5, ft.Colors.with_opacity(0.55, ft.Colors.WHITE)),
        alignment=ft.alignment.center,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
    )
    msg = ft.Text("", size=12)

    def snack(text: str, error: bool = False):
        msg.value = text
        msg.color = "#FF7A7A" if error else PRIMARY
        if msg.page:
            msg.update()

    def refresh_avatar():
        b64 = avatar_b64["val"]
        if b64:
            avatar_img.content = ft.Image(
                src_base64=b64, width=96, height=96, fit="cover",
            )
        else:
            label = (user.get("ho_ten") or "?")[0].upper()
            avatar_img.content = ft.Text(
                label, size=32, weight=ft.FontWeight.W_700, color=ft.Colors.WHITE,
            )
        if avatar_img.page:
            avatar_img.update()

    refresh_avatar()

    # ── File picker ────────────────────────────────────────────────────────
    def on_file_result(e: ft.FilePickerResultEvent):
        if not e.files:
            return
        try:
            with open(e.files[0].path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            avatar_b64["val"] = b64
            refresh_avatar()
            snack("Đã chọn ảnh. Nhấn 'Lưu thông tin' để cập nhật.")
        except Exception as ex:
            snack(f"Lỗi đọc ảnh: {ex}", error=True)

    file_picker = ft.FilePicker(on_result=on_file_result)
    page.overlay.append(file_picker)
    page.update()

    # ── Fields ────────────────────────────────────────────────────────────
    tf_ho_ten = inline_field("Họ và tên", ft.Icons.PERSON, value=user.get("ho_ten", ""))

    tf_username = inline_field(
        "Tên đăng nhập", ft.Icons.ALTERNATE_EMAIL,
        value=user.get("ten_dang_nhap", ""),
    )
    tf_username.read_only = True
    tf_username.bgcolor = ft.Colors.with_opacity(0.06, ft.Colors.WHITE)

    tf_role = inline_field("Vai trò", ft.Icons.BADGE, value="Chuyên gia")
    tf_role.read_only = True
    tf_role.bgcolor = ft.Colors.with_opacity(0.06, ft.Colors.WHITE)

    tf_old_pw = inline_field("Mật khẩu hiện tại", ft.Icons.LOCK, password=True)
    tf_new_pw = inline_field("Mật khẩu mới", ft.Icons.LOCK_OUTLINE, password=True)
    tf_cfm_pw = inline_field("Xác nhận mật khẩu mới", ft.Icons.LOCK_RESET, password=True)

    # ── Save handlers ──────────────────────────────────────────────────────
    def save_info(e):
        ho_ten = tf_ho_ten.value.strip()
        if not ho_ten:
            snack("Họ tên không được để trống.", error=True)
            return
        updates = {"ho_ten": ho_ten}
        if avatar_b64["val"]:
            updates["anh_dai_dien"] = avatar_b64["val"]
            sync_profile_session(page, anh_dai_dien=avatar_b64["val"])
        update_profile(user_id, updates)
        sync_profile_session(page, ho_ten=ho_ten)
        snack("Đã lưu thông tin thành công!")

    def save_password(e):
        old, new, cfm = tf_old_pw.value, tf_new_pw.value, tf_cfm_pw.value
        if not old or not new or not cfm:
            snack("Vui lòng điền đầy đủ các trường mật khẩu.", error=True)
            return
        if new != cfm:
            snack("Mật khẩu mới không khớp.", error=True)
            return
        ok, msg_txt = change_password_safe(user_id, old, new)
        if not ok:
            snack(msg_txt, error=True)
            return
        for tf in (tf_old_pw, tf_new_pw, tf_cfm_pw):
            tf.value = ""
        page.update()
        snack(msg_txt)

    # ── Layout ────────────────────────────────────────────────────────────
    return ft.Column(
        expand=True,
        scroll=ft.ScrollMode.AUTO,
        spacing=14,
        controls=[
            ft.Row(
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.IconButton(
                        icon=ft.Icons.ARROW_BACK_IOS_NEW,
                        icon_color=ft.Colors.WHITE70,
                        tooltip="Quay lại",
                        on_click=lambda e: on_back() if on_back else None,
                    ),
                    ft.Text("Hồ sơ cá nhân", size=18, weight=ft.FontWeight.W_700),
                ],
            ),
            glass_container(
                padding=20,
                content=ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=10,
                    controls=[
                        avatar_img,
                        ft.ElevatedButton(
                            "Chọn ảnh đại diện",
                            icon=ft.Icons.PHOTO_CAMERA,
                            style=button_style("surface"),
                            on_click=lambda e: file_picker.pick_files(
                                allowed_extensions=["jpg", "jpeg", "png", "webp"],
                                allow_multiple=False,
                            ),
                        ),
                        ft.Text(user.get("ho_ten", ""), size=16, weight=ft.FontWeight.W_600),
                        ft.Text(
                            f"@{user.get('ten_dang_nhap', '')}",
                            size=12, color=ft.Colors.WHITE54,
                        ),
                    ],
                ),
            ),
            glass_container(
                padding=20,
                content=ft.Column(
                    spacing=10,
                    controls=[
                        ft.Text(
                            "Thông tin cá nhân",
                            size=14, weight=ft.FontWeight.W_700,
                            color=ft.Colors.WHITE70,
                        ),
                        tf_ho_ten,
                        tf_username,
                        tf_role,
                        msg,
                        ft.ElevatedButton(
                            "Lưu thông tin",
                            icon=ft.Icons.SAVE,
                            style=button_style("primary"),
                            on_click=save_info,
                            expand=True,
                        ),
                    ],
                ),
            ),
            glass_container(
                padding=20,
                content=ft.Column(
                    spacing=10,
                    controls=[
                        ft.Text(
                            "Đổi mật khẩu",
                            size=14, weight=ft.FontWeight.W_700,
                            color=ft.Colors.WHITE70,
                        ),
                        tf_old_pw,
                        tf_new_pw,
                        tf_cfm_pw,
                        ft.ElevatedButton(
                            "Đổi mật khẩu",
                            icon=ft.Icons.LOCK_RESET,
                            style=button_style("secondary"),
                            on_click=save_password,
                            expand=True,
                        ),
                    ],
                ),
            ),
        ],
    )
