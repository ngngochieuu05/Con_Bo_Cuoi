"""
DAL — Data Access Layer
Khởi tạo tất cả repo và seed dữ liệu mặc định khi import lần đầu.
Khi chuyển sang PostgreSQL: chỉ cần thay BaseRepo bằng SQLAlchemy session.
"""
from dal.tai_khoan_repo import init_seed as _seed_users
from dal.model_repo import init_seed as _seed_models
from dal.camera_chuong_repo import init_seed as _seed_cameras
from dal.canh_bao_repo import init_seed as _seed_alerts
from dal.dataset_repo import init_seed as _seed_dataset
from dal.monitor_session_repo import init_seed as _seed_monitor_sessions
from dal.profile_repo import init_profile_tables as _init_profile_tables, ensure_profiles_for_users as _ensure_profiles_for_users
from dal.tai_khoan_repo import _repo as _user_repo
import dal.activity_log_repo  # noqa: F401 — ensures db file is created on first run


def init_all():
    """Gọi khi app khởi động để đảm bảo seed data sẵn sàng."""
    _seed_users()
    _seed_models()
    _seed_cameras()
    _seed_alerts()
    _seed_dataset()
    _seed_monitor_sessions()
    _init_profile_tables()
    _ensure_profiles_for_users(_user_repo.all())
