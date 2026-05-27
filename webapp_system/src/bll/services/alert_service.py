"""
BLL - Alert Service

Luồng cảnh báo hành vi realtime:
- giữ frame annotated cuối cùng để gửi Telegram
- tracking ID cho từng bò theo camera
- bò húc nhau khi 2 bbox tiếp xúc liên tục >= 1.5 giây
- bò bỏ ăn khi cùng một ID ở trạng thái nằm >= 2 giờ
"""
from __future__ import annotations

import threading
import time

from bll.services.monitor_service import load_config
from bll.services.telegram_alert import send_cow_alert

_STATE_LOCK = threading.RLock()
_LAST_FRAME_B64: str = ""
_LAST_ALERT_TS: dict[str, float] = {}
_CAMERA_STATES: dict[int, dict] = {}

_TRACK_MATCH_IOU = 0.15
_TRACK_STALE_SECONDS = 3.0
_BEHAVIOR_OVERLAP_IOU = 0.15
_TOUCH_GAP_PX = 20
_DEFAULT_FIGHT_CONTACT_SECONDS = 1.5
_DEFAULT_LYING_ALERT_SECONDS = 2 * 60 * 60
_DEFAULT_ALERT_COOLDOWN_SECONDS = 60

_LYING_KEYWORDS = ("nằm", "lying", "lie", "nam")
_COW_KEYWORDS = ("bò", "bo", "cow", "cattle", "beef")


def set_last_frame_b64(frame_b64: str | None) -> None:
    global _LAST_FRAME_B64
    with _STATE_LOCK:
        _LAST_FRAME_B64 = (frame_b64 or "").strip()


def get_last_frame_b64() -> str:
    with _STATE_LOCK:
        return _LAST_FRAME_B64


def reset_camera_state(id_camera_chuong: int | None = None) -> None:
    with _STATE_LOCK:
        if id_camera_chuong is None:
            _CAMERA_STATES.clear()
            return
        _CAMERA_STATES.pop(int(id_camera_chuong or 0), None)


def _resolve_farmer_chat_id(id_user: int) -> str | None:
    try:
        from dal.tai_khoan_repo import get_user_by_id

        user = get_user_by_id(int(id_user) or 0) or {}
        chat_id = str(user.get("telegram_chat_id") or "").strip()
        return chat_id or None
    except Exception:
        return None


def _get_thresholds() -> tuple[float, float, float]:
    cfg = load_config()
    thresholds = cfg.get("thresholds") or {}
    fight_seconds = float(
        thresholds.get("fight_contact_seconds_realtime", _DEFAULT_FIGHT_CONTACT_SECONDS)
        or _DEFAULT_FIGHT_CONTACT_SECONDS
    )
    lying_seconds = float(
        thresholds.get("lying_alert_seconds_realtime", _DEFAULT_LYING_ALERT_SECONDS)
        or _DEFAULT_LYING_ALERT_SECONDS
    )
    cooldown_seconds = float(
        thresholds.get("alert_cooldown_seconds", _DEFAULT_ALERT_COOLDOWN_SECONDS)
        or _DEFAULT_ALERT_COOLDOWN_SECONDS
    )
    return max(0.5, fight_seconds), max(60.0, lying_seconds), max(0.0, cooldown_seconds)


def _should_send_now(alert_type: str, id_user: int, id_camera_chuong: int, cooldown_seconds: float) -> bool:
    cfg = load_config()
    if not bool(cfg.get("notify_alert", True)):
        return False
    key = f"{alert_type}:{int(id_user or 0)}:{int(id_camera_chuong or 0)}"
    now = time.time()
    with _STATE_LOCK:
        last_ts = float(_LAST_ALERT_TS.get(key, 0.0) or 0.0)
        if cooldown_seconds and (now - last_ts) < cooldown_seconds:
            return False
        _LAST_ALERT_TS[key] = now
    return True


def notify_alert(
    alert_type: str,
    id_user: int,
    id_camera_chuong: int,
    extra: dict | None = None,
    *,
    cooldown_seconds: float | None = None,
    force: bool = False,
) -> bool:
    if alert_type not in {"cow_lie", "cow_fight"}:
        return False
    _, _, default_cooldown = _get_thresholds()
    effective_cooldown = default_cooldown if cooldown_seconds is None else max(0.0, float(cooldown_seconds))
    if not force and not _should_send_now(alert_type, id_user, id_camera_chuong, effective_cooldown):
        return False

    chat_id_override = _resolve_farmer_chat_id(id_user)
    frame_b64 = get_last_frame_b64()

    # Gửi bất đồng bộ (async) qua thread riêng để tránh chặn luồng suy luận của video
    threading.Thread(
        target=send_cow_alert,
        kwargs={
            "alert_type": alert_type,
            "camera_id": int(id_camera_chuong or 0),
            "extra": extra or {},
            "chat_id_override": chat_id_override,
            "frame_b64": frame_b64 or None,
        },
        daemon=True,
    ).start()
    return True


