import flet as ft
from ui.theme import (
    PRIMARY, SECONDARY, WARNING, DANGER,
    glass_container, status_badge, button_style,
    inline_field, section_title, empty_state, fmt_dt,
)
from bll.admin.user_management import (
    list_users as get_all_users, create_user, delete_user,
    reset_password as change_password, update_user, get_user_by_username,
)
from bll.admin.model_management import (
    list_models as get_all_models, update_model_config, update_model_status,
)

_MODEL_META = {
    "cattle_detect": ("Nhận diện bò",  ft.Icons.PETS,           PRIMARY),
    "behavior":      ("Hành vi bò",    ft.Icons.DIRECTIONS_RUN, SECONDARY),
}

_ROLE_MAP = {
    "admin":  ("Quản trị",   "secondary"),
    "expert": ("Chuyên gia", "primary"),
    "farmer": ("Nông dân",   "warning"),
}
_ROLE_OPTIONS = [
    ft.dropdown.Option("admin",  "Quản trị"),
    ft.dropdown.Option("expert", "Chuyên gia"),
    ft.dropdown.Option("farmer", "Nông dân"),
]
_ROLE_FILTER = [
    ("all",    "Tất cả"),
    ("admin",  "Quản trị"),
    ("expert", "Chuyên gia"),
    ("farmer", "Nông dân"),
]
_ROLE_COLOR = {"admin": SECONDARY, "expert": PRIMARY, "farmer": WARNING}


def _role_dot(role: str) -> ft.Container:
    return ft.Container(
        width=8, height=8, border_radius=4,
        bgcolor=_ROLE_COLOR.get(role, ft.Colors.WHITE38),
        margin=ft.margin.only(right=6, top=4),
    )


