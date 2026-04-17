import flet as ft
from ui.theme import build_auth_shell, button_style, auth_text_field


def LoginScreen(page: ft.Page, on_login_success=None, on_switch_to_register=None, on_forgot_password=None):
    """Tạo màn hình đăng nhập."""
    from bll.services.auth_service import login as auth_login

    username = auth_text_field("Tài khoản", ft.Icons.PERSON)
    password = auth_text_field("Mật khẩu", ft.Icons.LOCK, password=True, can_reveal=True)
    message = ft.Text("", color=ft.Colors.RED_200, size=12)
    btn_login = ft.ElevatedButton(
        "Đăng nhập",
        icon=ft.Icons.LOGIN,
        style=button_style("primary"),
        height=48,
    )

    def handle_login(e):
        from bll.services.auth_service import _is_locked_out
        uname = (username.value or "").strip()
        pwd = password.value or ""
        if not uname or not pwd:
            message.value = "Vui lòng nhập tài khoản và mật khẩu."
            message.update()
            return

        if _is_locked_out(uname):
            message.value = "Tài khoản tạm thời bị khóa. Vui lòng thử lại sau 15 phút."
            message.update()
            return

        btn_login.disabled = True
        btn_login.update()
        message.value = ""
        message.update()

        role = auth_login(uname, pwd, page)
        if role:
            if on_login_success:
                on_login_success(role)
        else:
            message.value = "Tài khoản hoặc mật khẩu không đúng."
            message.update()
            btn_login.disabled = False
            btn_login.update()

    btn_login.on_click = handle_login

    return build_auth_shell(
        title="Đăng nhập",
        description="Chào mừng trở lại! Vui lòng đăng nhập vào hệ thống.",
        form_controls=[
            username,
            password,
            message,
            ft.Container(height=4),
            btn_login,
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.TextButton(
                        "Quên mật khẩu?",
                        style=ft.ButtonStyle(color=ft.Colors.AMBER_200),
                        on_click=lambda e: on_forgot_password() if on_forgot_password else None,
                    ),
                    ft.TextButton(
                        "Tạo tài khoản →",
                        style=ft.ButtonStyle(color=ft.Colors.CYAN_200),
                        on_click=lambda e: on_switch_to_register() if on_switch_to_register else None,
                    ),
                ],
            ),
        ],
    )