def send_test_alert(alert_type: str, id_user: int, id_camera_chuong: int) -> bool:
    extra = {}
    if alert_type == "cow_fight":
        extra = {"cow_i": 1, "cow_j": 2, "contact_seconds": round(_DEFAULT_FIGHT_CONTACT_SECONDS, 1)}
    elif alert_type == "cow_lie":
        extra = {"duration_min": 120, "cow_id": 1}
    return notify_alert(
        alert_type=alert_type,
        id_user=id_user,
        id_camera_chuong=id_camera_chuong,
        extra=extra,
        cooldown_seconds=0.0,
        force=True,
    )


def _bbox_iou(box_a: list[int], box_b: list[int]) -> float:
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b
    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)
    if inter_x2 <= inter_x1 or inter_y2 <= inter_y1:
        return 0.0
    inter = float((inter_x2 - inter_x1) * (inter_y2 - inter_y1))
    area_a = max(1.0, float((ax2 - ax1) * (ay2 - ay1)))
    area_b = max(1.0, float((bx2 - bx1) * (by2 - by1)))
    return inter / (area_a + area_b - inter)


def _boxes_touch_or_overlap(box_a: list[int], box_b: list[int], gap_px: int = _TOUCH_GAP_PX) -> bool:
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b
    horizontal_gap = max(0, max(bx1 - ax2, ax1 - bx2))
    vertical_gap = max(0, max(by1 - ay2, ay1 - by2))
    return horizontal_gap <= gap_px and vertical_gap <= gap_px


def _get_camera_state(id_camera_chuong: int) -> dict:
    with _STATE_LOCK:
        state = _CAMERA_STATES.get(int(id_camera_chuong or 0))
        if state is None:
            state = {
                "next_track_id": 1,
                "tracks": {},
                "contacts": {},
            }
            _CAMERA_STATES[int(id_camera_chuong or 0)] = state
        return state


def _cleanup_state(state: dict, now: float) -> None:
    stale_ids = [
        track_id
        for track_id, track in state["tracks"].items()
        if (now - float(track.get("last_seen", 0.0) or 0.0)) > _TRACK_STALE_SECONDS
    ]
    for track_id in stale_ids:
        state["tracks"].pop(track_id, None)
    stale_pairs = [
        pair_key
        for pair_key, contact in state["contacts"].items()
        if (now - float(contact.get("last_seen", 0.0) or 0.0)) > 1.0
    ]
    for pair_key in stale_pairs:
        state["contacts"].pop(pair_key, None)


def _match_tracks(state: dict, boxes: list[list[int]], now: float) -> dict[int, dict]:
    tracks = state["tracks"]
    assignments: dict[int, dict] = {}
    unmatched_boxes = list(enumerate(boxes))
    used_track_ids: set[int] = set()

    candidates: list[tuple[float, int, int]] = []
    for track_id, track in tracks.items():
        prev_box = track.get("bbox")
        if not prev_box:
            continue
        for box_index, box in unmatched_boxes:
            iou = _bbox_iou(prev_box, box)
            if iou >= _TRACK_MATCH_IOU:
                candidates.append((iou, track_id, box_index))
    candidates.sort(reverse=True)

    used_box_indexes: set[int] = set()
    for _iou, track_id, box_index in candidates:
        if track_id in used_track_ids or box_index in used_box_indexes:
            continue
        box = boxes[box_index]
        track = tracks[track_id]
        track["bbox"] = box
        track["last_seen"] = now
        assignments[track_id] = track
        used_track_ids.add(track_id)
        used_box_indexes.add(box_index)

    for box_index, box in unmatched_boxes:
        if box_index in used_box_indexes:
            continue
        track_id = int(state["next_track_id"])
        state["next_track_id"] = track_id + 1
        track = {
            "id": track_id,
            "bbox": box,
            "created_at": now,
            "last_seen": now,
            "lie_start_ts": None,
            "last_lie_alert_ts": 0.0,
        }
        tracks[track_id] = track
        assignments[track_id] = track

    return assignments


def _is_cow_detection(det: dict) -> bool:
    if str(det.get("model") or "").strip().lower() == "cattle_detect":
        return True
    if str(det.get("model") or "").strip().lower() == "behavior":
        return True
    cls_lower = str(det.get("class") or "").strip().lower()
    return any(keyword in cls_lower for keyword in _COW_KEYWORDS)


def _is_lying_detection(det: dict) -> bool:
    if str(det.get("model") or "").strip().lower() != "behavior":
        return False
    cls_lower = str(det.get("class") or "").strip().lower()
    return any(keyword in cls_lower for keyword in _LYING_KEYWORDS)


