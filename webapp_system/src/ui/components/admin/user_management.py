import flet as ft

from bll.admin.user_management import (
    create_user,
    get_user_by_username,
    list_users as get_all_users,
)
from ui.theme import (
    PRIMARY,
    button_style,
    empty_state,
    glass_container,
    info_strip,
    inline_field,
    metric_card,
    page_header,
    section_title,
)

from .user_management_cards import ROLE_OPTIONS, build_user_card
from .user_management_filters import build_filter_chips, filter_users


def build_user_management():
    search_field = inline_field("Tim ten / tai khoan", ft.Icons.SEARCH)
    active_filter = {"role": "all"}
    list_ref = ft.Ref[ft.Column]()
    form_ref = ft.Ref[ft.Container]()
    filter_chips_ref = ft.Ref[ft.Row]()
    msg = ft.Text("", size=12, color=ft.Colors.GREEN_300)
    summary_ref = ft.Ref[ft.Row]()
    summary_row = ft.Row(ref=summary_ref, spacing=8, wrap=True, run_spacing=8, controls=[])

    f_uname = inline_field("Ten dang nhap", ft.Icons.PERSON)
    f_pwd = inline_field("Mat khau", ft.Icons.LOCK, password=True)
    f_hoten = inline_field("Ho ten (tuy chon)")
    f_role = ft.Dropdown(
        label="Vai tro",
        options=ROLE_OPTIONS,
        value="farmer",
        border_radius=12,
        bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
        border_color=ft.Colors.with_opacity(0.28, ft.Colors.WHITE),
        focused_border_color=PRIMARY,
        label_style=ft.TextStyle(color=ft.Colors.WHITE70, size=12),
        expand=True,
    )
    btn_save = ft.ElevatedButton(
        "Luu tai khoan",
        icon=ft.Icons.SAVE,
        style=button_style("primary"),
        height=40,
    )

    def refresh(keyword: str = "", role_filter: str = "all"):
        all_users = get_all_users()
        role_counts = {
            "expert": sum(1 for user in all_users if user.get("vai_tro") == "expert"),
            "farmer": sum(1 for user in all_users if user.get("vai_tro") == "farmer"),
            "admin": sum(1 for user in all_users if user.get("vai_tro") == "admin"),
        }
        users = filter_users(get_all_users(), keyword, role_filter)
        summary_ref.current.controls = [
            ft.Container(expand=1, content=metric_card("Tong tai khoan", str(len(all_users)), ft.Icons.GROUPS, PRIMARY)),
            ft.Container(expand=1, content=metric_card("Expert", str(role_counts["expert"]), ft.Icons.SUPPORT_AGENT, ft.Colors.CYAN_300)),
            ft.Container(expand=1, content=metric_card("Farmer", str(role_counts["farmer"]), ft.Icons.AGRICULTURE, ft.Colors.GREEN_300)),
            ft.Container(expand=1, content=metric_card("Admin", str(role_counts["admin"]), ft.Icons.ADMIN_PANEL_SETTINGS, ft.Colors.AMBER_300)),
        ]
        list_ref.current.controls = (
            [
                build_user_card(
                    user,
                    lambda: refresh(search_field.value or "", active_filter["role"]),
                )
                for user in users
            ]
            if users
            else [empty_state("Khong tim thay nguoi dung")]
        )
        if summary_ref.current.page:
            summary_ref.current.update()
        if list_ref.current.page:
            list_ref.current.update()

    def _do_add(e):
        username = (f_uname.value or "").strip()
        password = (f_pwd.value or "").strip()
        if not username or not password:
            msg.value = "Tai khoan va mat khau khong duoc de trong."
            msg.color = ft.Colors.RED_300
            msg.update()
            return
        if get_user_by_username(username):
            msg.value = f"Tai khoan '{username}' da ton tai."
            msg.color = ft.Colors.RED_300
            msg.update()
            return

        create_user(username, password, f_role.value or "farmer", f_hoten.value or "")
        msg.value = f"Da them '{username}' thanh cong."
        msg.color = ft.Colors.GREEN_300
        msg.update()

        f_uname.value = ""
        f_pwd.value = ""
        f_hoten.value = ""
        for field in (f_uname, f_pwd, f_hoten):
            field.update()

        _toggle_ref(form_ref)
        refresh(search_field.value or "", active_filter["role"])

    def _render_filter_row():
        filter_chips_ref.current.controls = build_filter_chips(active_filter["role"], _on_filter)
        filter_chips_ref.current.update()

    def _on_filter(key: str):
        active_filter["role"] = key
        _render_filter_row()
        refresh(search_field.value or "", key)

    btn_save.on_click = _do_add

    filter_row = ft.Row(
        ref=filter_chips_ref,
        spacing=6,
        scroll=ft.ScrollMode.AUTO,
        controls=build_filter_chips(active_filter["role"], _on_filter),
    )
    user_list = ft.Column(ref=list_ref, spacing=6, controls=[])
    add_form = ft.Container(
        ref=form_ref,
        visible=False,
        content=glass_container(
            padding=14,
            radius=14,
            content=ft.Column(
                spacing=10,
                controls=[
                    section_title("PERSON_ADD", "Them tai khoan moi"),
                    ft.Row(spacing=8, controls=[f_uname, f_pwd]),
                    ft.Row(spacing=8, controls=[f_hoten, f_role]),
                    btn_save,
                ],
            ),
        ),
    )

    refresh()

    return ft.Column(
        expand=True,
        spacing=12,
        scroll=ft.ScrollMode.AUTO,
        controls=[
            page_header(
                "Accounts",
                "Tap trung vao tai khoan, vai tro va thao tac chi tiet thay vi bang CRUD day dac.",
                icon_name="GROUPS",
                actions=[
                    ft.ElevatedButton(
                        "Them",
                        icon=ft.Icons.PERSON_ADD,
                        style=button_style("primary"),
                        height=36,
                        on_click=lambda e: _toggle_ref(form_ref),
                    )
                ],
            ),
            info_strip(
                "Mo tung account de sua nhanh, reset mat khau tam hoac xoa. "
                "Bo loc role va tim kiem chi tac dong tren danh sach hien tai.",
                tone="neutral",
            ),
            summary_row,
            ft.Row(
                spacing=8,
                controls=[
                    search_field,
                    ft.IconButton(
                        ft.Icons.SEARCH,
                        icon_color=ft.Colors.WHITE70,
                        on_click=lambda e: refresh(search_field.value or "", active_filter["role"]),
                    ),
                ],
            ),
            glass_container(
                padding=12,
                radius=16,
                content=ft.Column(spacing=10, controls=[filter_row, msg, add_form]),
            ),
            user_list,
        ],
    )


def _toggle_ref(ref: ft.Ref) -> None:
    ref.current.visible = not ref.current.visible
    ref.current.update()
