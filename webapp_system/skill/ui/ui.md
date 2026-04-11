# 🏆 Driver System UI Skillset: Glassmorphism & Modern Flet Workflow

Tài liệu này là bản đặc tả kỹ thuật cuối cùng, được verify dựa trên mã nguồn thực tế của dự án. Đây là bộ khung chuẩn (Workflow) để áp dụng cho các dự án Giao diện người dùng hiện đại bằng Flet.

---

## 🎨 1. Hệ thống Design Tokens (Theme Core)

Để bắt đầu một dự án mới theo phong cách này, hãy khởi tạo các thông số màu sắc và độ mờ chuẩn sau:

```python
# Palette màu chuẩn dự án
PRIMARY = "#4CAF50"      # Thành công / Hoạt động
SECONDARY = "#56CCF2"    # Quản trị / Thông tin
WARNING = "#F2C94C"      # Tạm dừng / Cảnh báo
DANGER = "#FF7A7A"       # Kết thúc / Lỗi vi phạm
TEXT_DARK = "#06131B"    # Chữ trên nền sáng accent

# Thông số Glassmorphism (Glass Specs)
GLASS_BG = ft.Colors.with_opacity(0.16, ft.Colors.WHITE)
GLASS_BORDER = ft.Colors.with_opacity(0.18, ft.Colors.WHITE)
GLASS_SHADOW = ft.BoxShadow(
    blur_radius=28, 
    color=ft.Colors.BLACK45, 
    offset=ft.Offset(0, 14)
)
```

---

## 🏛️ 2. Cấu trúc Component Chuẩn (Verified Snippets)

### A. Hàm Glass Container (Linh hồn của UI)
Đây là wrapper cho mọi bảng điều khiển trong hệ thống.
```python
def glass_container(content, width=None, height=None, padding=24, radius=28):
    return ft.Container(
        width=width, height=height, padding=padding,
        bgcolor=GLASS_BG,
        border=ft.border.all(1, GLASS_BORDER),
        border_radius=radius,
        shadow=GLASS_SHADOW,
        content=content,
    )
```

### B. Hệ thống Button (Phân cấp chức năng)
Dự án sử dụng hàm `_palette` để quản lý màu sắc tập trung cho Button.
```python
def button_style(kind="primary", radius=14):
    # kind mapping: primary->#4CAF50, surface->white opacity, danger->#FF7A7A
    bgcolor, text_color = get_palette(kind) 
    return ft.ButtonStyle(
        bgcolor=bgcolor,
        color=text_color,
        shape=ft.RoundedRectangleBorder(radius=radius),
        side=ft.BorderSide(1, GLASS_BORDER if kind=="surface" else bgcolor),
        text_style=ft.TextStyle(weight=ft.FontWeight.W_700),
    )
```

---

## 📊 3. Kỹ thuật Render Bảng Dữ liệu (DGV Workflow)

**Vấn đề:** Bảng mặc định của Flet khó tùy biến hiệu ứng Glass.
**Giải pháp:** Sử dụng `ListView` kết hợp `Row` và `Interactive Container`.

1.  **Header:** Container có `bgcolor` là `white opacity 0.3` để tạo độ tương phản.
2.  **Row (Dòng):** Container có thuộc tính `ink=True` (hiệu ứng gợn sóng) và `on_hover` để highlight.
3.  **Badge:** Container nhỏ với `border_radius=12` để hiển thị trạng thái (An toàn/Vi phạm).

```python
# Hiệu ứng hover cho dòng bảng (Verified logic)
def _on_row_hover(e):
    # e.data == "true" khi chuột đi vào
    e.control.bgcolor = ft.Colors.with_opacity(0.25, "white") if e.data == "true" else ft.Colors.with_opacity(0.1, "white")
    e.control.update()
```

---

## 🧭 4. Navigation & Layout Workflow

### A. Background Layering (3 Lớp chuẩn)
Để có chiều sâu, luôn sử dụng 1 `Stack` làm root của Page:
1.  **Lớp 1 (Image):** Ảnh nền chất lượng cao, `blur=14` đến `20` trong Container.
2.  **Lớp 2 (Overlay):** Container đen (`BLACK54` hoặc `BLACK62`) bao phủ toàn màn hình để text nổi bật.
3.  **Lớp 3 (Content):** Các Glass components nằm trên cùng.

### B. Sidebar "Slide & Blur"
- Sử dụng thuộc tính `animate_width` cho Sidebar Container.
- Khi mở: `width=250`, `blur=20`.
- Khi đóng: `width=0`, `opacity=0`, `visible=False`.

