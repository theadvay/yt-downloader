"""
yt-downloader — a small Flask web app around yt-dlp.

Paste a YouTube link in the browser, pick a quality (or grab just the audio),
and the server hands the finished file straight back as a download.

Run:
    python app.py
Then open http://127.0.0.1:5000
"""

from __future__ import annotations

import argparse
import os

from flask import (
    Flask,
    jsonify,
    render_template,
    request,
    send_file,
)

from downloader import DownloadError, cleanup, download, ffmpeg_available, get_info

app = Flask(__name__)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/")
def index():
    return render_template("index.html", ffmpeg=ffmpeg_available())


@app.get("/api/health")
def health():
    return jsonify({"ok": True, "ffmpeg": ffmpeg_available()})


@app.post("/api/info")
def api_info():
    data = request.get_json(silent=True) or {}
    try:
        info = get_info(data.get("url", ""))
    except DownloadError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:  # pragma: no cover - unexpected yt-dlp failure
        app.logger.exception("info failed")
        return jsonify({"ok": False, "error": f"Unexpected error: {exc}"}), 500
    return jsonify({"ok": True, "info": info})


@app.post("/api/download")
def api_download():
    data = request.get_json(silent=True) or {}
    url = data.get("url", "")
    quality = str(data.get("quality", "720"))
    audio_only = bool(data.get("audio_only", False))
    audio_format = str(data.get("audio_format", "mp3"))

    try:
        result = download(
            url, quality=quality, audio_only=audio_only, audio_format=audio_format
        )
    except DownloadError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:  # pragma: no cover
        app.logger.exception("download failed")
        return jsonify({"ok": False, "error": f"Unexpected error: {exc}"}), 500

    response = send_file(
        result.path,
        as_attachment=True,
        download_name=result.filename,
    )
    # Delete the temp file only once the response has been fully sent.
    response.call_on_close(lambda: cleanup(result.tmpdir))
    return response


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Run the yt-downloader web app.")
    parser.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "5000")))
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
