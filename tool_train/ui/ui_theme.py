from __future__ import annotations

import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox

# Dark-gray palette for Con Bo Cuoi tool suite.
PRIMARY = "#8B7BFF"
PRIMARY_DARK = "#7360FF"
PRIMARY_SOFT = "#2A263D"
PRIMARY_GLOW = "#B7AEFF"
SUCCESS = "#4BDC6B"
WARNING = "#F59E0B"
DANGER = "#FF5656"
INFO = "#22D3EE"

TEXT = "#F3F4F6"
TEXT_DIM = "#D1D5DB"
TEXT_DARK = TEXT
TEXT_MUTED = "#9CA3AF"
TEXT_SOFT = "#6B7280"

BG = "#2B2F36"
BG2 = "#343942"
BG3 = "#414751"
BG4 = "#4D5561"
BG5 = "#1F232A"
BG6 = "#171A20"
SIDEBAR = BG2
BORDER = "#575F6C"
INPUT_BG = "#3B414A"
INPUT_FG = TEXT_DIM
INPUT_MUTED_FG = TEXT_SOFT
INPUT_BORDER = BORDER

CHART_PRIMARY = "#7C3AED"
CHART_SECONDARY = "#06B6D4"
OVERLAY = "#000000"
CARD_RADIUS = 12
INPUT_RADIUS = 8
PILL_RADIUS = 999
SECTION_PAD_X = 18
SECTION_PAD_Y = 14
UI_FONT = "Segoe UI"

ACCENT = PRIMARY
ACCENT2 = PRIMARY_DARK
ACCENT3 = PRIMARY_SOFT

GROUP_COLORS = [
    "#7C3AED", "#06B6D4", "#4BDC6B", "#F59E0B",
    "#A78BFA", "#38BDF8", "#34D399", "#FB7185",
]

_MOJIBAKE_MARKERS = ("Ã", "Â", "â", "ð", "Ä", "Æ", "á»", "áº", "Tá»", "ChÆ", "Ä")
_CP1252_REVERSE = {}
for b in range(256):
    try:
        _CP1252_REVERSE[bytes([b]).decode("cp1252")] = b
    except UnicodeDecodeError:
        pass
for b in range(0x80, 0xA0):
    _CP1252_REVERSE.setdefault(chr(b), b)

_SILENCED_STD_STREAM = None


def _looks_mojibake(text: str) -> bool:
    return any(m in text for m in _MOJIBAKE_MARKERS)


def _to_sloppy_cp1252_bytes(text: str) -> bytes:
    out = bytearray()
    for ch in text:
        o = ord(ch)
        if o <= 0x7F:
            out.append(o)
        elif ch in _CP1252_REVERSE:
            out.append(_CP1252_REVERSE[ch])
        else:
            raise UnicodeEncodeError("sloppy-cp1252", ch, 0, 1, "character not reversible")
    return bytes(out)


def normalize_text(text):
    if not isinstance(text, str) or not text:
        return text
    cur = text
    for _ in range(4):
        if not _looks_mojibake(cur):
            break
        try:
            nxt = _to_sloppy_cp1252_bytes(cur).decode("utf-8")
        except Exception:
            break
        if nxt == cur:
            break
        cur = nxt
    return cur


def normalize_value(value):
    if isinstance(value, str):
        return normalize_text(value)
    if isinstance(value, tuple):
        return tuple(normalize_value(v) for v in value)
    if isinstance(value, list):
        return [normalize_value(v) for v in value]
    return value


def silence_console_output() -> None:
    global _SILENCED_STD_STREAM
    if _SILENCED_STD_STREAM is None:
        _SILENCED_STD_STREAM = open(os.devnull, "w", encoding="utf-8")
    sys.stdout = _SILENCED_STD_STREAM
    sys.stderr = _SILENCED_STD_STREAM


def _wrap_widget_class(cls, keys=("text", "placeholder_text")):
    if getattr(cls, "_ui_theme_patched", False):
        return
    orig_init = cls.__init__
    def __init__(self, *args, **kwargs):
        for key in keys:
            if key in kwargs:
                kwargs[key] = normalize_value(kwargs[key])
        orig_init(self, *args, **kwargs)
    cls.__init__ = __init__

    if hasattr(cls, "configure"):
        orig_cfg = cls.configure
        def configure(self, cnf=None, **kwargs):
            for key in keys:
                if key in kwargs:
                    kwargs[key] = normalize_value(kwargs[key])
            return orig_cfg(self, cnf, **kwargs)
        cls.configure = configure
        if hasattr(cls, "config"):
            cls.config = configure
    cls._ui_theme_patched = True


