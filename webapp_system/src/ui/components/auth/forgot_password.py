import flet as ft

from ui.theme import auth_text_field, build_auth_shell, button_style


def ForgotPasswordScreen(on_back_to_login=None):
    """Màn hình hướng dẫn quên mật khẩu."""

    username = auth_text_field("Tên đăng nhập", ft.Icons.PERSON_OUTLINE)
    message = ft.Text("", size=12)
    submit_btn = ft.ElevatedButton(
        "Gửi yêu cầu hỗ trợ",
        icon=ft.Icons.SUPPORT_AGENT,
        style=button_style("warning"),
        height=48,
    )

    def handle_submit(_e):
        uname = (username.value or "").strip()
        if not uname:
            message.value = "Vui lòng nhập tên đăng nhập cần hỗ trợ."
            message.color = ft.Colors.AMBER_200
            message.update()
            return
        message.value = (
            "Yêu cầu đã được ghi nhận. Vui lòng liên hệ quản trị viên hoặc chuyên gia hệ thống "
            "để được cấp lại mật khẩu."
        )
        message.color = ft.Colors.GREEN_300
        message.update()

    submit_btn.on_click = handle_submit

    return build_auth_shell(
        title="Quên mật khẩu",
        description="Nhập tên đăng nhập để gửi yêu cầu hỗ trợ đặt lại mật khẩu.",
        form_controls=[
            ft.Container(
                border_radius=14,
                bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.AMBER),
                border=ft.border.all(1, ft.Colors.with_opacity(0.3, ft.Colors.AMBER)),
                padding=ft.padding.symmetric(horizontal=14, vertical=10),
                content=ft.Row(
                    spacing=10,
                    controls=[
                        ft.Icon(ft.Icons.INFO_OUTLINE, color=ft.Colors.AMBER_200, size=18),
                        ft.Text(
                            "Hệ thống hiện không gửi email tự động. Quản trị viên sẽ hỗ trợ đặt lại mật khẩu thủ công.",
                            color=ft.Colors.AMBER_100,
                            size=12,
                            expand=True,
                        ),
                    ],
                ),
            ),
            username,
            message,
            ft.Container(height=4),
            submit_btn,
            ft.TextButton(
                "← Quay lại đăng nhập",
                style=ft.ButtonStyle(color=ft.Colors.WHITE70),
                on_click=lambda e: on_back_to_login() if on_back_to_login else None,
            ),
        ],
    )
