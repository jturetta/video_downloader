#!/usr/bin/env python3
"""
ytdlp_helper.py
----------------
Wrapper de linha de comando para o yt-dlp, para facilitar o uso diário:
baixar vídeo, extrair áudio em MP3 ou baixar uma playlist inteira,
sem precisar lembrar das flags toda vez.

Pré-requisitos:
    - yt-dlp instalado:  pip install -U yt-dlp
    - ffmpeg instalado e disponível no PATH (necessário para extrair
      áudio e para unir vídeo+áudio em alguns formatos)

Uso:
    python ytdlp_helper.py video "URL"
    python ytdlp_helper.py audio "URL"
    python ytdlp_helper.py playlist "URL"
    python ytdlp_helper.py video "URL" --output-dir ~/Downloads --quality 1080
    python ytdlp_helper.py --menu        # modo interativo com menu
    python ytdlp_ui.py                   # interface gráfica

Também pode ser usado como módulo:
    from ytdlp_helper import download_video, download_audio, download_playlist
"""

from __future__ import annotations

import argparse
import logging
import shutil
import sys
from pathlib import Path
from typing import Callable, Optional

ProgressHook = Callable[[dict], None]

try:
    import yt_dlp
except ImportError:
    print(
        "ERRO: a biblioteca 'yt-dlp' não está instalada.\n"
        "Instale com: pip install -U yt-dlp",
        file=sys.stderr,
    )
    sys.exit(1)


# --------------------------------------------------------------------------- #
# Configuração de logging
# --------------------------------------------------------------------------- #
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ytdlp_helper")

# Pasta Downloads do sistema operacional.
DEFAULT_OUTPUT_DIR = str(Path.home() / "Downloads")


class _YtDlpLog:
    """O yt-dlp manda o texto normal da tela em debug; o debug real começa com [debug]."""

    def __init__(self) -> None:
        self.already_downloaded = False

    def debug(self, msg: str) -> None:
        text = str(msg)
        if text.startswith("[debug]"):
            logger.debug("%s", text)
            return
        if "has already been downloaded" in text:
            self.already_downloaded = True
            logger.info("Esse arquivo já está na pasta. O download foi pulado.")
            return
        logger.info("%s", text)

    def info(self, msg: str) -> None:
        logger.info("%s", msg)

    def warning(self, msg: str) -> None:
        logger.warning("%s", msg)

    def error(self, msg: str) -> None:
        logger.error("%s", msg)


def _run_ydl(
    ydl_opts: dict,
    url: str,
    success_message: str,
    *,
    strict: bool = True,
) -> bool:
    """Executa o download e distingue arquivo novo, arquivo já salvo e erro."""
    bridge = _YtDlpLog()
    ydl_opts = {**ydl_opts, "logger": bridge}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            retcode = ydl.download([url])
    except yt_dlp.utils.DownloadError as exc:
        logger.error("Falha no download: %s", exc)
        return False
    except Exception:
        logger.exception("Erro inesperado no download.")
        return False

    if retcode and strict:
        logger.error("O yt-dlp terminou com erro (código %s).", retcode)
        return False
    if retcode:
        logger.warning("A lista terminou com algum item que falhou.")
    if not bridge.already_downloaded:
        logger.info("%s", success_message)
    return True


# --------------------------------------------------------------------------- #
# Verificações de ambiente
# --------------------------------------------------------------------------- #
def check_ffmpeg() -> bool:
    """Verifica se o ffmpeg está disponível no PATH."""
    return shutil.which("ffmpeg") is not None


def ensure_output_dir(output_dir: str) -> Path:
    """Garante que o diretório de saída exista (cria se necessário)."""
    path = Path(output_dir).expanduser().resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def _attach_progress(ydl_opts: dict, progress_hook: Optional[ProgressHook]) -> None:
    """Envia o progresso ao chamador e esconde a barra do terminal."""
    if progress_hook is None:
        return
    ydl_opts["progress_hooks"] = [progress_hook]
    ydl_opts["noprogress"] = True


