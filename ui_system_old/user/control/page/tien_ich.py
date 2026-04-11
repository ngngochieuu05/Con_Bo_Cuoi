"""
Tiện Ích — Con Bò Cười Dark Theme
Chatbot Demo, Thời tiết trang trại, Gợi ý nhanh
"""
import flet as ft
import threading
import time
from datetime import datetime

from src.ui.theme import (
    BG_MAIN, BG_PANEL, PRIMARY, SECONDARY, ACCENT,
    TEXT_MAIN, TEXT_SUB, TEXT_MUTED,
    WARNING, DANGER, SUCCESS, BORDER,
    GRAD_TEAL, GRAD_CYAN, GRAD_WARN, GRAD_PURPLE,
    RADIUS_CARD, RADIUS_BTN, SIZE_H1, SIZE_H2, SIZE_H3,
    SIZE_BODY, SIZE_CAPTION, SHADOW_CARD_GLOW,
    panel, primary_button,
)

# Demo dữ liệu thời tiết - thay bằng API thật nếu có
_DEMO_WEATHER = {"temp": 32, "humidity": 75, "desc": "Nắng nhẹ", "wind": "12 km/h"}
_DEMO_ALERTS  = [
    {"time": "05:12", "cam": "CAM-01", "msg": "Bò #B042 bất thường",      "sev": "Cao"},
    {"time": "04:38", "cam": "CAM-02", "msg": "Bò #B017 bỏ ăn",          "sev": "TB"},
    {"time": "03:15", "cam": "CAM-04", "msg": "Bò ra ngoài khu vực",      "sev": "Cao"},
    {"time": "02:00", "cam": "CAM-03", "msg": "Camera kết nối lại",       "sev": "OK"},
    {"time": "00:00", "cam": "SYS",    "msg": "Snapshot tự động lưu xong","sev": "OK"},
]

_DEMO_SUGGESTIONS = [
    {
        "icon": ft.Icons.WARNING_AMBER_ROUNDED, "color": WARNING,
        "title": "Kiểm tra Bò #B042 ngay",
        "body": "Camera CAM-01 phát hiện hành vi bất thường lúc 05:12. Nên xem lại video clip.",
    },
    {
        "icon": ft.Icons.THERMOSTAT_ROUNDED, "color": DANGER,
        "title": "Nhiệt độ chuồng cao — 36°C",
        "body": "Chuồng A2 vượt ngưỡng an toàn. Hãy bật thêm quạt thông gió.",
    },
    {
        "icon": ft.Icons.WATER_DROP_ROUNDED, "color": SECONDARY,
        "title": "Lịch tưới nước hôm nay",
        "body": "Dự báo nắng nóng 34°C, nên tăng lượng nước uống cho đàn bò thêm 20%.",
    },
    {
        "icon": ft.Icons.INSIGHTS_ROUNDED, "color": PRIMARY,
        "title": "Năng suất tháng này tăng 8%",
        "body": "So với tháng trước, số lượt nhận diện tăng đều. Mô hình YOLOv9 hoạt động tốt.",
    },
]

_CHAT_QUICK_PROMPTS = [
    "Hôm nay có bao nhiêu bò bất thường?",
    "Cách xử lý bò bỏ ăn?",
    "Nhiệt độ lý tưởng cho bò sữa?",
    "Lịch tiêm phòng tháng này?",
]


