<div align="center">

# yt-downloader

**Paste a YouTube link, pick a quality, download. That's it.**

A small, self-hosted web app built with Flask + [yt-dlp](https://github.com/yt-dlp/yt-dlp).
No database, no build step, no clutter — just a clean dark UI and a download.

<img src="docs/screenshot.png" alt="yt-downloader web UI" width="720" />

</div>

---

## Features

- **Paste-and-go** — drop in any YouTube URL and get an instant preview
  (thumbnail, title, channel, duration).
- **Quality control** — Best available, 2160p (4K), 1440p, 1080p, 720p, 480p, 360p.
- **Audio-only mode** — rip just the sound as **MP3**, **M4A** or **WAV**.
- **Streams straight to your browser** — the server downloads, hands you the file,
  then deletes its temporary copy automatically.
- **Safe by default** — only YouTube hosts are accepted, so the server can't be
  abused as an open proxy.
- **Docker ready** and covered by tests + CI.

## Requirements

- **Python 3.10+**
- **ffmpeg** — *strongly recommended*. Without it, yt-dlp can't merge separate
  video and audio streams, so quality is capped at the best pre-merged file
  (usually 720p) and MP3/WAV conversion is unavailable.
- **An external JavaScript runtime** — installed automatically by
  `yt-dlp[default,deno]` (a Deno runtime plus the EJS challenge scripts).
  Since yt-dlp **2025.11.12** a JS runtime is *required* for YouTube, because
  yt-dlp has to solve YouTube's JavaScript challenges. Plain `yt-dlp` is no
  longer enough — if you install manually, use `pip install "yt-dlp[default,deno]"`.

## Quick start

```bash
git clone https://github.com/theadvay/yt-downloader.git
cd yt-downloader

python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

pip install -r requirements.txt
python app.py
```

Then open **http://127.0.0.1:5000** in your browser.

### Installing ffmpeg

| Platform | Command |
| --- | --- |
| Debian / Ubuntu | `sudo apt install ffmpeg` |
| macOS (Homebrew) | `brew install ffmpeg` |
| Windows (winget) | `winget install Gyan.FFmpeg` |
| Windows (Chocolatey) | `choco install ffmpeg` |

## Run with Docker

```bash
docker build -t yt-downloader .
docker run --rm -p 5000:5000 yt-downloader
```

The image bundles ffmpeg, so everything works out of the box.

## Keeping it working

YouTube changes constantly and yt-dlp ships fixes within hours, so when a video
suddenly stops downloading, update yt-dlp before anything else:

```bash
pip install -U "yt-dlp[default,deno]"
```

`/api/health` tells you which version is running:

```json
{"ok": true, "ffmpeg": true, "js_runtime": true, "yt_dlp": "2026.10.21"}
```

## Configuration

The app reads a few environment variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `HOST` | `127.0.0.1` | Interface to bind (`--host` also works). |
| `PORT` | `5000` | Port to listen on (`--port` also works). |
| `YTDLP_COOKIES` | – | Path to a Netscape-format `cookies.txt`. |
| `YTDLP_COOKIES_FROM_BROWSER` | – | Browser to pull cookies from, e.g. `chrome`, `firefox`. |

### "Sign in to confirm you're not a bot"

YouTube sometimes shows this for datacenter or shared IPs (cloud servers, VPNs).
Passing cookies fixes it:

```bash
# Use cookies from your local browser (no export needed)
YTDLP_COOKIES_FROM_BROWSER=firefox python app.py

# Or point at an exported cookies.txt file
YTDLP_COOKIES=/path/to/cookies.txt python app.py
```

## HTTP API

The front-end is just a thin client over four endpoints — script it if you like.

| Method | Path | Body / Notes |
| --- | --- | --- |
| `GET` | `/` | The web UI. |
| `GET` | `/api/health` | `{"ok": true, "ffmpeg": true, "js_runtime": true, "yt_dlp": "..."}` |
| `POST` | `/api/info` | `{"url": "..."}` → video metadata. |
| `POST` | `/api/download` | `{"url": "...", "quality": "1080", "audio_only": false, "audio_format": "mp3"}` → the file. |

## Project structure

```
yt-downloader/
├── app.py                     # Flask routes
├── downloader.py              # yt-dlp wrapper (all the download logic)
├── templates/index.html       # UI markup
├── static/
│   ├── style.css
│   └── app.js
├── tests/test_downloader.py   # unit tests (network mocked)
├── requirements.txt
├── Dockerfile                 # optional: container build, ffmpeg included
├── .dockerignore
└── .github/workflows/ci.yml
```

## Tests

```bash
pip install pytest
pytest -q
```

## Disclaimer

This project is intended for **personal use** — downloading content you own, that
is public domain, that is licensed for reuse, or where you otherwise have
permission. Downloading copyrighted material without authorization may violate
copyright law and **YouTube's Terms of Service**. You are responsible for how you
use it.

## License

[MIT](LICENSE) © Advay