# --------------------------------------------------------------------------- #
# Funções principais
# --------------------------------------------------------------------------- #
def download_video(
    url: str,
    output_dir: str = DEFAULT_OUTPUT_DIR,
    quality: Optional[str] = None,
    progress_hook: Optional[ProgressHook] = None,
) -> bool:
    """
    Baixa um vídeo na melhor qualidade disponível (ou limitada por `quality`,
    ex.: "1080" para no máximo 1080p).

    Retorna True em caso de sucesso, False em caso de falha.
    """
    out_path = ensure_output_dir(output_dir)

    format_selector = "bestvideo+bestaudio/best"
    if quality:
        format_selector = (
            f"bestvideo[height<={quality}]+bestaudio/best[height<={quality}]"
        )

    ydl_opts = {
        "format": format_selector,
        "outtmpl": str(out_path / "%(title)s.%(ext)s"),
        "merge_output_format": "mp4",
        "noplaylist": True,
        "retries": 3,
        "fragment_retries": 3,
        "ignoreerrors": False,
    }
    _attach_progress(ydl_opts, progress_hook)

    logger.info("Iniciando download de vídeo: %s", url)
    return _run_ydl(
        ydl_opts,
        url,
        f"Download concluído com sucesso em: {out_path}",
    )


def download_audio(
    url: str,
    output_dir: str = DEFAULT_OUTPUT_DIR,
    audio_format: str = "mp3",
    audio_quality: str = "0",
    progress_hook: Optional[ProgressHook] = None,
) -> bool:
    """
    Extrai apenas o áudio da URL, convertendo para `audio_format`
    (padrão: mp3). `audio_quality` segue a escala do yt-dlp: "0" é a melhor.

    Retorna True em caso de sucesso, False em caso de falha.
    """
    if not check_ffmpeg():
        logger.error(
            "ffmpeg não encontrado no PATH. Instale o ffmpeg para extrair áudio."
        )
        return False

    out_path = ensure_output_dir(output_dir)

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": str(out_path / "%(title)s.%(ext)s"),
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": audio_format,
                "preferredquality": audio_quality,
            }
        ],
        "noplaylist": True,
        "retries": 3,
        "fragment_retries": 3,
        "ignoreerrors": False,
    }
    _attach_progress(ydl_opts, progress_hook)

    logger.info("Iniciando extração de áudio (%s): %s", audio_format, url)
    return _run_ydl(
        ydl_opts,
        url,
        f"Áudio extraído com sucesso em: {out_path}",
    )


def download_playlist(
    url: str,
    output_dir: str = DEFAULT_OUTPUT_DIR,
    quality: Optional[str] = None,
    audio_only: bool = False,
    progress_hook: Optional[ProgressHook] = None,
    audio_format: str = "mp3",
) -> bool:
    """
    Baixa uma playlist inteira. Se `audio_only=True`, extrai apenas o áudio
    de cada item no formato pedido (padrão: mp3).

    Retorna True em caso de sucesso (mesmo com itens individuais ignorados
    por erro), False em caso de falha geral.
    """
    out_path = ensure_output_dir(output_dir)

    ydl_opts = {
        "outtmpl": str(
            out_path / "%(playlist_title)s/%(playlist_index)s - %(title)s.%(ext)s"
        ),
        "noplaylist": False,
        "retries": 3,
        "fragment_retries": 3,
        # Continua a playlist mesmo se um item individual falhar
        "ignoreerrors": True,
    }

    if audio_only:
        if not check_ffmpeg():
            logger.error(
                "ffmpeg não encontrado no PATH. Instale o ffmpeg para extrair áudio."
            )
            return False
        ydl_opts["format"] = "bestaudio/best"
        ydl_opts["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": audio_format,
                "preferredquality": "0",
            }
        ]
    else:
        format_selector = "bestvideo+bestaudio/best"
        if quality:
            format_selector = (
                f"bestvideo[height<={quality}]+bestaudio/best[height<={quality}]"
            )
        ydl_opts["format"] = format_selector
        ydl_opts["merge_output_format"] = "mp4"

    _attach_progress(ydl_opts, progress_hook)

    logger.info("Iniciando download de playlist: %s", url)
    return _run_ydl(
        ydl_opts,
        url,
        f"Playlist processada. Verifique os arquivos em: {out_path}",
        strict=False,
    )


