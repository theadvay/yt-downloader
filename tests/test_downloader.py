"""Unit tests for the downloader core. Network and yt-dlp are mocked so these
run anywhere, fast."""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import downloader  # noqa: E402
from downloader import DownloadError, cleanup, download, get_info, validate_url  # noqa: E402


class FakeYDL:
    """Stands in for yt_dlp.YoutubeDL without touching the network."""

    def __init__(self, opts):
        self.opts = opts

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def extract_info(self, url, download=False):
        if download:
            outdir = os.path.dirname(self.opts["outtmpl"])
            with open(os.path.join(outdir, "My Video [abc123].mp4"), "w") as fh:
                fh.write("fake-bytes")
        return {
            "title": "My Video",
            "id": "abc123",
            "duration": 65,
            "duration_string": "1:05",
            "thumbnail": "https://example.com/t.jpg",
            "uploader": "Some Channel",
            "webpage_url": url,
            "is_live": False,
        }


@pytest.fixture(autouse=True)
def patch_ytdlp(monkeypatch):
    monkeypatch.setattr(downloader.yt_dlp, "YoutubeDL", FakeYDL)


# --- URL validation -------------------------------------------------------

@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/watch?v=abc123",
        "https://youtube.com/watch?v=abc123",
        "https://m.youtube.com/watch?v=abc123",
        "https://music.youtube.com/watch?v=abc123",
        "https://youtu.be/abc123",
        "youtube.com/watch?v=abc123",  # bare host gets https:// prepended
    ],
)
def test_validate_url_accepts_youtube(url):
    assert validate_url(url).startswith("https://")


@pytest.mark.parametrize(
    "url",
    ["", "   ", "not a url", "https://vimeo.com/12345", "https://evil.com/youtube.com"],
)
def test_validate_url_rejects_others(url):
    with pytest.raises(DownloadError):
        validate_url(url)


# --- Metadata -------------------------------------------------------------

def test_get_info_fields():
    info = get_info("https://youtu.be/abc123")
    assert info["title"] == "My Video"
    assert info["uploader"] == "Some Channel"
    assert info["duration_string"] == "1:05"
    assert info["is_live"] is False


# --- Download -------------------------------------------------------------

def test_download_produces_file_and_cleanup():
    result = download("https://youtu.be/abc123", quality="720")
    assert os.path.isfile(result.path)
    assert result.filename == "My Video [abc123].mp4"
    assert os.path.dirname(result.path) == result.tmpdir

    cleanup(result.tmpdir)
    assert not os.path.exists(result.tmpdir)


def test_download_audio_only_uses_bestaudio(monkeypatch):
    captured = {}

    class CapturingYDL(FakeYDL):
        def __init__(self, opts):
            super().__init__(opts)
            captured["opts"] = opts

    monkeypatch.setattr(downloader.yt_dlp, "YoutubeDL", CapturingYDL)
    result = download("https://youtu.be/abc123", audio_only=True, audio_format="m4a")
    assert captured["opts"]["format"].startswith("bestaudio")
    cleanup(result.tmpdir)
