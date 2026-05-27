import json
import subprocess
import sys
import threading
from pathlib import Path

import flet as ft

from bll.services.monitor_service import load_config, save_config
from ui.theme import PRIMARY, SECONDARY, WARNING, glass_container, button_style

_CAMERA_HELPER = str(Path(__file__).parent / "_camera_capture.py")


def build_farmer_settings(on_logout=None, page=None):
    cfg = load_config()

    server_field  = ft.TextField(
        label="Địa chỉ máy chủ",
        value=cfg.get("server_url", "http://127.0.0.1:8000"),
        border_radius=12,
    )
    auto_connect  = ft.Switch(
        label="Tự động kết nối khi mở ứng dụng",
        value=bool(cfg.get("auto_connect", False)),
    )
    notify_alert  = ft.Switch(
        label="Nhận thông báo cảnh báo",
        value=bool(cfg.get("notify_alert", True)),
    )
    conn_status   = ft.Text("", size=12, color=ft.Colors.WHITE70)

    # ---- Camera chụp ảnh / Tư vấn AI ----
    camera_capture_field = ft.TextField(
        label="Chỉ số camera chụp ảnh (0 = mặc định)",
        value=str(cfg.get("camera_capture_index", cfg.get("camera_index", 0))),
        keyboard_type=ft.KeyboardType.NUMBER,
        border_radius=12,
        hint_text="0, 1, 2 …",
        hint_style=ft.TextStyle(color=ft.Colors.WHITE38, size=12),
    )

    # ---- Camera chuồng trại / Giám sát ----
    camera_monitor_field = ft.TextField(
        label="Chỉ số camera chuồng trại (0 = mặc định)",
        value=str(cfg.get("monitor_camera_index", cfg.get("camera_index", 0))),
        keyboard_type=ft.KeyboardType.NUMBER,
        border_radius=12,
        hint_text="0, 1, 2 …",
        hint_style=ft.TextStyle(color=ft.Colors.WHITE38, size=12),
    )
    cam_status    = ft.Text("", size=12, color=ft.Colors.WHITE70)
    cam_preview   = ft.Image(width=180, border_radius=10, visible=False)

    def _test_camera(e):
        # Dùng camera chụp ảnh để kiểm tra
        cam_status.value = "Đang kiểm tra camera…"
        cam_status.color = ft.Colors.WHITE70
        cam_preview.visible = False
        cam_status.update()
        cam_preview.update()

        def _do():
            try:
                idx = int((camera_capture_field.value or "0").strip())
            except ValueError:
                idx = 0
            try:
                _flags = 0
                if hasattr(subprocess, 'CREATE_NO_WINDOW'):
                    _flags = subprocess.CREATE_NO_WINDOW
                result = subprocess.run(
                    [sys.executable, _CAMERA_HELPER, str(idx)],
                    capture_output=True, text=True, timeout=15,
                    creationflags=_flags,
                )
                out = result.stdout.strip()
                if not out:
                    cam_status.value = f"Camera {idx} không phản hồi."
                    cam_status.color = ft.Colors.ORANGE_300
                    cam_status.update()
                    return
                obj = json.loads(out)
            except subprocess.TimeoutExpired:
                cam_status.value = f"Camera {idx} timeout."
                cam_status.color = ft.Colors.RED_300
                cam_status.update()
                return
            except Exception as ex:
                cam_status.value = f"Lỗi: {ex}"
                cam_status.color = ft.Colors.RED_300
                cam_status.update()
                return
            if "error" in obj:
                err = obj["error"]
                if err == "opencv_not_installed":
                    cam_status.value = "Thiếu opencv-python."
                else:
                    cam_status.value = f"Không mở được camera {idx}."
                cam_status.color = ft.Colors.RED_300
                cam_status.update()
                return
            img_path = obj.get("path", "")
            if not img_path:
                cam_status.value = "Không lấy được ảnh."
                cam_status.color = ft.Colors.ORANGE_300
                cam_status.update()
                return
            cam_preview.src = img_path
            cam_preview.visible = True
            cam_status.value = f"Camera {idx} hoạt động tốt."
            cam_status.color = ft.Colors.GREEN_300
            cam_status.update()
            cam_preview.update()

        threading.Thread(target=_do, daemon=True).start()

    def save(e):
        try:
            data = {
                **load_config(),
                "server_url": (server_field.value or "").strip() or "http://127.0.0.1:8000",
                "camera_capture_index": int((camera_capture_field.value or "0").strip()),
                "monitor_camera_index": int((camera_monitor_field.value or "0").strip()),
                "camera_index": int((camera_capture_field.value or "0").strip()),  # legacy compat
                "auto_connect": bool(auto_connect.value),
                "notify_alert": bool(notify_alert.value),
            }
            save_config(data)
            conn_status.value = "Đã lưu cấu hình."
            conn_status.color = ft.Colors.GREEN_300
        except Exception as err:
            conn_status.value = f"Không lưu được: {str(err)[:60]}"
            conn_status.color = ft.Colors.RED_300
        conn_status.update()

    # ── Telegram section ──────────────────────────────────────────────────
    _username = page.data.get("user_id", "") if (page and page.data) else ""

    tg_status_text = ft.Text("", size=12, color=ft.Colors.WHITE70)
    tg_link_text   = ft.Text("", size=11, color=ft.Colors.BLUE_200, selectable=True)
    tg_link_row    = ft.Row(visible=False, spacing=8, controls=[
        tg_link_text,
        ft.IconButton(
            ft.Icons.COPY,
            icon_size=16,
            icon_color=ft.Colors.WHITE70,
            tooltip="Sao chép link",
            on_click=lambda e: (
                page.set_clipboard(tg_link_text.value) if page else None
            ),
        ),
    ])

    def _refresh_tg_status():
        if not _username:
            tg_status_text.value = "⚠️ Không xác định được tài khoản."
            tg_status_text.color = ft.Colors.ORANGE_300
            return
        try:
            from bll.services.auth_service import get_user_by_username
            user = get_user_by_username(_username)
            if user and user.get("telegram_chat_id"):
                tg_name   = user.get("telegram_username", "")
                linked_at = str(user.get("telegram_linked_at", ""))[:10]
                tg_status_text.value = (
                    "✅ Đã liên kết"
                    + (f" (@{tg_name})" if tg_name else "")
                    + (f" — {linked_at}" if linked_at else "")
                )
                tg_status_text.color = ft.Colors.GREEN_300
            else:
                tg_status_text.value = "🔗 Chưa liên kết Telegram."
                tg_status_text.color = ft.Colors.WHITE54
        except Exception:
            tg_status_text.value = "Không đọc được thông tin."
            tg_status_text.color = ft.Colors.ORANGE_300

    _refresh_tg_status()

    def _gen_tg_link(e):
        if not _username:
            return
        try:
            from bll.services.telegram_link import get_deep_link
            link = get_deep_link(_username)
            tg_link_text.value = link
            tg_link_row.visible = True
            tg_status_text.value = "Link đã tạo. Mở Telegram rồi gửi /start cho bot."
            tg_status_text.color = ft.Colors.BLUE_200
            tg_status_text.update()
            tg_link_text.update()
            tg_link_row.update()
        except Exception as ex:
            tg_status_text.value = f"Lỗi tạo link: {ex}"
            tg_status_text.color = ft.Colors.RED_300
            tg_status_text.update()

    def _unlink_tg(e):
        if not _username:
            return
        try:
            from bll.services.telegram_link import unbind_telegram
            unbind_telegram(_username)
            tg_link_row.visible = False
            _refresh_tg_status()
            tg_status_text.update()
            tg_link_row.update()
        except Exception as ex:
            tg_status_text.value = f"Lỗi hủy liên kết: {ex}"
            tg_status_text.color = ft.Colors.RED_300
            tg_status_text.update()

    return ft.Column(
        expand=True,
        spacing=14,
        scroll=ft.ScrollMode.AUTO,
        controls=[
            ft.Text("Cài đặt người dùng", size=22, weight=ft.FontWeight.W_700),

            # ---- Kết nối ----
            glass_container(
                padding=16, radius=18,
                content=ft.Column(spacing=10, controls=[
                    ft.Text("Kết nối", size=14, weight=ft.FontWeight.W_600),
                    server_field,
                    auto_connect,
                    notify_alert,
                    conn_status,
                    ft.ElevatedButton(
                        "Lưu cấu hình",
                        icon=ft.Icons.SAVE,
                        style=button_style("primary"),
                        on_click=save,
                    ),
                ]),
            ),

            # ---- Camera chụp ảnh ----
            glass_container(
                padding=16, radius=18,
                content=ft.Column(spacing=10, controls=[
                    ft.Row(
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Icon(ft.Icons.CAMERA_ALT, color=SECONDARY, size=18),
                            ft.Text("Camera Chụp Ảnh / Tư Vấn AI", size=14, weight=ft.FontWeight.W_600),
                        ],
                    ),
                    ft.Text(
                        "Camera dùng để chụp ảnh bò trong chức năng tư vấn sức khỏe AI.",
                        size=11, color=ft.Colors.WHITE54,
                    ),
                    camera_capture_field,
                    ft.Row(spacing=8, controls=[
                        ft.ElevatedButton(
                            "Lưu",
                            icon=ft.Icons.SAVE,
                            style=button_style("primary"),
                            on_click=save,
                        ),
                        ft.OutlinedButton(
                            "Kiểm tra camera",
                            icon=ft.Icons.VIDEOCAM,
                            on_click=_test_camera,
                        ),
                    ]),
                    cam_status,
                    cam_preview,
                ]),
            ),

            # ---- Camera chuồng trại ----
            glass_container(
                padding=16, radius=18,
                content=ft.Column(spacing=10, controls=[
                    ft.Row(
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Icon(ft.Icons.VIDEOCAM, color=WARNING, size=18),
                            ft.Text("Camera Chuồng Trại (Giám sát)", size=14, weight=ft.FontWeight.W_600),
                        ],
                    ),
                    ft.Text(
                        "Camera dùng trong trang Giám sát trực tiếp. Chỉ số này sẽ được dùng khi không tìm thấy camera từ danh sách chuồng.",
                        size=11, color=ft.Colors.WHITE54,
                    ),
                    camera_monitor_field,
                    ft.ElevatedButton(
                        "Lưu",
                        icon=ft.Icons.SAVE,
                        style=button_style("primary"),
                        on_click=save,
                    ),
                ]),
            ),

            # ---- Liên kết Telegram ----
            glass_container(
                padding=16, radius=18,
                content=ft.Column(spacing=10, controls=[
                    ft.Row(
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Icon(ft.Icons.TELEGRAM, color=ft.Colors.BLUE_300, size=18),
                            ft.Text("Liên kết Telegram", size=14, weight=ft.FontWeight.W_600),
                        ],
                    ),
                    ft.Text(
                        "Nhận cảnh báo bò tự động qua Telegram. Nhấn 'Tạo link' rồi click link để mở bot @Cattle_Farm_Bot.",
                        size=11, color=ft.Colors.WHITE54,
                    ),
                    tg_status_text,
                    tg_link_row,
                    ft.Row(spacing=8, controls=[
                        ft.ElevatedButton(
                            "Tạo link liên kết",
                            icon=ft.Icons.LINK,
                            style=button_style("primary"),
                            on_click=_gen_tg_link,
                        ),
                        ft.OutlinedButton(
                            "Hủy liên kết",
                            icon=ft.Icons.LINK_OFF,
                            on_click=_unlink_tg,
                        ),
                    ]),
                ]),
            ),

            # ---- Đăng xuất ----
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
