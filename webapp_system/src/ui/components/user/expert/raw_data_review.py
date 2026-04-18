"""
HITL - Human-in-the-Loop: Chuyen gia gan nhan Polygon cho anh benh bo.
Layout: Canvas (trai) + Panel phan loai (phai) - kieu Roboflow
  - Click trai  : dat diem
  - Click phai  : hoan thanh polygon (>= 3 diem)
  - Moi anh co the chua nhieu annotation
  - Xuat YOLO v8 segmentation (.txt)
"""
from __future__ import annotations

import shutil
from pathlib import Path

import flet as ft
import flet.canvas as cv

from ui.theme import PRIMARY, DANGER, WARNING, SECONDARY, glass_container, button_style

# -- Mau tu dong cap cho class -----------------------------------------------
_COLOR_PALETTE = [
    "#FF6B6B", "#FFD166", "#06D6A0", "#118AB2", "#95E1D3",
    "#A855F7", "#F97316", "#14B8A6", "#EC4899", "#EAB308",
]
_EXPORT_BASE = Path("models/dataset/dataset_v3")

# Kich thuoc canvas hien thi
_UI_W = 340
_UI_H = 255


def build_raw_data_review(page: ft.Page | None = None):  # noqa: C901

    # -- State ----------------------------------------------------------------
    state: dict = {
        # image_files: list of {"name":str, "path":str, "bytes":bytes|None}
        "image_files":   [],
        "current_index": 0,
        "cur_pts":       [],   # normalized (xn,yn) 0..1
        "annotations":   [],   # [{"cls":str, "pts":[(xn,yn)...]}, ...]
        "selected_cls":  None,
        "classes":       [],   # [{"id":str, "label":str, "color":str}, ...]
        "next_id":       0,
        "zoom":          1.0,  # he so zoom: 1.0 / 1.5 / 2.0 / 2.5
        "_pending_uploads":      {},   # {name: bytes|None} — dang upload web
        "_pending_files_order":  [],   # giu thu tu chon
    }

    # -- Canvas ---------------------------------------------------------------
    draw_canvas = cv.Canvas(width=_UI_W, height=_UI_H)

    # -- Controls -------------------------------------------------------------
    img_view = ft.Image(
        src=None, width=_UI_W, height=_UI_H,
        fit=ft.ImageFit.CONTAIN, border_radius=6,
        error_content=ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            tight=True, spacing=4,
            controls=[
                ft.Icon(ft.Icons.BROKEN_IMAGE, size=28, color=ft.Colors.WHITE38),
                ft.Text("Chọn thư mục ảnh", size=10, color=ft.Colors.WHITE38,
                        text_align=ft.TextAlign.CENTER),
            ],
        ),
    )

    img_name_lbl    = ft.Text("-", size=10, color=ft.Colors.WHITE54,
                              max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, expand=True)
    img_counter_lbl = ft.Text("0 / 0", size=10, color=ft.Colors.WHITE54)
    status_msg      = ft.Text("", size=11, color=ft.Colors.GREEN_300)
    image_list_col  = ft.Column(spacing=3, scroll=ft.ScrollMode.AUTO, height=150)
    annotations_col = ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO, height=200)
    yolo_output     = ft.Text("", size=10, color=ft.Colors.GREEN_300,
                              selectable=True, font_family="monospace",
                              max_lines=5, overflow=ft.TextOverflow.ELLIPSIS)

    # -- Helpers --------------------------------------------------------------
    def _safe_update(*_controls):
        # Use the page from outer scope if available (web + desktop)
        if page is not None:
            try:
                page.update()
                return
            except Exception:
                pass
        # Fallback: update each control individually
        for c in _controls:
            try:
                if c.page:
                    c.update()
            except Exception:
                pass

    def _get_cls(cls_id: str) -> tuple[str, str]:
        """Tra ve (label, color) cua class theo id."""
        for c in state["classes"]:
            if c["id"] == cls_id:
                return c["label"], c["color"]
        return cls_id, "#FFFFFF"

    def _cur_w() -> int:
        return int(_UI_W * state["zoom"])

    def _cur_h() -> int:
        return int(_UI_H * state["zoom"])

    def _redraw_canvas():
        draw_canvas.shapes.clear()
        pts_cur = state["cur_pts"]
        cw, ch  = _cur_w(), _cur_h()

        # Ve cac annotation da hoan thanh (fill + outline)
        for ann in state["annotations"]:
            _, color = _get_cls(ann["cls"])
            p = [(xn * cw, yn * ch) for xn, yn in ann["pts"]]
            if len(p) < 2:
                continue
            fill_paint = ft.Paint(
                color=ft.Colors.with_opacity(0.25, color),
                style=ft.PaintingStyle.FILL,
            )
            fill_path = cv.Path(
                elements=[cv.Path.MoveTo(p[0][0], p[0][1])],
                paint=fill_paint,
            )
            for px, py in p[1:]:
                fill_path.elements.append(cv.Path.LineTo(px, py))
            fill_path.elements.append(cv.Path.Close())
            draw_canvas.shapes.append(fill_path)

            out_paint = ft.Paint(
                color=color, stroke_width=1.5,
                style=ft.PaintingStyle.STROKE,
            )
            out_path = cv.Path(
                elements=[cv.Path.MoveTo(p[0][0], p[0][1])],
                paint=out_paint,
            )
            for px, py in p[1:]:
                out_path.elements.append(cv.Path.LineTo(px, py))
            out_path.elements.append(cv.Path.Close())
            draw_canvas.shapes.append(out_path)

        # Ve polygon dang ve (chua dong)
        _, cur_color = _get_cls(state["selected_cls"]) if state["selected_cls"] else ("", "#FFFFFF")
        pts_s = [(xn * cw, yn * ch) for xn, yn in pts_cur]
        if len(pts_s) >= 2:
            draw_path = cv.Path(
                elements=[cv.Path.MoveTo(pts_s[0][0], pts_s[0][1])],
                paint=ft.Paint(
                    color=cur_color, stroke_width=2,
                    style=ft.PaintingStyle.STROKE,
                ),
            )
            for px, py in pts_s[1:]:
                draw_path.elements.append(cv.Path.LineTo(px, py))
            draw_canvas.shapes.append(draw_path)

        # Diem nut
        for px, py in pts_s:
            draw_canvas.shapes.append(
                cv.Circle(px, py, radius=max(3, int(4 * state["zoom"])),
                          paint=ft.Paint(color=cur_color))
            )
        if pts_s:
            draw_canvas.shapes.append(
                cv.Circle(pts_s[0][0], pts_s[0][1],
                          radius=max(5, int(6 * state["zoom"])),
                          paint=ft.Paint(
                              color=cur_color, stroke_width=2,
                              style=ft.PaintingStyle.STROKE,
                          ))
            )
        _safe_update(draw_canvas)

    def _refresh_annotations_panel():
        annotations_col.controls.clear()
        for i, ann in enumerate(state["annotations"]):
            cls_label, color = _get_cls(ann["cls"])
            n_pts = len(ann["pts"])
            annotations_col.controls.append(
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=8, vertical=6),
                    border_radius=8,
                    bgcolor=ft.Colors.with_opacity(0.15, ft.Colors.WHITE),
                    border=ft.border.all(1, ft.Colors.with_opacity(0.20, color)),
                    content=ft.Row(
                        spacing=6,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Container(width=10, height=10, border_radius=5, bgcolor=color),
                            ft.Text(cls_label, size=11, color=ft.Colors.WHITE,
                                    expand=True, max_lines=1,
                                    overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text(f"{n_pts}pt", size=10, color=ft.Colors.WHITE54),
                            ft.IconButton(
                                ft.Icons.DELETE_OUTLINE, icon_size=14,
                                icon_color=ft.Colors.RED_300,
                                tooltip="Xóa",
                                on_click=lambda e, idx=i: _delete_annotation(idx),
                            ),
                        ],
                    ),
                )
            )
        if not state["annotations"]:
            annotations_col.controls.append(
                ft.Text("Chưa có nhãn", size=10, color=ft.Colors.WHITE38,
                        text_align=ft.TextAlign.CENTER)
            )
        _safe_update(annotations_col)

    def _delete_annotation(idx: int):
        if 0 <= idx < len(state["annotations"]):
            state["annotations"].pop(idx)
            _redraw_canvas()
            _refresh_annotations_panel()

    def _refresh_image_list():
        files = state["image_files"]
        cur   = state["current_index"]
        image_list_col.controls.clear()
        for i, finfo in enumerate(files):
            is_sel = i == cur
            image_list_col.controls.append(
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=8, vertical=5),
                    border_radius=6,
                    bgcolor=(
                        ft.Colors.with_opacity(0.25, PRIMARY) if is_sel
                        else ft.Colors.with_opacity(0.06, ft.Colors.WHITE)
                    ),
                    border=ft.border.all(
                        1,
                        ft.Colors.with_opacity(0.40, PRIMARY) if is_sel
                        else ft.Colors.TRANSPARENT,
                    ),
                    on_click=lambda e, idx=i: _load_image(idx),
                    content=ft.Row(spacing=6, controls=[
                        ft.Icon(ft.Icons.IMAGE, size=12,
                                color=PRIMARY if is_sel else ft.Colors.WHITE38),
                        ft.Text(finfo["name"], size=10,
                                color=ft.Colors.WHITE if is_sel else ft.Colors.WHITE60,
                                max_lines=1, overflow=ft.TextOverflow.ELLIPSIS,
                                expand=True),
                    ]),
                )
            )
        _safe_update(image_list_col)

    def _load_image(index: int):
        import base64
        files = state["image_files"]
        if not files or index < 0 or index >= len(files):
            return
        state["current_index"] = index
        state["cur_pts"]       = []
        state["annotations"]   = []
        finfo = files[index]
        if finfo["path"]:
            img_view.src        = finfo["path"]
            img_view.src_base64 = None
        elif finfo["bytes"]:
            img_view.src        = ""   # must be empty string, not None
            img_view.src_base64 = base64.b64encode(finfo["bytes"]).decode()
        else:
            img_view.src        = ""
            img_view.src_base64 = None
        img_name_lbl.value     = finfo["name"]
        img_counter_lbl.value  = f"{index + 1} / {len(files)}"
        status_msg.value       = ""
        yolo_output.value      = ""
        _redraw_canvas()
        _refresh_annotations_panel()
        _safe_update(img_view, img_name_lbl, img_counter_lbl, status_msg, yolo_output)
        _refresh_image_list()

    # -- Su kien ve -----------------------------------------------------------
    def _on_left_click(e: ft.TapEvent):
        """Chạm/click trái: thêm điểm (lưu normalized 0..1)."""
        cw, ch = _cur_w(), _cur_h()
        xn = max(0.0, min(1.0, e.local_x / cw))
        yn = max(0.0, min(1.0, e.local_y / ch))
        state["cur_pts"].append((xn, yn))
        _redraw_canvas()

    def _on_right_click(e: ft.TapEvent):
        """Click phải: hoàn thành polygon."""
        if not state["selected_cls"]:
            status_msg.value = "Hãy thêm và chọn một class trước!"
            status_msg.color = ft.Colors.AMBER_300
            _safe_update(status_msg)
            return
        pts = state["cur_pts"]
        if len(pts) < 3:
            status_msg.value = "Cần ít nhất 3 điểm để hoàn thành polygon!"
            status_msg.color = ft.Colors.AMBER_300
            _safe_update(status_msg)
            return
        state["annotations"].append({
            "cls": state["selected_cls"],
            "pts": list(pts),
        })
        state["cur_pts"] = []
        _redraw_canvas()
        _refresh_annotations_panel()
        cls_label, _ = _get_cls(state["selected_cls"])
        status_msg.value = f"Đã thêm polygon '{cls_label}' ({len(pts)} điểm)"
        status_msg.color = ft.Colors.GREEN_300
        _safe_update(status_msg)

    def _on_undo(e):
        if state["cur_pts"]:
            state["cur_pts"].pop()
            _redraw_canvas()

    def _on_complete_polygon(e):
        """Nut 'Luu vung' - tuong duong click phai."""
        _on_right_click(e)

    def _on_clear_current(e):
        state["cur_pts"] = []
        status_msg.value = "Đã hủy polygon đang vẽ."
        status_msg.color = ft.Colors.AMBER_300
        _redraw_canvas()
        _safe_update(status_msg)

    def _on_folder_pick(e: ft.FilePickerResultEvent):
        if not e.files:
            return
        first_path = e.files[0].path or ""
        if first_path:
            # ── Desktop: đọc toàn bộ thư mục qua path ──────────────────────
            folder = Path(first_path).parent
            exts   = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
            file_list = [
                {"name": p.name, "path": str(p), "bytes": None}
                for p in sorted(folder.iterdir())
                if p.suffix.lower() in exts
            ]
            state["image_files"]   = file_list
            state["current_index"] = 0
            state["cur_pts"]       = []
            state["annotations"]   = []
            n = len(file_list)
            status_msg.value = (
                f"Đã tải {n} ảnh" if n else "Không tìm thấy ảnh!"
            )
            status_msg.color = ft.Colors.GREEN_300 if n else ft.Colors.AMBER_300
            _safe_update(status_msg)
            if n:
                _load_image(0)
            else:
                _refresh_image_list()
        else:
            # ── Web/Phone: upload lên server, đọc sau ──────────────────────
            names = [f.name for f in e.files]
            state["_pending_uploads"]     = {n: None for n in names}
            state["_pending_files_order"] = names
            upload_list = []
            for f in e.files:
                try:
                    url = page.get_upload_url(f.name, 60)
                    upload_list.append(ft.FilePickerUploadFile(f.name, url))
                except Exception as ex:
                    status_msg.value = f"Lỗi lấy URL upload: {ex}"
                    status_msg.color = ft.Colors.RED_400
                    _safe_update(status_msg)
                    return
            folder_picker.upload(upload_list)
            status_msg.value = f"Đang tải {len(names)} ảnh lên..."
            status_msg.color = ft.Colors.AMBER_300
            _safe_update(status_msg)

    def _on_upload_progress(e: ft.FilePickerUploadEvent):
        """Gọi mỗi khi một file được upload xong (web mode)."""
        if e.error:
            status_msg.value = f"Lỗi upload '{e.file_name}': {e.error}"
            status_msg.color = ft.Colors.RED_400
            _safe_update(status_msg)
            return
        if e.progress == 1.0:
            # Đọc file từ upload_dir trên server
            upload_dir_str = ""
            if page and isinstance(page.data, dict):
                upload_dir_str = page.data.get("upload_dir", "")
            fbytes = None
            if upload_dir_str:
                try:
                    fbytes = (Path(upload_dir_str) / e.file_name).read_bytes()
                except Exception:
                    fbytes = None
            state["_pending_uploads"][e.file_name] = fbytes if fbytes is not None else b""
            # Kiểm tra xem tất cả đã xong chưa
            if all(v is not None for v in state["_pending_uploads"].values()):
                file_list = [
                    {"name": nm, "path": "", "bytes": state["_pending_uploads"][nm] or None}
                    for nm in state["_pending_files_order"]
                ]
                state["image_files"]   = file_list
                state["current_index"] = 0
                state["cur_pts"]       = []
                state["annotations"]   = []
                n = len(file_list)
                status_msg.value = f"Đã tải {n} ảnh"
                status_msg.color = ft.Colors.GREEN_300
                _safe_update(status_msg)
                if n:
                    _load_image(0)
                else:
                    _refresh_image_list()

    def _on_export_save(e):
        anns  = state["annotations"]
        files = state["image_files"]
        cur   = state["current_index"]
        if not files:
            status_msg.value = "Chưa chọn ảnh!"
            status_msg.color = ft.Colors.RED_400
            _safe_update(status_msg)
            return
        if not anns:
            status_msg.value = "Chưa có annotation! Vẽ polygon rồi nhấn Lưu."
            status_msg.color = ft.Colors.AMBER_300
            _safe_update(status_msg)
            return

        finfo       = files[cur]
        src_name    = finfo["name"]
        stem        = Path(src_name).stem
        out_img_dir = _EXPORT_BASE / "train" / "images"
        out_lbl_dir = _EXPORT_BASE / "train" / "labels"
        out_img_dir.mkdir(parents=True, exist_ok=True)
        out_lbl_dir.mkdir(parents=True, exist_ok=True)

        # Toa do da la normalized 0..1, ghi truc tiep
        lines = []
        for ann in anns:
            cls_id = ann["cls"]
            coords = " ".join(
                f"{round(xn, 6)} {round(yn, 6)}"
                for xn, yn in ann["pts"]
            )
            lines.append(f"{cls_id} {coords}")

        lbl_path = out_lbl_dir / (stem + ".txt")
        lbl_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        dst_img = out_img_dir / src_name
        if not dst_img.exists():
            if finfo["path"]:
                shutil.copy2(finfo["path"], dst_img)
            elif finfo["bytes"]:
                dst_img.write_bytes(finfo["bytes"])

        yolo_output.value = "\n".join(lines)
        status_msg.value  = f"Đã lưu {len(anns)} nhãn -> {lbl_path.name}"
        status_msg.color  = ft.Colors.GREEN_300
        _safe_update(status_msg, yolo_output)

        next_idx = cur + 1
        if next_idx < len(files):
            _load_image(next_idx)

    # -- Class selector buttons (dong - Roboflow style) ----------------------
    cls_buttons_row = ft.Row(wrap=True, spacing=6, run_spacing=6)
    cls_name_field  = ft.TextField(
        hint_text="Tên class mới...",
        height=32, text_size=11,
        border_radius=8,
        content_padding=ft.padding.symmetric(horizontal=8, vertical=0),
        expand=True,
    )

    def _refresh_cls_buttons():
        cls_buttons_row.controls.clear()
        classes = state["classes"]
        if not classes:
            cls_buttons_row.controls.append(
                ft.Text("Chưa có class", size=10, color=ft.Colors.WHITE38)
            )
        for cls in classes:
            cls_id    = cls["id"]
            cls_label = cls["label"]
            cls_color = cls["color"]
            is_sel    = state["selected_cls"] == cls_id

            def _make_click(cid):
                def _select(e):
                    state["selected_cls"] = cid
                    _refresh_cls_buttons()
                    _redraw_canvas()
                return _select

            def _make_delete(cid):
                def _del(e):
                    state["classes"] = [c for c in state["classes"] if c["id"] != cid]
                    state["annotations"] = [a for a in state["annotations"] if a["cls"] != cid]
                    if state["selected_cls"] == cid:
                        state["selected_cls"] = state["classes"][0]["id"] if state["classes"] else None
                    _refresh_cls_buttons()
                    _refresh_annotations_panel()
                    _redraw_canvas()
                return _del

            # Chip kieu Roboflow: [dot] label [x]
            cls_buttons_row.controls.append(
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=10, vertical=7),
                    border_radius=20,
                    border=ft.border.all(
                        2,
                        ft.Colors.with_opacity(0.85, cls_color) if is_sel
                        else ft.Colors.with_opacity(0.25, cls_color),
                    ),
                    bgcolor=ft.Colors.with_opacity(0.30 if is_sel else 0.08, cls_color),
                    on_click=_make_click(cls_id),
                    content=ft.Row(
                        spacing=5, tight=True,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Container(width=9, height=9, border_radius=5, bgcolor=cls_color),
                            ft.Text(
                                cls_label, size=12,
                                weight=ft.FontWeight.W_600 if is_sel else ft.FontWeight.W_400,
                                color=ft.Colors.WHITE if is_sel else ft.Colors.WHITE70,
                            ),
                            ft.GestureDetector(
                                on_tap=_make_delete(cls_id),
                                content=ft.Icon(
                                    ft.Icons.CLOSE, size=12,
                                    color=ft.Colors.WHITE54 if is_sel else ft.Colors.WHITE24,
                                ),
                            ),
                        ],
                    ),
                )
            )
        _safe_update(cls_buttons_row)

    def _on_add_class(e):
        label = cls_name_field.value.strip() if cls_name_field.value else ""
        if not label:
            return
        existing_labels = [c["label"].lower() for c in state["classes"]]
        if label.lower() in existing_labels:
            status_msg.value = f"Class '{label}' đã tồn tại!"
            status_msg.color = ft.Colors.AMBER_300
            _safe_update(status_msg)
            return
        cls_id = str(state["next_id"])
        color  = _COLOR_PALETTE[state["next_id"] % len(_COLOR_PALETTE)]
        state["classes"].append({"id": cls_id, "label": label, "color": color})
        state["next_id"] += 1
        if state["selected_cls"] is None:
            state["selected_cls"] = cls_id
        cls_name_field.value = ""
        _safe_update(cls_name_field)
        _refresh_cls_buttons()

    _refresh_cls_buttons()

    # -- File Picker ----------------------------------------------------------
    folder_picker = ft.FilePicker(on_result=_on_folder_pick, on_upload=_on_upload_progress)
    if page:
        page.overlay.append(folder_picker)
        page.update()

    # -- Image stack ----------------------------------------------------------
    _ZOOM_STEPS = [1.0, 1.5, 2.0, 2.5, 3.0]
    zoom_lbl = ft.Text("100%", size=11, color=ft.Colors.WHITE70,
                        width=38, text_align=ft.TextAlign.CENTER)

    gesture_det = ft.GestureDetector(
        on_tap_down=_on_left_click,
        on_secondary_tap_down=_on_right_click,
        width=_UI_W, height=_UI_H,
        drag_interval=50,
    )
    image_stack = ft.Stack(
        width=_UI_W, height=_UI_H,
        controls=[img_view, draw_canvas, gesture_det],
    )
    canvas_wrap = ft.Container(
        content=image_stack,
        border_radius=10,
        bgcolor=ft.Colors.with_opacity(0.20, ft.Colors.BLACK),
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        alignment=ft.alignment.center,
        width=_UI_W,
    )

    def _apply_zoom(z: float):
        state["zoom"] = z
        w, h = _cur_w(), _cur_h()
        img_view.width   = w
        img_view.height  = h
        draw_canvas.width  = w
        draw_canvas.height = h
        gesture_det.width  = w
        gesture_det.height = h
        image_stack.width  = w
        image_stack.height = h
        canvas_wrap.width  = w
        zoom_lbl.value = f"{int(z * 100)}%"
        _redraw_canvas()
        _safe_update(canvas_wrap, zoom_lbl)

    def _zoom_in(e):
        cur = state["zoom"]
        nxt = next((z for z in _ZOOM_STEPS if z > cur + 0.01), _ZOOM_STEPS[-1])
        _apply_zoom(nxt)

    def _zoom_out(e):
        cur = state["zoom"]
        nxt = next((z for z in reversed(_ZOOM_STEPS) if z < cur - 0.01), _ZOOM_STEPS[0])
        _apply_zoom(nxt)

    # -- Layout (doc, toi uu phone) ------------------------------------------
    return ft.Column(
        expand=True, spacing=12, scroll=ft.ScrollMode.AUTO,
        controls=[

            # ── Header ──────────────────────────────────────────────────────
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Column(tight=True, spacing=2, controls=[
                        ft.Text("Gán nhãn HITL", size=20, weight=ft.FontWeight.W_700),
                        ft.Text("Polygon · YOLO v8 Segmentation",
                                size=11, color=ft.Colors.WHITE54),
                    ]),
                    ft.ElevatedButton(
                        "Chọn ảnh", icon=ft.Icons.FOLDER_OPEN,
                        height=40, style=button_style("primary"),
                        on_click=lambda e: folder_picker.pick_files(
                            dialog_title="Chọn ảnh cần gán nhãn",
                            allow_multiple=True,
                            allowed_extensions=["jpg", "jpeg", "png", "bmp", "webp"],
                        ),
                    ),
                ],
            ),

            # ── Huong dan (an) ──────────────────────────────────────────────

            # ── Anh + ten file ──────────────────────────────────────────────
            glass_container(
                padding=10, radius=16,
                content=ft.Column(spacing=8, controls=[
                    ft.Row(
                        spacing=6,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Icon(ft.Icons.IMAGE, size=14, color=ft.Colors.WHITE38),
                            img_name_lbl,
                            img_counter_lbl,
                        ],
                    ),
                    canvas_wrap,
                    # Zoom controls
                    ft.Row(
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=4,
                        controls=[
                            ft.IconButton(
                                ft.Icons.ZOOM_OUT, icon_size=20,
                                icon_color=ft.Colors.WHITE70,
                                tooltip="Thu nhỏ",
                                on_click=_zoom_out,
                            ),
                            zoom_lbl,
                            ft.IconButton(
                                ft.Icons.ZOOM_IN, icon_size=20,
                                icon_color=ft.Colors.WHITE70,
                                tooltip="Phóng to",
                                on_click=_zoom_in,
                            ),
                        ],
                    ),
                    # Nut luu vung (hoan thanh polygon)
                    ft.ElevatedButton(
                        "Lưu",
                        icon=ft.Icons.PENTAGON,
                        height=44,
                        expand=True,
                        style=ft.ButtonStyle(
                            bgcolor=ft.Colors.GREEN_700,
                            color=ft.Colors.WHITE,
                            shape=ft.RoundedRectangleBorder(radius=10),
                        ),
                        on_click=lambda e: _on_complete_polygon(e),
                    ),
                    # Nav + edit controls
                    ft.Row(
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=4,
                        controls=[
                            ft.FilledTonalButton(
                                text="Trước", icon=ft.Icons.CHEVRON_LEFT,
                                height=38,
                                on_click=lambda e: _load_image(
                                    state["current_index"] - 1),
                            ),
                            ft.FilledTonalButton(
                                text="Tiếp", icon=ft.Icons.CHEVRON_RIGHT,
                                height=38,
                                on_click=lambda e: _load_image(
                                    state["current_index"] + 1),
                            ),
                            ft.Container(expand=True),
                            ft.FilledTonalButton(
                                text="Hoàn tác", icon=ft.Icons.UNDO,
                                height=38,
                                on_click=_on_undo,
                            ),
                            ft.FilledTonalButton(
                                text="Hủy", icon=ft.Icons.CLEAR,
                                height=38,
                                style=ft.ButtonStyle(
                                    color=ft.Colors.RED_300,
                                ),
                                on_click=_on_clear_current,
                            ),
                        ],
                    ),
                ]),
            ),

            # ── Class (dong) ────────────────────────────────────────────────
            glass_container(
                padding=12, radius=16,
                content=ft.Column(spacing=10, controls=[
                    ft.Text("Lớp đối tượng", size=13, weight=ft.FontWeight.W_700,
                            color=ft.Colors.WHITE),
                    ft.Row(
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            cls_name_field,
                            ft.FilledButton(
                                "Thêm", icon=ft.Icons.ADD,
                                height=38,
                                on_click=_on_add_class,
                            ),
                        ],
                    ),
                    cls_buttons_row,
                ]),
            ),

            # ── Annotation da ve ────────────────────────────────────────────
            glass_container(
                padding=12, radius=16,
                content=ft.Column(spacing=8, controls=[
                    ft.Text("Nhãn đã vẽ", size=13, weight=ft.FontWeight.W_700,
                            color=ft.Colors.WHITE),
                    annotations_col,
                ]),
            ),

            # ── Luu & Tiep ──────────────────────────────────────────────────
            ft.ElevatedButton(
                "Lưu & Sang ảnh tiếp theo",
                icon=ft.Icons.SAVE_ALT,
                height=48,
                expand=True,
                style=button_style("primary"),
                on_click=_on_export_save,
            ),

            # ── Status ──────────────────────────────────────────────────────
            status_msg,
            ft.Container(
                content=yolo_output,
                bgcolor=ft.Colors.with_opacity(0.35, ft.Colors.BLACK),
                padding=ft.padding.symmetric(horizontal=12, vertical=8),
                border_radius=10,
            ),

            # ── Danh sach anh ───────────────────────────────────────────────
            glass_container(
                padding=12, radius=16,
                content=ft.Column(spacing=6, controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Text("Ảnh trong thư mục", size=13,
                                    weight=ft.FontWeight.W_600,
                                    color=ft.Colors.WHITE70),
                            ft.Text("-> dataset_v3/",
                                    size=10, color=ft.Colors.WHITE38),
                        ],
                    ),
                    image_list_col,
                ]),
            ),
        ],
    )
