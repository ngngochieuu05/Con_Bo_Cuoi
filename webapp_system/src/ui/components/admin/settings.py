import subprocess
import sys
import threading
import time
from pathlib import Path

import flet as ft

from bll.services.monitor_service import get_local_ip, load_config, save_config
from bll.user.farmer.tu_van_ai import clear_model_cache
from ui.theme import PRIMARY, button_style, glass_container, inline_field, section_title


def _main_entry_path() -> Path:
    return Path(__file__).resolve().parents[3] / "main.py"


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[5]


def _restart_current_app() -> None:
    args = [sys.executable, str(_main_entry_path())]
    kwargs = {"cwd": str(_workspace_root())}
    if sys.platform.startswith("win"):
        creationflags = 0
        creationflags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        creationflags |= getattr(subprocess, "DETACHED_PROCESS", 0)
        kwargs["creationflags"] = creationflags
    subprocess.Popen(args, **kwargs)


def build_admin_settings(on_logout=None):
    cfg = load_config()
    app_mode = cfg.get("app_mode", "desktop")
    app_port = str(cfg.get("app_port", 8080))

    mode_dropdown = ft.Dropdown(
        label="Ch\u1ebf \u0111\u1ed9 kh\u1edfi \u0111\u1ed9ng",
        value=app_mode,
        border_radius=12,
        bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
        border_color=ft.Colors.with_opacity(0.28, ft.Colors.WHITE),
        focused_border_color=PRIMARY,
        label_style=ft.TextStyle(color=ft.Colors.WHITE70, size=12),
        options=[
            ft.dropdown.Option("desktop", "\u1ee8ng d\u1ee5ng Desktop"),
            ft.dropdown.Option("web", "\u1ee8ng d\u1ee5ng Web"),
        ],
        expand=True,
    )
    port_field = inline_field(
        "Port (ch\u1ebf \u0111\u1ed9 Web)",
        ft.Icons.SETTINGS_ETHERNET,
        value=app_port,
        keyboard_type=ft.KeyboardType.NUMBER,
    )
    port_field.visible = app_mode == "web"
    mode_status = ft.Text("", size=11, color=ft.Colors.WHITE70)

    def _url() -> str:
        ip = get_local_ip()
        port = int((port_field.value or "8080").strip() or "8080")
        return f"http://{ip}:{port}"

    def _web_hint(short: bool = False) -> str:
        return "\u2014 (b\u1eadt ch\u1ebf \u0111\u1ed9 Web)" if short else "\u2014 (b\u1eadt ch\u1ebf \u0111\u1ed9 Web \u0111\u1ec3 d\u00f9ng)"

    url_text = ft.Text(
        _url() if app_mode == "web" else _web_hint(False),
        size=13,
        weight=ft.FontWeight.W_700,
        color=ft.Colors.CYAN_200,
        selectable=True,
    )
    copy_status = ft.Text("", size=10, color=ft.Colors.GREEN_300)

    def refresh_ip(_e):
        url_text.value = _url() if mode_dropdown.value == "web" else _web_hint(True)
        copy_status.value = ""
        url_text.update()
        copy_status.update()

    def copy_url(e):
        if e.page:
            e.page.set_clipboard(url_text.value)
        copy_status.value = "\u0110\u00e3 sao ch\u00e9p!"
        copy_status.update()

    def on_mode_change(_e):
        port_field.visible = mode_dropdown.value == "web"
        url_text.value = _url() if mode_dropdown.value == "web" else _web_hint(True)
        copy_status.value = ""
        port_field.update()
        url_text.update()
        copy_status.update()

    mode_dropdown.on_change = on_mode_change

    def save_mode(e):
        try:
            current = load_config()
            old_mode = current.get("app_mode", "desktop")
            new_mode = mode_dropdown.value or "desktop"
            data = {**current, "app_mode": new_mode}
            if new_mode == "web":
                data["app_port"] = int((port_field.value or "8080").strip())
            save_config(data)

            url_text.value = _url() if new_mode == "web" else _web_hint(True)
            url_text.update()

            if new_mode == old_mode:
                mode_status.value = "\u0110\u00e3 l\u01b0u c\u1ea5u h\u00ecnh."
                mode_status.color = ft.Colors.GREEN_300
                mode_status.update()
                return

            page = getattr(e, "page", None)
            is_web_runtime = bool(getattr(page, "web", False)) if page else False

            if is_web_runtime:
                mode_status.value = (
                    "\u0110\u00e3 l\u01b0u ch\u1ebf \u0111\u1ed9 m\u1edbi. H\u00e3y \u0111\u00f3ng tab hi\u1ec7n t\u1ea1i v\u00e0 ch\u1ea1y l\u1ea1i \u1ee9ng d\u1ee5ng \u0111\u1ec3 \u00e1p d\u1ee5ng."
                )
                mode_status.color = ft.Colors.AMBER_300
                mode_status.update()
                return

            mode_status.value = "\u0110\u00e3 l\u01b0u. \u1ee8ng d\u1ee5ng s\u1ebd kh\u1edfi \u0111\u1ed9ng l\u1ea1i s\u1ea1ch trong gi\u00e2y l\u00e1t..."
            mode_status.color = ft.Colors.AMBER_300
            mode_status.update()

            def _restart():
                time.sleep(0.8)
                try:
                    _restart_current_app()
                finally:
                    try:
                        if page:
                            page.window.close()
                    except Exception:
                        pass

            threading.Thread(target=_restart, daemon=True).start()
        except Exception as err:
            mode_status.value = f"L\u1ed7i: {str(err)[:80]}"
            mode_status.color = ft.Colors.RED_300
            mode_status.update()

    sw_realtime = ft.Switch(
        label="C\u1ea3nh b\u00e1o th\u1eddi gian th\u1ef1c",
        value=True,
        active_color=PRIMARY,
    )
    sw_email = ft.Switch(
        label="G\u1eedi email t\u1ed5ng h\u1ee3p m\u1ed7i ng\u00e0y",
        value=True,
        active_color=PRIMARY,
    )

    yolo_mode_value = cfg.get("yolo_model_mode", "cpu")
    gemini_api_key = str(cfg.get("gemini_api_key") or "")
    yolo_mode_dropdown = ft.Dropdown(
        label="Ch\u1ebf \u0111\u1ed9 ch\u1ea1y model YOLO",
        value=yolo_mode_value,
        border_radius=12,
        bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
        border_color=ft.Colors.with_opacity(0.28, ft.Colors.WHITE),
        focused_border_color=PRIMARY,
        label_style=ft.TextStyle(color=ft.Colors.WHITE70, size=12),
        options=[
            ft.dropdown.Option("cpu", "CPU (\u01b0u ti\u00ean)"),
            ft.dropdown.Option("gpu", "GPU"),
            ft.dropdown.Option("auto", "T\u1ef1 \u0111\u1ed9ng"),
        ],
    )
    yolo_status = ft.Text("", size=11, color=ft.Colors.WHITE70)
    gemini_key_field = ft.TextField(
        value=gemini_api_key,
        hint_text="Gemini API key cho Tư vấn AI",
        border_radius=12,
        password=True,
        can_reveal_password=True,
        bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
        border_color=ft.Colors.with_opacity(0.28, ft.Colors.WHITE),
        focused_border_color=PRIMARY,
        hint_style=ft.TextStyle(color=ft.Colors.WHITE38, size=11),
        text_style=ft.TextStyle(color=ft.Colors.WHITE, size=12),
        cursor_color=ft.Colors.WHITE,
        content_padding=ft.padding.symmetric(horizontal=10, vertical=10),
        prefix_icon=ft.Icons.KEY_OUTLINED,
    )

    def save_yolo_mode(_e):
        try:
            current = load_config()
            new_mode = yolo_mode_dropdown.value or "cpu"
            save_config(
                {
                    **current,
                    "yolo_model_mode": new_mode,
                    "gemini_api_key": (gemini_key_field.value or "").strip(),
                }
            )
            clear_model_cache()
            yolo_status.value = (
                f"\u0110\u00e3 l\u01b0u ch\u1ebf \u0111\u1ed9 {new_mode} v\u00e0 API key Gemini. Cache model \u0111\u00e3 \u0111\u01b0\u1ee3c l\u00e0m m\u1edbi cho l\u1ea7n suy lu\u1eadn ti\u1ebfp theo."
            )
            yolo_status.color = ft.Colors.GREEN_300
        except Exception as err:
            yolo_status.value = f"L\u1ed7i: {str(err)[:80]}"
            yolo_status.color = ft.Colors.RED_300
        yolo_status.update()

    return ft.Column(
        expand=True,
        spacing=12,
        scroll=ft.ScrollMode.AUTO,
        controls=[
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Column(
                        tight=True,
                        spacing=1,
                        controls=[
                            ft.Text("C\u00e0i \u0111\u1eb7t h\u1ec7 th\u1ed1ng", size=20, weight=ft.FontWeight.W_700),
                            ft.Text("C\u1ea5u h\u00ecnh v\u00e0 b\u1ea3o m\u1eadt", size=11, color=ft.Colors.WHITE54),
                        ],
                    ),
                    ft.Icon(ft.Icons.SETTINGS, color=ft.Colors.WHITE24, size=26),
                ],
            ),
            glass_container(
                padding=14,
                radius=16,
                content=ft.Column(
                    spacing=10,
                    controls=[
                        section_title("NOTIFICATIONS", "Th\u00f4ng b\u00e1o"),
                        sw_realtime,
                        sw_email,
                    ],
                ),
            ),
            glass_container(
                padding=14,
                radius=16,
                content=ft.Column(
                    spacing=10,
                    controls=[
                        section_title("MEMORY", "C\u1ea5u h\u00ecnh AI"),
                        ft.Text(
                            "Ch\u1ecdn thi\u1ebft b\u1ecb ch\u1ea1y YOLO inference. GPU nhanh h\u01a1n nh\u01b0ng c\u1ea7n CUDA. Ch\u1ebf \u0111\u1ed9 t\u1ef1 \u0111\u1ed9ng s\u1ebd \u01b0u ti\u00ean CPU v\u00e0 ch\u1ec9 chuy\u1ec3n khi ph\u00f9 h\u1ee3p.",
                            size=11,
                            color=ft.Colors.WHITE54,
                        ),
                        yolo_mode_dropdown,
                        gemini_key_field,
                        yolo_status,
                        ft.ElevatedButton(
                            "L\u01b0u c\u1ea5u h\u00ecnh AI",
                            icon=ft.Icons.SAVE,
                            style=button_style("primary"),
                            height=40,
                            on_click=save_yolo_mode,
                        ),
                    ],
                ),
            ),
            glass_container(
                padding=14,
                radius=16,
                content=ft.Column(
                    spacing=10,
                    controls=[
                        section_title("LANGUAGE", "Ch\u1ebf \u0111\u1ed9 kh\u1edfi \u0111\u1ed9ng v\u00e0 m\u1ea1ng LAN"),
                        ft.Text(
                            "N\u1ebfu \u0111\u1ed5i gi\u1eefa Desktop v\u00e0 Web, \u1ee9ng d\u1ee5ng s\u1ebd \u0111\u00f3ng b\u1ea3n hi\u1ec7n t\u1ea1i r\u1ed3i kh\u1edfi \u0111\u1ed9ng l\u1ea1i s\u1ea1ch.",
                            size=11,
                            color=ft.Colors.WHITE54,
                        ),
                        ft.Row(spacing=8, controls=[mode_dropdown, port_field]),
                        ft.Container(
                            border_radius=12,
                            bgcolor=ft.Colors.with_opacity(0.12, ft.Colors.CYAN),
                            border=ft.border.all(1, ft.Colors.with_opacity(0.3, ft.Colors.CYAN)),
                            padding=ft.padding.symmetric(horizontal=12, vertical=10),
                            content=ft.Column(
                                spacing=6,
                                controls=[
                                    ft.Row(
                                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                        controls=[
                                            ft.Row(
                                                tight=True,
                                                spacing=6,
                                                controls=[
                                                    ft.Icon(ft.Icons.WIFI, size=14, color=ft.Colors.CYAN_300),
                                                    ft.Text("URL truy c\u1eadp LAN", size=11, color=ft.Colors.CYAN_100),
                                                ],
                                            ),
                                            ft.Row(
                                                spacing=0,
                                                tight=True,
                                                controls=[
                                                    ft.IconButton(
                                                        ft.Icons.REFRESH,
                                                        icon_size=16,
                                                        tooltip="L\u1ea5y IP m\u1edbi",
                                                        icon_color=ft.Colors.CYAN_200,
                                                        on_click=refresh_ip,
                                                    ),
                                                    ft.IconButton(
                                                        ft.Icons.COPY,
                                                        icon_size=16,
                                                        tooltip="Sao ch\u00e9p URL",
                                                        icon_color=ft.Colors.CYAN_200,
                                                        on_click=copy_url,
                                                    ),
                                                ],
                                            ),
                                        ],
                                    ),
                                    url_text,
                                    copy_status,
                                ],
                            ),
                        ),
                        mode_status,
                        ft.ElevatedButton(
                            "L\u01b0u c\u1ea5u h\u00ecnh",
                            icon=ft.Icons.SAVE,
                            style=button_style("warning"),
                            height=40,
                            on_click=save_mode,
                        ),
                    ],
                ),
            ),
            glass_container(
                padding=14,
                radius=16,
                content=ft.Column(
                    spacing=10,
                    controls=[
                        section_title("KEY", "Phi\u00ean l\u00e0m vi\u1ec7c"),
                        ft.Text(
                            "K\u1ebft th\u00fac phi\u00ean hi\u1ec7n t\u1ea1i v\u00e0 quay v\u1ec1 m\u00e0n h\u00ecnh \u0111\u0103ng nh\u1eadp.",
                            size=11,
                            color=ft.Colors.WHITE54,
                        ),
                        ft.ElevatedButton(
                            "\u0110\u0103ng xu\u1ea5t",
                            icon=ft.Icons.LOGOUT,
                            style=button_style("danger"),
                            height=40,
                            on_click=lambda e: on_logout() if on_logout else None,
                        ),
                    ],
                ),
            ),
        ],
    )
