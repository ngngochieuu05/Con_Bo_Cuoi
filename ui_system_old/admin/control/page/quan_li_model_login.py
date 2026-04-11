import flet as ft
import cv2
import threading
import time
import json
import os

def QuanLiModel(page_title, page):
    
    # =================== PHÁT HIỆN CAMERA CÓ SẴN ===================
    def get_available_cameras():
        """Phát hiện tất cả camera có sẵn trên hệ thống - kiểm tra thực tế bằng cách đọc frame"""
        available_cameras = []
        # Kiểm tra tối đa 5 camera
        for i in range(5):
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)  # Dùng CAP_DSHOW cho Windows để nhanh hơn
            if cap.isOpened():
                # Thử đọc frame để xác nhận camera thực sự hoạt động
                ret, frame = cap.read()
                if ret and frame is not None:
                    # Chỉ thêm vào danh sách nếu đọc được frame thực tế
                    backend_name = cap.getBackendName()
                    camera_name = f"Camera {i}"
                    if backend_name:
                        camera_name = f"Camera {i} ({backend_name})"
                    available_cameras.append({"index": i, "name": camera_name})
                cap.release()
        
        # Nếu không tìm thấy camera nào, trả về danh sách rỗng
        if not available_cameras:
            available_cameras = [{"index": -1, "name": "Không tìm thấy camera"}]
        
        return available_cameras
    
    cameras = get_available_cameras()
    
    # =================== MODEL NHẬN DIỆN SINH TRẮC HỌC ===================
    # Global model instance
    current_face_model = None
    
    biometric_models = ["ArcFace (v2.1)", "FaceNet (v1.0)", "DeepFace (v1.5)"]
    
    def on_model_select(e):
        """Callback khi admin chọn model"""
        nonlocal current_face_model
        
        model_name = e.control.value
        pass; # print(f"\n{'='*70}")
        pass; # print(f"🔄 [MODEL SELECT] Admin đang chọn: {model_name}")
        pass; # print(f"{'='*70}")
        
        # Lấy config từ UI và thêm model_path từ loaded_config
        face_config = loaded_config.get("face_recognition", {})
        config = {
            'confidence_threshold': float(bio_threshold.value),
            'min_face_size': int(bio_min_face_size.value),
            'cosine_threshold': float(bio_cosine_threshold.value),
            'model_path': face_config.get('model_path', 'yolov8n.pt')
        }
        
        pass; # print(f"📋 [CONFIG] Using model_path: {config['model_path']}")
        
        try:
            if "ArcFace" in model_name:
                from src.bll.ai_core.login_user.Arc_face import ArcFaceModel
                current_face_model = ArcFaceModel(config)
                pass; # print(f"✅ [SUCCESS] Loaded ArcFace model với config:")
                pass; # print(f"   ├─ Model Path: {config['model_path']}")
                pass; # print(f"   ├─ Confidence: {config['confidence_threshold']}")
                pass; # print(f"   ├─ Min Face Size: {config['min_face_size']}px")
                pass; # print(f"   └─ Cosine Threshold: {config['cosine_threshold']}")
                
            elif "FaceNet" in model_name:
                pass; # print(f"⚠️  [WARNING] FaceNet chưa được triển khai")
                pass; # print(f"   Thành viên nhóm sẽ tạo src/bll/ai_core/FaceNet.py")
                
            elif "DeepFace" in model_name:
                pass; # print(f"⚠️  [WARNING] DeepFace chưa được triển khai")
                pass; # print(f"   Thành viên nhóm sẽ tạo src/bll/ai_core/DeepFace.py")
                
        except Exception as ex:
            pass; # print(f"❌ [ERROR] Không thể load model: {ex}")
            import traceback
            traceback.print_exc()
            current_face_model = None
    
    selected_biometric = ft.Dropdown(
        label="Chọn Model Sinh Trắc Học",
        width=300,
        options=[ft.dropdown.Option(m) for m in biometric_models],
        value=biometric_models[0],
        on_change=on_model_select
    )
    
    bio_file_path = ft.Text("Chưa chọn file", size=12, color=ft.Colors.GREY, italic=True)
    
    def pick_bio_model(e: ft.FilePickerResultEvent):
        pass; # print(f"🔵 [DEBUG] Bio file picker called")
        if e.files:
            pass; # print(f"✅ [SUCCESS] Selected file: {e.files[0].path}")
            bio_file_path.value = e.files[0].path
            bio_file_path.italic = False
            bio_file_path.color = ft.Colors.GREEN
            bio_file_path.update()
        else:
            pass; # print(f"⚠️  [WARNING] No file selected")
    
    bio_file_picker = ft.FilePicker(on_result=pick_bio_model)
    pass; # print(f"🔵 [DEBUG] Adding bio_file_picker to page.overlay")
    page.overlay.append(bio_file_picker)
    page.update()  # CRITICAL: Update page to register the file picker
    pass; # print(f"✅ [SUCCESS] bio_file_picker added and page updated")
    
    # Load config from model_config.json - USE ABSOLUTE PATH FOR CONSISTENCY
    # quan_li_model_pt.py path: src/ui/admin/control/page/quan_li_model_pt.py
    # Need to go up 6 levels to reach giam_sat_lai_xe
    current_file = os.path.abspath(__file__)  # Full path to quan_li_model_pt.py
    # count: page -> control -> admin -> GUI -> src -> giam_sat_lai_xe
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_file))))))
    config_path = os.path.join(project_root, "src", "ui", "data", "model_config.json")
    pass; # print(f"📂 [CONFIG_PATH] Loading from: {config_path}")
    
    loaded_config = {}
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            loaded_config = json.load(f)
            face_config = loaded_config.get("face_recognition", {})
            pass; # print(f"✅ [CONFIG] Loaded model_config.json")
            pass; # print(f"   ├─ Confidence: {face_config.get('confidence_threshold', 0.75)}")
            pass; # print(f"   ├─ Min Face Size: {face_config.get('min_face_size', 40)}")
            pass; # print(f"   └─ Cosine Threshold: {face_config.get('cosine_threshold', 0.75)}")
    except Exception as e:
        pass; # print(f"⚠️  [CONFIG] Could not load config: {e}, using defaults")
        loaded_config = {
            "face_recognition": {
                "confidence_threshold": 0.75,
                "min_face_size": 40,
                "cosine_threshold": 0.75
            }
        }
    
    face_config = loaded_config.get("face_recognition", {})
    default_confidence = face_config.get('confidence_threshold', 0.75)
    default_min_face = face_config.get('min_face_size', 40)
    default_cosine = face_config.get('cosine_threshold', 0.75)
    
    bio_threshold = ft.Text(f"{default_confidence:.2f}", weight="bold", color=ft.Colors.BLUE)
    bio_min_face_size = ft.Text(f"{default_min_face}", weight="bold", color=ft.Colors.BLUE)
    bio_cosine_threshold = ft.Text(f"{default_cosine:.2f}", weight="bold", color=ft.Colors.BLUE)
    
    def update_bio_threshold(e):
        bio_threshold.value = f"{e.control.value:.2f}"
        bio_threshold.update()
        if current_face_model:
            current_face_model.confidence_threshold = e.control.value
            pass; # print(f"🔄 [CONFIG UPDATE] Confidence threshold: {e.control.value:.2f}")
    
    def update_bio_min_face(e):
        bio_min_face_size.value = f"{int(e.control.value)}"
        bio_min_face_size.update()
        if current_face_model:
            current_face_model.min_face_size = int(e.control.value)
            pass; # print(f"🔄 [CONFIG UPDATE] Min face size: {int(e.control.value)}px")
    
    def update_bio_cosine_threshold(e):
        bio_cosine_threshold.value = f"{e.control.value:.2f}"
        bio_cosine_threshold.update()
        if current_face_model:
            current_face_model.cosine_threshold = e.control.value
            pass; # print(f"🔄 [CONFIG UPDATE] Cosine threshold: {e.control.value:.2f}")
    
    def save_config(e):
        """Lưu cấu hình hiện tại vào model_config.json"""
        try:
            # Đọc config hiện tại
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)
            
            # Cập nhật face_recognition settings (bao gồm file path)
            config_data["face_recognition"] = {
                "model_name": selected_biometric.value,
                "model_path": bio_file_path.value if bio_file_path.value != "Chưa chọn file" else "",
                "confidence_threshold": float(bio_threshold.value),
                "min_face_size": int(bio_min_face_size.value),
                "cosine_threshold": float(bio_cosine_threshold.value)
            }
            
            # Ghi lại file
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            pass; # print(f"✅ [SAVE] Biometric configuration saved to model_config.json")
            pass; # print(f"   ├─ Model: {selected_biometric.value}")
            pass; # print(f"   ├─ Model Path: {bio_file_path.value}")
            pass; # print(f"   ├─ Confidence: {bio_threshold.value}")
            pass; # print(f"   ├─ Min Face Size: {bio_min_face_size.value}")
            pass; # print(f"   └─ Cosine Threshold: {bio_cosine_threshold.value}")
            
            # Show success message
            page.open(ft.SnackBar(
                content=ft.Text("✅ Đã lưu cấu hình sinh trắc học!"),
                bgcolor=ft.Colors.GREEN_700
            ))
            
        except Exception as ex:
            pass; # print(f"❌ [SAVE ERROR] {ex}")
            import traceback
            traceback.print_exc()
            page.open(ft.SnackBar(
                content=ft.Text(f"❌ Lỗi lưu cấu hình: {ex}"),
                bgcolor=ft.Colors.RED_700
            ))
    
    def test_biometric_model(e):
        """Test model sinh trắc học và log ra terminal"""
        pass; # print(f"\n{'='*70}")
        pass; # print(f"🧪 [TEST] Starting Biometric Model Test")
        pass; # print(f"{'='*70}")
        
        if not current_face_model:
            pass; # print(f"❌ [TEST ERROR] No model loaded! Please select a model first.")
            page.open(ft.SnackBar(
                content=ft.Text("❌ Chưa load model! Hãy chọn model trước."),
                bgcolor=ft.Colors.RED_700
            ))
            return
        
        pass; # print(f"📋 [TEST] Model Configuration:")
        pass; # print(f"   ├─ Model Name: {selected_biometric.value}")
        pass; # print(f"   ├─ Model Path: {bio_file_path.value}")
        pass; # print(f"   ├─ Confidence Threshold: {bio_threshold.value}")
        pass; # print(f"   ├─ Min Face Size: {bio_min_face_size.value}px")
        pass; # print(f"   └─ Cosine Threshold: {bio_cosine_threshold.value}")
        
        pass; # print(f"\n✅ [TEST] Model is loaded and ready")
        pass; # print(f"   Model Type: {type(current_face_model).__name__}")
        
        # Show success
        page.open(ft.SnackBar(
            content=ft.Text("✅ Model test completed! Check terminal for details."),
            bgcolor=ft.Colors.GREEN_700
        ))
        
        pass; # print(f"{'='*70}\n")
    
    biometric_config_card = ft.Container(
        bgcolor="surface", border_radius=15, padding=20,
        border=ft.border.all(1, "outlineVariant"),
        shadow=ft.BoxShadow(blur_radius=10, spread_radius=1, color=ft.Colors.with_opacity(0.1, "shadow")),
        content=ft.Column([
            ft.Text("🔐 Model Nhận Diện Sinh Trắc Học", size=18, weight=ft.FontWeight.BOLD, color="primary"),
            ft.Divider(color="outlineVariant"),
            selected_biometric,
            ft.Container(height=10),
            ft.ElevatedButton(
                "Browse File (.pt)",
                icon=ft.Icons.FOLDER_OPEN,
                on_click=lambda _: bio_file_picker.pick_files(
                    allowed_extensions=["pt"],
                    dialog_title="Chọn Model Sinh Trắc Học (.pt)"
                ),
                style=ft.ButtonStyle(
                    bgcolor="primary",
                    color=ft.Colors.WHITE,
                    padding=15
                )
            ),
            ft.Container(height=5),
            bio_file_path,
            ft.Container(height=10),
            ft.Text("Tham Số Model:", size=14, weight=ft.FontWeight.BOLD),
            ft.Row([
                ft.Text("Ngưỡng Độ Tin Cậy: "), bio_threshold
            ]),
            ft.Slider(min=0.3, max=1.0, divisions=70, value=default_confidence, on_change=update_bio_threshold),
            
            ft.Row([
                ft.Text("Kích Thước Khuôn Mặt Tối Thiểu (px): "), bio_min_face_size
            ]),
            ft.Slider(min=20, max=100, divisions=80, value=default_min_face, on_change=update_bio_min_face),
            
            ft.Row([
                ft.Text("Ngưỡng Cosine Similarity: "), bio_cosine_threshold
            ]),
            ft.Slider(min=0.2, max=1.0, divisions=80, value=default_cosine, on_change=update_bio_cosine_threshold),
            
            ft.Container(height=10),
            ft.Row([
                ft.ElevatedButton("Lưu Cấu Hình", icon=ft.Icons.SAVE, bgcolor="primary", color=ft.Colors.WHITE, on_click=save_config),
                ft.ElevatedButton("Test Model", icon=ft.Icons.PLAY_ARROW, bgcolor="secondary", color=ft.Colors.WHITE, on_click=test_biometric_model)
            ])
        ])
    )


    
    # =================== KHO LƯU TRỮ MODEL ===================
    model_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Loại Model", color="onBackground")),
            ft.DataColumn(ft.Text("Tên File", color="onBackground")),
            ft.DataColumn(ft.Text("Version", color="onBackground")),
            ft.DataColumn(ft.Text("Ngày Upload", color="onBackground")),
            ft.DataColumn(ft.Text("Accuracy", color="onBackground")),
            ft.DataColumn(ft.Text("Kích thước", color="onBackground")),
            ft.DataColumn(ft.Text("Trạng thái", color="onBackground")),
            ft.DataColumn(ft.Text("Hành động", color="onBackground")),
        ],
        rows=[
            ft.DataRow(cells=[
                ft.DataCell(ft.Icon(ft.Icons.FACE, color="primary")),
                ft.DataCell(ft.Text("facenet_model.h5")),
                ft.DataCell(ft.Text("v1.0.0")),
                ft.DataCell(ft.Text("20/01/2026")),
                ft.DataCell(ft.Text("98.5%")),
                ft.DataCell(ft.Text("25 MB")),
                ft.DataCell(ft.Container(content=ft.Text("Active", color="onPrimary", size=10), bgcolor="primary", padding=5, border_radius=5)),
                ft.DataCell(ft.Row([
                    ft.IconButton(ft.Icons.DOWNLOAD, tooltip="Tải xuống"),
                    ft.IconButton(ft.Icons.SETTINGS, tooltip="Cấu hình"),
                ])),
            ]),
        ],
        border=ft.border.all(1, "outlineVariant"),
        border_radius=10,
        vertical_lines=ft.border.BorderSide(1, "outlineVariant"),
    )

    list_card = ft.Container(
        bgcolor="surface", border_radius=15, padding=20, expand=True,
        border=ft.border.all(1, "outlineVariant"),
        content=ft.Column([
            ft.Row([
                ft.Text("📦 Kho Lưu Trữ Model", size=18, weight=ft.FontWeight.BOLD, color="onBackground"),
                ft.ElevatedButton("Upload Model Sinh Trắc", icon=ft.Icons.UPLOAD_FILE, bgcolor="primary", color="onPrimary"),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(color="outlineVariant"),
            ft.Container(content=model_table, expand=True, padding=0)
        ])
    )

    return ft.Column([
        ft.Text("⚙️ " + page_title, size=24, weight=ft.FontWeight.BOLD, color="onBackground"),
        ft.Container(height=10),
        # Hàng 1: Model Card Sinh Trắc Học
        ft.Row([
            ft.Container(content=biometric_config_card, width=500),
        ]),
        ft.Container(height=20),
        # Phần kho lưu trữ
        ft.Container(content=list_card, expand=True)
    ], expand=True, scroll=ft.ScrollMode.AUTO)