def _bind_ctk_interactions(widget, *, hover_color: str | None = None,
                           text_hover: str | None = None,
                           press_color: str | None = None) -> None:
    if getattr(widget, "_ui_theme_fx_bound", False):
        return
    try:
        base_fg = str(widget.cget("fg_color"))
    except Exception:
        base_fg = None
    try:
        base_text = str(widget.cget("text_color"))
    except Exception:
        base_text = None

    def _apply(fg=None, text=None):
        kwargs = {}
        if fg is not None:
            kwargs["fg_color"] = fg
        if text is not None:
            kwargs["text_color"] = text
        if kwargs:
            try:
                widget.configure(**kwargs)
            except Exception:
                pass

    def _enter(_event):
        _apply(hover_color, text_hover)

    def _leave(_event):
        _apply(base_fg, base_text)

    def _press(_event):
        _apply(press_color or hover_color or base_fg, text_hover or base_text)

    widget.bind("<Enter>", _enter, add="+")
    widget.bind("<Leave>", _leave, add="+")
    widget.bind("<ButtonPress-1>", _press, add="+")
    widget.bind("<ButtonRelease-1>", _enter, add="+")
    widget._ui_theme_fx_bound = True


def patch_tk_text() -> None:
    for cls in (tk.Label, tk.Button, tk.Checkbutton, tk.Radiobutton, tk.Message):
        _wrap_widget_class(cls, ("text",))
    _wrap_widget_class(ttk.Button, ("text",))
    _wrap_widget_class(ttk.Label, ("text",))
    _wrap_widget_class(ttk.Checkbutton, ("text",))
    _wrap_widget_class(ttk.Radiobutton, ("text",))
    _wrap_widget_class(ttk.Combobox, ("text", "values"))

    if not getattr(tk.Tk, "_ui_theme_title_patched", False):
        _orig_tk_title = tk.Tk.title
        _orig_top_title = tk.Toplevel.title
        def _title(self, text=None):
            if text is None:
                return _orig_tk_title(self)
            return _orig_tk_title(self, normalize_text(text))
        def _top_title(self, text=None):
            if text is None:
                return _orig_top_title(self)
            return _orig_top_title(self, normalize_text(text))
        tk.Tk.title = _title
        tk.Toplevel.title = _top_title
        tk.Tk._ui_theme_title_patched = True

    if not getattr(messagebox, "_ui_theme_patched", False):
        for name in ("showinfo", "showwarning", "showerror", "askyesno", "askokcancel", "askquestion"):
            if hasattr(messagebox, name):
                orig = getattr(messagebox, name)
                def _make(orig_func):
                    def _wrapped(title=None, message=None, *args, **kwargs):
                        if title is not None:
                            title = normalize_text(title)
                        if message is not None:
                            message = normalize_text(message)
                        return orig_func(title, message, *args, **kwargs)
                    return _wrapped
                setattr(messagebox, name, _make(orig))
        messagebox._ui_theme_patched = True


def patch_customtkinter_text(ctk) -> None:
    for name in ("CTkLabel", "CTkButton", "CTkCheckBox", "CTkRadioButton", "CTkEntry"):
        cls = getattr(ctk, name, None)
        if cls is not None:
            _wrap_widget_class(cls, ("text", "placeholder_text"))


def setup_ctk(ctk) -> None:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    patch_customtkinter_text(ctk)


