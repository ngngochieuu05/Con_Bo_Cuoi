import base64

import flet as ft

from bll.services.auth_service import get_user_by_id, update_profile, change_password_safe
from bll.services.local_chat_store import save_local_profile_snapshot
from bll.admin.dashboard_service import get_dashboard_stats
from ui.theme import button_style, glass_container, inline_field, PRIMARY, WARNING, DANGER
from ui.upload_bridge import build_upload_batch, is_web_picker_file


def _stat_chip(label: str, value: str, color: str):
    return ft.Container(
        expand=1,
        padding=ft.padding.symmetric(horizontal=10, vertical=12),
        border_radius=14,
        bgcolor=ft.Colors.with_opacity(0.12, ft.Colors.WHITE),
        border=ft.border.all(1, ft.Colors.with_opacity(0.2, ft.Colors.WHITE)),
        content=ft.Column(
            tight=True,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Text(value, size=22, weight=ft.FontWeight.W_700, color=color),
                ft.Text(label, size=10, color=ft.Colors.WHITE60,
                        text_align=ft.TextAlign.CENTER),
            ],
        ),
    )


def build_profile_admin(page: ft.Page, on_back=None):
    user_id = int(page.client_storage.get("user_id") or 0)
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
                src_base64=b64, width=96, height=96, fit=ft.ImageFit.COVER,
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
        file_obj = e.files[0]
        if is_web_picker_file(file_obj):
            try:
                items, jobs = build_upload_batch(page, [file_obj], subdir="profile/admin")
                file_picker.data = {"pending": items}
                file_picker.upload(jobs)
                snack("Đang tải ảnh từ thiết bị...")
            except Exception as ex:
                snack(f"Lỗi tải ảnh: {ex}", error=True)
            return
        try:
            with open(file_obj.path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            avatar_b64["val"] = b64
            save_local_profile_snapshot(user_id, {"anh_dai_dien": b64})
            refresh_avatar()
            snack("Đã chọn ảnh. Nhấn 'Lưu thông tin' để cập nhật.")
        except Exception as ex:
            snack(f"Lỗi đọc ảnh: {ex}", error=True)

    def on_file_upload(e: ft.FilePickerUploadEvent):
        state = file_picker.data if isinstance(file_picker.data, dict) else None
        if not state:
            return
        if e.error:
            file_picker.data = None
            snack(f"Lỗi upload ảnh: {e.error}", error=True)
            return
        if e.progress != 1.0:
            return
        item = state["pending"][0]
        try:
            with open(item["server_path"], "rb") as f:
                avatar_b64["val"] = base64.b64encode(f.read()).decode()
            save_local_profile_snapshot(user_id, {"anh_dai_dien": avatar_b64["val"]})
            refresh_avatar()
            snack("Đã chọn ảnh. Nhấn 'Lưu thông tin' để cập nhật.")
        except Exception as ex:
            snack(f"Lỗi đọc ảnh: {ex}", error=True)
        finally:
            file_picker.data = None

    file_picker = ft.FilePicker(on_result=on_file_result, on_upload=on_file_upload)
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

    tf_role = inline_field("Vai trò", ft.Icons.BADGE, value="Quản trị viên")
    tf_role.read_only = True
    tf_role.bgcolor = ft.Colors.with_opacity(0.06, ft.Colors.WHITE)
    tf_phone = inline_field("Số điện thoại", ft.Icons.PHONE, value=user.get("so_dien_thoai", ""))
    tf_email = inline_field("Email", ft.Icons.EMAIL_OUTLINED, value=user.get("email", ""))
    tf_address = inline_field("Địa chỉ", ft.Icons.LOCATION_ON_OUTLINED, value=user.get("dia_chi", ""))
    tf_department = inline_field("Bộ phận", ft.Icons.BUSINESS_CENTER, value=user.get("bo_phan", ""))
    tf_scope = inline_field("Phạm vi quản trị", ft.Icons.ADMIN_PANEL_SETTINGS, value=user.get("pham_vi_quan_tri", ""))

    tf_old_pw = inline_field("Mật khẩu hiện tại", ft.Icons.LOCK, password=True)
    tf_new_pw = inline_field("Mật khẩu mới", ft.Icons.LOCK_OUTLINE, password=True)
    tf_cfm_pw = inline_field("Xác nhận mật khẩu mới", ft.Icons.LOCK_RESET, password=True)

    # ── System stats ─────────────────────────────────────────────────────
    stats = get_dashboard_stats()
    total_users   = stats.get("users", 0)
    models_online = stats.get("models_online", 0)
    cams_online   = stats.get("cameras_online", 0)

    stats_section = glass_container(
        padding=20,
        content=ft.Column(
            spacing=12,
            controls=[
                ft.Row(
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=8,
                    controls=[
                        ft.Icon(ft.Icons.ADMIN_PANEL_SETTINGS, color=WARNING, size=18),
                        ft.Text(
                            "Thống kê hệ thống",
                            size=14, weight=ft.FontWeight.W_700,
                            color=ft.Colors.WHITE70,
                        ),
                    ],
                ),
                ft.Row(
                    spacing=8,
                    controls=[
                        _stat_chip("Tài khoản", str(total_users), PRIMARY),
                        _stat_chip("Model online", str(models_online), "#4CAF50"),
                        _stat_chip("Camera online", str(cams_online), WARNING),
                    ],
                ),
                ft.Text(
                    "Vai trò: Quản trị viên hệ thống",
                    size=11,
                    color=ft.Colors.WHITE38,
                    italic=True,
                ),
            ],
        ),
    )

    # ── Save handlers ──────────────────────────────────────────────────────
    def save_info(e):
        ho_ten = tf_ho_ten.value.strip()
        if not ho_ten:
            snack("Họ tên không được để trống.", error=True)
            return
        updates = {"ho_ten": ho_ten}
        updates["so_dien_thoai"] = tf_phone.value.strip()
        updates["email"] = tf_email.value.strip()
        updates["dia_chi"] = tf_address.value.strip()
        updates["bo_phan"] = tf_department.value.strip()
        updates["pham_vi_quan_tri"] = tf_scope.value.strip()
        if avatar_b64["val"]:
            updates["anh_dai_dien"] = avatar_b64["val"]
            page.client_storage.set("anh_dai_dien", avatar_b64["val"])
        ok, msg_txt = update_profile(user_id, updates)
        if not ok:
            snack(msg_txt, error=True)
            return
        page.client_storage.set("ho_ten", ho_ten)
        if isinstance(page.data, dict):
            page.data["ho_ten"] = ho_ten
            if avatar_b64["val"]:
                page.data["anh_dai_dien"] = avatar_b64["val"]
        snack(msg_txt)

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
                        tf_phone,
                        tf_email,
                        tf_address,
                        ft.Divider(height=1, color=ft.Colors.with_opacity(0.15, ft.Colors.WHITE)),
                        ft.Text(
                            "Thông tin quản trị",
                            size=13, weight=ft.FontWeight.W_600,
                            color=ft.Colors.WHITE70,
                        ),
                        tf_department,
                        tf_scope,
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
            stats_section,
        ],
    )
