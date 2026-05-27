import time

from bll.train.process_runner import launch_inline_python


def stream_inline_job(
    script: str,
    python_exe: str,
    cwd: str,
    line_callback,
    is_active,
    *,
    on_process_started=None,
    unbuffered: bool = False,
    force_utf8: bool = False,
):
    process = None
    try:
        process = launch_inline_python(
            script,
            python_exe,
            cwd,
            unbuffered=unbuffered,
            force_utf8=force_utf8,
        )
        if on_process_started:
            on_process_started(process)
        for line in process.stdout:
            if not is_active():
                break
            line_callback(line)
        process.wait()
        return process.returncode, None
    except Exception as ex:
        return -1, ex
    finally:
        if on_process_started:
            on_process_started(None)


def detect_stream_tag(line: str) -> str:
    if "[EPOCH]" in line or line.strip().startswith("Epoch"):
        return "epoch"
    if "[BATCH]" in line:
        return "dim"
    if "[BEST]" in line:
        return "best"
    if "[DONE]" in line or "[RESULT]" in line or "✔" in line:
        return "ok"
    if "[WARN]" in line or "WARNING" in line or "warn" in line.lower():
        return "warn"
    if "[ERROR]" in line or "Error" in line or "Traceback" in line:
        return "err"
    if "[INFO]" in line:
        return "info"
    return ""


def parse_epoch_progress(line: str, start_time: float):
    cur = tot = None
    acc_str = ""
    if "[EPOCH]" in line:
        try:
            parts = line.split()
            cur, tot = parts[1].split("/")
            cur, tot = int(cur), int(tot)
            if "Val Acc:" in line:
                acc_str = line.split("Val Acc:")[1].split("|")[0].strip()
        except Exception:
            return None
    elif "Epoch" in line and "/" in line:
        try:
            for part in line.split():
                if "/" in part:
                    cur, tot = part.split("/")
                    cur, tot = int(cur.strip()), int(tot.strip())
                    break
        except Exception:
            return None
    else:
        return None

    if not cur or not tot:
        return None
    elapsed = max(time.time() - start_time, 0.0)
    eta_s = (elapsed / cur) * (tot - cur) if cur > 0 else 0.0
    return {
        "cur": cur,
        "tot": tot,
        "pct": int(cur / tot * 100),
        "acc_str": acc_str,
        "elapsed": elapsed,
        "eta_s": eta_s,
    }