def build_app_header(ctk, parent, *, title: str, subtitle: str, status_text: str | None = None,
                     status_color: str = ACCENT):
    header = ctk.CTkFrame(
        parent,
        fg_color=BG2,
        corner_radius=CARD_RADIUS,
        border_width=1,
        border_color=BORDER,
    )

    logo_img = None
    try:
        from PIL import Image as PILImage
        import os
        # 1. Thử đường dẫn logo local trong tool_train trước
        logo_path = os.path.join(os.path.dirname(__file__), "data", "logo.png")
        if not os.path.exists(logo_path):
            # 2. Thử đường dẫn webapp_system (4 cấp thư mục từ ui_theme.py: ui -> src -> tool_train -> Con_Bo_Cuoi_App -> webapp_system)
            logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "webapp_system", "data", "logo.png")
        
        if os.path.exists(logo_path):
            pil_img = PILImage.open(logo_path)
            # Tính toán tỷ lệ gốc để không bị bóp méo
            orig_w, orig_h = pil_img.size
            target_h = 48
            target_w = int(orig_w * (target_h / orig_h))
            logo_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(target_w, target_h))
    except Exception:
        pass

    if logo_img:
        logo_lbl = ctk.CTkLabel(header, image=logo_img, text="")
        logo_lbl.pack(side="left", padx=(SECTION_PAD_X, 0), pady=18)

    title_wrap = ctk.CTkFrame(header, fg_color="transparent")
    title_wrap.pack(side="left", fill="x", expand=True, padx=SECTION_PAD_X, pady=18)
    ctk.CTkLabel(
        title_wrap,
        text=title,
        font=(UI_FONT, 26, "bold"),
        text_color=TEXT,
    ).pack(anchor="w")
    ctk.CTkLabel(
        title_wrap,
        text=subtitle,
        font=(UI_FONT, 12),
        text_color=TEXT_MUTED,
    ).pack(anchor="w", pady=(4, 0))
    status_lbl = None
    if status_text is not None:
        status_lbl = ctk.CTkLabel(
            header,
            text=status_text,
            font=(UI_FONT, 12, "bold"),
            text_color="white",
            fg_color=status_color,
            corner_radius=PILL_RADIUS,
            padx=18,
            pady=8,
        )
        status_lbl.pack(side="right", padx=SECTION_PAD_X, pady=18)
    return header, status_lbl


def build_app_taskbar(ctk, parent, *, title: str, subtitle: str = "", status_text: str | None = None,
                      status_color: str = ACCENT, actions: list[dict] | None = None, **_ignored):
    bar = ctk.CTkFrame(
        parent,
        fg_color=BG2,
        corner_radius=CARD_RADIUS + 6,
        border_width=1,
        border_color=BORDER,
        height=124,
    )
    inner = ctk.CTkFrame(bar, fg_color="transparent")
    inner.pack(fill="both", expand=True, padx=28, pady=22)

    logo_img = None
    try:
        from PIL import Image as PILImage
        import os
        # 1. Thử đường dẫn logo local trong tool_train trước
        logo_path = os.path.join(os.path.dirname(__file__), "data", "logo.png")
        if not os.path.exists(logo_path):
            # 2. Thử đường dẫn webapp_system (4 cấp thư mục từ ui_theme.py: ui -> src -> tool_train -> Con_Bo_Cuoi_App -> webapp_system)
            logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "webapp_system", "data", "logo.png")
        
        if os.path.exists(logo_path):
            pil_img = PILImage.open(logo_path)
            # Tính toán tỷ lệ gốc để không bị bóp méo
            orig_w, orig_h = pil_img.size
            target_h = 48
            target_w = int(orig_w * (target_h / orig_h))
            logo_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(target_w, target_h))
    except Exception:
        pass

    if logo_img:
        logo_wrap = ctk.CTkFrame(
            inner,
            fg_color=BG3,
            corner_radius=18,
            width=78,
            height=78,
            border_width=1,
            border_color=BORDER,
        )
        logo_wrap.pack(side="left", padx=(0, 18))
        logo_wrap.pack_propagate(False)
        logo_lbl = ctk.CTkLabel(logo_wrap, image=logo_img, text="")
        logo_lbl.place(relx=0.5, rely=0.5, anchor="center")

    left = ctk.CTkFrame(inner, fg_color="transparent")
    left.pack(side="left", fill="x", expand=True)

    title_row = ctk.CTkFrame(left, fg_color="transparent")
    title_row.pack(anchor="w")

    ctk.CTkLabel(
        title_row,
        text=title,
        font=(UI_FONT, 28, "bold"),
        text_color=TEXT,
    ).pack(side="left")

    if subtitle:
        ctk.CTkLabel(
            left,
            text=subtitle,
            font=(UI_FONT, 12),
            text_color=TEXT_MUTED,
            justify="left",
        ).pack(anchor="w", pady=(2, 0))

    if actions:
        acts = ctk.CTkFrame(title_row, fg_color="transparent")
        acts.pack(side="left", padx=(16, 0))
        for action in actions:
            btn = ctk.CTkButton(
                acts,
                text=action.get("text", ""),
                command=action.get("command"),
                fg_color=BG3,
                hover_color=PRIMARY_SOFT,
                text_color=TEXT_DIM,
                border_width=1,
                border_color=BORDER,
                corner_radius=16,
                height=38,
                font=(UI_FONT, 12, "bold"),
                width=0,
            )
            btn.pack(side="left", padx=(0, 8))
            _bind_ctk_interactions(btn, hover_color=BG4, text_hover=TEXT, press_color=PRIMARY_SOFT)

    status_lbl = None
    if status_text is not None:
        status_lbl = ctk.CTkLabel(
            inner,
            text=status_text,
            font=(UI_FONT, 13, "bold"),
            text_color="white",
            fg_color=status_color,
            corner_radius=PILL_RADIUS,
            padx=18,
            pady=9,
        )
        status_lbl.pack(side="right")
    nav_host = ctk.CTkFrame(bar, fg_color="transparent")
    bar._nav_host = nav_host
    return bar, status_lbl


