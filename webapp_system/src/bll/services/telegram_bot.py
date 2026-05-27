"""
BLL — Telegram Bot Long Polling
Nhận lệnh từ Telegram và phản hồi trạng thái hệ thống.

Lệnh hỗ trợ:
  /start [token]          — Chào mừng hoặc liên kết Telegram
  /help                   — Danh sách tất cả lệnh
  /ping                   — Kiểm tra kết nối
  /status                 — Trạng thái hệ thống (cảnh báo, camera)
  /herd                   — Tình trạng đàn bò hiện tại
  /alerts                 — Danh sách cảnh báo chưa xử lý
  /report [YYYY-MM-DD]    — Báo cáo cảnh báo theo ngày (mặc định: hôm nay)
  /report_month [YYYY-MM] — Báo cáo cảnh báo theo tháng
  /report_year [YYYY]     — Báo cáo cảnh báo theo năm
  /disease                — Bệnh phát hiện hôm nay
  /disease_month [YYYY-MM]— Bệnh phát hiện theo tháng
  /disease_year [YYYY]    — Bệnh phát hiện theo năm
  /resolve <id>           — Đánh dấu đã xử lý cảnh báo
  /camera_list            — Danh sách camera
  /alert_on               — Bật thông báo
  /alert_off              — Tắt thông báo
"""
from __future__ import annotations

import threading
import time

import requests

from bll.services.telegram_alert import _get_bot_config, send_message

_bot_started = False
_bot_lock    = threading.Lock()


# ──────────────────────────────────────────────────────────────────
# Command handlers
# ──────────────────────────────────────────────────────────────────

