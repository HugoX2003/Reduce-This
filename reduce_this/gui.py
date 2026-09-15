"""Interfaz gráfica (Tkinter) para el reductor de tamaño de videos."""
import os
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import compressor
import ffmpeg_utils

PRESETS_MB = [200, 500]
AUDIO_OPTIONS = [128, 160, 192]


def format_duration(seconds):
    if not seconds:
        return "?"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Reductor de tamaño de video")
        self.resizable(False, False)
        self.geometry("560x480")

        self.input_path = None
        self.video_info = None
        self.worker_thread = None
        self.cancel_event = threading.Event()
        self.progress_queue = queue.Queue()

        self._build_widgets()
        self.after(100, self._poll_queue)

    # ---------- UI ----------
    def _build_widgets(self):
        pad = {"padx": 10, "pady": 6}

        # Archivo de entrada
        frame_in = ttk.LabelFrame(self, text="Video de entrada")
        frame_in.pack(fill="x", **pad)

        self.lbl_input = ttk.Label(frame_in, text="(ningún archivo seleccionado)", wraplength=400)
        self.lbl_input.pack(side="left", padx=8, pady=8, fill="x", expand=True)
        ttk.Button(frame_in, text="Seleccionar...", command=self.on_select_input).pack(side="right", padx=8, pady=8)

        self.lbl_info = ttk.Label(self, text="", foreground="#555555")
        self.lbl_info.pack(fill="x", padx=14)

        # Tamaño objetivo
        frame_size = ttk.LabelFrame(self, text="Tamaño objetivo")
        frame_size.pack(fill="x", **pad)

        self.target_var = tk.StringVar(value="200")
        for mb in PRESETS_MB:
            ttk.Radiobutton(
                frame_size, text=f"{mb} MB", value=str(mb), variable=self.target_var,
                command=self._update_estimate,
            ).pack(side="left", padx=8, pady=8)

        ttk.Radiobutton(
            frame_size, text="Personalizado:", value="custom", variable=self.target_var,
            command=self._update_estimate,
        ).pack(side="left", padx=(8, 2), pady=8)

        self.custom_mb_var = tk.StringVar(value="300")
        custom_spin = ttk.Spinbox(
            frame_size, from_=5, to=10000, increment=10, width=6,
            textvariable=self.custom_mb_var, command=self._update_estimate,
        )
        custom_spin.pack(side="left", pady=8)
        custom_spin.bind("<KeyRelease>", lambda e: self._update_estimate())
        ttk.Label(frame_size, text="MB").pack(side="left", padx=(2, 8))

        # Calidad de audio
        frame_audio = ttk.LabelFrame(self, text="Calidad de audio (AAC)")
        frame_audio.pack(fill="x", **pad)

        self.audio_var = tk.StringVar(value="160")
        for kbps in AUDIO_OPTIONS:
            ttk.Radiobutton(
                frame_audio, text=f"{kbps} kbps" + (" (recomendado)" if kbps == 160 else ""),
                value=str(kbps), variable=self.audio_var, command=self._update_estimate,
            ).pack(side="left", padx=8, pady=8)

        # Estimación
        self.lbl_estimate = ttk.Label(self, text="", foreground="#555555")
        self.lbl_estimate.pack(fill="x", padx=14, pady=(0, 6))

        # Salida
        frame_out = ttk.LabelFrame(self, text="Guardar como")
        frame_out.pack(fill="x", **pad)
        self.output_var = tk.StringVar()
        ttk.Entry(frame_out, textvariable=self.output_var).pack(side="left", padx=8, pady=8, fill="x", expand=True)
        ttk.Button(frame_out, text="Elegir...", command=self.on_choose_output).pack(side="right", padx=8, pady=8)

        # Progreso
        frame_progress = ttk.Frame(self)
        frame_progress.pack(fill="x", **pad)
        self.progress = ttk.Progressbar(frame_progress, maximum=100)
        self.progress.pack(fill="x", padx=4, pady=(4, 2))
        self.lbl_status = ttk.Label(frame_progress, text="Listo.")
        self.lbl_status.pack(anchor="w", padx=4)

        # Botones
        frame_buttons = ttk.Frame(self)
        frame_buttons.pack(fill="x", **pad)
        self.btn_start = ttk.Button(frame_buttons, text="Comprimir", command=self.on_start)
        self.btn_start.pack(side="left", padx=8)
        self.btn_cancel = ttk.Button(frame_buttons, text="Cancelar", command=self.on_cancel, state="disabled")
        self.btn_cancel.pack(side="left", padx=8)

    # ---------- Helpers ----------
    def _get_target_mb(self):
        val = self.target_var.get()
        if val == "custom":
            try:
                return float(self.custom_mb_var.get())
            except ValueError:
                return None
        return float(val)

    def _update_estimate(self):
        if not self.video_info or not self.video_info.get("duration"):
            self.lbl_estimate.config(text="")
            return
        target_mb = self._get_target_mb()
        if not target_mb or target_mb <= 0:
            self.lbl_estimate.config(text="")
            return
        audio_kbps = int(self.audio_var.get())
        duration = self.video_info["duration"]
        video_kbps = compressor.calculate_video_bitrate(duration, target_mb, audio_kbps)
        warning = ""
        if video_kbps <= compressor.MIN_VIDEO_KBPS:
            warning = "  ⚠ El tamaño pedido es muy chico para la duración: la calidad se verá afectada."
        self.lbl_estimate.config(
            text=f"Bitrate estimado: video ≈ {video_kbps} kbps, audio = {audio_kbps} kbps.{warning}"
        )

    def _suggest_output_path(self, input_path):
        base, _ext = os.path.splitext(input_path)
        return f"{base}_reducido.mp4"

    # ---------- Eventos ----------
    def on_select_input(self):
        path = filedialog.askopenfilename(
            title="Selecciona un video",
            filetypes=[
                ("Videos", "*.mp4 *.mov *.mkv *.avi *.webm *.m4v *.wmv *.flv"),
                ("Todos los archivos", "*.*"),
            ],
        )
        if not path:
            return
        self.input_path = path
        self.lbl_input.config(text=path)
        self.output_var.set(self._suggest_output_path(path))
        self.lbl_status.config(text="Analizando video...")
        self.lbl_info.config(text="")
        threading.Thread(target=self._probe_input, args=(path,), daemon=True).start()

    def _probe_input(self, path):
        try:
            info = ffmpeg_utils.probe(path)
            size_mb = os.path.getsize(path) / (1024 * 1024)
            info["size_mb"] = size_mb
        except Exception as exc:  # noqa: BLE001
            self.progress_queue.put(("error", f"No se pudo leer el video: {exc}"))
            return
        self.progress_queue.put(("info", info))

    def on_choose_output(self):
        path = filedialog.asksaveasfilename(
            title="Guardar video comprimido como",
            defaultextension=".mp4",
            filetypes=[("MP4", "*.mp4")],
        )
        if path:
            self.output_var.set(path)

    def on_start(self):
        if not self.input_path:
            messagebox.showwarning("Falta el video", "Primero selecciona un video de entrada.")
            return
        target_mb = self._get_target_mb()
        if not target_mb or target_mb <= 0:
            messagebox.showwarning("Tamaño inválido", "Ingresa un tamaño objetivo válido en MB.")
            return
        output_path = self.output_var.get().strip()
        if not output_path:
            messagebox.showwarning("Falta la salida", "Elige dónde guardar el video comprimido.")
            return
        if os.path.abspath(output_path) == os.path.abspath(self.input_path):
            messagebox.showwarning("Ruta inválida", "El archivo de salida no puede ser el mismo que el de entrada.")
            return

        self.cancel_event = threading.Event()
        self.btn_start.config(state="disabled")
        self.btn_cancel.config(state="normal")
        self.progress.config(value=0)
        self.lbl_status.config(text="Comprimiendo... (pasada 1 de 2)")

        audio_kbps = int(self.audio_var.get())
        self.worker_thread = threading.Thread(
            target=self._run_compression,
            args=(self.input_path, output_path, target_mb, audio_kbps),
            daemon=True,
        )
        self.worker_thread.start()

    def _run_compression(self, input_path, output_path, target_mb, audio_kbps):
        def progress_cb(frac):
            self.progress_queue.put(("progress", frac))

        try:
            stats = compressor.run_two_pass(
                input_path, output_path, target_mb,
                audio_kbps=audio_kbps,
                progress_cb=progress_cb,
                cancel_event=self.cancel_event,
            )
            self.progress_queue.put(("done", stats))
        except compressor.CompressionCancelled:
            self.progress_queue.put(("cancelled", None))
        except Exception as exc:  # noqa: BLE001
            self.progress_queue.put(("error", str(exc)))

    def on_cancel(self):
        if self.worker_thread and self.worker_thread.is_alive():
            self.cancel_event.set()
            self.lbl_status.config(text="Cancelando...")
            self.btn_cancel.config(state="disabled")

    # ---------- Cola de progreso ----------
    def _poll_queue(self):
        try:
            while True:
                kind, payload = self.progress_queue.get_nowait()
                if kind == "info":
                    self.video_info = payload
                    dur = format_duration(payload.get("duration"))
                    res = f"{payload.get('width')}x{payload.get('height')}" if payload.get("width") else "?"
                    fps = payload.get("fps")
                    fps_txt = f"{fps:.0f} fps" if fps else "? fps"
                    self.lbl_info.config(
                        text=f"Duración: {dur}   Resolución: {res}   {fps_txt}   "
                             f"Tamaño actual: {payload.get('size_mb', 0):.1f} MB"
                    )
                    self.lbl_status.config(text="Listo.")
                    self._update_estimate()
                elif kind == "progress":
                    pct = max(0.0, min(1.0, payload)) * 100
                    self.progress.config(value=pct)
                    pass_txt = "pasada 1 de 2" if payload < 0.4 else "pasada 2 de 2"
                    self.lbl_status.config(text=f"Comprimiendo... ({pass_txt}) {pct:.0f}%")
                elif kind == "done":
                    self.progress.config(value=100)
                    self.lbl_status.config(text="¡Listo!")
                    self.btn_start.config(state="normal")
                    self.btn_cancel.config(state="disabled")
                    messagebox.showinfo(
                        "Compresión completa",
                        "Video comprimido correctamente.\n"
                        f"Tamaño final: {payload['output_size_mb']:.1f} MB\n"
                        f"Video: {payload['video_kbps']} kbps   Audio: {payload['audio_kbps']} kbps\n"
                        f"Guardado en: {self.output_var.get()}",
                    )
                elif kind == "cancelled":
                    self.lbl_status.config(text="Cancelado.")
                    self.btn_start.config(state="normal")
                    self.btn_cancel.config(state="disabled")
                elif kind == "error":
                    self.lbl_status.config(text="Error.")
                    self.btn_start.config(state="normal")
                    self.btn_cancel.config(state="disabled")
                    messagebox.showerror("Error", payload)
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)


def main():
    app = App()
    app.mainloop()
