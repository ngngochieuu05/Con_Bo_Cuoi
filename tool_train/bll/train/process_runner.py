import os
import subprocess


def launch_inline_python(script: str, python_exe: str, cwd: str, *, unbuffered: bool = False, force_utf8: bool = False):
    env = os.environ.copy()
    if force_utf8:
        env["PYTHONUTF8"] = "1"
    args = [str(python_exe)]
    if unbuffered:
        args.append("-u")
    args.extend(["-c", script])
    return subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        encoding="utf-8",
        errors="replace",
        cwd=str(cwd),
        env=env,
    )