def _handle_command(text: str, chat_id: str, token: str, tg_username: str = "") -> str:
    """Xử lý lệnh Telegram; trả về chuỗi reply (HTML) hoặc rỗng."""
    parts = text.strip().split()
    cmd   = parts[0].lower()

    # Normalise: /command@BotName → /command
    if "@" in cmd:
        cmd = cmd.split("@")[0]

    # ── /start [token] ──
    if cmd == "/start":
        if len(parts) > 1:
            link_token = parts[1]
            return _handle_link_token(link_token, chat_id, tg_username)
        return _help_text()

    # ── /help ──
    elif cmd == "/help":
        return _help_text()

    # ── /ping ──
    elif cmd == "/ping":
        return "🏓 Pong! Bot đang hoạt động bình thường."

    # ── /status ──
    elif cmd == "/status":
        try:
            from dal.canh_bao_repo import count_open
            from dal.camera_chuong_repo import get_all_cameras
            open_alerts = count_open()
            cameras     = get_all_cameras()
            online_cams = sum(1 for c in cameras if c.get("trang_thai") == "online")
            now_str     = __import__("datetime").datetime.now().strftime("%H:%M:%S %d/%m/%Y")
            return (
                f"📊 <b>Trạng thái Hệ thống</b>\n\n"
                f"🔹 <b>Cảnh báo chưa xử lý:</b> {open_alerts}\n"
                f"🔹 <b>Camera trực tuyến:</b> {online_cams}/{len(cameras)}\n"
                f"🔹 <b>Thời gian:</b> {now_str}"
            )
        except Exception as e:
            return f"❌ Lỗi lấy trạng thái: {e}"

    # ── /herd ──
    elif cmd == "/herd":
        try:
            from dal.canh_bao_repo import get_by_status
            from dal.camera_chuong_repo import get_all_cameras
            cameras  = get_all_cameras()
            pending  = get_by_status("CHUA_XU_LY")
            lines = ["🐄 <b>Tình trạng đàn bò</b>\n"]
            for cam in cameras:
                status = cam.get("trang_thai", "?")
                icon   = "🟢" if status == "online" else ("🟡" if status == "warning" else "🔴")
                cam_id = cam.get("id_camera", "?")
                khu    = cam.get("khu_vuc_chuong", "?")
                lines.append(f"{icon} {khu} ({cam_id}) — {status}")
            lines.append(f"\n⚠️ Cảnh báo đang mở: <b>{len(pending)}</b>")
            return "\n".join(lines)
        except Exception as e:
            return f"❌ Lỗi: {e}"

    # ── /camera_list ──
    elif cmd == "/camera_list":
        try:
            from dal.camera_chuong_repo import get_all_cameras
            cameras = get_all_cameras()
            if not cameras:
                return "📷 Chưa có camera nào được cấu hình."
            lines = [f"📷 <b>Danh sách {len(cameras)} camera:</b>\n"]
            for c in cameras:
                st   = c.get("trang_thai", "?")
                icon = "🟢" if st == "online" else ("🟡" if st == "warning" else "🔴")
                cid  = c.get("id_camera", "?")
                khu  = c.get("khu_vuc_chuong", "?")
                lines.append(f"{icon} [{cid}] {khu} — {st}")
            return "\n".join(lines)
        except Exception as e:
            return f"❌ Lỗi: {e}"

    # ── /alerts ──
    elif cmd == "/alerts":
        try:
            from dal.canh_bao_repo import get_by_status
            alerts = get_by_status("CHUA_XU_LY")
            if not alerts:
                return "✅ Không có cảnh báo nào chưa xử lý."
            lines = ["🚨 <b>Cảnh báo chưa xử lý:</b>\n"]
            for a in alerts[-5:]:
                loai  = "🐄 Bỏ ăn" if a["loai_canh_bao"] == "cow_lie" else "⚡ Húc nhau"
                cam   = a.get("id_camera_chuong", "?")
                t     = str(a.get("created_at", "?"))[:16].replace("T", " ")
                a_id  = a.get("id_canh_bao", "?")
                lines.append(f"• [#{a_id}] {loai} | CAM-{cam} | {t}")
            lines.append("\nDùng /resolve &lt;id&gt; để đánh dấu đã xử lý.")
            return "\n".join(lines)
        except Exception as e:
            return f"❌ Lỗi: {e}"

    # ── /report [YYYY-MM-DD] — báo cáo ngày ──
    elif cmd == "/report":
        return _report_by_date(parts[1] if len(parts) > 1 else None)

    # ── /report_month [YYYY-MM] ──
    elif cmd == "/report_month":
        return _report_by_month(parts[1] if len(parts) > 1 else None)

    # ── /report_year [YYYY] ──
    elif cmd == "/report_year":
        return _report_by_year(parts[1] if len(parts) > 1 else None)

    # ── /disease [YYYY-MM-DD] — bệnh theo ngày ──
    elif cmd == "/disease":
        return _disease_by_date(parts[1] if len(parts) > 1 else None)

    # ── /disease_month [YYYY-MM] ──
    elif cmd == "/disease_month":
        return _disease_by_month(parts[1] if len(parts) > 1 else None)

    # ── /disease_year [YYYY] ──
    elif cmd == "/disease_year":
        return _disease_by_year(parts[1] if len(parts) > 1 else None)

    # ── /resolve <id> ──
    elif cmd == "/resolve":
        if len(parts) < 2 or not parts[1].isdigit():
            return "⚠️ Cú pháp: /resolve &lt;id_canh_bao&gt;\nVí dụ: /resolve 3"
        try:
            from dal.canh_bao_repo import resolve_alert
            result = resolve_alert(int(parts[1]))
            if result:
                return f"✅ Đã xử lý cảnh báo #{parts[1]}."
            return f"❌ Không tìm thấy cảnh báo #{parts[1]}."
        except Exception as e:
            return f"❌ Lỗi: {e}"

    # ── /alert_on ──
    elif cmd == "/alert_on":
        try:
            from bll.services.monitor_service import load_config, save_config
            cfg = load_config()
            cfg["notify_alert"] = True
            save_config(cfg)
        except Exception:
            pass
        return "🔔 Đã <b>BẬT</b> cảnh báo."

    # ── /alert_off ──
    elif cmd == "/alert_off":
        try:
            from bll.services.monitor_service import load_config, save_config
            cfg = load_config()
            cfg["notify_alert"] = False
            save_config(cfg)
        except Exception:
            pass
        return "🔕 Đã <b>TẮT</b> cảnh báo."

    else:
        return "❓ Lệnh không hợp lệ. Dùng /help để xem danh sách lệnh."


# ──────────────────────────────────────────────────────────────────
# Help text
# ──────────────────────────────────────────────────────────────────

def _help_text() -> str:
    return (
        "🐄 <b>Hệ thống Con Bò Cười</b>\n\n"
        "Chào mừng đến với bot giám sát đàn bò!\n\n"
        "<b>📋 Lệnh có sẵn:</b>\n\n"
        "<b>── Giám sát ──</b>\n"
        "/status                  - Trạng thái hệ thống\n"
        "/herd                    - Tình trạng đàn bò\n"
        "/camera_list             - Danh sách camera\n"
        "/alerts                  - Cảnh báo chưa xử lý\n"
        "/resolve &lt;id&gt;           - Xử lý cảnh báo\n\n"
        "<b>── Báo cáo cảnh báo ──</b>\n"
        "/report [YYYY-MM-DD]     - Báo cáo ngày (mặc định hôm nay)\n"
        "/report_month [YYYY-MM]  - Báo cáo theo tháng\n"
        "/report_year [YYYY]      - Báo cáo theo năm\n\n"
        "<b>── Báo cáo bệnh ──</b>\n"
        "/disease [YYYY-MM-DD]    - Bệnh phát hiện ngày\n"
        "/disease_month [YYYY-MM] - Bệnh phát hiện tháng\n"
        "/disease_year [YYYY]     - Bệnh phát hiện năm\n\n"
        "<b>── Thông báo ──</b>\n"
        "/alert_on                - Bật cảnh báo\n"
        "/alert_off               - Tắt cảnh báo\n\n"
        "<b>── Khác ──</b>\n"
        "/ping                    - Kiểm tra kết nối\n"
        "/help                    - Xem lệnh này"
    )


