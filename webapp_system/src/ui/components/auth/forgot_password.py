import flet as ft
from ui.theme import build_auth_shell, button_style, auth_text_field


def ForgotPasswordScreen(on_back_to_login=None):
    """Tạo màn hình quên mật khẩu."""
    email = auth_text_field("Email đã đăng ký", ft.Icons.EMAIL)
    message = ft.Text("", size=12)
    submit_btn = ft.ElevatedButton(
        "Gửi yêu cầu đặt lại",
        icon=ft.Icons.SEND,
        style=button_style("warning"),
        height=48,
    )

    def handle_submit(e):
        if not email.value or "@" not in email.value:
            message.value = "Vui lòng nhập email hợp lệ."
            message.color = ft.Colors.AMBER_200
            message.update()
            return
        # Hiển thị thông báo thành công (UI mockup)
        message.value = f"Đã gửi link đặt lại mật khẩu tới {email.value}"
        message.color = ft.Colors.GREEN_300
        email.disabled = True
        submit_btn.disabled = True
        message.update()
        email.update()
        submit_btn.update()

    submit_btn.on_click = handle_submit

    return build_auth_shell(
        title="Quên mật khẩu",
        description="Nhập email đã đăng ký, chúng tôi sẽ gửi link đặt lại mật khẩu.",
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
                            "Link xác nhận sẽ được gửi về hộp thư của bạn.",
                            color=ft.Colors.AMBER_100,
                            size=12,
                            expand=True,
                        ),
                    ],
                ),
            ),
            email,
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
