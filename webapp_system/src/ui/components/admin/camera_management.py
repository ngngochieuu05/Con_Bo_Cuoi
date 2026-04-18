import flet as ft
from ui.theme import (
    PRIMARY, SECONDARY, WARNING, DANGER,
    glass_container, status_badge, button_style,
    inline_field, section_title, empty_state, fmt_dt,
)
from bll.admin.camera_management import (
    list_cameras, create_camera, update_camera, set_camera_status, delete_camera,
)
from bll.services.activity_service import log_action

_STATUS_META = {
    "online":  ("Online",     "primary"),
    "warning": ("Cảnh báo",   "warning"),
    "offline": ("Ngoại tuyến","danger"),
}
_STATUS_OPTIONS = [
    ft.dropdown.Option("online",  "Online"),
    ft.dropdown.Option("warning", "Cảnh báo"),
    ft.dropdown.Option("offline", "Ngoại tuyến"),
]
_STATUS_COLORS = {"online": PRIMARY, "warning": WARNING, "offline": DANGER}


def _camera_card(cam: dict, page: ft.Page | None, on_refresh) -> ft.Control:
    cid    = cam.get("id_camera_chuong")
    cam_id = cam.get("id_camera", "—")
    chuong = cam.get("id_chuong", "—")
    khu    = cam.get("khu_vuc_chuong", "—")
    status = cam.get("trang_thai", "offline")
    uid    = cam.get("id_user")
    upd    = cam.get("updated_at", "")
    lbl, kind = _STATUS_META.get(status, ("—", "warning"))

    detail_ref = ft.Ref[ft.Container]()
    edit_msg   = ft.Text("", size=11, color=ft.Colors.GREEN_300)

    e_khu    = ft.TextField(
        value=khu, label="Khu vực chuồng",
        border_radius=10, expand=True,
        bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
        border_color=ft.Colors.with_opacity(0.25, ft.Colors.WHITE),
        focused_border_color=PRIMARY,
        label_style=ft.TextStyle(color=ft.Colors.WHITE60, size=11),
        text_style=ft.TextStyle(color=ft.Colors.WHITE, size=12),
        cursor_color=ft.Colors.WHITE,
        content_padding=ft.padding.symmetric(horizontal=10, vertical=8),
    )
    e_status = ft.Dropdown(
        value=status, label="Trạng thái",
        options=_STATUS_OPTIONS,
        border_radius=10, width=150,
        bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
        border_color=ft.Colors.with_opacity(0.25, ft.Colors.WHITE),
        focused_border_color=PRIMARY,
        label_style=ft.TextStyle(color=ft.Colors.WHITE60, size=11),
        text_style=ft.TextStyle(color=ft.Colors.WHITE, size=12),
    )

    def _toggle(e):
        detail_ref.current.visible = not detail_ref.current.visible
        detail_ref.current.update()

    def _save(e):
        updates = {}
        new_khu = (e_khu.value or "").strip()
        if new_khu and new_khu != khu:
            updates["khu_vuc_chuong"] = new_khu
        new_st = e_status.value or status
        if new_st != status:
            updates["trang_thai"] = new_st
        if updates:
            ok, msg_txt = update_camera(cid, updates)
            edit_msg.value = msg_txt
            edit_msg.color = ft.Colors.GREEN_300 if ok else ft.Colors.RED_300
            edit_msg.update()
            if ok:
                cur_uid = int(page.data.get("user_id", 0)) if page and page.data else None
                log_action(cur_uid, "UPDATE_CAMERA", f"camera {cam_id}")
                on_refresh()
        else:
            edit_msg.value = "Không có thay đổi."
            edit_msg.color = ft.Colors.WHITE38
            edit_msg.update()

    def _delete(e):
        ok, msg_txt = delete_camera(cid)
        if ok:
            cur_uid = int(page.data.get("user_id", 0)) if page and page.data else None
            log_action(cur_uid, "DELETE_CAMERA", f"camera {cam_id}")
        on_refresh()

    detail_panel = ft.Container(
        ref=detail_ref, visible=False,
        padding=ft.padding.only(top=8),
        content=ft.Column(spacing=8, controls=[
            ft.Divider(color=ft.Colors.with_opacity(0.12, ft.Colors.WHITE), height=1),
            ft.Row(spacing=6, tight=True, controls=[
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=8, vertical=4),
                    border_radius=8,
                    bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
                    content=ft.Row(tight=True, spacing=4, controls=[
                        ft.Icon(ft.Icons.TAG, size=11, color=ft.Colors.WHITE38),
                        ft.Text(f"ID chuồng: {chuong}", size=10, color=ft.Colors.WHITE54),
                    ]),
                ),
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=8, vertical=4),
                    border_radius=8,
                    bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
                    content=ft.Row(tight=True, spacing=4, controls=[
                        ft.Icon(ft.Icons.PERSON, size=11, color=ft.Colors.WHITE38),
                        ft.Text(f"User #{uid}", size=10, color=ft.Colors.WHITE54),
                    ]),
                ),
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=8, vertical=4),
                    border_radius=8,
                    bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
                    content=ft.Row(tight=True, spacing=4, controls=[
                        ft.Icon(ft.Icons.SCHEDULE, size=11, color=ft.Colors.WHITE38),
                        ft.Text(fmt_dt(upd), size=10, color=ft.Colors.WHITE54),
                    ]),
                ),
            ]),
            ft.Row(spacing=8, controls=[e_khu, e_status]),
            ft.Row(spacing=8, controls=[
                ft.ElevatedButton(
                    "Lưu thay đổi", icon=ft.Icons.SAVE,
                    style=button_style("primary"), height=32,
                    on_click=_save,
                ),
                ft.OutlinedButton(
                    "Xóa camera", icon=ft.Icons.DELETE_OUTLINE,
                    height=32,
                    style=ft.ButtonStyle(
                        color=ft.Colors.RED_300,
                        side=ft.BorderSide(1, ft.Colors.RED_300),
                        shape=ft.RoundedRectangleBorder(radius=8),
                    ),
                    on_click=_delete,
                ),
                edit_msg,
            ]),
        ]),
    )

    accent = _STATUS_COLORS.get(status, ft.Colors.WHITE38)
    return ft.Container(
        ink=True,
        border_radius=12,
        padding=ft.padding.symmetric(horizontal=12, vertical=10),
        bgcolor=ft.Colors.with_opacity(0.09, ft.Colors.WHITE),
        border=ft.border.all(1, ft.Colors.with_opacity(0.10, ft.Colors.WHITE)),
        on_click=_toggle,
        content=ft.Column(spacing=0, controls=[
            ft.Row(
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(
                        width=8, height=8, border_radius=4,
                        bgcolor=accent,
                        margin=ft.margin.only(right=8, top=3),
                    ),
                    ft.Column(
                        expand=True, tight=True, spacing=2,
                        controls=[
                            ft.Text(cam_id, size=14, weight=ft.FontWeight.W_600,
                                    max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Row(spacing=6, tight=True, controls=[
                                ft.Text(khu, size=11, color=ft.Colors.WHITE54,
                                        max_lines=1, overflow=ft.TextOverflow.CLIP),
                                ft.Text("·", size=11, color=ft.Colors.WHITE24),
                                status_badge(lbl, kind),
                            ]),
                        ],
                    ),
                    ft.Row(spacing=4, tight=True, controls=[
                        ft.Text(fmt_dt(upd, "%d/%m"), size=10, color=ft.Colors.WHITE38),
                        ft.Icon(ft.Icons.EXPAND_MORE, size=16, color=ft.Colors.WHITE38),
                    ]),
                ],
            ),
            detail_panel,
        ]),
    )


