"""Localización de ffmpeg y extracción de metadatos de video."""
import re
import subprocess
import sys

import imageio_ffmpeg

_FFMPEG_EXE = None

_DURATION_RE = re.compile(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)")
_RES_RE = re.compile(r"(\d{2,5})x(\d{2,5})")
_FPS_RE = re.compile(r"([\d.]+)\s*fps")
_VIDEO_LINE_RE = re.compile(r"Stream #\d+:\d+.*Video:")


def creation_flags():
    return subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


def get_ffmpeg_exe():
    """Devuelve la ruta al binario de ffmpeg, descargándolo la primera vez si hace falta."""
    global _FFMPEG_EXE
    if _FFMPEG_EXE is None:
        _FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
    return _FFMPEG_EXE


def probe(input_path):
    """Extrae duración (segundos), resolución y fps corriendo `ffmpeg -i` y parseando stderr."""
    exe = get_ffmpeg_exe()
    proc = subprocess.run(
        [exe, "-i", input_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        creationflags=creation_flags(),
    )
    out = proc.stdout or ""

    duration = None
    m = _DURATION_RE.search(out)
    if m:
        h, mi, s = m.groups()
        duration = int(h) * 3600 + int(mi) * 60 + float(s)

    width = height = fps = None
    for line in out.splitlines():
        if _VIDEO_LINE_RE.search(line):
            rm = _RES_RE.search(line)
            if rm:
                width, height = int(rm.group(1)), int(rm.group(2))
            fm = _FPS_RE.search(line)
            if fm:
                fps = float(fm.group(1))
            break

    return {"duration": duration, "width": width, "height": height, "fps": fps, "raw": out}