---

## 🤖 5. UI floating & Overlays

Hệ thống hỗ trợ các cửa sổ nổi (Floating Windows) như Chatbox AI hoặc Mini Player:
- **Nguyên lý:** Đặt các Container này vào `Stack` nội dung chính, sử dụng thuộc tính `right` và `bottom` để cố định vị trí.
- **Z-Index:** Thành phần nào được thêm vào sau trong danh sách `controls` của `Stack` sẽ nằm trên cùng.

---

## 📝 6. Các quy tắc "Vàng" khi làm Dự án mới
1.  **Assets Management:** Luôn khai báo `assets_dir="."` khi chạy `ft.app` để đường dẫn ảnh/icon ngắn gọn.
2.  **Performance:** Chỉ `update()` những component nhỏ thay vì `page.update()` toàn bộ trang để tránh giật lag.
3.  **Window Config:** Luôn thiết lập `window_min_width` và `window_min_height` để bảo vệ bố cục Glassmorphism không bị vỡ.

---

## 📦 7. Ràng buộc Phiên bản Flet

Dự án này được verify và tương thích với **Flet >= 0.21.0** (API mới dùng `ft.Colors`, `ft.Icons` viết hoa).

```
# requirements.txt
flet>=0.21.0,<0.30.0
```

| Phiên bản | Ghi chú |
|-----------|---------|
| < 0.21.0  | ❌ Dùng `ft.colors` (chữ thường) — KHÔNG dùng cho dự án này |
| >= 0.21.0 | ✅ `ft.Colors`, `ft.Icons` viết hoa — chuẩn của dự án |
| >= 0.28.x | ✅ Đã test, tương thích hoàn toàn |

---

## 🐛 8. Các Lỗi Cú Pháp Thường Gặp (Common Gotchas)

### A. `ft.colors` vs `ft.Colors` — Lỗi phổ biến nhất

```python
# ❌ SAI — API cũ (< 0.21), sẽ raise AttributeError hoặc DeprecationWarning
ft.colors.WHITE
ft.colors.with_opacity(0.16, ft.colors.WHITE)
ft.icons.SEARCH

# ✅ ĐÚNG — API mới (>= 0.21)
ft.Colors.WHITE
ft.Colors.with_opacity(0.16, ft.Colors.WHITE)
ft.Icons.SEARCH
```

### B. `ft.colors.BLACK45` vs `ft.Colors.BLACK45`

Các preset màu có opacity sẵn (như `BLACK12`, `BLACK26`, `BLACK45`, `BLACK54`) cũng phải viết hoa:
```python
# ❌ SAI
color=ft.colors.BLACK45

# ✅ ĐÚNG
color=ft.Colors.BLACK45
```

### C. `ft.FontWeight` — Không dùng chuỗi

```python
# ❌ SAI — không nhận string trực tiếp
ft.TextStyle(weight="bold")
ft.TextStyle(weight="w700")

# ✅ ĐÚNG — dùng enum
ft.TextStyle(weight=ft.FontWeight.BOLD)
ft.TextStyle(weight=ft.FontWeight.W_700)
```

### D. `ft.border.all` vs `ft.Border`

```python
# ❌ SAI — thiếu module prefix
border=ft.Border.all(1, color)

# ✅ ĐÚNG — hàm helper nằm ở ft.border (chữ thường)
border=ft.border.all(1, color)
```

### E. `ft.BoxShadow` — `offset` dùng `ft.Offset`, không phải tuple

```python
# ❌ SAI
shadow=ft.BoxShadow(blur_radius=28, color=ft.Colors.BLACK45, offset=(0, 14))

# ✅ ĐÚNG
shadow=ft.BoxShadow(blur_radius=28, color=ft.Colors.BLACK45, offset=ft.Offset(0, 14))
```

### F. `animate_width` — Kiểu dữ liệu

```python
# ❌ SAI — truyền số nguyên thô
animate_width=300

# ✅ ĐÚNG — truyền đối tượng Animation
animate_width=ft.Animation(300, ft.AnimationCurve.EASE_IN_OUT)
```

### G. `page.window_min_width` — Đặt trước khi add controls

```python
# ✅ ĐÚNG — luôn config window trước khi render
def main(page: ft.Page):
    page.window_min_width = 900
    page.window_min_height = 600
    page.window_width = 1280
    page.window_height = 800
    # ... sau đó mới page.add(...)
```

---
*Bản verify cuối cùng - Sẵn sàng làm Workflow cho dự án mới.*