def build_camera_management(page: ft.Page | None = None):
    search_field  = inline_field("Tìm ID camera / khu vực", ft.Icons.SEARCH)
    list_ref      = ft.Ref[ft.Column]()
    form_ref      = ft.Ref[ft.Container]()
    msg           = ft.Text("", size=12, color=ft.Colors.GREEN_300)
    active_filter = {"status": "all"}

    # ── Add-camera form ───────────────────────────────────────────────────
    f_id_camera = inline_field("ID camera (vd: CAM-04)",   ft.Icons.VIDEOCAM)
    f_id_chuong = inline_field("ID chuồng  (vd: CHUONG-D)")
    f_khu       = inline_field("Khu vực   (vd: Khu D)")
    f_uid       = inline_field("ID nông dân", ft.Icons.PERSON, keyboard_type=ft.KeyboardType.NUMBER)
    btn_save    = ft.ElevatedButton(
        "Lưu camera", icon=ft.Icons.SAVE,
        style=button_style("primary"), height=40,
    )

    def refresh(keyword: str = "", status_filter: str = "all"):
        kw = keyword.lower()
        cams = list_cameras()
        if status_filter != "all":
            cams = [c for c in cams if c.get("trang_thai") == status_filter]
        if kw:
            cams = [
                c for c in cams
                if kw in c.get("id_camera", "").lower()
                or kw in c.get("khu_vuc_chuong", "").lower()
            ]
        cards = (
            [_camera_card(c, page, lambda: refresh(search_field.value or "", active_filter["status"]))
             for c in cams]
            if cams
            else [empty_state("Không tìm thấy camera")]
        )
        list_ref.current.controls = cards
        if list_ref.current.page:
            list_ref.current.update()

    def _do_add(e):
        uid_str = (f_uid.value or "").strip()
        try:
            uid_val = int(uid_str) if uid_str else 0
        except ValueError:
            msg.value = "ID nông dân phải là số."
            msg.color = ft.Colors.RED_300
            msg.update(); return

        ok, msg_txt = create_camera(
            f_id_chuong.value or "",
            f_khu.value or "",
            f_id_camera.value or "",
            uid_val,
        )
        msg.value = msg_txt
        msg.color = ft.Colors.GREEN_300 if ok else ft.Colors.RED_300
        msg.update()
        if ok:
            cur_uid = int(page.data.get("user_id", 0)) if page and page.data else None
            log_action(cur_uid, "CREATE_CAMERA", f"cam {f_id_camera.value}")
            for f in (f_id_camera, f_id_chuong, f_khu, f_uid):
                f.value = ""
                f.update()
            form_ref.current.visible = False
            form_ref.current.update()
            refresh(search_field.value or "", active_filter["status"])

    btn_save.on_click = _do_add

    # ── Status filter chips ───────────────────────────────────────────────
    _FILTERS = [
        ("all",     "Tất cả"),
        ("online",  "Online"),
        ("warning", "Cảnh báo"),
        ("offline", "Ngoại tuyến"),
    ]
    filter_chips_ref = ft.Ref[ft.Row]()

    def _build_chips():
        chips = []
        for key, lbl in _FILTERS:
            is_active = active_filter["status"] == key
            chips.append(
                ft.Container(
                    ink=True, border_radius=20,
                    padding=ft.padding.symmetric(horizontal=12, vertical=5),
                    bgcolor=ft.Colors.with_opacity(
                        0.28 if is_active else 0.10,
                        PRIMARY if is_active else ft.Colors.WHITE,
                    ),
                    border=ft.border.all(1, ft.Colors.with_opacity(
                        0.4 if is_active else 0.15,
                        PRIMARY if is_active else ft.Colors.WHITE,
                    )),
                    on_click=lambda e, k=key: _on_filter(k),
                    content=ft.Text(
                        lbl, size=12,
                        weight=ft.FontWeight.W_600 if is_active else ft.FontWeight.W_400,
                    ),
                )
            )
        return chips

    def _on_filter(key):
        active_filter["status"] = key
        filter_chips_ref.current.controls = _build_chips()
        filter_chips_ref.current.update()
        refresh(search_field.value or "", key)

    filter_row  = ft.Row(ref=filter_chips_ref, spacing=6, scroll=ft.ScrollMode.AUTO,
                         controls=_build_chips())
    camera_list = ft.Column(ref=list_ref, spacing=6, controls=[])
    refresh()

    add_form = ft.Container(
        ref=form_ref, visible=False,
        content=glass_container(
            padding=14, radius=14,
            content=ft.Column(spacing=10, controls=[
                section_title("VIDEOCAM_PLUS", "Thêm camera mới"),
                ft.Row(spacing=8, controls=[f_id_camera, f_id_chuong]),
                ft.Row(spacing=8, controls=[f_khu, f_uid]),
                btn_save,
            ]),
        ),
    )

    return ft.Column(
        expand=True, spacing=12, scroll=ft.ScrollMode.AUTO,
        controls=[
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Column(tight=True, spacing=1, controls=[
                        ft.Text("Quản lý Camera", size=20, weight=ft.FontWeight.W_700),
                        ft.Text("Nhấn vào camera để xem chi tiết và chỉnh sửa",
                                size=11, color=ft.Colors.WHITE54),
                    ]),
                    ft.ElevatedButton(
                        "Thêm", icon=ft.Icons.ADD,
                        style=button_style("primary"), height=36,
                        on_click=lambda e: _toggle_form(form_ref),
                    ),
                ],
            ),
            ft.Row(spacing=8, controls=[
                search_field,
                ft.IconButton(
                    ft.Icons.SEARCH, icon_color=ft.Colors.WHITE70,
                    on_click=lambda e: refresh(search_field.value or "", active_filter["status"]),
                ),
            ]),
            filter_row,
            msg,
            add_form,
            camera_list,
        ],
    )


def _toggle_form(ref: ft.Ref) -> None:
    ref.current.visible = not ref.current.visible
    ref.current.update()