# ──────────────────────────────────────────────────────────────────
# Report helpers — cảnh báo theo ngày / tháng / năm
# ──────────────────────────────────────────────────────────────────

def _report_by_date(date_str: str | None) -> str:
    from datetime import date as _date
    try:
        from dal.canh_bao_repo import get_all
        all_alerts = get_all()
    except Exception as e:
        return f"❌ Lỗi: {e}"

    if date_str:
        try:
            _date.fromisoformat(date_str)   # validate format
            prefix = date_str[:10]
        except ValueError:
            return "⚠️ Định dạng ngày không hợp lệ. Ví dụ: /report 2026-05-08"
    else:
        prefix = _date.today().isoformat()

    subset = [a for a in all_alerts if str(a.get("created_at", "")).startswith(prefix)]
    return _format_alert_report(subset, f"ngày {prefix}")


def _report_by_month(month_str: str | None) -> str:
    from datetime import date as _date
    try:
        from dal.canh_bao_repo import get_all
        all_alerts = get_all()
    except Exception as e:
        return f"❌ Lỗi: {e}"

    if month_str:
        prefix = month_str[:7]
    else:
        prefix = _date.today().strftime("%Y-%m")

    subset = [a for a in all_alerts if str(a.get("created_at", "")).startswith(prefix)]
    return _format_alert_report(subset, f"tháng {prefix}")


def _report_by_year(year_str: str | None) -> str:
    from datetime import date as _date
    try:
        from dal.canh_bao_repo import get_all
        all_alerts = get_all()
    except Exception as e:
        return f"❌ Lỗi: {e}"

    prefix = (year_str or str(_date.today().year))[:4]
    subset = [a for a in all_alerts if str(a.get("created_at", "")).startswith(prefix)]
    return _format_alert_report(subset, f"năm {prefix}")


def _format_alert_report(subset: list, period: str) -> str:
    if not subset:
        return f"📋 Không có cảnh báo nào trong {period}."
    done    = sum(1 for a in subset if a.get("trang_thai") == "DA_XU_LY")
    pending = len(subset) - done
    fight   = sum(1 for a in subset if a.get("loai_canh_bao") == "cow_fight")
    lie     = sum(1 for a in subset if a.get("loai_canh_bao") == "cow_lie")
    return (
        f"📋 <b>Báo cáo cảnh báo — {period}</b>\n\n"
        f"🔢 Tổng:           <b>{len(subset)}</b>\n"
        f"⚡ Bò húc nhau:   <b>{fight}</b>\n"
        f"🐄 Bò bỏ ăn:      <b>{lie}</b>\n"
        f"✅ Đã xử lý:      <b>{done}</b>\n"
        f"🟡 Còn tồn:       <b>{pending}</b>"
    )


# ──────────────────────────────────────────────────────────────────
# Report helpers — bệnh theo ngày / tháng / năm
# Dùng bảng lich_su_kiem_duyet (lịch sử tư vấn / bệnh)
# ──────────────────────────────────────────────────────────────────

def _get_disease_history() -> list[dict]:
    """Lấy lịch sử phát hiện bệnh từ bảng lich_su_kiem_duyet."""
    try:
        from dal.base_repo import BaseRepo
        repo = BaseRepo("lich_su_kiem_duyet", pk_field="id_lich_su")
        return repo.find_all() or []
    except Exception:
        return []


def _disease_by_date(date_str: str | None) -> str:
    from datetime import date as _date
    if date_str:
        try:
            _date.fromisoformat(date_str)
            prefix = date_str[:10]
        except ValueError:
            return "⚠️ Định dạng ngày không hợp lệ. Ví dụ: /disease 2026-05-08"
    else:
        prefix = _date.today().isoformat()

    records = [r for r in _get_disease_history()
               if str(r.get("created_at", "") or r.get("thoi_gian", "")).startswith(prefix)]
    return _format_disease_report(records, f"ngày {prefix}")


