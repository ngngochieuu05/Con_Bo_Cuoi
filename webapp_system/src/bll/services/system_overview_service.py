from __future__ import annotations

from datetime import date

from bll.services import chat_service
from bll.services.monitor_service import load_cache, load_config
from dal.activity_log_repo import get_all as get_all_logs
from dal.camera_chuong_repo import get_all_cameras, get_by_user as get_cameras_by_user
from dal.canh_bao_repo import count_open, get_all as get_all_alerts, get_by_user as get_alerts_by_user
from dal.model_repo import count_online, get_all_models
from dal.tai_khoan_repo import get_all_users


def _today() -> str:
    return date.today().isoformat()


def get_system_overview(user_id: int | None = None, role: str = "farmer") -> dict:
    role = (role or "farmer").lower()
    cfg = load_config()
    cache = load_cache()
    users = get_all_users()
    alerts = get_all_alerts()
    cameras = get_all_cameras()
    models = get_all_models()
    logs = get_all_logs()
    today = _today()

    own_cameras = get_cameras_by_user(int(user_id or 0)) if user_id else []
    own_alerts = get_alerts_by_user(int(user_id or 0)) if user_id else []
    expert_convos = chat_service.list_conversations_for_expert(int(user_id or 0)) if role == "expert" and user_id else []

    return {
        "server_url": cfg.get("server_url", "--"),
        "app_mode": cfg.get("app_mode", "desktop"),
        "app_port": cfg.get("app_port", 0),
        "yolo_mode": cfg.get("yolo_model_mode", "cpu"),
        "camera_index": cfg.get("camera_index", 0),
        "models_total": len(models),
        "models_online": count_online(),
        "users_total": len(users),
        "experts_total": sum(1 for user in users if user.get("vai_tro") == "expert"),
        "farmers_total": sum(1 for user in users if user.get("vai_tro") == "farmer"),
        "alerts_open": count_open(),
        "alerts_today": sum(1 for alert in alerts if str(alert.get("created_at", "")).startswith(today)),
        "cameras_total": len(cameras),
        "cameras_online": sum(1 for cam in cameras if cam.get("trang_thai") == "online"),
        "cameras_warning": sum(1 for cam in cameras if cam.get("trang_thai") == "warning"),
        "cameras_offline": sum(1 for cam in cameras if cam.get("trang_thai") == "offline"),
        "activity_total": len(logs),
        "activity_today": sum(1 for log in logs if str(log.get("timestamp", "")).startswith(today)),
        "cache_total_cows": cache.get("total_cows", 0),
        "cache_active_alerts": cache.get("active_alerts", 0),
        "cache_recent_alerts": len(cache.get("recent_alerts", [])),
        "own_cameras_total": len(own_cameras),
        "own_cameras_online": sum(1 for cam in own_cameras if cam.get("trang_thai") == "online"),
        "own_alerts_total": len(own_alerts),
        "own_alerts_open": sum(1 for alert in own_alerts if alert.get("trang_thai") == "CHUA_XU_LY"),
        "own_conversations_total": len(expert_convos),
        "own_conversations_unread": sum(int(convo.get("unread_expert", 0) or 0) for convo in expert_convos),
    }
