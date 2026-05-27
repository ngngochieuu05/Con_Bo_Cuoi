import flet as ft
from ui.theme import build_auth_shell, button_style, auth_text_field, auth_dropdown
from bll.services.auth_service import register as bll_register


def _show_telegram_link_dialog(page: ft.Page, username: str, deep_link: str,
                                on_done):
    """Dialog hướng dẫn liên kết Telegram sau khi đăng ký."""
    link_field = ft.TextField(
        value=deep_link,
        read_only=True,
        text_size=11,
        border_color=ft.Colors.WHITE30,
        color=ft.Colors.WHITE,
        bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.WHITE),
        expand=True,
    )

    copied_msg = ft.Text("", size=11, color=ft.Colors.GREEN_300)

    def copy_link(e):
        page.set_clipboard(deep_link)
        copied_msg.value = "✅ Đã sao chép!"
        copied_msg.update()

    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Row(
            controls=[
                ft.Icon(ft.Icons.SEND, color=ft.Colors.BLUE_300, size=20),
                ft.Text(" Liên kết Telegram", weight=ft.FontWeight.W_700, size=15),
            ]
        ),
        content=ft.Column(
            tight=True,
            spacing=12,
            controls=[
                ft.Text(
                    f"Tài khoản {username} đã được tạo thành công!\n\n"
                    "Trình duyệt đã được mở tự động. Nếu không thấy, hãy sao chép link bên dưới và gửi vào Telegram:",
                    size=12,
                    color=ft.Colors.WHITE70,
                ),
                ft.Row(
                    controls=[
                        link_field,
                        ft.IconButton(
                            icon=ft.Icons.COPY,
                            tooltip="Sao chép link",
                            on_click=copy_link,
                            icon_color=ft.Colors.WHITE70,
                        ),
                    ]
                ),
                copied_msg,
                ft.Text(
                    "Bước tiếp theo:\n"
                    "1. Mở Telegram (trình duyệt đã được mở tự động)\n"
                    "2. Nhấn Start / Gửi để hoàn tất liên kết\n"
                    "3. Quay lại đây và nhấn 'Đã liên kết, tiếp tục'",
                    size=11,
                    color=ft.Colors.WHITE54,
                ),
            ],
        ),
        actions=[
            ft.TextButton(
                "Bỏ qua",
                style=ft.ButtonStyle(color=ft.Colors.WHITE54),
                on_click=lambda e: _close(e),
            ),
            ft.ElevatedButton(
                "🔗 Mở Telegram",
                style=ft.ButtonStyle(
                    bgcolor={ft.ControlState.DEFAULT: ft.Colors.BLUE_700},
                    color=ft.Colors.WHITE,
                ),
                on_click=lambda e: page.launch_url(deep_link),
            ),
            ft.ElevatedButton(
                "Đã liên kết, tiếp tục",
                icon=ft.Icons.CHECK_CIRCLE,
                style=button_style("primary"),
                on_click=lambda e: _close(e),
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    def _close(e):
        dialog.open = False
        page.update()
        on_done()

    page.overlay.append(dialog)
    dialog.open = True
    page.update()

    # Tự động mở trình duyệt với deep-link ngay khi dialog xuất hiện
    try:
        page.launch_url(deep_link)
    except Exception:
        pass


def RegisterScreen(page: ft.Page = None, on_register_success=None, on_back_to_login=None):
    """Tạo màn hình đăng ký."""
    fullname = auth_text_field("Họ tên", ft.Icons.BADGE)
    username = auth_text_field("Tài khoản", ft.Icons.PERSON)
    password = auth_text_field("Mật khẩu", ft.Icons.LOCK, password=True, can_reveal=True)
    confirm  = auth_text_field("Xác nhận mật khẩu", ft.Icons.LOCK_OUTLINE, password=True, can_reveal=True)
    role_dropdown = auth_dropdown(
        "Vai trò mặc định sau khi đăng ký",
        [("expert", "Chuyên gia"), ("farmer", "Nông dân")],
        "farmer",
    )
    message = ft.Text("", color=ft.Colors.RED_200, size=12)
    btn = ft.ElevatedButton(
        "Đăng ký",
        icon=ft.Icons.PERSON_ADD,
        style=button_style("secondary"),
        height=48,
    )

    def handle_register(e):
        uname = (username.value or "").strip()
        pwd   = password.value or ""
        cpwd  = confirm.value or ""
        hoten = (fullname.value or "").strip()

        if not uname or not pwd:
            message.value = "Vui lòng nhập tài khoản và mật khẩu."
            message.update()
            return
        if pwd != cpwd:
            message.value = "Mật khẩu xác nhận không khớp."
            message.update()
            return

        btn.disabled = True
        btn.update()
        role = role_dropdown.value or "farmer"
        ok, msg_text, deep_link, user_id = bll_register(uname, pwd, hoten, role)
        if not ok:
            message.value = msg_text
            message.update()
            btn.disabled = False
            btn.update()
            return

        def _proceed():
            if page:
                page.client_storage.set("user_role", role)
                page.client_storage.set("user_id", str(user_id or ""))
                page.client_storage.set("ho_ten", hoten)
                if isinstance(page.data, dict):
                    page.data["user_role"] = role
                    page.data["user_id"] = str(user_id or "")
                    page.data["ho_ten"] = hoten
            if on_register_success:
                on_register_success(role)

        # Farmer có deep_link → hiển thị dialog liên kết Telegram trước khi vào app
        if role == "farmer" and deep_link and page:
            _show_telegram_link_dialog(page, uname, deep_link, on_done=_proceed)
        else:
            _proceed()

    btn.on_click = handle_register

    return build_auth_shell(
        title="Tạo tài khoản",
        description="Đăng ký nhanh để truy cập hệ thống theo vai trò của bạn.",
        form_controls=[
            fullname,
            username,
            password,
            confirm,
            role_dropdown,
            message,
            ft.Container(height=4),
            btn,
            ft.TextButton(
                "← Quay lại đăng nhập",
                style=ft.ButtonStyle(color=ft.Colors.WHITE70),
                on_click=lambda e: on_back_to_login() if on_back_to_login else None,
            ),
        ],
    )
