import flet as ft
import os, sys, threading, time
from bll.services.monitor_service import load_config, save_config, get_local_ip
from ui.theme import glass_container, button_style, section_title, inline_field, DANGER, WARNING, PRIMARY, SECONDARY


def build_admin_settings(on_logout=None):
    cfg      = load_config()
    app_mode = cfg.get("app_mode", "desktop")
    app_port = str(cfg.get("app_port", 8080))

    mode_dropdown = ft.Dropdown(
        label="Chế độ khởi động",
        value=app_mode,
        border_radius=12,
        bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
        border_color=ft.Colors.with_opacity(0.28, ft.Colors.WHITE),
        focused_border_color=PRIMARY,
        label_style=ft.TextStyle(color=ft.Colors.WHITE70, size=12),
        options=[
            ft.dropdown.Option("desktop", "Desktop App"),
            ft.dropdown.Option("web",     "Web Browser"),
        ],
        expand=True,
    )
    port_field = inline_field(
        "Port (chế độ Web)", ft.Icons.SETTINGS_ETHERNET,
        value=app_port,
        keyboard_type=ft.KeyboardType.NUMBER,
    )
    port_field.visible = (app_mode == "web")
    mode_status = ft.Text("", size=11, color=ft.Colors.WHITE70)

    # ── LAN URL card ──────────────────────────────────────────────────────
    def _url():
        ip   = get_local_ip()
        port = int((port_field.value or "8080").strip() or "8080")
        return f"http://{ip}:{port}"

    url_text = ft.Text(
        _url() if app_mode == "web" else "— (bật chế độ Web để dùng)",
        size=13, weight=ft.FontWeight.W_700,
        color=ft.Colors.CYAN_200, selectable=True,
    )
    copy_status = ft.Text("", size=10, color=ft.Colors.GREEN_300)

    def refresh_ip(e):
        url_text.value   = _url() if mode_dropdown.value == "web" else "— (bật chế độ Web)"
        copy_status.value = ""
        url_text.update(); copy_status.update()

    def copy_url(e):
        if e.page:
            e.page.set_clipboard(url_text.value)
        copy_status.value = "Đã sao chép!"
        copy_status.update()

    def on_mode_change(e):
        port_field.visible   = (mode_dropdown.value == "web")
        url_text.value       = _url() if mode_dropdown.value == "web" else "— (bật chế độ Web)"
        copy_status.value    = ""
        port_field.update(); url_text.update(); copy_status.update()

    mode_dropdown.on_change = on_mode_change

    def save_mode(e):
        try:
            old_mode = load_config().get("app_mode", "desktop")
            data = {**load_config()}
            data["app_mode"] = mode_dropdown.value or "desktop"
            if mode_dropdown.value == "web":
                data["app_port"] = int((port_field.value or "8080").strip())
            save_config(data)
            new_mode = data["app_mode"]

            if new_mode != old_mode:
                # Đổi giao thức → đếm ngược rồi tự khởi động lại
                url_text.value = _url() if new_mode == "web" else "— (bật chế độ Web)"
                url_text.update()

                def _countdown():
                    for i in (3, 2, 1):
                        mode_status.value = f"Đã lưu. Khởi động lại sau {i}s..."
                        mode_status.color = ft.Colors.AMBER_300
                        mode_status.update()
                        time.sleep(1)
                    # Restart toàn bộ process
                    try:
                        os.execv(sys.executable, [sys.executable] + sys.argv)
                    except Exception:
                        # Fallback: chỉ tắt window nếu execv không dùng được
                        if e.page:
                            e.page.window.close()

                threading.Thread(target=_countdown, daemon=True).start()
            else:
                # Cùng giao thức, chỉ lưu config
                url_text.value = _url() if new_mode == "web" else "— (bật chế độ Web)"
                url_text.update()
                mode_status.value = "Đã lưu cấu hình."
                mode_status.color = ft.Colors.GREEN_300
                mode_status.update()
        except Exception as err:
            mode_status.value = f"Lỗi: {str(err)[:60]}"
            mode_status.color = ft.Colors.RED_300
            mode_status.update()

    # ── Notification config (local state only) ────────────────────────────
    sw_realtime = ft.Switch(label="Cảnh báo thời gian thực", value=True, active_color=PRIMARY)
    sw_email    = ft.Switch(label="Gửi email tổng hợp mỗi ngày", value=True, active_color=PRIMARY)

    return ft.Column(
        expand=True,
        spacing=12,
        scroll=ft.ScrollMode.AUTO,
        controls=[
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Column(tight=True, spacing=1, controls=[
                        ft.Text("Cài đặt hệ thống", size=20, weight=ft.FontWeight.W_700),
                        ft.Text("Cấu hình & bảo mật", size=11, color=ft.Colors.WHITE54),
                    ]),
                    ft.Icon(ft.Icons.SETTINGS, color=ft.Colors.WHITE24, size=26),
                ],
            ),

            # Thông báo
            glass_container(padding=14, radius=16, content=ft.Column(spacing=10, controls=[
                section_title("NOTIFICATIONS", "Thông báo"),
                sw_realtime,
                sw_email,
            ])),

            # Chế độ & LAN URL
            glass_container(padding=14, radius=16, content=ft.Column(spacing=10, controls=[
                section_title("LANGUAGE", "Chế độ khởi động & Mạng LAN"),
                ft.Text(
                    "Web mode: Phone cùng WiFi mở trình duyệt với URL bên dưới.",
                    size=11, color=ft.Colors.WHITE54,
                ),
                ft.Row(spacing=8, controls=[mode_dropdown, port_field]),
                ft.Container(
                    border_radius=12,
                    bgcolor=ft.Colors.with_opacity(0.12, ft.Colors.CYAN),
                    border=ft.border.all(1, ft.Colors.with_opacity(0.3, ft.Colors.CYAN)),
                    padding=ft.padding.symmetric(horizontal=12, vertical=10),
                    content=ft.Column(spacing=6, controls=[
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Row(tight=True, spacing=6, controls=[
                                    ft.Icon(ft.Icons.WIFI, size=14, color=ft.Colors.CYAN_300),
                                    ft.Text("URL truy cập LAN", size=11, color=ft.Colors.CYAN_100),
                                ]),
                                ft.Row(spacing=0, tight=True, controls=[
                                    ft.IconButton(ft.Icons.REFRESH, icon_size=16, tooltip="Lấy IP mới", icon_color=ft.Colors.CYAN_200, on_click=refresh_ip),
                                    ft.IconButton(ft.Icons.COPY,    icon_size=16, tooltip="Sao chép URL", icon_color=ft.Colors.CYAN_200, on_click=copy_url),
                                ]),
                            ],
                        ),
                        url_text,
                        copy_status,
                    ]),
                ),
                mode_status,
                ft.ElevatedButton(
                    "Lưu cấu hình",
                    icon=ft.Icons.SAVE,
                    style=button_style("warning"),
                    height=40,
                    on_click=save_mode,
                ),
            ])),

            # Đăng xuất
            glass_container(padding=14, radius=16, content=ft.Column(spacing=10, controls=[
                section_title("KEY", "Phiên làm việc"),
                ft.Text("Kết thúc phiên hiện tại và quay về màn hình đăng nhập.", size=11, color=ft.Colors.WHITE54),
                ft.ElevatedButton(
                    "Đăng xuất",
                    icon=ft.Icons.LOGOUT,
                    style=button_style("danger"),
                    height=40,
                    on_click=lambda e: on_logout() if on_logout else None,
                ),
            ])),
        ],
    )


    mode_dropdown = ft.Dropdown(
        label="Chế độ khởi động",
        value=app_mode,
        border_radius=12,
        options=[
            ft.dropdown.Option("desktop", "Desktop App"),
            ft.dropdown.Option("web", "Web Browser"),
        ],
    )
    port_field = ft.TextField(
        label="Port (chế độ Web)",
        value=app_port,
        keyboard_type=ft.KeyboardType.NUMBER,
        border_radius=12,
        visible=(app_mode == "web"),
    )
    mode_status = ft.Text("", size=11, color=ft.Colors.WHITE70)

    # ---- LAN Access card ----
    def _build_url():
        ip = get_local_ip()
        port = int((port_field.value or "8080").strip() or "8080")
        return f"http://{ip}:{port}"

    url_text = ft.Text(
        _build_url() if app_mode == "web" else "— (bật chế độ Web để dùng)",
        size=13,
        weight=ft.FontWeight.W_700,
        color=ft.Colors.CYAN_200,
        selectable=True,
    )
    copy_status = ft.Text("", size=10, color=ft.Colors.GREEN_300)

    def refresh_ip(e):
        url_text.value = _build_url() if mode_dropdown.value == "web" else "— (bật chế độ Web)"
        copy_status.value = ""
        url_text.update()
        copy_status.update()

    def copy_url(e):
        if e.page:
            e.page.set_clipboard(url_text.value)
        copy_status.value = "Đã sao chép!"
        copy_status.update()

    def on_mode_change(e):
        port_field.visible = (mode_dropdown.value == "web")
        url_text.value = _build_url() if mode_dropdown.value == "web" else "— (bật chế độ Web)"
        copy_status.value = ""
        port_field.update()
        url_text.update()
        copy_status.update()

    mode_dropdown.on_change = on_mode_change

    def save_mode(e):
        try:
            data = {**load_config()}
            data["app_mode"] = mode_dropdown.value or "desktop"
            if mode_dropdown.value == "web":
                data["app_port"] = int((port_field.value or "8080").strip())
            save_config(data)
            url_text.value = _build_url() if mode_dropdown.value == "web" else "— (bật chế độ Web)"
            url_text.update()
            mode_status.value = "Đã lưu. Khởi động lại ứng dụng để áp dụng."
            mode_status.color = ft.Colors.GREEN_300
        except Exception as err:
            mode_status.value = f"Lỗi: {str(err)[:60]}"
            mode_status.color = ft.Colors.RED_300
        mode_status.update()

    return ft.Column(
        expand=True,
        spacing=14,
        scroll=ft.ScrollMode.AUTO,
        controls=[
            ft.Text("Hệ thống & Bảo mật", size=22, weight=ft.FontWeight.W_700),

            # Thông báo & Phân quyền
            glass_container(
                padding=16, radius=18,
                content=ft.Column(spacing=10, controls=[
                    ft.Text("Thông báo", size=14, weight=ft.FontWeight.W_600),
                    ft.Switch(label="Cảnh báo thời gian thực", value=True),
                    ft.Switch(label="Gửi email tổng hợp mỗi ngày", value=True),
                    ft.Divider(color=ft.Colors.WHITE12),
                    ft.Text("Phân quyền", size=14, weight=ft.FontWeight.W_600),
                    ft.Dropdown(
                        label="Vai trò mặc định khi tạo tài khoản",
                        border_radius=12,
                        options=[
                            ft.dropdown.Option("user", "Người dùng"),
                            ft.dropdown.Option("expert", "Chuyên gia"),
                            ft.dropdown.Option("admin", "Quản trị"),
                        ],
                        value="user",
                    ),
                    ft.ElevatedButton("Lưu cấu hình", icon=ft.Icons.SAVE, style=button_style("primary")),
                ]),
            ),

            # Chế độ + LAN URL
            glass_container(
                padding=16, radius=18,
                content=ft.Column(spacing=10, controls=[
                    ft.Text("Chế độ & Truy cập mạng", size=14, weight=ft.FontWeight.W_600),
                    ft.Text(
                        "Web mode: phone cùng mạng WiFi mở trình duyệt vào URL bên dưới.",
                        size=11, color=ft.Colors.WHITE60,
                    ),
                    mode_dropdown,
                    port_field,
                    # URL card
                    ft.Container(
                        border_radius=12,
                        bgcolor=ft.Colors.with_opacity(0.12, ft.Colors.CYAN),
                        border=ft.border.all(1, ft.Colors.with_opacity(0.3, ft.Colors.CYAN)),
                        padding=ft.padding.symmetric(horizontal=12, vertical=10),
                        content=ft.Column(spacing=6, controls=[
                            ft.Row(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                controls=[
                                    ft.Text("URL truy cập LAN", size=11, color=ft.Colors.CYAN_100),
                                    ft.Row(spacing=4, tight=True, controls=[
                                        ft.IconButton(
                                            ft.Icons.REFRESH,
                                            icon_size=16,
                                            tooltip="Lấy IP mới",
                                            on_click=refresh_ip,
                                        ),
                                        ft.IconButton(
                                            ft.Icons.COPY,
                                            icon_size=16,
                                            tooltip="Sao chép URL",
                                            on_click=copy_url,
                                        ),
                                    ]),
                                ],
                            ),
                            url_text,
                            copy_status,
                        ]),
                    ),
                    mode_status,
                    ft.ElevatedButton(
                        "Lưu & khởi động lại",
                        icon=ft.Icons.RESTART_ALT,
                        style=button_style("warning"),
                        on_click=save_mode,
                    ),
                ]),
            ),

            # Đăng xuất
            glass_container(
                padding=16, radius=18,
                content=ft.Column(spacing=10, controls=[
                    ft.Text("Phiên làm việc", size=14, weight=ft.FontWeight.W_600),
                    ft.Text("Kết thúc phiên và quay về đăng nhập.", size=11, color=ft.Colors.WHITE60),
                    ft.ElevatedButton(
                        "Đăng xuất",
                        icon=ft.Icons.LOGOUT,
                        style=button_style("danger"),
                        on_click=lambda e: on_logout() if on_logout else None,
                    ),
                ]),
            ),
        ],
    )
