import os
import sys
import threading
import time

import flet as ft

from bll.services.monitor_service import get_local_ip, load_config, save_config
from bll.user.farmer.tu_van_ai import clear_model_cache
from ui.theme import button_style, collapsible_section, glass_container, inline_field, page_header


def build_admin_settings(on_logout=None):
    cfg = load_config()
    mode_dropdown = ft.Dropdown(
        label="Che do khoi dong",
        value=cfg.get("app_mode", "desktop"),
        border_radius=12,
        bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
        border_color=ft.Colors.with_opacity(0.28, ft.Colors.WHITE),
        focused_border_color="#4CAF50",
        label_style=ft.TextStyle(color=ft.Colors.WHITE70, size=12),
        options=[ft.dropdown.Option("desktop", "Desktop"), ft.dropdown.Option("web", "Web")],
    )
    port_field = inline_field("Port web", ft.Icons.SETTINGS_ETHERNET, value=str(cfg.get("app_port", 8080)), keyboard_type=ft.KeyboardType.NUMBER)
    port_field.visible = mode_dropdown.value == "web"
    yolo_dropdown = ft.Dropdown(
        label="YOLO mode",
        value=cfg.get("yolo_model_mode", "cpu"),
        border_radius=12,
        bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
        border_color=ft.Colors.with_opacity(0.28, ft.Colors.WHITE),
        focused_border_color="#4CAF50",
        label_style=ft.TextStyle(color=ft.Colors.WHITE70, size=12),
        options=[ft.dropdown.Option("cpu", "CPU"), ft.dropdown.Option("gpu", "GPU"), ft.dropdown.Option("auto", "Auto")],
    )
    mode_status = ft.Text("", size=11, color=ft.Colors.WHITE70)
    yolo_status = ft.Text("", size=11, color=ft.Colors.WHITE70)
    copy_status = ft.Text("", size=10, color=ft.Colors.GREEN_300)
    sw_realtime = ft.Switch(label="Canh bao realtime", value=True)
    sw_email = ft.Switch(label="Email tong hop", value=True)
    sw_auto_assign = ft.Switch(label="Tu dong gan nguoi xu ly", value=False)
    default_sla = inline_field("SLA mac dinh (phut)", ft.Icons.TIMER, value="120", keyboard_type=ft.KeyboardType.NUMBER)
    security_note = ft.Text("2FA va role lock se duoc ap dung o ban tiep theo.", size=11, color=ft.Colors.WHITE54)
    backup_note = ft.Text("Lich backup JSON + log xoay vong theo ngay.", size=11, color=ft.Colors.WHITE54)
    generic_status = ft.Text("", size=11, color=ft.Colors.WHITE60)

    def _build_url() -> str:
        return f"http://{get_local_ip()}:{int((port_field.value or '8080').strip() or '8080')}"

    url_text = ft.Text(_build_url() if mode_dropdown.value == "web" else "Bat web mode de dung LAN", size=13, weight=ft.FontWeight.W_700, color=ft.Colors.CYAN_200, selectable=True)

    def _update_mode_visibility(e=None):
        port_field.visible = mode_dropdown.value == "web"
        url_text.value = _build_url() if mode_dropdown.value == "web" else "Bat web mode de dung LAN"
        port_field.update()
        url_text.update()

    def _save_mode(e):
        try:
            current = load_config()
            next_mode = mode_dropdown.value or "desktop"
            data = {**current, "app_mode": next_mode}
            if next_mode == "web":
                data["app_port"] = int((port_field.value or "8080").strip())
            save_config(data)
            if current.get("app_mode") != next_mode:
                def _restart():
                    for idx in (3, 2, 1):
                        mode_status.value = f"Da luu. Restart sau {idx}s..."
                        mode_status.color = ft.Colors.AMBER_300
                        mode_status.update()
                        time.sleep(1)
                    try:
                        os.execv(sys.executable, [sys.executable] + sys.argv)
                    except Exception:
                        if e.page:
                            e.page.window.close()
                threading.Thread(target=_restart, daemon=True).start()
            else:
                mode_status.value = "Da luu cau hinh."
                mode_status.color = ft.Colors.GREEN_300
                mode_status.update()
            _update_mode_visibility()
        except Exception as err:
            mode_status.value = f"Loi: {str(err)[:60]}"
            mode_status.color = ft.Colors.RED_300
            mode_status.update()

    def _save_yolo(e):
        try:
            data = {**load_config(), "yolo_model_mode": yolo_dropdown.value or "cpu"}
            save_config(data)
            clear_model_cache()
            yolo_status.value = "Da luu mode AI va clear cache model."
            yolo_status.color = ft.Colors.GREEN_300
        except Exception as err:
            yolo_status.value = f"Loi: {str(err)[:60]}"
            yolo_status.color = ft.Colors.RED_300
        yolo_status.update()

    def _save_alert_defaults(e):
        generic_status.value = "Da luu mac dinh canh bao."
        generic_status.color = ft.Colors.GREEN_300
        generic_status.update()

    def _run_backup_now(e):
        generic_status.value = "Da kich hoat backup thu cong (mock flow)."
        generic_status.color = ft.Colors.CYAN_200
        generic_status.update()

    mode_dropdown.on_change = _update_mode_visibility

    return ft.Column(
        expand=True,
        spacing=14,
        scroll=ft.ScrollMode.AUTO,
        controls=[
            page_header("Cai dat he thong", "Nhom theo accordion de mobile de quet hon.", icon_name="SETTINGS"),
            glass_container(
                padding=14,
                radius=18,
                content=ft.Column(
                    spacing=10,
                    controls=[
                        collapsible_section("Thong bao", ft.Column(spacing=8, controls=[sw_realtime, sw_email]), initially_open=True),
                        collapsible_section(
                            "Mac dinh canh bao",
                            ft.Column(
                                spacing=8,
                                controls=[
                                    sw_auto_assign,
                                    default_sla,
                                    ft.ElevatedButton(
                                        "Luu mac dinh",
                                        icon=ft.Icons.SAVE,
                                        style=button_style("secondary"),
                                        on_click=_save_alert_defaults,
                                    ),
                                ],
                            ),
                            initially_open=False,
                        ),
                        collapsible_section(
                            "AI va inference",
                            ft.Column(
                                spacing=8,
                                controls=[
                                    yolo_dropdown,
                                    yolo_status,
                                    ft.ElevatedButton("Luu AI", icon=ft.Icons.SAVE, style=button_style("primary"), on_click=_save_yolo),
                                ],
                            ),
                        ),
                        collapsible_section(
                            "Bao mat",
                            ft.Column(
                                spacing=8,
                                controls=[
                                    ft.Switch(label="Khoa doi role khi dang nhap", value=True),
                                    ft.Switch(label="Bat xac thuc buoc 2 (preview)", value=False),
                                    security_note,
                                ],
                            ),
                        ),
                        collapsible_section(
                            "Sao luu va log",
                            ft.Column(
                                spacing=8,
                                controls=[
                                    ft.Switch(label="Backup tu dong luc 00:30", value=True),
                                    ft.Switch(label="Giu log 14 ngay", value=True),
                                    backup_note,
                                    ft.ElevatedButton(
                                        "Backup ngay",
                                        icon=ft.Icons.BACKUP,
                                        style=button_style("warning"),
                                        on_click=_run_backup_now,
                                    ),
                                ],
                            ),
                        ),
                        collapsible_section(
                            "LAN va app mode",
                            ft.Column(
                                spacing=8,
                                controls=[
                                    mode_dropdown,
                                    port_field,
                                    ft.Container(
                                        padding=ft.padding.symmetric(horizontal=12, vertical=10),
                                        border_radius=12,
                                        bgcolor=ft.Colors.with_opacity(0.12, ft.Colors.CYAN),
                                        border=ft.border.all(1, ft.Colors.with_opacity(0.25, ft.Colors.CYAN)),
                                        content=ft.Column(spacing=6, controls=[ft.Text("URL LAN", size=11, color=ft.Colors.CYAN_100), url_text, copy_status]),
                                    ),
                                    mode_status,
                                    ft.ElevatedButton("Luu mode", icon=ft.Icons.SAVE, style=button_style("warning"), on_click=_save_mode),
                                ],
                            ),
                            initially_open=True,
                        ),
                        collapsible_section(
                            "Phien lam viec",
                            ft.Column(
                                spacing=8,
                                controls=[
                                    ft.Text("Ket thuc phien hien tai va quay lai dang nhap.", size=11, color=ft.Colors.WHITE60),
                                    ft.ElevatedButton("Dang xuat", icon=ft.Icons.LOGOUT, style=button_style("danger"), on_click=lambda e: on_logout() if on_logout else None),
                                ],
                            ),
                        ),
                        generic_status,
                    ],
                ),
            ),
        ],
    )
