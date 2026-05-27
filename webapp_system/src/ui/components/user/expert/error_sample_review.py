from __future__ import annotations

import flet as ft

from bll.user.expert.error_sample_service import (
    STATUS_OPEN,
    STATUS_RELABEL,
    STATUS_RESOLVED,
    STATUS_REVIEWING,
    get_error_sample_summary,
    list_error_samples,
    mark_error_sample_status,
    remove_error_sample,
)
from ui.theme import DANGER, PRIMARY, SECONDARY, WARNING

_STATUS_META = {
    STATUS_OPEN: ("Mới", WARNING, ft.Icons.ERROR_OUTLINE),
    STATUS_REVIEWING: ("Đang xem", PRIMARY, ft.Icons.RATE_REVIEW),
    STATUS_RELABEL: ("Cần gán nhãn lại", DANGER, ft.Icons.LABEL_IMPORTANT_OUTLINE),
    STATUS_RESOLVED: ("Đã xử lý", SECONDARY, ft.Icons.TASK_ALT),
}


def _status_chip(status: str) -> ft.Control:
    label, color, icon = _STATUS_META.get(status, _STATUS_META[STATUS_OPEN])
    return ft.Container(
        padding=ft.padding.symmetric(horizontal=10, vertical=5),
        border_radius=999,
        bgcolor=ft.Colors.with_opacity(0.16, color),
        border=ft.border.all(1, ft.Colors.with_opacity(0.35, color)),
        content=ft.Row(
            tight=True,
            spacing=5,
            controls=[
                ft.Icon(icon, size=12, color=color),
                ft.Text(label, size=10, color=color, weight=ft.FontWeight.W_700),
            ],
        ),
    )