def _disease_by_month(month_str: str | None) -> str:
    from datetime import date as _date
    prefix = (month_str or _date.today().strftime("%Y-%m"))[:7]
    records = [r for r in _get_disease_history()
               if str(r.get("created_at", "") or r.get("thoi_gian", "")).startswith(prefix)]
    return _format_disease_report(records, f"tháng {prefix}")


def _disease_by_year(year_str: str | None) -> str:
    from datetime import date as _date
    prefix = (year_str or str(_date.today().year))[:4]
    records = [r for r in _get_disease_history()
               if str(r.get("created_at", "") or r.get("thoi_gian", "")).startswith(prefix)]
    return _format_disease_report(records, f"năm {prefix}")


def _format_disease_report(records: list, period: str) -> str:
    if not records:
        return f"🩺 Không có bệnh nào được phát hiện trong {period}."

    # Đếm theo loại bệnh
    from collections import Counter
    counter: Counter = Counter()
    for r in records:
        disease = (
            r.get("ket_qua_chan_doan")
            or r.get("loai_benh")
            or r.get("label")
            or "Không rõ"
        )
        counter[disease] += 1

    lines = [f"🩺 <b>Phát hiện bệnh — {period}</b>\n", f"📊 Tổng ca: <b>{len(records)}</b>\n"]
    for disease, count in counter.most_common(10):
        lines.append(f"• {disease}: <b>{count}</b> ca")
    return "\n".join(lines)


def _handle_link_token(link_token: str, chat_id: str, tg_username: str = "") -> str:
    """Xử lý /start <token> — liên kết Telegram với tài khoản farmer."""
    try:
        from bll.services.telegram_link import validate_token, bind_telegram
        username = validate_token(link_token)
        if not username:
            return "❌ Token không hợp lệ hoặc đã hết hạn.\nVui lòng tạo lại liên kết trong ứng dụng."
        success = bind_telegram(username, chat_id, tg_username)
        if success:
            return (
                f"✅ <b>Liên kết thành công!</b>\n\n"
                f"Tài khoản <b>{username}</b> đã liên kết với Telegram.\n"
                f"Bạn sẽ nhận cảnh báo bò tự động từ hệ thống Con Bò Cười.\n\n"
                f"Dùng /start để xem các lệnh có sẵn."
            )
        return (
            "⚠️ Tài khoản đã được liên kết trước đó.\n"
            "Nếu muốn cập nhật lại, hãy liên hệ admin hoặc dùng chức năng Hủy liên kết trong ứng dụng."
        )
    except Exception as e:
        return f"❌ Lỗi liên kết: {e}"


# ──────────────────────────────────────────────────────────────────
# Long Polling Loop
# ──────────────────────────────────────────────────────────────────

def _polling_loop():
    """Vòng lặp long-polling nhận lệnh từ Telegram (daemon thread)."""
    bot_cfg = _get_bot_config()
    token   = bot_cfg.get("bot_token", "")

    if not token:
        print("[CowBot] Bot token chưa cấu hình — polling không khởi động.")
        return

    last_id = 0
    print("[CowBot] Bot khởi động — bắt đầu long polling...")

    while True:
        try:
            url    = f"https://api.telegram.org/bot{token}/getUpdates"
            params = {"offset": last_id + 1, "timeout": 30}
            resp   = requests.get(url, params=params, timeout=35)
            result = resp.json()

            if not result.get("ok"):
                time.sleep(5)
                continue

            for update in result.get("result", []):
                uid = update.get("update_id", 0)
                if uid > last_id:
                    last_id = uid

                message      = update.get("message", {})
                text         = (message.get("text") or "").strip()
                chat_id      = str(message.get("chat", {}).get("id", ""))
                tg_username  = message.get("from", {}).get("username", "")

                if text.startswith("/") and chat_id:
                    reply = _handle_command(text, chat_id, token, tg_username)
                    if reply:
                        send_message(token, chat_id, reply)

        except requests.exceptions.Timeout:
            continue        # Long polling timeout là bình thường
        except requests.exceptions.ConnectionError as e:
            # 10054 = server reset connection (bình thường với long-poll)
            err_str = str(e)
            if "10054" in err_str or "ConnectionReset" in err_str or "RemoteDisconnected" in err_str:
                time.sleep(2)   # Ngắn — Telegram reset, kết nối lại nhanh
            else:
                print(f"[CowBot] Mất kết nối: {e}")
                time.sleep(10)
        except Exception as e:
            print(f"[CowBot] Lỗi polling: {e}")
            time.sleep(5)


def start_bot() -> None:
    """Khởi động bot trong background daemon thread (singleton)."""
    global _bot_started
    with _bot_lock:
        if _bot_started:
            return
        _bot_started = True
    threading.Thread(target=_polling_loop, daemon=True, name="TelegramBot").start()
    print("[CowBot] Daemon thread khởi động.")