def build_app_shell(ctk, parent, *, corner_radius: int = CARD_RADIUS):
    shell = ctk.CTkFrame(
        parent,
        fg_color=BG2,
        corner_radius=corner_radius,
        border_width=1,
        border_color=BORDER,
    )
    return shell


def build_tabview(ctk, parent):
    tabview = ctk.CTkTabview(
        parent,
        fg_color="transparent",
        corner_radius=CARD_RADIUS,
        segmented_button_fg_color=BG3,
        segmented_button_selected_color=ACCENT,
        segmented_button_selected_hover_color=ACCENT2,
        segmented_button_unselected_color=BG3,
        segmented_button_unselected_hover_color=BG4,
        text_color=TEXT,
        border_width=0,
    )
    try:
        tabview._segmented_button.configure(
            height=42,
            corner_radius=18,
            font=(UI_FONT, 13, "bold"),
            fg_color=BG3,
            selected_color=ACCENT,
            selected_hover_color=ACCENT2,
            unselected_color=BG3,
            unselected_hover_color=BG4,
            text_color=TEXT,
            text_color_disabled=TEXT_MUTED,
        )
        tabview._segmented_button.grid_configure(sticky="w", padx=18, pady=(2, 14))
    except Exception:
        pass
    return tabview


def build_page_body(ctk, parent, *, padx: int = 10, pady: int = 10):
    shell = ctk.CTkFrame(parent, fg_color=BG, corner_radius=22, border_width=0)
    shell.pack(fill="both", expand=True, padx=padx, pady=pady)
    return shell


def build_card(ctk, parent, *, elevated: bool = False, fg_color: str = BG2):
    return ctk.CTkFrame(
        parent,
        fg_color=fg_color,
        corner_radius=CARD_RADIUS + 2 if not elevated else CARD_RADIUS + 6,
        border_width=1,
        border_color=BORDER,
    )


def build_dashboard_banner(ctk, parent, *, eyebrow: str, title: str, description: str,
                           accent: str = ACCENT, compact: bool = False):
    card = ctk.CTkFrame(
        parent,
        fg_color=BG2,
        corner_radius=CARD_RADIUS + 8,
        border_width=1,
        border_color=BORDER,
    )
    pad_x = 20 if compact else 26
    pad_y = 16 if compact else 22
    body = ctk.CTkFrame(card, fg_color="transparent")
    body.pack(fill="both", expand=True, padx=pad_x, pady=pad_y)

    ctk.CTkLabel(
        body,
        text=eyebrow,
        font=(UI_FONT, 10, "bold"),
        text_color=accent,
    ).pack(anchor="w")
    ctk.CTkLabel(
        body,
        text=title,
        font=(UI_FONT, 26 if not compact else 22, "bold"),
        text_color=TEXT,
        justify="left",
    ).pack(anchor="w", pady=(6, 0))
    ctk.CTkLabel(
        body,
        text=description,
        font=(UI_FONT, 12),
        text_color=TEXT_MUTED,
        justify="left",
        wraplength=980,
    ).pack(anchor="w", pady=(8, 0))
    return card