def build_error_sample_review(page: ft.Page | None = None):
    expert_id = int((page.client_storage.get("user_id") or 0) if page else 0)
    rows_ref = ft.Ref[ft.Column]()
    filter_dd = ft.Ref[ft.Dropdown]()
    summary_ref = ft.Ref[ft.Row]()

    def _open_dialog(dialog: ft.AlertDialog):
        if page:
            try:
                page.open(dialog)
                return
            except Exception:
                pass
        dialog.open = True
        if page:
            page.dialog = dialog
            page.update()

    def _close_dialog(dialog: ft.AlertDialog):
        if page:
            try:
                page.close(dialog)
                return
            except Exception:
                pass
        dialog.open = False
        if page:
            page.update()

    def _summary_cards() -> list[ft.Control]:
        data = get_error_sample_summary()
        defs = [
            ("Tổng", data["total"], ft.Icons.DATA_OBJECT, ft.Colors.BLUE_300),
            ("Mới", data[STATUS_OPEN], ft.Icons.ERROR_OUTLINE, WARNING),
            ("Đang xem", data[STATUS_REVIEWING], ft.Icons.RATE_REVIEW, PRIMARY),
            ("Gán nhãn", data[STATUS_RELABEL], ft.Icons.LABEL_IMPORTANT_OUTLINE, DANGER),
            ("Hoàn tất", data[STATUS_RESOLVED], ft.Icons.TASK_ALT, SECONDARY),
        ]
        cards: list[ft.Control] = []
        for label, value, icon, color in defs:
            cards.append(
                ft.Container(
                    expand=1,
                    padding=14,
                    border_radius=16,
                    bgcolor=ft.Colors.with_opacity(0.08, ft.Colors.WHITE),
                    border=ft.border.all(1, ft.Colors.with_opacity(0.10, ft.Colors.WHITE)),
                    content=ft.Row(
                        spacing=10,
                        controls=[
                            ft.Container(
                                width=38,
                                height=38,
                                border_radius=12,
                                bgcolor=ft.Colors.with_opacity(0.18, color),
                                alignment=ft.alignment.center,
                                content=ft.Icon(icon, size=18, color=color),
                            ),
                            ft.Column(
                                tight=True,
                                spacing=2,
                                controls=[
                                    ft.Text(label, size=11, color=ft.Colors.WHITE60),
                                    ft.Text(str(value), size=18, weight=ft.FontWeight.W_700),
                                ],
                            ),
                        ],
                    ),
                )
            )
        return cards

    def _show_detail(row: dict):
        if row.get("image_b64"):
            image_ctrl = ft.Image(
                src_base64=row["image_b64"],
                width=360,
                height=280,
                fit=ft.ImageFit.CONTAIN,
                border_radius=12,
            )
        elif row.get("image_path"):
            image_ctrl = ft.Image(
                src=row["image_path"],
                width=360,
                height=280,
                fit=ft.ImageFit.CONTAIN,
                border_radius=12,
            )
        else:
            image_ctrl = ft.Container(
                width=360,
                height=220,
                border_radius=12,
                bgcolor=ft.Colors.with_opacity(0.08, ft.Colors.WHITE),
                alignment=ft.alignment.center,
                content=ft.Text("Không có ảnh", color=ft.Colors.WHITE54),
            )

        ai_result = row.get("ai_result") or {}
        diagnosis = ai_result.get("diagnosis") or {}
        detected = diagnosis.get("detected") or []
        detected_text = ", ".join(d.get("class", "?") for d in detected[:5]) if detected else "Không có"

        dlg = ft.AlertDialog(
            modal=True,
            bgcolor=ft.Colors.with_opacity(0.98, ft.Colors.GREY_900),
            title=ft.Text("Chi tiết mẫu lỗi", weight=ft.FontWeight.W_700),
            content=ft.Container(
                width=520,
                content=ft.Column(
                    scroll=ft.ScrollMode.AUTO,
                    spacing=10,
                    controls=[
                        image_ctrl,
                        _status_chip(row.get("status", STATUS_OPEN)),
                        ft.Text(f"Model: {row.get('model_name', '-')}", size=12),
                        ft.Text(f"Loại model: {row.get('model_type', '-')}", size=12, color=ft.Colors.WHITE70),
                        ft.Text(f"Người gửi: {row.get('farmer_name', '-')}", size=12, color=ft.Colors.WHITE70),
                        ft.Text(f"Nhãn dự đoán: {row.get('predicted_label', '-')}", size=12, color=ft.Colors.WHITE70),
                        ft.Text(f"Dự đoán bệnh: {detected_text}", size=12, color=ft.Colors.WHITE70),
                        ft.Text(f"Ghi chú farmer: {row.get('note', '') or '-'}", size=12),
                        ft.Text(f"Ghi chú expert: {row.get('review_comment', '') or '-'}", size=12),
                    ],
                ),
            ),
            actions=[ft.TextButton("Đóng", on_click=lambda e: _close_dialog(dlg))],
        )
        _open_dialog(dlg)

    def _open_status_dialog(row: dict, status: str):
        note_tf = ft.TextField(
            label="Ghi chú xử lý",
            value=row.get("review_comment", "") or "",
            multiline=True,
            min_lines=3,
            max_lines=5,
            border_radius=12,
        )
        label = _STATUS_META.get(status, _STATUS_META[STATUS_OPEN])[0]

        def _save(_):
            mark_error_sample_status(
                row["id_error_sample"],
                status,
                expert_id=expert_id or None,
                review_comment=note_tf.value or "",
            )
            _close_dialog(dlg)
            refresh()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Cập nhật trạng thái: {label}"),
            content=ft.Container(width=420, content=note_tf),
            actions=[
                ft.TextButton("Hủy", on_click=lambda e: _close_dialog(dlg)),
                ft.ElevatedButton("Lưu", on_click=_save),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        _open_dialog(dlg)

    def _build_row(row: dict) -> ft.Control:
        predicted = row.get("predicted_label", "") or "-"
        model_name = row.get("model_name", "") or "AI Model"
        confidence = row.get("confidence")
        conf_text = f"{float(confidence):.2f}" if isinstance(confidence, (int, float)) else "-"
        if row.get("image_b64"):
            thumb = ft.Image(src_base64=row["image_b64"], width=92, height=72, fit=ft.ImageFit.COVER, border_radius=10)
        elif row.get("image_path"):
            thumb = ft.Image(src=row["image_path"], width=92, height=72, fit=ft.ImageFit.COVER, border_radius=10)
        else:
            thumb = ft.Container(width=92, height=72, border_radius=10, bgcolor=ft.Colors.with_opacity(0.08, ft.Colors.WHITE))

        return ft.Container(
            padding=12,
            border_radius=16,
            bgcolor=ft.Colors.with_opacity(0.06, ft.Colors.WHITE),
            border=ft.border.all(1, ft.Colors.with_opacity(0.08, ft.Colors.WHITE)),
            content=ft.Column(
                spacing=8,
                controls=[
                    ft.Row(
                        vertical_alignment=ft.CrossAxisAlignment.START,
                        controls=[
                            thumb,
                            ft.Column(
                                expand=True,
                                spacing=4,
                                controls=[
                                    ft.Row(
                                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                        controls=[
                                            ft.Text(model_name, size=14, weight=ft.FontWeight.W_700, expand=True),
                                            _status_chip(row.get("status", STATUS_OPEN)),
                                        ],
                                    ),
                                    ft.Text(f"Nhãn dự đoán: {predicted}", size=12, color=ft.Colors.WHITE70),
                                    ft.Text(f"Độ tin cậy: {conf_text}", size=12, color=ft.Colors.WHITE54),
                                    ft.Text(f"Ghi chú: {row.get('note', '') or '-'}", size=11, color=ft.Colors.WHITE54, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                                ],
                            ),
                        ],
                    ),
                    ft.Row(
                        wrap=True,
                        spacing=8,
                        run_spacing=8,
                        controls=[
                            ft.OutlinedButton("Xem chi tiết", icon=ft.Icons.VISIBILITY, on_click=lambda e: _show_detail(row)),
                            ft.ElevatedButton("Đang xem", icon=ft.Icons.RATE_REVIEW, on_click=lambda e: _open_status_dialog(row, STATUS_REVIEWING)),
                            ft.ElevatedButton("Cần gán nhãn lại", icon=ft.Icons.LABEL_IMPORTANT_OUTLINE, on_click=lambda e: _open_status_dialog(row, STATUS_RELABEL)),
                            ft.ElevatedButton("Hoàn tất", icon=ft.Icons.TASK_ALT, on_click=lambda e: _open_status_dialog(row, STATUS_RESOLVED)),
                            ft.TextButton("Xóa", icon=ft.Icons.DELETE_OUTLINE, on_click=lambda e: (remove_error_sample(row["id_error_sample"]), refresh())),
                        ],
                    ),
                ],
            ),
        )

    def refresh():
        status = filter_dd.current.value if filter_dd.current else "all"
        rows = list_error_samples(None if status == "all" else status)
        rows_ref.current.controls = [_build_row(row) for row in rows] or [
            ft.Container(
                padding=24,
                border_radius=18,
                bgcolor=ft.Colors.with_opacity(0.06, ft.Colors.WHITE),
                content=ft.Text("Chưa có mẫu lỗi nào.", color=ft.Colors.WHITE54),
            )
        ]
        summary_ref.current.controls = _summary_cards()
        if page:
            page.update()

    root = ft.Column(
        expand=True,
        spacing=14,
        scroll=ft.ScrollMode.AUTO,
        controls=[
            ft.Column(
                spacing=2,
                controls=[
                    ft.Text("Mẫu lỗi AI", size=20, weight=ft.FontWeight.W_700),
                    ft.Text("Quản lý ảnh AI nhận sai hoặc cần gán nhãn lại.", size=12, color=ft.Colors.WHITE60),
                ],
            ),
            ft.Row(ref=summary_ref, spacing=10, wrap=True, controls=[]),
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Dropdown(
                        ref=filter_dd,
                        label="Lọc trạng thái",
                        width=220,
                        value="all",
                        options=[
                            ft.dropdown.Option("all", "Tất cả"),
                            ft.dropdown.Option(STATUS_OPEN, "Mới"),
                            ft.dropdown.Option(STATUS_REVIEWING, "Đang xem"),
                            ft.dropdown.Option(STATUS_RELABEL, "Cần gán nhãn lại"),
                            ft.dropdown.Option(STATUS_RESOLVED, "Hoàn tất"),
                        ],
                        on_change=lambda e: refresh(),
                    ),
                    ft.IconButton(icon=ft.Icons.REFRESH, tooltip="Làm mới", on_click=lambda e: refresh()),
                ],
            ),
            ft.Column(ref=rows_ref, spacing=10, controls=[]),
        ],
    )
    refresh()
    return root
