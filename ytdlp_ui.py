#!/usr/bin/env python3
"""
Interface gráfica para baixar vídeo, áudio ou playlist.

Uso:
    python ytdlp_ui.py
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk
from tkinter.scrolledtext import ScrolledText

from ytdlp_helper import (
    DEFAULT_OUTPUT_DIR,
    download_audio,
    download_playlist,
    download_video,
    logger,
)

MODES = (
    ("video", "Vídeo"),
    ("audio", "Áudio"),
    ("playlist", "Playlist (vídeo)"),
    ("playlist_audio", "Playlist (áudio)"),
)
QUALITIES = ("Melhor disponível", "2160", "1440", "1080", "720", "480", "360")
AUDIO_FORMATS = ("mp3", "m4a", "wav", "flac", "opus")
AUDIO_MODES = {"audio", "playlist_audio"}


class UiLogHandler(logging.Handler):
    """Encaminha o log do yt-dlp para a caixa de texto da janela."""

    def __init__(self, app: "App") -> None:
        super().__init__(level=logging.INFO)
        self.app = app
        self.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)-8s | %(message)s", "%H:%M:%S")
        )

    def emit(self, record: logging.LogRecord) -> None:
        message = self.format(record)
        self.app.after(0, self.app.append_log, message)


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Video Downloader")
        self.geometry("760x560")
        self.minsize(640, 480)

        self.mode_var = tk.StringVar(value="video")
        self.url_var = tk.StringVar()
        self.output_var = tk.StringVar(value=DEFAULT_OUTPUT_DIR)
        self.quality_var = tk.StringVar(value=QUALITIES[0])
        self.format_var = tk.StringVar(value=AUDIO_FORMATS[0])
        self.status_var = tk.StringVar(value="Pronto.")
        self.detail_var = tk.StringVar(value="")
        self._last_progress = 0.0
        self._progress_indeterminate = False

        self._build()
        self._sync_mode()
        logger.addHandler(UiLogHandler(self))
        self.url_entry.focus_set()

    def _build(self) -> None:
        container = ttk.Frame(self, padding=16)
        container.grid(row=0, column=0, sticky="nsew")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(4, weight=1)

        header = ttk.Frame(container)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        ttk.Label(header, text="Video Downloader", font=("", 18, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            header,
            text="Baixa vídeo, áudio ou playlist para a pasta Downloads.",
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        form = ttk.LabelFrame(container, text="Download", padding=12)
        form.grid(row=1, column=0, sticky="ew")
        form.columnconfigure(1, weight=1)

        ttk.Label(form, text="URL").grid(row=0, column=0, sticky="w", pady=4)
        self.url_entry = ttk.Entry(form, textvariable=self.url_var)
        self.url_entry.grid(row=0, column=1, columnspan=2, sticky="ew", pady=4)

        ttk.Label(form, text="Tipo").grid(row=1, column=0, sticky="w", pady=4)
        modes = ttk.Frame(form)
        modes.grid(row=1, column=1, columnspan=2, sticky="w", pady=4)
        self._mode_buttons = []
        for value, label in MODES:
            button = ttk.Radiobutton(
                modes,
                text=label,
                value=value,
                variable=self.mode_var,
                command=self._sync_mode,
            )
            button.pack(side="left", padx=(0, 12))
            self._mode_buttons.append(button)

        ttk.Label(form, text="Opções").grid(row=2, column=0, sticky="w", pady=4)
        options = ttk.Frame(form)
        options.grid(row=2, column=1, columnspan=2, sticky="w", pady=4)
        ttk.Label(options, text="Qualidade").pack(side="left")
        self.quality_box = ttk.Combobox(
            options,
            textvariable=self.quality_var,
            values=QUALITIES,
            state="readonly",
            width=18,
        )
        self.quality_box.pack(side="left", padx=(8, 16))
        ttk.Label(options, text="Formato").pack(side="left")
        self.format_box = ttk.Combobox(
            options,
            textvariable=self.format_var,
            values=AUDIO_FORMATS,
            state="disabled",
            width=10,
        )
        self.format_box.pack(side="left", padx=(8, 0))

        ttk.Label(form, text="Pasta").grid(row=3, column=0, sticky="w", pady=4)
        self.output_entry = ttk.Entry(form, textvariable=self.output_var)
        self.output_entry.grid(row=3, column=1, sticky="ew", pady=4, padx=(0, 8))
        folder_buttons = ttk.Frame(form)
        folder_buttons.grid(row=3, column=2, sticky="e", pady=4)
        ttk.Button(folder_buttons, text="Escolher", command=self._choose_folder).pack(
            side="left"
        )
        ttk.Button(folder_buttons, text="Abrir", command=self._open_folder).pack(
            side="left", padx=(6, 0)
        )

        actions = ttk.Frame(container)
        actions.grid(row=2, column=0, sticky="ew", pady=(12, 8))
        actions.columnconfigure(1, weight=1)
        self.download_button = ttk.Button(
            actions, text="Baixar", command=self._start_download
        )
        self.download_button.grid(row=0, column=0, sticky="w")
        ttk.Label(actions, textvariable=self.status_var).grid(
            row=0, column=1, sticky="w", padx=12
        )

        self.progress = ttk.Progressbar(actions, mode="determinate", maximum=100)
        self.progress.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        ttk.Label(actions, textvariable=self.detail_var).grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(4, 0)
        )

        log_frame = ttk.LabelFrame(container, text="Registro", padding=8)
        log_frame.grid(row=4, column=0, sticky="nsew", pady=(8, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        self.log = ScrolledText(log_frame, height=12, wrap="word", state="disabled")
        self.log.grid(row=0, column=0, sticky="nsew")

    def _sync_mode(self) -> None:
        audio = self.mode_var.get() in AUDIO_MODES
        self.quality_box.configure(state="disabled" if audio else "readonly")
        self.format_box.configure(state="readonly" if audio else "disabled")

    def _choose_folder(self) -> None:
        current = self.output_var.get().strip() or DEFAULT_OUTPUT_DIR
        selected = filedialog.askdirectory(initialdir=current)
        if selected:
            self.output_var.set(selected)

    def _open_folder(self) -> None:
        path = Path(self.output_var.get().strip() or DEFAULT_OUTPUT_DIR).expanduser()
        if not path.is_dir():
            self.status_var.set("A pasta ainda não existe.")
            return
        if sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=False)
        elif sys.platform == "win32":
            subprocess.run(["explorer", str(path)], check=False)
        else:
            subprocess.run(["xdg-open", str(path)], check=False)

    def append_log(self, message: str) -> None:
        if not self.winfo_exists():
            return
        self.log.configure(state="normal")
        self.log.insert("end", message + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _clear_log(self) -> None:
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    def _selected_quality(self) -> str | None:
        quality = self.quality_var.get().strip()
        if not quality or quality == QUALITIES[0]:
            return None
        return quality

    def _set_busy(self, busy: bool) -> None:
        state = "disabled" if busy else "normal"
        self.download_button.configure(state=state)
        self.url_entry.configure(state=state)
        self.output_entry.configure(state=state)
        for button in self._mode_buttons:
            button.configure(state=state)
        if busy:
            self.status_var.set("Baixando...")
            self.quality_box.configure(state="disabled")
            self.format_box.configure(state="disabled")
        else:
            self._sync_mode()

    def _apply_progress(self, percent: float | None, detail: str) -> None:
        if not self.winfo_exists():
            return
        if percent is None:
            if not self._progress_indeterminate:
                self.progress.configure(mode="indeterminate")
                self.progress.start(12)
                self._progress_indeterminate = True
        else:
            if self._progress_indeterminate:
                self.progress.stop()
                self.progress.configure(mode="determinate", maximum=100)
                self._progress_indeterminate = False
            self.progress["value"] = percent
        self.detail_var.set(detail)

    def _on_progress(self, data: dict) -> None:
        # O hook roda na thread de download; a janela só atualiza na thread principal.
        status = data.get("status")
        now = time.monotonic()
        if status == "downloading" and now - self._last_progress < 0.1:
            return
        self._last_progress = now

        if status == "downloading":
            total = data.get("total_bytes") or data.get("total_bytes_estimate")
            done = data.get("downloaded_bytes") or 0
            percent = (done / total * 100.0) if total else None
            parts = []
            if percent is not None:
                parts.append(f"{percent:.0f}%")
            speed = (data.get("_speed_str") or "").strip()
            eta = (data.get("_eta_str") or "").strip()
            if speed:
                parts.append(speed)
            if eta:
                parts.append(f"restante {eta}")
            self.after(0, self._apply_progress, percent, " · ".join(parts))
        elif status == "finished":
            self.after(0, self._apply_progress, 100.0, "Processando arquivo...")

    def _start_download(self) -> None:
        url = self.url_var.get().strip()
        if not url:
            self.status_var.set("Informe uma URL.")
            return

        output_dir = self.output_var.get().strip() or DEFAULT_OUTPUT_DIR
        mode = self.mode_var.get()
        quality = self._selected_quality()
        audio_format = self.format_var.get().strip() or "mp3"

        self._clear_log()
        self._last_progress = 0.0
        self._apply_progress(0.0, "")
        self._set_busy(True)

        # O download fica fora da thread da interface para a janela não travar.
        threading.Thread(
            target=self._download,
            args=(url, output_dir, mode, quality, audio_format),
            daemon=True,
        ).start()

    def _download(
        self,
        url: str,
        output_dir: str,
        mode: str,
        quality: str | None,
        audio_format: str,
    ) -> None:
        try:
            if mode == "video":
                ok = download_video(
                    url, output_dir, quality, progress_hook=self._on_progress
                )
            elif mode == "audio":
                ok = download_audio(
                    url,
                    output_dir,
                    audio_format,
                    progress_hook=self._on_progress,
                )
            elif mode == "playlist":
                ok = download_playlist(
                    url,
                    output_dir,
                    quality,
                    audio_only=False,
                    progress_hook=self._on_progress,
                )
            else:
                ok = download_playlist(
                    url,
                    output_dir,
                    audio_only=True,
                    progress_hook=self._on_progress,
                    audio_format=audio_format,
                )
        except Exception:
            logger.exception("Erro inesperado na interface.")
            ok = False
        self.after(0, self._finish, ok)

    def _finish(self, ok: bool) -> None:
        if not self.winfo_exists():
            return
        self._set_busy(False)
        if ok:
            self._apply_progress(100.0, "Concluído")
            self.status_var.set("Concluído.")
        else:
            self.status_var.set("Falha no download. Veja o registro.")


def _prefer_local_tools() -> None:
    """Inclui o ffmpeg do Homebrew quando o app abre fora do Terminal."""
    extra = ("/opt/homebrew/bin", "/usr/local/bin")
    folders = [part for part in os.environ.get("PATH", "").split(os.pathsep) if part]
    for folder in reversed(extra):
        if Path(folder).is_dir() and folder not in folders:
            folders.insert(0, folder)
    os.environ["PATH"] = os.pathsep.join(folders)


def main() -> None:
    _prefer_local_tools()
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
