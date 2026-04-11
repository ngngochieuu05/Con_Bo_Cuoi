import flet as ft
from datetime import datetime

# Import ThongBaoService từ BUS layer (Tạm comment - Chỉ UI trước)
# from src.bll.oa_core.sua_thong_bao.tuy_chinh_thong_bao import ThongBaoService

# ===== KHỞI TẠO SERVICE (MOCK) =====
class ThongBaoService:
    """Mock service - Không logic thực tế"""
    def get_default_token(self):
        return "MOCK_TOKEN_12345"
    
    def get_default_chat_id(self):
        return "MOCK_CHAT_ID_67890"

    def load_log(self):
        return []

thong_bao_service = ThongBaoService()

# ===== CẤU HÌNH TELEGRAM =====
TELEGRAM_BOT_TOKEN = thong_bao_service.get_default_token()
DEFAULT_CHAT_ID = thong_bao_service.get_default_chat_id()


def QuanLiThongBao(page_title):
    # Biến local để lưu chat_id (không dùng global)
    current_chat_id = DEFAULT_CHAT_ID
    
    # Biến để lưu reference đến các control
    status_text = ft.Text("", size=14)
    
    # Chat ID field - cho phép chỉnh sửa
    chat_id_field = ft.TextField(
        label="Chat ID", 
        value=current_chat_id,
        prefix_icon=ft.Icons.CHAT,
        on_change=lambda e: update_chat_id(e.control.value)
    )
    
    def update_chat_id(new_id: str):
        """Cập nhật Chat ID khi người dùng thay đổi"""
        nonlocal current_chat_id
        if new_id.strip():
            current_chat_id = new_id.strip()
    
    message_input = ft.TextField(
        label="Nội dung tin nhắn", 
        prefix_icon=ft.Icons.MESSAGE,
        multiline=True,
        min_lines=3,
        max_lines=5,
        value="🚨 <b>Cảnh báo!</b>\nHệ thống phát hiện tài xế có dấu hiệu buồn ngủ."
    )
    
    # Tạo DataTable cho log
    log_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Thời gian")),
            ft.DataColumn(ft.Text("Nội dung")),
            ft.DataColumn(ft.Text("Trạng thái")),
        ],
        rows=[],
        border=ft.border.all(1, "outlineVariant"),
        heading_row_color="surfaceVariant",
    )
    
    def load_logs_from_json():
        """Load log từ thong_bao_log.json và hiển thị lên DataTable"""
        logs = thong_bao_service.load_log()
        log_table.rows.clear()
        
        # Lấy tối đa 20 log để hiển thị
        for log in logs[:20]:
            time_str = log.get("time", "N/A")
            content = log.get("content", "")
            status = log.get("status", "")
            
            if status == "success":
                status_text_log = ft.Text("✓ Thành công", color="green")
            else:
                status_text_log = ft.Text("✗ Thất bại", color="red")
            
            log_table.rows.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(time_str)),
                ft.DataCell(ft.Text(content[:50] + "..." if len(content) > 50 else content)),
                ft.DataCell(status_text_log),
            ]))
    
    def add_log_to_table(content: str, success: bool):
        """Thêm log vào bảng hiển thị"""
        time_str = datetime.now().strftime("%d/%m %H:%M:%S")
        status_text_log = ft.Text("✓ Thành công", color="green") if success else ft.Text("✗ Thất bại", color="red")
        
        log_table.rows.insert(0, ft.DataRow(cells=[
            ft.DataCell(ft.Text(time_str)),
            ft.DataCell(ft.Text(content[:50] + "..." if len(content) > 50 else content)),
            ft.DataCell(status_text_log),
        ]))
        
        # Giữ tối đa 20 log trên UI
        if len(log_table.rows) > 20:
            log_table.rows.pop()
        
        log_table.update()
    
    def on_test_connection(e):
        """Xử lý kiểm tra kết nối - dùng ThongBaoService"""
        status_text.value = "⏳ Đang kiểm tra kết nối..."
        status_text.color = ft.Colors.ORANGE
        status_text.update()
        
        # Sử dụng ThongBaoService.test_connection()
        result = thong_bao_service.test_connection(TELEGRAM_BOT_TOKEN)
        
        if result.get("ok"):
            bot_info = result.get("result", {})
            bot_name = bot_info.get("first_name", "Unknown")
            bot_username = bot_info.get("username", "Unknown")
            status_text.value = f"✅ Kết nối thành công!\nBot: {bot_name} (@{bot_username})"
            status_text.color = ft.Colors.GREEN
        else:
            error = result.get("error", result.get("description", "Lỗi không xác định"))
            status_text.value = f"❌ Kết nối thất bại: {error}"
            status_text.color = ft.Colors.RED
        
        status_text.update()
    
    def on_send_message(e):
        """Xử lý gửi tin nhắn - dùng ThongBaoService"""
        msg = message_input.value.strip()
        if not msg:
            status_text.value = "⚠️ Vui lòng nhập nội dung tin nhắn!"
            status_text.color = ft.Colors.ORANGE
            status_text.update()
            return
        
        status_text.value = "⏳ Đang gửi tin nhắn..."
        status_text.color = ft.Colors.ORANGE
        status_text.update()
        
        # Sử dụng ThongBaoService.send_message()
        result = thong_bao_service.send_message(TELEGRAM_BOT_TOKEN, current_chat_id, msg)
        
        if result.get("ok"):
            status_text.value = "✅ Gửi tin nhắn thành công!"
            status_text.color = ft.Colors.GREEN
            add_log_to_table(msg, True)
        else:
            error = result.get("error", result.get("description", "Lỗi không xác định"))
            status_text.value = f"❌ Gửi thất bại: {error}"
            status_text.color = ft.Colors.RED
            add_log_to_table(msg, False)
        
        status_text.update()
    
    def on_send_test_alert(e):
        """Gửi cảnh báo test nhanh - dùng ThongBaoService"""
        test_msg = f"""🚨 <b>CẢNH BÁO HỆ THỐNG</b>

⚠️ <b>Loại:</b> Phát hiện buồn ngủ
👤 <b>Tài xế:</b> Nguyễn Văn A
🚗 <b>Biển số:</b> 30A-12345
📍 <b>Vị trí:</b> Quốc lộ 1A, Km 52
⏰ <b>Thời gian:</b> {datetime.now().strftime("%H:%M:%S %d/%m/%Y")}

<i>Đây là tin nhắn test từ Hệ thống Giám sát Lái xe</i>"""
        
        status_text.value = "⏳ Đang gửi cảnh báo test..."
        status_text.color = ft.Colors.ORANGE
        status_text.update()
        
        # Sử dụng ThongBaoService.send_message()
        result = thong_bao_service.send_message(TELEGRAM_BOT_TOKEN, current_chat_id, test_msg)
        
        if result.get("ok"):
            status_text.value = "✅ Gửi cảnh báo test thành công!"
            status_text.color = ft.Colors.GREEN
            add_log_to_table("Cảnh báo test", True)
        else:
            error = result.get("error", result.get("description", "Lỗi không xác định"))
            status_text.value = f"❌ Gửi thất bại: {error}"
            status_text.color = ft.Colors.RED
            add_log_to_table("Cảnh báo test", False)
        
        status_text.update()
    
    def on_clear_log(e):
        """Xóa toàn bộ log"""
        thong_bao_service.clear_log()
        log_table.rows.clear()
        log_table.update()
        status_text.value = "🗑️ Đã xóa lịch sử!"
        status_text.color = ft.Colors.BLUE
        status_text.update()
    
    def on_reload_log(e):
        """Reload log từ file JSON"""
        load_logs_from_json()
        log_table.update()
        status_text.value = "🔄 Đã tải lại log!"
        status_text.color = ft.Colors.BLUE
        status_text.update()

    # Load log từ JSON khi khởi tạo
    load_logs_from_json()

    # ===== UI COMPONENTS =====
    
    # 1. Card cấu hình Telegram
    api_config_card = ft.Container(
        bgcolor="surface", 
        border_radius=15, 
        padding=20,
        border=ft.border.all(1, "outlineVariant"),
        content=ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.TELEGRAM, color="primary", size=28),
                ft.Text("Cấu Hình Telegram", size=18, weight=ft.FontWeight.BOLD, color="onBackground"),
            ]),
            ft.Divider(color="outlineVariant"),
            # Bot Token - ẨN HOÀN TOÀN dưới dạng password
            ft.TextField(
                label="Bot Token", 
                value="••••••••••••••••••••••••••••••••••••••••••••",
                prefix_icon=ft.Icons.KEY,
                password=True,
                can_reveal_password=False,
                read_only=True,
                bgcolor="surfaceVariant"
            ),
            # Chat ID - CHO PHÉP CHỈNH SỬA
            chat_id_field,
            ft.Container(height=10),
            ft.Row([
                ft.ElevatedButton(
                    "Kiểm tra kết nối", 
                    icon=ft.Icons.WIFI_TETHERING, 
                    color=ft.Colors.WHITE,
                    bgcolor=ft.Colors.BLUE,
                    on_click=on_test_connection
                ),
            ], alignment=ft.MainAxisAlignment.END),
            ft.Container(height=10),
            status_text,
        ])
    )
    
    # 2. Card gửi tin nhắn
    send_message_card = ft.Container(
        bgcolor="surface", 
        border_radius=15, 
        padding=20,
        border=ft.border.all(1, "outlineVariant"),
        content=ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.SEND, color="secondary", size=28),
                ft.Text("Gửi Thông Báo", size=18, weight=ft.FontWeight.BOLD, color="onBackground"),
            ]),
            ft.Divider(color="outlineVariant"),
            message_input,
            ft.Container(height=10),
            ft.Row([
                ft.ElevatedButton(
                    "Gửi Cảnh Báo Test", 
                    icon=ft.Icons.WARNING_AMBER,
                    color=ft.Colors.WHITE,
                    bgcolor=ft.Colors.ORANGE,
                    on_click=on_send_test_alert
                ),
                ft.ElevatedButton(
                    "Gửi Tin Nhắn", 
                    icon=ft.Icons.SEND,
                    color=ft.Colors.WHITE,
                    bgcolor=ft.Colors.GREEN,
                    on_click=on_send_message
                ),
            ], alignment=ft.MainAxisAlignment.END, spacing=10),
        ])
    )

    # 3. Card lịch sử gửi
    log_card = ft.Container(
        bgcolor="surface", 
        border_radius=15, 
        padding=20, 
        expand=True,
        border=ft.border.all(1, "outlineVariant"),
        content=ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.HISTORY, color="tertiary", size=28),
                ft.Text("Lịch Sử Gửi Tin", size=18, weight=ft.FontWeight.BOLD, color="onBackground"),
                ft.Container(expand=True),
                ft.OutlinedButton(
                    "Tải lại", 
                    icon=ft.Icons.REFRESH, 
                    style=ft.ButtonStyle(color="primary"),
                    on_click=on_reload_log
                ),
                ft.OutlinedButton(
                    "Xóa Log", 
                    icon=ft.Icons.DELETE_SWEEP, 
                    style=ft.ButtonStyle(color="error"),
                    on_click=on_clear_log
                )
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(color="outlineVariant"),
            ft.Container(
                content=log_table, 
                padding=0, 
                expand=True,
            )
        ], expand=True)
    )

    # ===== LAYOUT CHÍNH =====
    return ft.Column([
        ft.Text("Quản Lý Thông Báo Telegram", size=24, weight=ft.FontWeight.BOLD, color="onBackground"),
        ft.Container(height=10),
        ft.Row([
            ft.Column([
                api_config_card,
                ft.Container(height=15),
                send_message_card,
            ], width=420),
            ft.Container(content=log_card, expand=True)
        ], expand=True, vertical_alignment=ft.CrossAxisAlignment.START, spacing=20)
    ], expand=True, spacing=10)