"""Lógica de compresión: calcula bitrate objetivo y ejecuta ffmpeg en dos pasadas."""
import os
import subprocess
import sys
import tempfile

from ffmpeg_utils import get_ffmpeg_exe, probe, creation_flags

MIN_VIDEO_KBPS = 150  # por debajo de esto la calidad se degrada mucho
FPS_CAP = 30  # las grabaciones de pantalla no necesitan más para verse nítidas


class CompressionError(Exception):
    pass


class CompressionCancelled(Exception):
    pass


def calculate_video_bitrate(duration_sec, target_size_mb, audio_kbps, safety_margin=0.97):
    """Reparte el tamaño objetivo entre video y audio, dejando un margen de seguridad."""
    target_bits = target_size_mb * 8 * 1024 * 1024 * safety_margin
    video_kbps = target_bits / duration_sec / 1000 - audio_kbps
    return max(int(video_kbps), MIN_VIDEO_KBPS)


def _target_fps(source_fps):
    if source_fps and source_fps > FPS_CAP + 0.5:
        return FPS_CAP
    return None  # conservar el fps original


def run_two_pass(input_path, output_path, target_size_mb, audio_kbps=160,
                  progress_cb=None, cancel_event=None, preset="slow"):
    """Comprime input_path a output_path apuntando a target_size_mb (aprox). Devuelve stats."""
    info = probe(input_path)
    duration = info["duration"]
    if not duration or duration <= 0:
        raise CompressionError("No se pudo determinar la duración del video.")

    video_kbps = calculate_video_bitrate(duration, target_size_mb, audio_kbps)
    fps = _target_fps(info.get("fps"))

    exe = get_ffmpeg_exe()
    passlog = os.path.join(tempfile.gettempdir(), f"reducemeesta_pass_{os.getpid()}")
    null_out = "NUL" if sys.platform == "win32" else "/dev/null"
    fps_args = ["-r", str(fps)] if fps else []

    def _run(cmd, weight_start, weight_end):
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, creationflags=creation_flags(),
        )
        for line in proc.stdout:
            if cancel_event is not None and cancel_event.is_set():
                proc.terminate()
                proc.wait()
                raise CompressionCancelled()
            if "out_time_ms=" in line:
                try:
                    ms = int(line.strip().split("=")[1])
                    frac = min(max(ms / 1_000_000 / duration, 0.0), 1.0)
                    if progress_cb:
                        progress_cb(weight_start + frac * (weight_end - weight_start))
                except (ValueError, ZeroDivisionError):
                    pass
        proc.wait()
        if proc.returncode != 0:
            raise CompressionError(f"ffmpeg terminó con código {proc.returncode} (paso {weight_start}-{weight_end})")

    pass1_cmd = [
        exe, "-y", "-i", input_path, *fps_args,
        "-c:v", "libx264", "-b:v", f"{video_kbps}k", "-preset", preset,
        "-pass", "1", "-passlogfile", passlog,
        "-an", "-f", "mp4",
        "-progress", "pipe:1", "-nostats",
        null_out,
    ]
    pass2_cmd = [
        exe, "-y", "-i", input_path, *fps_args,
        "-c:v", "libx264", "-b:v", f"{video_kbps}k", "-preset", preset,
        "-pass", "2", "-passlogfile", passlog,
        "-c:a", "aac", "-b:a", f"{audio_kbps}k",
        "-movflags", "+faststart",
        "-progress", "pipe:1", "-nostats",
        output_path,
    ]

    try:
        _run(pass1_cmd, 0.0, 0.4)
        _run(pass2_cmd, 0.4, 1.0)
    finally:
        for suffix in ("-0.log", "-0.log.mbtree", ".log", ".log.mbtree", "-0.log.temp", "-0.log.mbtree.temp"):
            try:
                os.remove(passlog + suffix)
            except OSError:
                pass

    if progress_cb:
        progress_cb(1.0)

    return {
        "video_kbps": video_kbps,
        "audio_kbps": audio_kbps,
        "fps": fps or info.get("fps"),
        "width": info.get("width"),
        "height": info.get("height"),
        "output_size_mb": os.path.getsize(output_path) / (1024 * 1024),
    }
