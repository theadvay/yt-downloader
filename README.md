# yt-downloader

Paste a YouTube link, pick a quality, download. A small Flask web app powered by
[yt-dlp](https://github.com/yt-dlp/yt-dlp).

## Run it

Needs **Python 3.10+**.

```bash
git clone https://github.com/theadvay/yt-downloader.git
cd yt-downloader

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
python app.py
```

Open **http://127.0.0.1:5000**.

### ffmpeg

Install it for 1080p/4K merging and MP3 output. Without it, downloads fall back
to the best single file (usually 720p) and audio conversion is unavailable.

```bash
sudo apt install ffmpeg        # Debian / Ubuntu
brew install ffmpeg            # macOS
winget install Gyan.FFmpeg     # Windows
```

## What it does

- Previews the video before you download it — thumbnail, title, channel, duration
- Quality: best, 2160p, 1440p, 1080p, 720p, 480p, 360p
- Audio-only mode: MP3, M4A or WAV
- Hands the file straight to your browser, then deletes its temp copy
- Only accepts YouTube links

## If a download stops working

YouTube changes often, so update yt-dlp first:

```bash
pip install -U "yt-dlp[default,deno]"
```

If it still fails, YouTube is probably asking for a signed-in session. Point the
app at cookies from your browser:

```bash
YTDLP_COOKIES_FROM_BROWSER=firefox python app.py
```

`http://127.0.0.1:5000/api/health` shows what's installed.

## Tests

```bash
pip install pytest
pytest -q
```

## License

MIT. For personal use — respect copyright and YouTube's Terms of Service.