def process_behavior_alerts(
    detections: list[dict],
    id_user: int,
    id_camera_chuong: int,
) -> list[str]:
    now = time.time()
    fight_seconds, lying_seconds, cooldown_seconds = _get_thresholds()
    state = _get_camera_state(id_camera_chuong)

    cattle_boxes = [
        list(map(int, det.get("bbox") or []))
        for det in detections
        if str(det.get("model") or "").strip().lower() == "cattle_detect" and len(det.get("bbox") or []) == 4
    ]
    behavior_boxes = [
        list(map(int, det.get("bbox") or []))
        for det in detections
        if str(det.get("model") or "").strip().lower() == "behavior" and len(det.get("bbox") or []) == 4
    ]
    cow_boxes = cattle_boxes or behavior_boxes or [
        list(map(int, det.get("bbox") or []))
        for det in detections
        if _is_cow_detection(det) and len(det.get("bbox") or []) == 4
    ]
    lying_boxes = [list(map(int, det.get("bbox") or [])) for det in detections if _is_lying_detection(det) and len(det.get("bbox") or []) == 4]

    alerts_created: list[str] = []
    seen_types: set[str] = set()

    with _STATE_LOCK:
        _cleanup_state(state, now)
        if not cow_boxes:
            return alerts_created

        active_tracks = _match_tracks(state, cow_boxes, now)

        for track_id, track in active_tracks.items():
            box = track.get("bbox") or []
            is_lying = any(_bbox_iou(box, lying_box) >= _BEHAVIOR_OVERLAP_IOU or _boxes_touch_or_overlap(box, lying_box, gap_px=0) for lying_box in lying_boxes)
            if is_lying:
                if track.get("lie_start_ts") is None:
                    track["lie_start_ts"] = now
                duration_seconds = now - float(track.get("lie_start_ts") or now)
                if (
                    duration_seconds >= lying_seconds
                    and (now - float(track.get("last_lie_alert_ts", 0.0) or 0.0)) >= cooldown_seconds
                ):
                    try:
                        from dal.canh_bao_repo import create_alert

                        create_alert("cow_lie", id_user, id_camera_chuong)
                        notify_alert(
                            "cow_lie",
                            id_user=id_user,
                            id_camera_chuong=id_camera_chuong,
                            extra={
                                "cow_id": track_id,
                                "duration_min": round(duration_seconds / 60.0, 1),
                            },
                            cooldown_seconds=0.0,
                        )
                        track["last_lie_alert_ts"] = now
                        if "cow_lie" not in seen_types:
                            alerts_created.append("cow_lie")
                            seen_types.add("cow_lie")
                    except Exception:
                        pass
            else:
                track["lie_start_ts"] = None

        active_items = list(active_tracks.items())
        live_pair_keys: set[str] = set()
        for idx, (track_id_a, track_a) in enumerate(active_items):
            box_a = track_a.get("bbox") or []
            for track_id_b, track_b in active_items[idx + 1:]:
                box_b = track_b.get("bbox") or []
                if not box_a or not box_b or not _boxes_touch_or_overlap(box_a, box_b):
                    continue
                pair_ids = sorted((int(track_id_a), int(track_id_b)))
                pair_key = f"{pair_ids[0]}:{pair_ids[1]}"
                live_pair_keys.add(pair_key)
                contact = state["contacts"].setdefault(
                    pair_key,
                    {"start_ts": now, "last_seen": now, "last_alert_ts": 0.0},
                )
                contact["last_seen"] = now
                duration_seconds = now - float(contact.get("start_ts", now) or now)
                if (
                    duration_seconds >= fight_seconds
                    and (now - float(contact.get("last_alert_ts", 0.0) or 0.0)) >= cooldown_seconds
                ):
                    try:
                        from dal.canh_bao_repo import create_alert

                        create_alert("cow_fight", id_user, id_camera_chuong)
                        notify_alert(
                            "cow_fight",
                            id_user=id_user,
                            id_camera_chuong=id_camera_chuong,
                            extra={
                                "cow_i": pair_ids[0],
                                "cow_j": pair_ids[1],
                                "contact_seconds": round(duration_seconds, 1),
                            },
                            cooldown_seconds=0.0,
                        )
                        contact["last_alert_ts"] = now
                        if "cow_fight" not in seen_types:
                            alerts_created.append("cow_fight")
                            seen_types.add("cow_fight")
                    except Exception:
                        pass

    return alerts_created


def resolve_farmer_alert(id_canh_bao: int) -> bool:
    """Đánh dấu cảnh báo đã xử lý."""
    from dal.canh_bao_repo import resolve_alert
    try:
        resolve_alert(id_canh_bao)
        return True
    except Exception:
        return False


def get_alerts_by_user_or_all(id_user: int | None = None) -> list[dict]:
    """Lấy danh sách cảnh báo của farmer hoặc tất cả."""
    from dal.canh_bao_repo import get_by_user, get_all
    try:
        if id_user:
            return get_by_user(id_user)
        return get_all()
    except Exception:
        return []