def _user_card(u: dict, on_refresh) -> ft.Control:
    """Card nguoi dung voi panel chi tiet co the mo/dong de chinh sua."""
    uid       = u.get("id_user")
    role      = u.get("vai_tro", "farmer")
    hoten     = u.get("ho_ten", "")
    uname     = u.get("ten_dang_nhap", "")
    created   = u.get("created_at", "")
    rlabel, rkind = _ROLE_MAP.get(role, ("Khác", "warning"))

    detail_ref = ft.Ref[ft.Container]()
    edit_msg   = ft.Text("", size=11, color=ft.Colors.GREEN_300)

    # Edit fields inside detail panel
    e_hoten = ft.TextField(
        value=hoten, label="Họ tên",
        border_radius=10, expand=True,
        bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
        border_color=ft.Colors.with_opacity(0.25, ft.Colors.WHITE),
        focused_border_color=PRIMARY,
        label_style=ft.TextStyle(color=ft.Colors.WHITE60, size=11),
        text_style=ft.TextStyle(color=ft.Colors.WHITE, size=12),
        cursor_color=ft.Colors.WHITE,
        content_padding=ft.padding.symmetric(horizontal=10, vertical=8),
    )
    e_role = ft.Dropdown(
        value=role, label="Vai trò",
        options=_ROLE_OPTIONS,
        border_radius=10, width=130,
        bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
        border_color=ft.Colors.with_opacity(0.25, ft.Colors.WHITE),
        focused_border_color=PRIMARY,
        label_style=ft.TextStyle(color=ft.Colors.WHITE60, size=11),
        text_style=ft.TextStyle(color=ft.Colors.WHITE, size=12),
    )
    e_newpwd = ft.TextField(
        label="Mật khẩu mới (để trống nếu giữ nguyên)",
        password=True, can_reveal_password=True,
        border_radius=10, expand=True,
        bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
        border_color=ft.Colors.with_opacity(0.25, ft.Colors.WHITE),
        focused_border_color=WARNING,
        label_style=ft.TextStyle(color=ft.Colors.WHITE60, size=11),
        text_style=ft.TextStyle(color=ft.Colors.WHITE, size=12),
        cursor_color=ft.Colors.WHITE,
        content_padding=ft.padding.symmetric(horizontal=10, vertical=8),
    )

    def _toggle_detail(e):
        detail_ref.current.visible = not detail_ref.current.visible
        detail_ref.current.update()

    def _save_edit(e):
        updates = {}
        new_ht = (e_hoten.value or "").strip()
        if new_ht != hoten:
            updates["ho_ten"] = new_ht
        new_role = e_role.value or role
        if new_role != role:
            updates["vai_tro"] = new_role
        if updates:
            update_user(uid, updates)
        new_pwd = (e_newpwd.value or "").strip()
        if new_pwd:
            if len(new_pwd) < 6:
                edit_msg.value = "Mật khẩu phải từ 6 ký tự"
                edit_msg.color = ft.Colors.AMBER_300
                edit_msg.update()
                return
            change_password(uid, new_pwd)
            e_newpwd.value = ""
            e_newpwd.update()
        edit_msg.value = "Đã lưu thay đổi"
        edit_msg.color = ft.Colors.GREEN_300
        edit_msg.update()
        on_refresh()

    def _delete(e):
        delete_user(uid)
        on_refresh()

    # ── Phan cau hinh model YOLO (chi farmer / expert) ───────────────────
    def _make_model_controls():
        if role not in ("farmer", "expert"):
            return []
        user_models = [m for m in get_all_models()
                       if m.get("loai_mo_hinh") in _MODEL_META]
        if not user_models:
            return []

        blocks = [
            ft.Divider(color=ft.Colors.with_opacity(0.10, ft.Colors.WHITE), height=1),
            ft.Row(tight=True, spacing=5, controls=[
                ft.Icon(ft.Icons.TUNE, size=12, color=ft.Colors.WHITE54),
                ft.Text("Cấu hình Model YOLO", size=11,
                        weight=ft.FontWeight.W_600, color=ft.Colors.WHITE70),
            ]),
        ]

        for m in user_models:
            loai   = m.get("loai_mo_hinh")
            mid    = m["id_model"]
            name, icon, accent = _MODEL_META[loai]
            conf_v = float(m.get("conf", 0.50))
            iou_v  = float(m.get("iou",  0.45))
            pt_v   = m.get("duong_dan_file", "")
            st_key = m.get("trang_thai", "offline")
            _sv    = {"conf": conf_v, "iou": iou_v}

            lbl_conf = ft.Text(f"{conf_v:.2f}", size=11,
                               weight=ft.FontWeight.W_700, color=accent, width=34)
            lbl_iou  = ft.Text(f"{iou_v:.2f}", size=11,
                               weight=ft.FontWeight.W_700, color=SECONDARY, width=34)

            def _chg_conf(e, sv=_sv, lb=lbl_conf):
                sv["conf"] = round(float(e.control.value), 2)
                lb.value = f"{sv['conf']:.2f}"; lb.update()

            def _chg_iou(e, sv=_sv, lb=lbl_iou):
                sv["iou"] = round(float(e.control.value), 2)
                lb.value = f"{sv['iou']:.2f}"; lb.update()

            pt_tf = ft.TextField(
                value=pt_v, label="File .pt",
                hint_text=f"models/{loai}.pt",
                prefix_icon=ft.Icons.FOLDER_OPEN,
                border_radius=8, expand=True,
                bgcolor=ft.Colors.with_opacity(0.08, ft.Colors.WHITE),
                border_color=ft.Colors.with_opacity(0.18, ft.Colors.WHITE),
                focused_border_color=accent,
                label_style=ft.TextStyle(color=ft.Colors.WHITE54, size=10),
                text_style=ft.TextStyle(color=ft.Colors.WHITE, size=11),
                cursor_color=ft.Colors.WHITE,
                content_padding=ft.padding.symmetric(horizontal=8, vertical=5),
            )
            save_lbl = ft.Text("", size=10, color=ft.Colors.GREEN_300)

            def _copy_path(e, tf=pt_tf, lb=save_lbl):
                val = (tf.value or "").strip()
                if val and e.page:
                    e.page.set_clipboard(val)
                    lb.value = "Đã sao chép!"; lb.color = ft.Colors.CYAN_300; lb.update()

            def _paste_path(e, tf=pt_tf, lb=save_lbl):
                async def _do(e=e, tf=tf, lb=lb):
                    try:
                        clip = await e.page.get_clipboard_async()
                        if clip:
                            tf.value = clip.strip()
                            tf.update()
                            lb.value = "Đã dán!"; lb.color = ft.Colors.GREEN_300; lb.update()
                    except Exception:
                        pass
                e.page.run_task(_do)

            def _save_m(e, _mid=mid, sv=_sv, tf=pt_tf, lb=save_lbl):
                path = (tf.value or "").strip()
                if path and not path.endswith(".pt"):
                    lb.value = "Phải là .pt"; lb.color = ft.Colors.AMBER_300
                    lb.update(); return
                update_model_config(_mid, sv["conf"], sv["iou"], path)
                lb.value = "Đã lưu"; lb.color = ft.Colors.GREEN_300; lb.update()

            def _toggle_st(e, _mid=mid, _sk=st_key):
                new_st = "online" if _sk in ("offline", "testing") else "offline"
                update_model_status(_mid, new_st)
                on_refresh()

            st_label = "Đang chạy" if st_key == "online" else "Ngoại tuyến"
            st_kind  = "primary"   if st_key == "online" else "danger"
            tog_lbl  = "Tắt" if st_key == "online" else "Bật"
            tog_col  = DANGER if st_key == "online" else PRIMARY

            blocks.append(
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=10, vertical=8),
                    border_radius=10,
                    bgcolor=ft.Colors.with_opacity(0.06, ft.Colors.WHITE),
                    border=ft.border.all(1, ft.Colors.with_opacity(0.12, accent)),
                    content=ft.Column(spacing=5, controls=[
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Row(tight=True, spacing=5, controls=[
                                    ft.Icon(icon, size=13, color=accent),
                                    ft.Text(name, size=12,
                                            weight=ft.FontWeight.W_600, color=accent),
                                ]),
                                ft.Row(tight=True, spacing=4, controls=[
                                    status_badge(st_label, st_kind),
                                    ft.TextButton(
                                        tog_lbl,
                                        style=ft.ButtonStyle(color=tog_col),
                                        on_click=_toggle_st,
                                    ),
                                ]),
                            ],
                        ),
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[ft.Text("conf", size=10, color=ft.Colors.WHITE54), lbl_conf],
                        ),
                        ft.Slider(
                            value=conf_v, min=0.05, max=0.95, divisions=18,
                            active_color=accent,
                            inactive_color=ft.Colors.with_opacity(0.15, ft.Colors.WHITE),
                            thumb_color=accent, expand=True, on_change=_chg_conf,
                        ),
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[ft.Text("iou", size=10, color=ft.Colors.WHITE54), lbl_iou],
                        ),
                        ft.Slider(
                            value=iou_v, min=0.05, max=0.95, divisions=18,
                            active_color=SECONDARY,
                            inactive_color=ft.Colors.with_opacity(0.15, ft.Colors.WHITE),
                            thumb_color=SECONDARY, expand=True, on_change=_chg_iou,
                        ),
                        ft.Row(spacing=4, controls=[
                            pt_tf,
                            ft.IconButton(
                                ft.Icons.COPY, icon_size=16,
                                tooltip="Sao chép đường dẫn",
                                icon_color=ft.Colors.WHITE54,
                                on_click=_copy_path,
                            ),
                            ft.IconButton(
                                ft.Icons.CONTENT_PASTE, icon_size=16,
                                tooltip="Dán đường dẫn",
                                icon_color=ft.Colors.WHITE54,
                                on_click=_paste_path,
                            ),
                        ]),
                        ft.Row(spacing=6, controls=[
                            ft.ElevatedButton(
                                "Lưu", icon=ft.Icons.SAVE,
                                style=button_style("primary"), height=28,
                                on_click=_save_m,
                            ),
                            save_lbl,
                        ]),
                    ]),
                )
            )
        return blocks

    detail_panel = ft.Container(
        ref=detail_ref, visible=False,
        padding=ft.padding.only(top=8),
        content=ft.Column(spacing=8, controls=[
            ft.Divider(color=ft.Colors.with_opacity(0.12, ft.Colors.WHITE), height=1),
            # info row
            ft.Row(spacing=8, tight=True, controls=[
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=8, vertical=4),
                    border_radius=8,
                    bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
                    content=ft.Row(tight=True, spacing=4, controls=[
                        ft.Icon(ft.Icons.TAG, size=11, color=ft.Colors.WHITE38),
                        ft.Text(f"ID: {uid}", size=10, color=ft.Colors.WHITE54),
                    ]),
                ),
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=8, vertical=4),
                    border_radius=8,
                    bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
                    content=ft.Row(tight=True, spacing=4, controls=[
                        ft.Icon(ft.Icons.CALENDAR_TODAY, size=11, color=ft.Colors.WHITE38),
                        ft.Text(f"Tạo: {fmt_dt(created)}", size=10, color=ft.Colors.WHITE54),
                    ]),
                ),
            ]),
            # edit fields
            ft.Row(spacing=8, controls=[e_hoten, e_role]),
            e_newpwd,
            ft.Row(spacing=8, controls=[
                ft.ElevatedButton(
                    "Lưu thay đổi", icon=ft.Icons.SAVE,
                    style=button_style("primary"), height=32,
                    on_click=_save_edit,
                ),
                ft.OutlinedButton(
                    "Xóa tài khoản", icon=ft.Icons.DELETE_OUTLINE,
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
            *_make_model_controls(),
        ]),
    )

    return ft.Container(
        ink=True,
        border_radius=12,
        padding=ft.padding.symmetric(horizontal=12, vertical=10),
        bgcolor=ft.Colors.with_opacity(0.09, ft.Colors.WHITE),
        border=ft.border.all(1, ft.Colors.with_opacity(0.10, ft.Colors.WHITE)),
        on_click=_toggle_detail,
        content=ft.Column(spacing=0, controls=[
            ft.Row(
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    _role_dot(role),
                    ft.Column(
                        expand=True, tight=True, spacing=2,
                        controls=[
                            ft.Text(
                                hoten or uname, size=14, weight=ft.FontWeight.W_600,
                                max_lines=1, overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            ft.Row(spacing=6, tight=True, controls=[
                                ft.Text(uname, size=11, color=ft.Colors.WHITE54,
                                        max_lines=1, overflow=ft.TextOverflow.CLIP),
                                ft.Text("·", size=11, color=ft.Colors.WHITE24),
                                status_badge(rlabel, rkind),
                            ]),
                        ],
                    ),
                    ft.Row(spacing=4, tight=True, controls=[
                        ft.Text(fmt_dt(created, "%d/%m"), size=10, color=ft.Colors.WHITE38),
                        ft.Icon(ft.Icons.EXPAND_MORE, size=16, color=ft.Colors.WHITE38),
                    ]),
                ],
            ),
            detail_panel,
        ]),
    )