# --------------------------------------------------------------------------- #
# Menu interativo (opcional, para quem não quiser usar flags)
# --------------------------------------------------------------------------- #
def interactive_menu() -> None:
    print("\n=== yt-dlp Helper ===")
    print("1) Baixar vídeo")
    print("2) Extrair áudio (MP3)")
    print("3) Baixar playlist (vídeo)")
    print("4) Baixar playlist (áudio)")
    print("0) Sair")

    choice = input("\nEscolha uma opção: ").strip()
    if choice == "0":
        return

    url = input("Cole a URL: ").strip()
    if not url:
        logger.error("URL vazia. Encerrando.")
        return

    output_dir = (
        input(f"Pasta de destino (Enter para '{DEFAULT_OUTPUT_DIR}'): ").strip()
        or DEFAULT_OUTPUT_DIR
    )

    if choice == "1":
        quality = (
            input(
                "Qualidade máxima em p (ex.: 1080, Enter para melhor disponível): "
            ).strip()
            or None
        )
        download_video(url, output_dir, quality)
    elif choice == "2":
        download_audio(url, output_dir)
    elif choice == "3":
        quality = (
            input(
                "Qualidade máxima em p (ex.: 1080, Enter para melhor disponível): "
            ).strip()
            or None
        )
        download_playlist(url, output_dir, quality=quality, audio_only=False)
    elif choice == "4":
        download_playlist(url, output_dir, audio_only=True)
    else:
        logger.error("Opção inválida.")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Wrapper simplificado para o yt-dlp (vídeo, áudio e playlists)."
    )
    parser.add_argument(
        "--menu",
        action="store_true",
        help="Abre um menu interativo em vez de usar subcomandos.",
    )

    subparsers = parser.add_subparsers(dest="command")

    # video
    p_video = subparsers.add_parser("video", help="Baixa um vídeo único.")
    p_video.add_argument("url", help="URL do vídeo.")
    p_video.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help="Pasta de destino (padrão: Downloads do sistema).",
    )
    p_video.add_argument(
        "--quality",
        default=None,
        help="Altura máxima do vídeo em pixels (ex.: 720, 1080).",
    )

    # audio
    p_audio = subparsers.add_parser("audio", help="Extrai apenas o áudio de um vídeo.")
    p_audio.add_argument("url", help="URL do vídeo.")
    p_audio.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help="Pasta de destino (padrão: Downloads do sistema).",
    )
    p_audio.add_argument(
        "--format", default="mp3", help="Formato de áudio (padrão: mp3)."
    )

    # playlist
    p_playlist = subparsers.add_parser("playlist", help="Baixa uma playlist inteira.")
    p_playlist.add_argument("url", help="URL da playlist.")
    p_playlist.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help="Pasta de destino (padrão: Downloads do sistema).",
    )
    p_playlist.add_argument(
        "--quality",
        default=None,
        help="Altura máxima do vídeo em pixels (ex.: 720, 1080).",
    )
    p_playlist.add_argument(
        "--audio-only",
        action="store_true",
        help="Extrai apenas o áudio (MP3) de cada item da playlist.",
    )

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.menu or not args.command:
        interactive_menu()
        return

    success = False
    if args.command == "video":
        success = download_video(args.url, args.output_dir, args.quality)
    elif args.command == "audio":
        success = download_audio(args.url, args.output_dir, args.format)
    elif args.command == "playlist":
        success = download_playlist(
            args.url, args.output_dir, args.quality, args.audio_only
        )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
