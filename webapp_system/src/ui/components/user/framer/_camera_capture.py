"""
Helper script chay trong subprocess doc lap de chup anh camera.
Usage: python _camera_capture.py <camera_index>
Output: JSON { "path": "<path_to_jpg>" } hoac { "error": "<msg>" }
Luu ra file thay vi base64 de tranh Flutter renderer crash voi data URI lon.
"""
import json
import os
import sys
import tempfile

try:
    import ctypes
    ctypes.windll.kernel32.SetErrorMode(0x8007)
except Exception:
    pass


def main():
    try:
        idx = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    except (ValueError, IndexError):
        idx = 0

    try:
        import cv2
    except ImportError:
        print(json.dumps({"error": "opencv_not_installed"}))
        sys.exit(1)

    cap = None
    try:
        cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(idx)
        if not cap.isOpened():
            print(json.dumps({"error": f"cannot_open_{idx}"}))
            sys.exit(1)

        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter.fourcc("M", "J", "P", "G"))
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        for _ in range(5):
            cap.grab()

        ret, frame = cap.read()
        if not ret:
            print(json.dumps({"error": "no_frame"}))
            sys.exit(1)

        fd, path = tempfile.mkstemp(suffix=".jpg", prefix="cam_snap_")
        os.close(fd)
        cv2.imwrite(path, frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        print(json.dumps({"path": path}))

    finally:
        if cap is not None:
            try:
                cap.release()
            except Exception:
                pass


if __name__ == "__main__":
    main()