def build_user_management():
    search_field = inline_field("Tìm tên / tài khoản", ft.Icons.SEARCH)
    active_filter = {"role": "all"}
    list_ref  = ft.Ref[ft.Column]()
    form_ref  = ft.Ref[ft.Container]()
    msg = ft.Text("", size=12, color=ft.Colors.GREEN_300)

    # ── Add-user form fields ──────────────────────────────────────────────
    f_uname  = inline_field("Tên đăng nhập",    ft.Icons.PERSON)
    f_pwd    = inline_field("Mật khẩu",         ft.Icons.LOCK, password=True)
    f_hoten  = inline_field("Họ tên (tùy chọn)")
    f_role   = ft.Dropdown(
        label="Vai trò", options=_ROLE_OPTIONS, value="farmer",
        border_radius=12,
        bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
        border_color=ft.Colors.with_opacity(0.28, ft.Colors.WHITE),
        focused_border_color=PRIMARY,
        label_style=ft.TextStyle(color=ft.Colors.WHITE70, size=12),
        expand=True,
    )
    btn_save = ft.ElevatedButton(
        "Lưu tài khoản", icon=ft.Icons.SAVE,
        style=button_style("primary"), height=40,
    )

    def refresh(keyword: str = "", role_filter: str = "all"):
        kw = keyword.lower()
        users = get_all_users()
        if role_filter != "all":
            users = [u for u in users if u.get("vai_tro") == role_filter]
        if kw:
            users = [
                u for u in users
                if kw in u.get("ten_dang_nhap", "").lower()
                or kw in u.get("ho_ten", "").lower()
            ]
        cards = [_user_card(u, lambda: refresh(search_field.value or "", active_filter["role"]))
                 for u in users] if users else [empty_state("Không tìm thấy người dùng")]
        list_ref.current.controls = cards
        if list_ref.current.page:
            list_ref.current.update()

    def _do_add(e):
        uname = (f_uname.value or "").strip()
        pwd   = (f_pwd.value or "").strip()
        if not uname or not pwd:
            msg.value = "Tài khoản và mật khẩu không được để trống."
            msg.color = ft.Colors.RED_300
            msg.update(); return
        if get_user_by_username(uname):
            msg.value = f"Tài khoản '{uname}' đã tồn tại."
            msg.color = ft.Colors.RED_300
            msg.update(); return
        create_user(uname, pwd, f_role.value or "farmer", f_hoten.value or "")
        msg.value = f"Đã thêm '{uname}' thành công."
        msg.color = ft.Colors.GREEN_300
        msg.update()
        f_uname.value = f_pwd.value = f_hoten.value = ""
        for f in (f_uname, f_pwd, f_hoten): f.update()
        form_ref.current.visible = False
        form_ref.current.update()
        refresh(search_field.value or "", active_filter["role"])

    btn_save.on_click = _do_add

    # ── Filter chips ──────────────────────────────────────────────────────
    filter_chips_ref = ft.Ref[ft.Row]()

    def _build_filter_chips():
        chips = []
        for key, lbl in _ROLE_FILTER:
            is_active = active_filter["role"] == key
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
        active_filter["role"] = key
        filter_chips_ref.current.controls = _build_filter_chips()
        filter_chips_ref.current.update()
        refresh(search_field.value or "", key)

    filter_row = ft.Row(
        ref=filter_chips_ref, spacing=6, scroll=ft.ScrollMode.AUTO,
        controls=_build_filter_chips(),
    )

    user_list = ft.Column(ref=list_ref, spacing=6, controls=[])
    refresh()

    add_form = ft.Container(
        ref=form_ref, visible=False,
        content=glass_container(
            padding=14, radius=14,
            content=ft.Column(spacing=10, controls=[
                section_title("PERSON_ADD", "Thêm tài khoản mới"),
                ft.Row(spacing=8, controls=[f_uname, f_pwd]),
                ft.Row(spacing=8, controls=[f_hoten, f_role]),
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
                        ft.Text("Quản lý tài khoản", size=20, weight=ft.FontWeight.W_700),
                        ft.Text("Nhấn vào tài khoản để xem chi tiết và chỉnh sửa",
                                size=11, color=ft.Colors.WHITE54),
                    ]),
                    ft.ElevatedButton(
                        "Thêm", icon=ft.Icons.PERSON_ADD,
                        style=button_style("primary"), height=36,
                        on_click=lambda e: _toggle_ref(form_ref),
                    ),
                ],
            ),
            ft.Row(spacing=8, controls=[
                search_field,
                ft.IconButton(
                    ft.Icons.SEARCH, icon_color=ft.Colors.WHITE70,
                    on_click=lambda e: refresh(search_field.value or "", active_filter["role"]),
                ),
            ]),
            filter_row,
            msg,
            add_form,
            user_list,
        ],
    )


def _toggle_ref(ref: ft.Ref) -> None:
    ref.current.visible = not ref.current.visible
    ref.current.update()