def build_stat_card(ctk, parent, *, title: str, value: str, hint: str = "",
                    accent: str = ACCENT, width: int = 0):
    card = ctk.CTkFrame(
        parent,
        fg_color=BG3,
        corner_radius=CARD_RADIUS + 4,
        border_width=1,
        border_color=BORDER,
        width=width,
    )
    body = ctk.CTkFrame(card, fg_color="transparent")
    body.pack(fill="both", expand=True, padx=16, pady=14)
    ctk.CTkLabel(
        body,
        text=title,
        font=(UI_FONT, 10, "bold"),
        text_color=accent,
    ).pack(anchor="w")
    ctk.CTkLabel(
        body,
        text=value,
        font=(UI_FONT, 21, "bold"),
        text_color=TEXT,
    ).pack(anchor="w", pady=(6, 0))
    if hint:
        ctk.CTkLabel(
            body,
            text=hint,
            font=(UI_FONT, 11),
            text_color=TEXT_MUTED,
            justify="left",
            wraplength=220,
        ).pack(anchor="w", pady=(4, 0))
    def _on_enter(_event):
        try:
            card.configure(border_color=accent)
        except Exception:
            pass
    def _on_leave(_event):
        try:
            card.configure(border_color=BORDER)
        except Exception:
            pass
    card.bind("<Enter>", _on_enter, add="+")
    card.bind("<Leave>", _on_leave, add="+")
    body.bind("<Enter>", _on_enter, add="+")
    body.bind("<Leave>", _on_leave, add="+")
    return card