class TienIchPage(ft.Column):
    def __init__(self):
        super().__init__(expand=True, scroll=ft.ScrollMode.AUTO, spacing=0)
        self.chat_messages = []
        self._build()

    # ─── Weather card ────────────────────────────────────────────────────────
    def _weather_card(self) -> ft.Container:
        w = _DEMO_WEATHER
        temp_color = DANGER if w["temp"] >= 35 else WARNING if w["temp"] >= 30 else PRIMARY

        # Weather icon mapping
        icon = ft.Icons.WB_SUNNY_ROUNDED if "nắng" in w["desc"].lower() \
            else ft.Icons.CLOUD_ROUNDED if "mây" in w["desc"].lower() \
            else ft.Icons.THUNDERSTORM_ROUNDED

        def _metric(label, value, icon_n, color):
            return ft.Container(
                content=ft.Column([
                    ft.Icon(icon_n, size=18, color=color),
                    ft.Text(value, size=14, color=TEXT_MAIN, weight=ft.FontWeight.BOLD),
                    ft.Text(label, size=9, color=TEXT_SUB),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3),
                bgcolor=ft.Colors.with_opacity(0.08, color),
                border_radius=10,
                padding=ft.padding.symmetric(horizontal=14, vertical=10),
                expand=True,
                border=ft.border.all(1, ft.Colors.with_opacity(0.15, color)),
            )

        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Column([
                        ft.Row([
                            ft.Icon(ft.Icons.LOCATION_ON_ROUNDED, size=14, color=TEXT_SUB),
                            ft.Text("TP. Hồ Chí Minh", size=12, color=TEXT_SUB),
                        ], spacing=4),
                        ft.Row([
                            ft.Icon(icon, size=44, color=temp_color),
                            ft.Text(f"{w['temp']}°C", size=48, color=temp_color,
                                    weight=ft.FontWeight.BOLD),
                        ], spacing=8),
                        ft.Text(w["desc"], size=SIZE_BODY, color=TEXT_SUB),
                    ], expand=True, spacing=4),
                    ft.Container(
                        content=ft.Column([
                            ft.Text("Dự báo hôm nay", size=10, color=TEXT_SUB),
                            ft.Container(height=6),
                            ft.Text("🌅 Sáng: 28°C", size=11, color=TEXT_MAIN),
                            ft.Text("☀️ Trưa: 35°C", size=11, color=WARNING),
                            ft.Text("🌆 Chiều: 32°C", size=11, color=TEXT_MAIN),
                            ft.Text("🌙 Tối: 27°C", size=11, color=TEXT_MAIN),
                        ], spacing=4),
                        bgcolor=ft.Colors.with_opacity(0.06, ft.Colors.WHITE),
                        border_radius=10, border=ft.border.all(1, BORDER),
                        padding=ft.padding.all(12),
                    ),
                ], spacing=16),
                ft.Container(height=12),
                ft.Row([
                    _metric("Độ Ẩm",  f"{w['humidity']}%",  ft.Icons.WATER_DROP_ROUNDED, ACCENT),
                    ft.Container(width=8),
                    _metric("Gió",    w["wind"],  ft.Icons.AIR_ROUNDED,    SECONDARY),
                    ft.Container(width=8),
                    _metric("UV",     "Cao",      ft.Icons.WB_SUNNY_ROUNDED, WARNING),
                    ft.Container(width=8),
                    _metric("Cập nhật", "Vừa xong", ft.Icons.SYNC_ROUNDED, PRIMARY),
                ]),
            ]),
            bgcolor=BG_PANEL,
            border_radius=RADIUS_CARD,
            padding=ft.padding.all(20),
            border=ft.border.all(1, BORDER),
            shadow=SHADOW_CARD_GLOW,
        )

    # ─── Farm alerts ─────────────────────────────────────────────────────────
    def _alerts_panel(self) -> ft.Container:
        def _row(a):
            sev_color = DANGER if a["sev"] == "Cao" \
                else WARNING if a["sev"] == "TB" \
                else PRIMARY

            return ft.Container(
                content=ft.Row([
                    ft.Container(
                        content=ft.Text(a["sev"], size=8, color=ft.Colors.WHITE,
                                        weight=ft.FontWeight.BOLD),
                        bgcolor=sev_color, border_radius=6,
                        padding=ft.padding.symmetric(horizontal=6, vertical=3),
                        width=48,
                    ),
                    ft.Text(a["time"], size=10, color=TEXT_MUTED, width=36),
                    ft.Text(a["cam"],  size=10, color=TEXT_SUB, width=56),
                    ft.Text(a["msg"],  size=SIZE_BODY, color=TEXT_MAIN, expand=True),
                ], spacing=8),
                bgcolor=ft.Colors.with_opacity(0.03, ft.Colors.WHITE),
                border_radius=6,
                padding=ft.padding.symmetric(horizontal=10, vertical=7),
                border=ft.border.all(1, ft.Colors.with_opacity(0.05, ft.Colors.WHITE)),
            )

        rows = ft.Column(
            [r for a in _DEMO_ALERTS
             for r in [_row(a), ft.Divider(color=BORDER, height=1)]],
            spacing=0,
        )

        return panel(
            content=rows,
            title="Tình Hình Thông Báo Trang Trại",
            icon=ft.Icons.CAMPAIGN_ROUNDED,
            action_widget=ft.Container(
                content=ft.Text("5 thông báo", size=10,
                                color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
                bgcolor=DANGER, border_radius=12,
                padding=ft.padding.symmetric(horizontal=9, vertical=3),
            ),
        )

    # ─── Quick suggestions ───────────────────────────────────────────────────
    def _suggestions_panel(self) -> ft.Container:
        def _card(s):
            return ft.Container(
                content=ft.Row([
                    ft.Container(
                        content=ft.Icon(s["icon"], color=ft.Colors.WHITE, size=20),
                        width=42, height=42, border_radius=21,
                        bgcolor=s["color"], alignment=ft.alignment.center,
                    ),
                    ft.Column([
                        ft.Text(s["title"], size=SIZE_BODY, color=TEXT_MAIN,
                                weight=ft.FontWeight.W_600),
                        ft.Text(s["body"], size=10, color=TEXT_SUB),
                    ], expand=True, spacing=3),
                    ft.Icon(ft.Icons.CHEVRON_RIGHT_ROUNDED, color=TEXT_MUTED, size=18),
                ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor=ft.Colors.with_opacity(0.04, ft.Colors.WHITE),
                border_radius=10,
                padding=ft.padding.all(12),
                border=ft.border.all(1, ft.Colors.with_opacity(0.06, ft.Colors.WHITE)),
                ink=True,
                animate_scale=ft.Animation(120, ft.AnimationCurve.EASE_OUT),
            )

        cards = ft.Column([_card(s) for s in _DEMO_SUGGESTIONS], spacing=8)

        return panel(
            content=cards,
            title="Gợi Ý Nhanh Từ Dữ Liệu",
            icon=ft.Icons.LIGHTBULB_ROUNDED,
        )

    # ─── Chatbot ─────────────────────────────────────────────────────────────
    def _chatbot_panel(self) -> ft.Container:
        # Chat history list
        self._chat_list = ft.ListView(
            expand=True,
            spacing=8,
            padding=ft.padding.all(12),
            auto_scroll=True,
        )

        # Initial bot greeting
        self._add_bot_msg(
            "Xin chào! Tôi là trợ lý Con Bò Cười 🐄\n"
            "Tôi có thể giúp bạn về quản lý trang trại, phân tích dữ liệu bò, "
            "hoặc trả lời câu hỏi chăn nuôi.\n\n"
            "*(Demo — API chưa được kết nối)*"
        )

        self._chat_input = ft.TextField(
            hint_text="Nhập câu hỏi về trang trại...",
            border_radius=10,
            border_color=BORDER,
            focused_border_color=PRIMARY,
            cursor_color=PRIMARY,
            text_style=ft.TextStyle(color=TEXT_MAIN, size=SIZE_BODY),
            hint_style=ft.TextStyle(color=TEXT_MUTED, size=SIZE_BODY),
            bgcolor=ft.Colors.with_opacity(0.06, ft.Colors.WHITE),
            content_padding=ft.padding.symmetric(horizontal=14, vertical=10),
            expand=True,
            on_submit=self._send_chat,
        )

        # Quick prompts
        quick_row = ft.Row([
            ft.Container(
                content=ft.Text(q, size=10, color=PRIMARY),
                bgcolor=ft.Colors.with_opacity(0.1, PRIMARY),
                border_radius=20,
                border=ft.border.all(1, ft.Colors.with_opacity(0.3, PRIMARY)),
                padding=ft.padding.symmetric(horizontal=10, vertical=5),
                ink=True,
                on_click=lambda e, q=q: self._quick_send(q),
            )
            for q in _CHAT_QUICK_PROMPTS
        ], spacing=6, wrap=True)

        chat_body = ft.Column([
            # API notice
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.INFO_OUTLINE_ROUNDED, size=14, color=WARNING),
                    ft.Text("Demo giao diện — Chưa kết nối API key",
                            size=11, color=WARNING),
                ], spacing=6),
                bgcolor=ft.Colors.with_opacity(0.1, WARNING),
                border_radius=8,
                padding=ft.padding.symmetric(horizontal=12, vertical=7),
                border=ft.border.all(1, ft.Colors.with_opacity(0.3, WARNING)),
            ),
            ft.Container(height=8),
            ft.Text("Gợi ý câu hỏi:", size=10, color=TEXT_SUB),
            ft.Container(height=4),
            quick_row,
            ft.Container(height=8),
            ft.Divider(color=BORDER, height=1),
            ft.Container(
                content=self._chat_list,
                height=280,
            ),
            ft.Divider(color=BORDER, height=1),
            ft.Container(height=8),
            ft.Row([
                self._chat_input,
                ft.Container(
                    content=ft.Icon(ft.Icons.SEND_ROUNDED, color=ft.Colors.WHITE, size=18),
                    width=42, height=42, border_radius=21,
                    bgcolor=PRIMARY, alignment=ft.alignment.center,
                    ink=True, on_click=self._send_chat,
                ),
            ], spacing=10),
        ], spacing=0)

        return panel(
            content=chat_body,
            title="Trợ Lý AI Con Bò Cười",
            icon=ft.Icons.SMART_TOY_ROUNDED,
            expand=True,
        )

    def _add_bot_msg(self, text: str):
        self.chat_messages.append({
            "role": "bot", "text": text,
            "time": datetime.now().strftime("%H:%M"),
        })

    def _add_user_msg(self, text: str):
        self.chat_messages.append({
            "role": "user", "text": text,
            "time": datetime.now().strftime("%H:%M"),
        })

    def _rebuild_chat(self):
        if not hasattr(self, "_chat_list"):
            return
        self._chat_list.controls.clear()
        for msg in self.chat_messages:
            is_user = msg["role"] == "user"
            bubble = ft.Container(
                content=ft.Column([
                    ft.Text(msg["text"], size=SIZE_BODY,
                            color=ft.Colors.WHITE if is_user else TEXT_MAIN),
                    ft.Text(msg["time"], size=9,
                            color=ft.Colors.with_opacity(0.6, ft.Colors.WHITE)
                            if is_user else TEXT_MUTED),
                ], spacing=3),
                bgcolor=PRIMARY if is_user else ft.Colors.with_opacity(0.08, ft.Colors.WHITE),
                border_radius=ft.BorderRadius(
                    14, 14, 0 if is_user else 14, 14 if is_user else 0
                ),
                padding=ft.padding.symmetric(horizontal=12, vertical=8),
                border=ft.border.all(1, BORDER) if not is_user else None,
            )
            self._chat_list.controls.append(
                ft.Row([
                    ft.Container(expand=True) if is_user else ft.Container(width=0),
                    bubble,
                    ft.Container(width=0) if is_user else ft.Container(expand=True),
                ], spacing=8)
            )
        try:
            self._chat_list.update()
        except Exception:
            pass

    def _quick_send(self, text: str):
        if hasattr(self, "_chat_input"):
            self._chat_input.value = text
            try:
                self._chat_input.update()
            except Exception:
                pass
        self._process_send(text)

    def _send_chat(self, e):
        text = self._chat_input.value.strip()
        if not text:
            return
        self._chat_input.value = ""
        try:
            self._chat_input.update()
        except Exception:
            pass
        self._process_send(text)

    def _process_send(self, text: str):
        self._add_user_msg(text)
        self._rebuild_chat()

        # Demo response
        def _fake_reply():
            time.sleep(0.8)
            replies = {
                "bất thường": "Có 2 bò phát hiện bất thường hôm nay: Bò #B042 (05:12) và Bò #B031 (07:30). Hãy kiểm tra ngay camera CAM-01.",
                "bỏ ăn": "Bò bỏ ăn có thể do stress, thay đổi thức ăn, hoặc bệnh tiêu hóa. Nên quan sát thêm 2–4h, nếu kéo dài hãy gọi thú y.",
                "nhiệt độ": "Nhiệt độ lý tưởng cho bò sữa: 10–25°C. Trên 30°C cần bổ sung nước và quạt thông gió.",
                "tiêm phòng": "Lịch tiêm phòng tháng 3: Vaccine FMD (15/03), Tẩy ký sinh trùng (20/03). Liên hệ thú y để đặt lịch.",
            }
            lower = text.lower()
            reply = next(
                (v for k, v in replies.items() if k in lower),
                "Xin lỗi, tôi chưa có dữ liệu để trả lời câu hỏi này. "
                "Vui lòng liên hệ bộ phận hỗ trợ hoặc kết nối API key để sử dụng đầy đủ."
            )
            self._add_bot_msg(reply)
            self._rebuild_chat()

        threading.Thread(target=_fake_reply, daemon=True).start()

    # ─── Build ───────────────────────────────────────────────────────────────
    def _build(self):
        weather   = self._weather_card()
        alerts    = self._alerts_panel()
        suggest   = self._suggestions_panel()
        chatbot   = self._chatbot_panel()

        self.controls = [
            ft.Container(
                content=ft.Column([
                    # Title
                    ft.Text("Tiện Ích Trang Trại", size=SIZE_H1,
                            weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
                    ft.Text("Thời tiết · Thông báo · Gợi ý · Trợ lý AI",
                            size=SIZE_CAPTION, color=TEXT_SUB),
                    ft.Container(height=16),

                    # Row 1: Weather + Alerts
                    ft.Row([
                        ft.Container(content=weather, expand=True),
                        ft.Container(width=12),
                        ft.Container(content=alerts, width=360),
                    ], vertical_alignment=ft.CrossAxisAlignment.START),

                    ft.Container(height=14),

                    # Row 2: Suggestions + Chatbot
                    ft.Row([
                        ft.Container(content=suggest, width=380),
                        ft.Container(width=12),
                        chatbot,
                    ], vertical_alignment=ft.CrossAxisAlignment.START, expand=True),

                    ft.Container(height=20),
                ], spacing=0),
                padding=ft.padding.symmetric(horizontal=4, vertical=4),
            )
        ]