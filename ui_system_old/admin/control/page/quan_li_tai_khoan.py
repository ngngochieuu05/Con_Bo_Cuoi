"""
Quản Lý Tài Khoản (Khách Hàng) — Admin
Quản Lý Tài Khoản — Con Bò Cười Dark Theme
"""
import flet as ft
import json
import os
from datetime import datetime

from src.ui.theme import (
    BG_MAIN, BG_PANEL, PRIMARY, SECONDARY, ACCENT,
    TEXT_MAIN, TEXT_SUB, TEXT_MUTED,
    WARNING, DANGER, SUCCESS, BORDER,
    RADIUS_CARD, RADIUS_BTN, RADIUS_INPUT, RADIUS_BADGE,
    SIZE_H1, SIZE_H2, SIZE_H3, SIZE_BODY, SIZE_CAPTION,
    PAD_CARD, SHADOW_CARD, SHADOW_CARD_GLOW,
    kpi_card, panel, primary_button, status_badge,
    divider, avatar_initials, styled_input, section_label,
    GRAD_TEAL, GRAD_WARN, GRAD_DANGER, GRAD_PURPLE,
)

JSON_FILE = "src/ui/data/accounts.json"


class QuanLiTaiKhoan(ft.Column):
    """Trang Quản Lý Tài Khoản Khách Hàng — Admin."""

    def __init__(self):
        super().__init__(expand=True, scroll=ft.ScrollMode.AUTO, spacing=0)
        self.accounts   = []
        self.filtered   = []
        self.search_val = ""
        self.filter_val = "Tất cả"
        self._edit_mode = False
        self._edit_id   = None

        self._load_accounts()
        
        # FilePicker for selecting .pt models
        self.model_picker = ft.FilePicker(on_result=self._on_model_picked)
        self.quick_model_picker = ft.FilePicker(on_result=self._on_quick_model_picked)

        # Quick Cattle Model Dialog
        self._f_quick_model = ft.Dropdown(
            label="Chọn Model Cattle",
            bgcolor=BG_PANEL,
            border_color=BORDER,
            focused_border_color=PRIMARY,
            text_style=ft.TextStyle(color=TEXT_MAIN, size=SIZE_BODY),
            width=300,
        )
        self._f_quick_conf = ft.Slider(min=0.1, max=1.0, divisions=90, value=0.25)
        self._f_quick_iou = ft.Slider(min=0.1, max=1.0, divisions=90, value=0.45)
        self._quick_conf_text = ft.Text("0.25", weight="bold", color=PRIMARY)
        self._quick_iou_text = ft.Text("0.45", weight="bold", color=PRIMARY)

        def _on_quick_conf_change(e):
            self._quick_conf_text.value = f"{e.control.value:.2f}"
            self._quick_conf_text.update()

        def _on_quick_iou_change(e):
            self._quick_iou_text.value = f"{e.control.value:.2f}"
            self._quick_iou_text.update()

        self._f_quick_conf.on_change = _on_quick_conf_change
        self._f_quick_iou.on_change = _on_quick_iou_change

        self._current_quick_acc = None
        self._cattle_dialog = ft.AlertDialog(
            title=ft.Text("Tùy chỉnh Model Cattle", weight=ft.FontWeight.BOLD),
            content=ft.Column([
                ft.Text("Chọn model nhận diện bò cho tài khoản này:", size=SIZE_BODY),
                ft.Row([
                    self._f_quick_model,
                    ft.IconButton(ft.Icons.FOLDER_OPEN, on_click=lambda _: self.quick_model_picker.pick_files(allowed_extensions=["pt"]))
                ], spacing=10),
                ft.Container(height=10),
                ft.Row([ft.Text("Ngưỡng tin cậy: "), self._quick_conf_text]),
                self._f_quick_conf,
                ft.Row([ft.Text("Ngưỡng IOU: "), self._quick_iou_text]),
                self._f_quick_iou,
            ], tight=True, spacing=10, width=450),
            actions=[
                ft.TextButton("Hủy", on_click=lambda _: self._close_cattle_dialog()),
                ft.ElevatedButton("Lưu Thay Đổi", bgcolor=PRIMARY, color=ft.Colors.WHITE, on_click=self._save_quick_model),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        self._build()

    def did_mount(self):
        self.page.overlay.append(self.model_picker)
        self.page.overlay.append(self.quick_model_picker)
        self.page.overlay.append(self._cattle_dialog)
        self.page.update()

    def _on_model_picked(self, e: ft.FilePickerResultEvent):
        if e.files and len(e.files) > 0:
            file_path = e.files[0].path
            file_name = e.files[0].name
            # Copy to models/ if not exists
            if not os.path.exists("models"):
                os.makedirs("models")
            
            # Simple check if already in list
            exists = False
            for opt in self._f_model.options:
                if opt.key == file_name:
                    exists = True
                    break
            
            if not exists:
                self._f_model.options.append(ft.dropdown.Option(file_name))
            
            self._f_model.value = file_name
            self._f_model.update()

    def _on_quick_model_picked(self, e: ft.FilePickerResultEvent):
        if e.files and len(e.files) > 0:
            file_name = e.files[0].name
            exists = False
            for opt in self._f_quick_model.options:
                if opt.key == file_name:
                    exists = True
                    break
            if not exists:
                self._f_quick_model.options.append(ft.dropdown.Option(file_name))
            
            self._f_quick_model.value = file_name
            self._f_quick_model.update()

    def _open_cattle_dialog(self, e):
        acc = e.control.data
        self._current_quick_acc = acc
        
        # Refresh model list
        model_options = [ft.dropdown.Option("yolov8n.pt")]
        if os.path.exists("models"):
            for f in os.listdir("models"):
                if f.endswith(".pt") and f != "yolov8n.pt":
                    model_options.append(ft.dropdown.Option(f))
        
        self._f_quick_model.options = model_options
        self._f_quick_model.value = acc.get("model", "yolov8n.pt")
        
        self._f_quick_conf.value = acc.get("confidence", 0.25)
        self._f_quick_iou.value = acc.get("iou", 0.45)
        self._quick_conf_text.value = f"{self._f_quick_conf.value:.2f}"
        self._quick_iou_text.value = f"{self._f_quick_iou.value:.2f}"
        
        self.page.open(self._cattle_dialog)

    def _close_cattle_dialog(self):
        self.page.close(self._cattle_dialog)

    def _save_quick_model(self, e):
        if not self._current_quick_acc: return
        
        new_model = self._f_quick_model.value
        conf = self._f_quick_conf.value
        iou = self._f_quick_iou.value
        acc_id = self._current_quick_acc["id"]
        
        # Update in accounts list
        for a in self.accounts:
            if a["id"] == acc_id:
                a["model"] = new_model
                a["confidence"] = conf
                a["iou"] = iou
                break
        
        self._save_to_json()
        self._apply_filter()
        self._close_cattle_dialog()
        self.page.open(ft.SnackBar(ft.Text(f"✅ Đã cập nhật model cho {self._current_quick_acc['name']}"), bgcolor=SUCCESS))


    # ────────────────────────────────────────────────────────────────────────
    def _load_accounts(self):
        self.accounts = []
        if os.path.exists(JSON_FILE):
            try:
                with open(JSON_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                arr = data.get("user_accounts", [])
                for u in arr:
                    self.accounts.append({
                        "username": u.get("username", ""),
                        "id":      u.get("driver_id", u.get("username", "")),
                        "name":    u.get("name", ""),
                        "phone":   u.get("phone", ""),
                        "email":   u.get("email", ""),
                        "farms":   u.get("farms", 1),
                        "model":   u.get("model", "yolov8n.pt"),
                        "confidence": u.get("confidence", 0.25),
                        "iou":      u.get("iou", 0.45),
                        "status":  u.get("status", "Active"),
                        "created": u.get("created_at", datetime.now().strftime("%d/%m/%Y")),
                        "original": u # Keep original data like face_data
                    })
                self.filtered = list(self.accounts)
                return
            except Exception as e:
                print(f"Error loading accounts: {e}")

        # Fallback sample
        self.accounts = [
            {"username": "user01", "id": "TX001", "name": "Nguyễn Văn An", "phone": "0901234567",
             "email": "an@farm.vn", "farms": 3, "model": "yolov8n.pt", "status": "Active", "created": "01/03/2026"}
        ]
        self.filtered = self.accounts[:]

    # ────────────────────────────────────────────────────────────────────────
    def _build(self):
        total   = len(self.accounts)
        active  = sum(1 for a in self.accounts if a["status"] == "Active")
        inactive = total - active

        # ── KPI ──────────────────────────────────────────────────────────────
        kpi_row = ft.Row([
            kpi_card(ft.Icons.PEOPLE_ALT_ROUNDED,
                     "Tổng Tài Khoản", str(total),
                     "Khách hàng đã đăng ký",
                     grad_colors=GRAD_TEAL),
            kpi_card(ft.Icons.CHECK_CIRCLE_ROUNDED,
                     "Đang Hoạt Động", str(active),
                     "Tài khoản Active",
                     grad_colors=["#00C897", "#009E7A"]),
            kpi_card(ft.Icons.PAUSE_CIRCLE_ROUNDED,
                     "Tạm Dừng", str(inactive),
                     "Tài khoản Inactive",
                     grad_colors=GRAD_WARN),
        ], spacing=14)

        # ── Search + Filter toolbar ──────────────────────────────────────────
        self.search_field = ft.TextField(
            hint_text="🔍  Tìm theo tên / SĐT / email...",
            border_radius=10,
            border_color=BORDER,
            focused_border_color=PRIMARY,
            cursor_color=PRIMARY,
            text_style=ft.TextStyle(color=TEXT_MAIN, size=SIZE_BODY),
            hint_style=ft.TextStyle(color=TEXT_MUTED, size=SIZE_BODY),
            bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.WHITE),
            content_padding=ft.padding.symmetric(horizontal=14, vertical=10),
            expand=True,
            on_change=self._on_search,
        )

        self.filter_dd = ft.Dropdown(
            options=[
                ft.dropdown.Option("Tất cả"),
                ft.dropdown.Option("Active"),
                ft.dropdown.Option("Inactive"),
            ],
            value="Tất cả",
            border_radius=10,
            border_color=BORDER,
            focused_border_color=PRIMARY,
            text_style=ft.TextStyle(color=TEXT_MAIN, size=SIZE_BODY),
            width=160,
            bgcolor=BG_PANEL,
            on_change=self._on_filter,
        )

        toolbar = ft.Row([
            self.search_field,
            ft.Container(width=10),
            self.filter_dd,
            ft.Container(width=10),
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.FILTER_LIST_ROUNDED, color=TEXT_SUB, size=16),
                    ft.Text("Reset", size=SIZE_BODY, color=TEXT_SUB),
                ], spacing=6),
                padding=ft.padding.symmetric(horizontal=14, vertical=10),
                border_radius=10,
                border=ft.border.all(1, BORDER),
                ink=True,
                on_click=self._reset_filter,
            ),
            ft.Container(expand=True),
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.PERSON_ADD_ROUNDED, color=ft.Colors.WHITE, size=16),
                    ft.Text("Thêm Tài Khoản", color=ft.Colors.WHITE,
                            size=SIZE_BODY, weight=ft.FontWeight.W_600),
                ], spacing=8),
                bgcolor=PRIMARY,
                border_radius=RADIUS_BTN,
                padding=ft.padding.symmetric(horizontal=16, vertical=10),
                ink=True,
                on_click=self._open_add_modal,
                animate_scale=ft.Animation(120, ft.AnimationCurve.EASE_OUT),
            ),
        ], spacing=0, vertical_alignment=ft.CrossAxisAlignment.CENTER)

        # ── Table header ────────────────────────────────────────────────────
        def _th(text, w=None, expand=False):
            return ft.Container(
                content=ft.Text(text, size=10, color=TEXT_SUB,
                                weight=ft.FontWeight.BOLD),
                width=w, expand=expand,
            )

        table_header = ft.Container(
            content=ft.Row([
                _th("#", w=30),
                _th("Khách Hàng", expand=True),
                _th("Liên Hệ", w=160),
                _th("Trang Trại", w=90),
                _th("Model", w=90),
                _th("Trạng Thái", w=100),
                _th("Ngày Tạo", w=95),
                _th("Hành Động", w=110),
            ], spacing=10),
            bgcolor=ft.Colors.with_opacity(0.04, ft.Colors.WHITE),
            border_radius=ft.BorderRadius(8, 8, 0, 0),
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
            border=ft.border.all(1, BORDER),
        )

        # ── Table rows ──────────────────────────────────────────────────────
        self.table_col = ft.Column(spacing=2)
        self._rebuild_rows()

        self.table_content = ft.Column([
            table_header,
            self.table_col,
        ], spacing=0)

        table_panel = ft.Container(
            content=ft.Column([
                self.table_content,
            ], spacing=0),
            bgcolor=BG_PANEL,
            border_radius=RADIUS_CARD,
            border=ft.border.all(1, BORDER),
            shadow=SHADOW_CARD_GLOW,
        )

        # ── Modal add/edit ───────────────────────────────────────────────────
        self._modal = self._build_modal()

        # ── Layout ──────────────────────────────────────────────────────────
        self.controls = [
            ft.Container(
                content=ft.Column([
                    # Title
                    ft.Row([
                        ft.Column([
                            ft.Text("Quản Lý Tài Khoản",
                                    size=SIZE_H1, weight=ft.FontWeight.BOLD,
                                    color=TEXT_MAIN),
                            ft.Text("Thêm, chỉnh sửa và quản lý tài khoản khách hàng sử dụng hệ thống",
                                    size=SIZE_CAPTION, color=TEXT_SUB),
                        ], spacing=2),
                    ]),
                    ft.Container(height=16),
                    kpi_row,
                    ft.Container(height=16),
                    toolbar,
                    ft.Container(height=12),
                    table_panel,
                    ft.Container(height=20),
                    self._modal,
                ], spacing=0),
                padding=ft.padding.symmetric(horizontal=4, vertical=4),
            )
        ]

    # ────────────────────────────────────────────────────────────────────────
    def _account_row(self, idx: int, acc: dict) -> ft.Container:
        status_color = PRIMARY if acc["status"] == "Active" else TEXT_MUTED

        return ft.Container(
            content=ft.Row([
                ft.Text(str(idx), size=10, color=TEXT_MUTED, width=30),
                # Avatar + tên + email
                ft.Row([
                    ft.Container(
                        content=ft.Text(acc["name"][0].upper(),
                                        color=ft.Colors.WHITE, size=11,
                                        weight=ft.FontWeight.BOLD),
                        width=32, height=32, border_radius=16,
                        bgcolor=PRIMARY, alignment=ft.alignment.center,
                    ),
                    ft.Column([
                        ft.Text(acc["name"], size=SIZE_BODY, color=TEXT_MAIN,
                                weight=ft.FontWeight.W_500),
                        ft.Text(acc["email"], size=10, color=TEXT_SUB),
                    ], spacing=1),
                ], spacing=10, expand=True),
                # Liên hệ
                ft.Column([
                    ft.Text(acc["phone"], size=SIZE_BODY, color=TEXT_MAIN),
                    ft.Text(acc["id"], size=10, color=TEXT_MUTED),
                ], spacing=1, width=160),
                # Farms
                ft.Text(f"{acc['farms']} trang trại", size=SIZE_BODY,
                        color=TEXT_SUB, width=90),
                # Model tag
                ft.Container(
                    content=ft.Text(acc["model"], size=9,
                                    color=PRIMARY, weight=ft.FontWeight.BOLD),
                    border=ft.border.all(1, PRIMARY),
                    border_radius=6,
                    padding=ft.padding.symmetric(horizontal=8, vertical=3),
                    width=90,
                ),
                # Status badge
                ft.Container(
                    content=ft.Row([
                        ft.Container(
                            width=6, height=6, border_radius=3,
                            bgcolor=status_color,
                        ),
                        ft.Text(acc["status"], size=10,
                                color=status_color, weight=ft.FontWeight.W_500),
                    ], spacing=5),
                    width=100,
                ),
                # Date
                ft.Text(acc["created"], size=10, color=TEXT_MUTED, width=95),
                # Actions
                ft.Row([
                    ft.IconButton(
                        ft.Icons.VISIBILITY_ROUNDED,
                        icon_color=ACCENT, icon_size=16,
                        tooltip="Tùy chọn Model Cattle",
                        data=acc,
                        on_click=self._open_cattle_dialog,
                    ),
                    ft.IconButton(
                        ft.Icons.EDIT_ROUNDED,
                        icon_color=WARNING, icon_size=16,
                        tooltip="Chỉnh sửa",
                        data=acc,
                        on_click=self._open_edit_modal,
                    ),
                    ft.IconButton(
                        ft.Icons.DELETE_ROUNDED,
                        icon_color=DANGER, icon_size=16,
                        tooltip="Xóa",
                        data=acc["id"],
                        on_click=self._confirm_delete,
                    ),
                ], spacing=0, width=110),
            ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=ft.Colors.with_opacity(0.02, ft.Colors.WHITE),
            border=ft.border.all(1, ft.Colors.with_opacity(0.04, ft.Colors.WHITE)),
            border_radius=0,
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
            animate_opacity=ft.Animation(150, ft.AnimationCurve.EASE_IN),
        )

    def _rebuild_rows(self):
        self.table_col.controls.clear()
        for i, acc in enumerate(self.filtered, 1):
            self.table_col.controls.append(self._account_row(i, acc))
            if i < len(self.filtered):
                self.table_col.controls.append(
                    ft.Divider(color=BORDER, height=1)
                )
        try:
            self.table_col.update()
        except Exception:
            pass

    # ────────────────────────────────────────────────────────────────────────
    def _on_search(self, e):
        self.search_val = e.control.value.strip().lower()
        self._apply_filter()

    def _on_filter(self, e):
        self.filter_val = e.control.value
        self._apply_filter()

    def _reset_filter(self, e):
        self.search_val = ""
        self.filter_val = "Tất cả"
        self.search_field.value = ""
        self.filter_dd.value = "Tất cả"
        self.filtered = list(self.accounts)
        try:
            self.search_field.update()
            self.filter_dd.update()
        except Exception:
            pass
        self._rebuild_rows()

    def _apply_filter(self):
        result = self.accounts
        if self.search_val:
            result = [
                a for a in result
                if self.search_val in a["name"].lower()
                or self.search_val in a["phone"]
                or self.search_val in a["email"].lower()
            ]
        if self.filter_val != "Tất cả":
            result = [a for a in result if a["status"] == self.filter_val]
        self.filtered = result
        self._rebuild_rows()

    # ────────────────────────────────────────────────────────────────────────
    def _build_modal(self) -> ft.Container:
        """Panel thêm/sửa tài khoản — hiển thị dưới bảng."""
        self._f_username = styled_input("Tên đăng nhập *", "user01")
        self._f_id       = styled_input("ID Nhân viên *", "TX001")
        self._f_name     = styled_input("Họ và tên *", "Nguyễn Văn A", expand=True)
        self._f_phone    = styled_input("Số điện thoại *", "090xxxxxxx")
        self._f_email    = styled_input("Email *", "example@farm.vn", expand=True)
        self._f_pass     = styled_input("Mật khẩu *", "Tối thiểu 8 ký tự",
                                       password=True)
        
        # Scan models directory for options
        model_options = [ft.dropdown.Option("yolov8n.pt")]
        if os.path.exists("models"):
            for f in os.listdir("models"):
                if f.endswith(".pt") and f != "yolov8n.pt":
                    model_options.append(ft.dropdown.Option(f))

        self._f_model  = ft.Dropdown(
            label="Model Nhận Diện Bò",
            options=model_options,
            value="yolov8n.pt",
            bgcolor=BG_PANEL,
            border_color=BORDER,
            focused_border_color=PRIMARY,
            text_style=ft.TextStyle(color=TEXT_MAIN, size=SIZE_BODY),
            width=200,
        )
        
        self._btn_add_model = ft.IconButton(
            icon=ft.Icons.FOLDER_OPEN,
            icon_color=ft.Colors.WHITE,
            bgcolor=PRIMARY,
            tooltip="Chọn Model .pt từ máy tính",
            on_click=lambda _: self.model_picker.pick_files(
                allowed_extensions=["pt"], 
                dialog_title="Chọn model .pt"
            )
        )
        
        self._model_row = ft.Row([self._f_model, self._btn_add_model], spacing=8)
        
        self._f_status = ft.Dropdown(
            label="Trạng thái",
            options=[
                ft.dropdown.Option("Active"),
                ft.dropdown.Option("Inactive"),
            ],
            value="Active",
            bgcolor=BG_PANEL,
            border_color=BORDER,
            focused_border_color=PRIMARY,
            text_style=ft.TextStyle(color=TEXT_MAIN, size=SIZE_BODY),
            width=160,
        )
        self._save_status = ft.Text("", size=SIZE_CAPTION, color=SUCCESS)

        form = ft.Column([
            ft.Row([self._f_username, ft.Container(width=12), self._f_id, ft.Container(width=12), self._f_name], spacing=0),
            ft.Container(height=10),
            ft.Row([self._f_phone, ft.Container(width=12), self._f_email], spacing=0),
            ft.Container(height=10),
            ft.Row([self._f_pass, ft.Container(width=12), self._f_model, ft.Container(width=12), self._f_status], spacing=0),
            ft.Container(height=10),
            ft.Row([self._btn_add_model, ft.Text("Chọn model .pt khác", size=12, color=TEXT_SUB)], spacing=8),
            ft.Container(height=16),
            ft.Row([
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.SAVE_ROUNDED, color=ft.Colors.WHITE, size=16),
                        ft.Text("Lưu Tài Khoản", color=ft.Colors.WHITE,
                                size=SIZE_BODY, weight=ft.FontWeight.W_600),
                    ], spacing=8),
                    bgcolor=PRIMARY, border_radius=RADIUS_BTN,
                    padding=ft.padding.symmetric(horizontal=18, vertical=10),
                    ink=True, on_click=self._save_account,
                ),
                ft.Container(width=12),
                self._save_status,
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ], spacing=0)

        self._form_panel = panel(
            content=form,
            title="Thêm Tài Khoản Mới",
            icon=ft.Icons.PERSON_ADD_ROUNDED,
        )
        self._form_panel.visible = False
        return self._form_panel

    def _open_add_modal(self, e):
        self._edit_mode = False
        self._edit_id = None
        self._form_panel.title_text.value = "Thêm Tài Khoản Mới"
        self._f_username.value = ""
        self._f_id.value = ""
        self._f_name.value = ""
        self._f_phone.value = ""
        self._f_email.value = ""
        self._f_pass.value = ""
        self._save_status.value = ""
        self._form_panel.visible = True
        try:
            self._form_panel.update()
        except Exception:
            pass

    def _open_edit_modal(self, e):
        acc = e.control.data
        self._edit_mode = True
        self._edit_id = acc["username"]
        self._form_panel.title_text.value = f"Chỉnh Sửa Tài Khoản: {self._edit_id}"
        self._f_username.value = acc["username"]
        self._f_id.value = acc["id"]
        self._f_name.value = acc["name"]
        self._f_phone.value = acc["phone"]
        self._f_email.value = acc["email"]
        self._f_pass.value = acc.get("original", {}).get("password", "********")
        self._f_model.value = acc["model"]
        self._f_status.value = acc["status"]
        self._save_status.value = ""
        self._form_panel.visible = True
        try:
            self._form_panel.update()
        except Exception:
            pass

    def _save_account(self, e):
        username = self._f_username.value.strip()
        driver_id = self._f_id.value.strip()
        name     = self._f_name.value.strip()
        phone    = self._f_phone.value.strip()
        email    = self._f_email.value.strip()

        if not username or not name or not phone or not email:
            self._save_status.value  = "⚠ Vui lòng điền đầy đủ các trường bắt buộc"
            self._save_status.color  = DANGER
            try: self._save_status.update()
            except: pass
            return

        if self._edit_mode:
            # Edit existing
            for acc in self.accounts:
                if acc["username"] == self._edit_id:
                    acc["username"] = username
                    acc["id"] = driver_id
                    acc["name"] = name
                    acc["phone"] = phone
                    acc["email"] = email
                    acc["model"] = self._f_model.value
                    acc["confidence"] = conf if (conf := getattr(self, '_f_quick_conf', None)) else acc.get("confidence", 0.25)
                    acc["iou"] = iou if (iou := getattr(self, '_f_quick_iou', None)) else acc.get("iou", 0.45)
                    acc["status"] = self._f_status.value
                    # Update password in original if changed from placeholder
                    if self._f_pass.value != "********":
                        acc.setdefault("original", {})["password"] = self._f_pass.value
                    break
            msg = f"✅ Đã cập nhật tài khoản {name}"
        else:
            # Add new
            new_acc = {
                "username": username,
                "id":      driver_id or username,
                "name":    name,
                "phone":   phone,
                "email":   email,
                "farms":   1,
                "model":   self._f_model.value or "yolov8n.pt",
                "confidence": 0.25,
                "iou": 0.45,
                "status":  self._f_status.value or "Active",
                "created": datetime.now().strftime("%d/%m/%Y"),
                "original": {"password": self._f_pass.value or "123456"}
            }
            self.accounts.append(new_acc)
            msg = f"✅ Đã thêm tài khoản {name}"

        self._save_to_json()
        self._apply_filter()

        self._save_status.value = msg
        self._save_status.color = SUCCESS
        if not self._edit_mode:
            for ctrl in [self._f_username, self._f_id, self._f_name, self._f_phone, self._f_email, self._f_pass]:
                ctrl.value = ""
        
        try:
            self._save_status.update()
            if not self._edit_mode:
                for ctrl in [self._f_username, self._f_id, self._f_name, self._f_phone, self._f_email, self._f_pass]:
                    ctrl.update()
        except Exception:
            pass

    def _save_to_json(self):
        """Lưu danh sách accounts xuống file JSON để persist."""
        try:
            # Load current data to preserve admin_accounts and other keys
            current_data = {"admin_accounts": [], "user_accounts": []}
            if os.path.exists(JSON_FILE):
                with open(JSON_FILE, "r", encoding="utf-8") as f:
                    current_data = json.load(f)

            new_user_accounts = []
            for acc in self.accounts:
                # Build user object starting with original to preserve face_data etc.
                user_obj = dict(acc.get("original", {}))
                user_obj.update({
                    "username": acc["username"],
                    "driver_id": acc["id"],
                    "name": acc["name"],
                    "phone": acc["phone"],
                    "email": acc["email"],
                    "farms": acc["farms"],
                    "model": acc["model"],
                    "confidence": acc.get("confidence", 0.25),
                    "iou": acc.get("iou", 0.45),
                    "status": acc["status"],
                    "created_at": acc["created"]
                })
                new_user_accounts.append(user_obj)
            
            current_data["user_accounts"] = new_user_accounts
            
            os.makedirs(os.path.dirname(JSON_FILE), exist_ok=True)
            with open(JSON_FILE, "w", encoding="utf-8") as f:
                json.dump(current_data, f, ensure_ascii=False, indent=2)
            print(f"✅ [DATA] Saved {len(self.accounts)} accounts to {JSON_FILE}")
        except Exception as e:
            print(f"❌ [DATA] Error saving JSON: {e}")

    def _confirm_delete(self, e):
        acc_id = e.control.data
        self.accounts = [a for a in self.accounts if a["id"] != acc_id and a["username"] != acc_id]
        self._save_to_json()
        self._apply_filter()
