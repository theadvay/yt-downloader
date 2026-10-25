/* Front-end logic for yt-downloader. */

const $ = (id) => document.getElementById(id);

const urlForm = $("url-form");
const urlInput = $("url");
const fetchBtn = $("fetch-btn");
const statusEl = $("status");
const preview = $("preview");
const thumb = $("thumb");
const duration = $("duration");
const titleEl = $("title");
const channelEl = $("channel");
const options = $("options");
const quality = $("quality");
const audioOnly = $("audio-only");
const audioFormatGroup = $("audio-format-group");
const audioFormat = $("audio-format");
const downloadBtn = $("download-btn");

let currentUrl = "";
let ready = false;

function setStatus(message, kind = "info") {
  statusEl.textContent = message || "";
  statusEl.className = "status" + (message ? " " + kind : "");
}

function setLoading(button, loading) {
  button.classList.toggle("loading", loading);
  button.disabled = loading;
}

function formatDuration(info) {
  if (info.duration_string) return info.duration_string;
  if (!info.duration) return "";
  const total = Math.round(info.duration);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  const pad = (n) => String(n).padStart(2, "0");
  return h > 0 ? `${h}:${pad(m)}:${pad(s)}` : `${m}:${pad(s)}`;
}

/* ---- Fetch metadata ---- */
urlForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const url = urlInput.value.trim();
  if (!url) return;

  setStatus("Fetching video details…", "info");
  setLoading(fetchBtn, true);
  preview.classList.add("hidden");
  options.classList.add("hidden");
  downloadBtn.classList.add("hidden");
  ready = false;

  try {
    const res = await fetch("/api/info", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });
    const data = await res.json();

    if (!res.ok || !data.ok) {
      throw new Error(data.error || "Could not fetch this video.");
    }

    const info = data.info;
    currentUrl = info.webpage_url || url;

    titleEl.textContent = info.title || "Untitled";
    channelEl.textContent = info.uploader ? `by ${info.uploader}` : "";
    if (info.thumbnail) {
      thumb.src = info.thumbnail;
      thumb.style.display = "block";
    } else {
      thumb.style.display = "none";
    }
    duration.textContent = formatDuration(info);
    duration.style.display = info.duration ? "block" : "none";

    preview.classList.remove("hidden");
    options.classList.remove("hidden");
    downloadBtn.classList.remove("hidden");
    downloadBtn.disabled = false;
    ready = true;
    setStatus("Ready to download.", "ok");
  } catch (err) {
    setStatus(err.message, "error");
  } finally {
    setLoading(fetchBtn, false);
  }
});

/* ---- Audio-only toggle ---- */
audioOnly.addEventListener("change", () => {
  audioFormatGroup.hidden = !audioOnly.checked;
  quality.disabled = audioOnly.checked;
});

/* ---- Download ---- */
downloadBtn.addEventListener("click", async () => {
  if (!ready) return;

  const payload = {
    url: currentUrl,
    quality: quality.value,
    audio_only: audioOnly.checked,
    audio_format: audioFormat.value,
  };

  setStatus("Preparing your download… this can take a moment for longer videos.", "info");
  setLoading(downloadBtn, true);
  downloadBtn.textContent = "";

  try {
    const res = await fetch("/api/download", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      let message = "Download failed.";
      try {
        const data = await res.json();
        if (data.error) message = data.error;
      } catch (_) { /* non-JSON error body */ }
      throw new Error(message);
    }

    const filename = parseFilename(res.headers.get("Content-Disposition")) ||
      (audioOnly.checked ? `audio.${audioFormat.value}` : "video.mp4");

    const blob = await res.blob();
    const objectUrl = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = objectUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(objectUrl), 4000);

    setStatus(`Saved “${filename}”.`, "ok");
  } catch (err) {
    setStatus(err.message, "error");
  } finally {
    setLoading(downloadBtn, false);
    downloadBtn.textContent = "Download";
  }
});

/* Pull the filename out of the Content-Disposition header. */
function parseFilename(header) {
  if (!header) return null;
  // RFC 5987: filename*=UTF-8''<percent-encoded>
  const star = header.match(/filename\*=UTF-8''([^;]+)/i);
  if (star) {
    try { return decodeURIComponent(star[1]); } catch (_) { /* fall through */ }
  }
  const plain = header.match(/filename="?([^";]+)"?/i);
  return plain ? plain[1] : null;
}