def build_metric_strip(ctk, parent, metrics: list[dict], *, columns: int = 4):
    grid = ctk.CTkFrame(parent, fg_color="transparent")
    for col in range(columns):
        grid.grid_columnconfigure(col, weight=1)
    for idx, metric in enumerate(metrics):
        card = build_stat_card(
            ctk,
            grid,
            title=metric.get("title", ""),
            value=metric.get("value", ""),
            hint=metric.get("hint", ""),
            accent=metric.get("accent", ACCENT),
        )
        card.grid(row=idx // columns, column=idx % columns, sticky="nsew", padx=6, pady=6)
    return grid


def build_workspace_card(ctk, parent, *, icon: str, eyebrow: str, title: str, description: str,
                         accent: str = ACCENT, command=None, button_text: str = "Mở không gian làm việc"):
    card = ctk.CTkFrame(
        parent,
        fg_color=BG3,
        corner_radius=CARD_RADIUS + 8,
        border_width=1,
        border_color=BORDER,
    )
    body = ctk.CTkFrame(card, fg_color="transparent")
    body.pack(fill="both", expand=True, padx=20, pady=20)

    top = ctk.CTkFrame(body, fg_color="transparent")
    top.pack(fill="x")

    icon_wrap = ctk.CTkFrame(
        top,
        fg_color=accent,
        corner_radius=18,
        width=54,
        height=54,
    )
    icon_wrap.pack(side="left")
    icon_wrap.pack_propagate(False)
    ctk.CTkLabel(
        icon_wrap,
        text=icon,
        font=(UI_FONT, 24),
        text_color="white",
    ).place(relx=0.5, rely=0.5, anchor="center")

    text_col = ctk.CTkFrame(top, fg_color="transparent")
    text_col.pack(side="left", fill="x", expand=True, padx=(14, 0))
    ctk.CTkLabel(
        text_col,
        text=eyebrow,
        font=(UI_FONT, 10, "bold"),
        text_color=accent,
    ).pack(anchor="w")
    ctk.CTkLabel(
        text_col,
        text=title,
        font=(UI_FONT, 20, "bold"),
        text_color=TEXT,
    ).pack(anchor="w", pady=(4, 0))

    ctk.CTkLabel(
        body,
        text=description,
        font=(UI_FONT, 12),
        text_color=TEXT_DIM,
        justify="left",
        wraplength=300,
    ).pack(anchor="w", pady=(14, 16))

    btn = ctk.CTkButton(
        body,
        text=button_text,
        command=command,
        fg_color=accent,
        hover_color=ACCENT2 if accent == ACCENT else accent,
        text_color="white",
        corner_radius=14,
        height=42,
        font=(UI_FONT, 13, "bold"),
    )
    btn.pack(anchor="w")
    _bind_ctk_interactions(btn, hover_color=PRIMARY_GLOW if accent == ACCENT else accent, text_hover="white")
    def _on_enter(_event):
        try:
            card.configure(border_color=accent, fg_color=BG2)
        except Exception:
            pass
    def _on_leave(_event):
        try:
            card.configure(border_color=BORDER, fg_color=BG3)
        except Exception:
            pass
    for widget in (card, body, top, text_col):
        widget.bind("<Enter>", _on_enter, add="+")
        widget.bind("<Leave>", _on_leave, add="+")
    return card, btn


def build_empty_state(ctk, parent, *, title: str, description: str, accent: str = ACCENT):
    card = ctk.CTkFrame(
        parent,
        fg_color=BG2,
        corner_radius=CARD_RADIUS + 8,
        border_width=1,
        border_color=BORDER,
    )
    body = ctk.CTkFrame(card, fg_color="transparent")
    body.pack(fill="both", expand=True, padx=24, pady=22)
    ctk.CTkLabel(
        body,
        text=title,
        font=(UI_FONT, 18, "bold"),
        text_color=accent,
    ).pack(anchor="w")
    ctk.CTkLabel(
        body,
        text=description,
        font=(UI_FONT, 12),
        text_color=TEXT_MUTED,
        justify="left",
        wraplength=720,
    ).pack(anchor="w", pady=(6, 0))
    return card


def style_ctk_button(button, *, kind: str = "primary") -> None:
    if kind == "primary":
        button.configure(
            fg_color=ACCENT,
            hover_color=ACCENT2,
            text_color="white",
            corner_radius=8,
            border_width=0,
            font=(UI_FONT, 13, "bold"),
        )
        _bind_ctk_interactions(button, hover_color=PRIMARY_GLOW, text_hover="white", press_color=ACCENT2)
        return
    if kind == "secondary":
        button.configure(
            fg_color=BG3,
            hover_color=BG4,
            text_color=TEXT_DIM,
            corner_radius=8,
            border_width=1,
            border_color=BORDER,
            font=(UI_FONT, 13, "bold"),
        )
        _bind_ctk_interactions(button, hover_color=BG4, text_hover=TEXT, press_color=PRIMARY_SOFT)
        return
    if kind == "ghost":
        button.configure(
            fg_color="transparent",
            hover_color=BG3,
            text_color=TEXT_DIM,
            corner_radius=8,
            border_width=0,
            font=(UI_FONT, 12, "bold"),
        )
        _bind_ctk_interactions(button, hover_color=BG3, text_hover=TEXT, press_color=BG4)
        return


def apply_entry_theme(widget, *, fg: str | None = None, bg: str | None = None) -> None:
    fg = fg or INPUT_FG
    bg = bg or INPUT_BG
    widget.configure(
        bg=bg,
        fg=fg,
        insertbackground=fg,
        disabledbackground=BG3,
        disabledforeground=TEXT_MUTED,
        readonlybackground=bg,
        relief="flat",
        highlightthickness=1,
        highlightbackground=INPUT_BORDER,
        highlightcolor=ACCENT,
        selectbackground=ACCENT,
        selectforeground="white",
    )


def apply_textbox_theme(widget, *, dark: bool = False) -> None:
    if dark:
        widget.configure(
            bg="#111827",
            fg="#E5E7EB",
            insertbackground="#F8FAFC",
            selectbackground=ACCENT,
            selectforeground="white",
            relief="flat",
        )
        return
    widget.configure(
        bg=INPUT_BG,
        fg=INPUT_FG,
        insertbackground=INPUT_FG,
        selectbackground=ACCENT,
        selectforeground="white",
        relief="flat",
    )


def apply_ttk_theme(style: ttk.Style) -> None:
    patch_tk_text()
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure(".", background=BG, foreground=TEXT)
    style.configure("TNotebook", background=BG, borderwidth=0)
    style.configure(
        "TNotebook.Tab",
        background=BG3,
        foreground=TEXT_DIM,
        padding=[16, 8],
        font=(UI_FONT, 10, "bold"),
        borderwidth=0,
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", ACCENT), ("active", ACCENT3)],
        foreground=[("selected", "white"), ("active", TEXT)],
    )

    style.configure(
        "TCombobox",
        fieldbackground=BG2,
        background=BG2,
        foreground=TEXT,
        bordercolor=BORDER,
        lightcolor=BORDER,
        darkcolor=BORDER,
        arrowcolor=TEXT,
        padding=6,
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", BG2)],
        background=[("readonly", BG2)],
        foreground=[("readonly", TEXT)],
        selectbackground=[("readonly", BG2)],
        selectforeground=[("readonly", TEXT)],
    )

    style.configure(
        "Vertical.TScrollbar",
        background=BG4,
        troughcolor=BG3,
        arrowcolor=TEXT_DIM,
        bordercolor=BG3,
    )
    style.configure(
        "Horizontal.TScrollbar",
        background=BG4,
        troughcolor=BG3,
        arrowcolor=TEXT_DIM,
        bordercolor=BG3,
    )


# ─────────────────────────────────────────────────────────────────────────────
# NEW HELPERS – dùng trong yolo_mixin, cnn_jilsa, netmb_plos
# ─────────────────────────────────────────────────────────────────────────────

def build_section_label(ctk, parent, text: str) -> None:
    """Tiêu đề section: accent pill + text, không cần separator."""
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(fill="x", pady=(12, 4))
    ctk.CTkLabel(
        row,
        text="▍",
        font=(UI_FONT, 16, "bold"),
        text_color=ACCENT,
        width=14,
    ).pack(side="left")
    ctk.CTkLabel(
        row,
        text=text,
        font=(UI_FONT, 11, "bold"),
        text_color=ACCENT,
    ).pack(side="left", padx=(4, 0))


def build_form_row_ctk(ctk, parent, label: str, widget) -> None:
    """Đặt label + widget thành 1 hàng ngang với CTkLabel."""
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(fill="x", pady=2)
    ctk.CTkLabel(
        row,
        text=label,
        font=(UI_FONT, 11),
        text_color=TEXT_DIM,
        width=130,
        anchor="w",
    ).pack(side="left")
    widget.pack(side="left", fill="x", expand=True)


def build_ctk_spinbox(ctk, parent, textvariable, from_: float, to: float,
                       increment: float = 1, width: int = 90, fmt: str = "") -> "ctk.CTkFrame":
    """
    Spinbox giả bằng CTkEntry + hai CTkButton ▲▼.
    Giữ nguyên textvariable (tk.IntVar / tk.DoubleVar) để logic không thay đổi.
    """
    frame = ctk.CTkFrame(parent, fg_color="transparent")

    entry = ctk.CTkEntry(
        frame,
        textvariable=textvariable,
        width=width,
        font=(UI_FONT, 11),
        fg_color=INPUT_BG,
        border_color=BORDER,
        text_color=TEXT,
    )
    entry.pack(side="left")

    btn_col = ctk.CTkFrame(frame, fg_color="transparent")
    btn_col.pack(side="left", padx=(2, 0))

    def _step(direction: int):
        try:
            cur = float(textvariable.get())
        except (ValueError, tk.TclError):
            cur = from_
        nxt = max(from_, min(to, cur + direction * increment))
        if isinstance(textvariable, tk.IntVar):
            textvariable.set(int(round(nxt)))
        else:
            textvariable.set(round(nxt, 6))

    ctk.CTkButton(
        btn_col, text="▲", width=26, height=18,
        font=(UI_FONT, 9, "bold"),
        fg_color=BG3, hover_color=BG4,
        text_color=TEXT_DIM, corner_radius=4,
        command=lambda: _step(1),
    ).pack()
    ctk.CTkButton(
        btn_col, text="▼", width=26, height=18,
        font=(UI_FONT, 9, "bold"),
        fg_color=BG3, hover_color=BG4,
        text_color=TEXT_DIM, corner_radius=4,
        command=lambda: _step(-1),
    ).pack(pady=(1, 0))

    return frame


def build_epoch_header_ctk(ctk, parent,
                            epoch_lbl_attr: str,
                            pct_lbl_attr: str,
                            elapsed_lbl_attr: str,
                            acc_lbl_attr: str | None = None,
                            prog_lbl_attr: str | None = None,
                            accent_color: str = ACCENT) -> tuple:
    """
    Tạo epoch counter card + progress bar dùng CTk widgets.
    Trả về (progressbar_widget,) để logic có thể gọi progressbar["value"] = x.
    Gán các label attr vào self (owner) bằng setattr sau khi gọi.
    """
    # epoch box card
    ep_card = ctk.CTkFrame(
        parent,
        fg_color=BG3,
        corner_radius=CARD_RADIUS,
        border_width=1,
        border_color=accent_color,
    )
    ep_card.pack(fill="x", padx=8, pady=(8, 4))

    inner = ctk.CTkFrame(ep_card, fg_color="transparent")
    inner.pack(fill="x", padx=16, pady=10)

    ctk.CTkLabel(
        inner,
        text="EPOCH",
        font=(UI_FONT, 9, "bold"),
        text_color=TEXT_MUTED,
    ).pack(side="left")

    epoch_lbl = ctk.CTkLabel(
        inner,
        text="— / —",
        font=(UI_FONT, 26, "bold"),
        text_color=accent_color,
    )
    epoch_lbl.pack(side="left", padx=(10, 0))

    pct_lbl = ctk.CTkLabel(
        inner,
        text="0%",
        font=(UI_FONT, 16, "bold"),
        text_color=TEXT_DIM,
    )
    pct_lbl.pack(side="left", padx=(8, 0))

    if acc_lbl_attr:
        acc_lbl = ctk.CTkLabel(
            inner,
            text="Val Acc: —",
            font=(UI_FONT, 11, "bold"),
            text_color=SUCCESS,
        )
        acc_lbl.pack(side="left", padx=(16, 0))
    else:
        acc_lbl = None

    elapsed_lbl = ctk.CTkLabel(
        inner,
        text="",
        font=(UI_FONT, 10),
        text_color=TEXT_MUTED,
    )
    elapsed_lbl.pack(side="right")

    # progress row
    prog_row = ctk.CTkFrame(parent, fg_color="transparent")
    prog_row.pack(fill="x", padx=8, pady=(0, 4))

    if prog_lbl_attr:
        prog_lbl = ctk.CTkLabel(
            prog_row,
            text="—",
            font=(UI_FONT, 10, "bold"),
            text_color=accent_color,
        )
        prog_lbl.pack(side="left", padx=(4, 8))
    else:
        prog_lbl = None

    progressbar = ctk.CTkProgressBar(
        parent,
        fg_color=BG3,
        progress_color=accent_color,
        height=10,
        corner_radius=5,
    )
    progressbar.set(0)
    progressbar.pack(fill="x", padx=8, pady=(0, 6))

    return epoch_lbl, pct_lbl, elapsed_lbl, acc_lbl, prog_lbl, progressbar


def build_log_textbox(ctk, parent, title: str, accent_color: str = ACCENT,
                      tags: list[tuple] | None = None) -> tk.Text:
    """
    Tạo log panel với title + CTkTextbox-styled tk.Text.
    Trả về tk.Text để logic có thể gọi .insert(), .tag_config(), .configure().
    """
    log_frame = ctk.CTkFrame(
        parent,
        fg_color=BG2,
        corner_radius=CARD_RADIUS,
        border_width=1,
        border_color=BORDER,
    )
    log_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    header = ctk.CTkFrame(log_frame, fg_color="transparent")
    header.pack(fill="x", padx=12, pady=(8, 4))
    ctk.CTkLabel(
        header,
        text="⬛",
        font=(UI_FONT, 8),
        text_color="#FF5F57",
    ).pack(side="left")
    ctk.CTkLabel(
        header,
        text="⬛",
        font=(UI_FONT, 8),
        text_color="#FFBD2E",
    ).pack(side="left", padx=2)
    ctk.CTkLabel(
        header,
        text="⬛",
        font=(UI_FONT, 8),
        text_color="#28CA41",
    ).pack(side="left")
    ctk.CTkLabel(
        header,
        text=title,
        font=(UI_FONT, 11, "bold"),
        text_color=accent_color,
    ).pack(side="left", padx=(12, 0))

    # scrollbar
    vsb = tk.Scrollbar(log_frame)
    vsb.pack(side="right", fill="y", padx=(0, 4), pady=4)

    text_widget = tk.Text(
        log_frame,
        bg="#0d0d1a",
        fg="#d4d4d4",
        insertbackground="white",
        relief="flat",
        font=("Cascadia Code", 8),
        wrap="word",
        state="disabled",
        yscrollcommand=vsb.set,
        highlightthickness=0,
        borderwidth=0,
    )
    text_widget.pack(fill="both", expand=True, padx=(8, 0), pady=(0, 8))
    vsb.config(command=text_widget.yview)

    # default tags
    _default_tags = [
        ("epoch", ACCENT2),
        ("ok", SUCCESS),
        ("warn", WARNING),
        ("err", DANGER),
        ("info", INFO),
        ("dim", "#64748b"),
        ("best", "#fbbf24"),
    ]
    all_tags = _default_tags + (tags or [])
    for tag, clr in all_tags:
        text_widget.tag_config(tag, foreground=clr)

    return text_widget
