"""
Core download logic for yt-downloader.

Everything that talks to yt-dlp lives here so the Flask layer stays thin.
Only YouTube hosts are accepted (see ALLOWED_HOSTS) to keep the app from
being abused as a generic server-side fetcher.
"""

from __future__ import annotations

import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

import yt_dlp

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ALLOWED_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
    "www.youtu.be",
}

# Map the friendly quality labels used by the UI to yt-dlp format strings.
QUALITY_FORMATS = {
    "best": "bestvideo*+bestaudio/best",
    "2160": "bestvideo[height<=2160]+bestaudio/best[height<=2160]",
    "1440": "bestvideo[height<=1440]+bestaudio/best[height<=1440]",
    "1080": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
    "720": "bestvideo[height<=720]+bestaudio/best[height<=720]",
    "480": "bestvideo[height<=480]+bestaudio/best[height<=480]",
    "360": "bestvideo[height<=360]+bestaudio/best[height<=360]",
}

# Audio formats that yt-dlp can produce without ffmpeg re-encoding.
NATIVE_AUDIO_FORMATS = {"m4a", "opus", "webm"}

_ANSI = re.compile(r"\x1b\[[0-9;]*m")


class DownloadError(Exception):
    """A user-facing error: bad link, unavailable video, network hiccup."""


@dataclass
class DownloadResult:
    """A finished download sitting in a temp directory on disk."""

    path: str
    filename: str
    tmpdir: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def ffmpeg_available() -> bool:
    """True when ffmpeg is on PATH (needed to merge high-res video + audio)."""
    return shutil.which("ffmpeg") is not None


def _clean_error(exc: Exception) -> str:
    """Turn a noisy yt-dlp traceback into one readable sentence."""
    msg = _ANSI.sub("", str(exc)).strip()
    for prefix in ("ERROR: ", "WARNING: "):
        if msg.startswith(prefix):
            msg = msg[len(prefix):]
    msg = msg.splitlines()[0].strip() if msg else ""
    # Drop the trailing "See https://..." help links yt-dlp appends.
    msg = re.split(r"\s*See\s+https?://", msg)[0].strip()
    if len(msg) > 240:
        msg = msg[:237].rstrip() + "..."
    return msg or "Could not process this link."


def validate_url(url: str) -> str:
    """Normalise and sanity-check the incoming URL, raising DownloadError."""
    url = (url or "").strip()
    if not url:
        raise DownloadError("Please paste a YouTube link.")

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        # Allow people to paste "youtube.com/watch?v=..." or "youtu.be/xyz".
        parsed = urlparse("https://" + url)
        url = parsed.geturl()

    host = (parsed.hostname or "").lower()
    if host not in ALLOWED_HOSTS:
        raise DownloadError("Only YouTube links (youtube.com / youtu.be) are supported.")

    return url


def _base_opts() -> dict:
    """Options shared by the metadata lookup and the download."""
    opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "nocheckcertificate": True,
        "socket_timeout": 30,
        "retries": 3,
        "extractor_retries": 2,
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        },
    }

    # Optional authentication. YouTube sometimes asks datacenter / shared IPs to
    # "confirm you're not a bot"; passing cookies works around that.
    cookiefile = os.environ.get("YTDLP_COOKIES")
    if cookiefile and os.path.isfile(cookiefile):
        opts["cookiefile"] = cookiefile
    browser = os.environ.get("YTDLP_COOKIES_FROM_BROWSER")
    if browser:
        opts["cookiesfrombrowser"] = (browser,)

    return opts


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_info(url: str) -> dict:
    """Fetch metadata for a video without downloading it."""
    url = validate_url(url)
    with yt_dlp.YoutubeDL(_base_opts()) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
        except yt_dlp.utils.DownloadError as exc:
            raise DownloadError(_clean_error(exc)) from exc

    return {
        "title": info.get("title"),
        "uploader": info.get("uploader") or info.get("channel"),
        "duration": info.get("duration"),
        "duration_string": info.get("duration_string"),
        "thumbnail": info.get("thumbnail"),
        "view_count": info.get("view_count"),
        "webpage_url": info.get("webpage_url") or url,
        "is_live": bool(info.get("is_live")),
    }


def download(
    url: str,
    quality: str = "720",
    audio_only: bool = False,
    audio_format: str = "mp3",
) -> DownloadResult:
    """
    Download a video (or its audio) into a fresh temp directory.

    The caller owns the returned tmpdir and must remove it when done.
    """
    url = validate_url(url)
    tmpdir = tempfile.mkdtemp(prefix="ytdl_")
    has_ffmpeg = ffmpeg_available()

    opts = _base_opts()
    opts.update(
        {
            "outtmpl": os.path.join(tmpdir, "%(title).180B [%(id)s].%(ext)s"),
            "windowsfilenames": True,
            "restrictfilenames": False,
        }
    )

    if audio_only:
        if audio_format in NATIVE_AUDIO_FORMATS or not has_ffmpeg:
            opts["format"] = "bestaudio/best"
            if has_ffmpeg and audio_format in ("mp3", "wav", "aac"):
                opts["postprocessors"] = [
                    {"key": "FFmpegExtractAudio", "preferredcodec": audio_format}
                ]
        else:
            opts["format"] = "bestaudio/best"
            opts["postprocessors"] = [
                {"key": "FFmpegExtractAudio", "preferredcodec": audio_format}
            ]
    else:
        fmt = QUALITY_FORMATS.get(str(quality), QUALITY_FORMATS["720"])
        if not has_ffmpeg:
            # Without ffmpeg we cannot merge separate video/audio streams,
            # so fall back to the best pre-merged single file.
            fmt = "best[ext=mp4]/best"
        opts["format"] = fmt
        if has_ffmpeg:
            opts["merge_output_format"] = "mp4"

    with yt_dlp.YoutubeDL(opts) as ydl:
        try:
            ydl.extract_info(url, download=True)
        except yt_dlp.utils.DownloadError as exc:
            shutil.rmtree(tmpdir, ignore_errors=True)
            raise DownloadError(_clean_error(exc)) from exc

    produced = [
        os.path.join(tmpdir, name)
        for name in os.listdir(tmpdir)
        if not name.endswith((".part", ".ytdl", ".temp"))
        and os.path.isfile(os.path.join(tmpdir, name))
    ]
    if not produced:
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise DownloadError("Download finished but produced no file.")

    path = max(produced, key=os.path.getsize)
    return DownloadResult(path=path, filename=os.path.basename(path), tmpdir=tmpdir)


def cleanup(tmpdir: str) -> None:
    """Best-effort removal of a download's temp directory."""
    shutil.rmtree(tmpdir, ignore_errors=True)
