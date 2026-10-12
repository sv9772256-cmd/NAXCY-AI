import os
import subprocess
import tempfile
import shutil
import urllib.request
from pathlib import Path

import cv2
import numpy as np
import streamlit as st
import imageio_ffmpeg
from PIL import Image

# NAXCY-AI
# This version provides robust conventional enhancement and optional AI hooks.
# It does NOT claim AI restoration unless a compatible Real-ESRGAN model is installed.
# For production AI, install/configure the model and weights in the hosting environment.

st.set_page_config(
    page_title="NAXCY-AI | Video & Image Enhancer",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.stApp { background:#0b1018; color:#eef5ff; }
.logo-container {
  text-align:center; padding:25px 12px; margin:8px 0 24px;
  border-radius:18px; border:1px solid #00e6c3;
  background:linear-gradient(135deg,#03111e,#092b43);
  box-shadow:0 0 22px rgba(0,230,195,.18);
}
.logo-text { font:900 38px 'Courier New',monospace; letter-spacing:4px;
  color:#00ffd0; text-shadow:0 0 14px #00ffd0; }
.logo-subtext { font-size:12px; letter-spacing:2px; color:#c4d7e8; margin-top:7px; }
.small-note { color:#9fb2c8; font-size:0.9rem; }
</style>
<div class="logo-container">
  <div class="logo-text">⚡ NAXCY-AI ⚡</div>
  <div class="logo-subtext">VIDEO & IMAGE ENHANCEMENT STUDIO</div>
</div>
""", unsafe_allow_html=True)

QUALITY = {
    "Keep original resolution": None,
    "720p HD": 720,
    "1080p Full HD": 1080,
    "2K QHD (1440p)": 1440,
    "4K UHD (2160p)": 2160,
}
RATIOS = {
    "Keep original ratio": None,
    "9:16 — Reels / Shorts": (9, 16),
    "16:9 — YouTube / TV": (16, 9),
    "1:1 — Square": (1, 1),
    "4:5 — Portrait post": (4, 5),
    "3:2 — Photo": (3, 2),
    "2:3 — Portrait photo": (2, 3),
}

def even_dim(v):
    v = max(2, int(round(v)))
    return v if v % 2 == 0 else v + 1

def output_size(src_w, src_h, quality, ratio_name):
    """When ratio is unchanged, preserve source geometry and scale by output height."""
    ratio = RATIOS[ratio_name]
    requested_h = QUALITY[quality]
    if ratio is None:
        scale = 1.0 if requested_h is None else requested_h / src_h
        return even_dim(src_w * scale), even_dim(src_h * scale)

    rw, rh = ratio
    # Selected ratio's vertical resolution is controlled by chosen quality.
    base_h = requested_h if requested_h is not None else src_h
    out_h = even_dim(base_h)
    out_w = even_dim(out_h * rw / rh)
    return out_w, out_h

def fit_frame(frame, out_w, out_h, fit_mode):
    """No stretching: crop excess or pad with black bars."""
    h, w = frame.shape[:2]
    if w == out_w and h == out_h:
        return frame
    if fit_mode == "Pad (show entire image)":
        scale = min(out_w / w, out_h / h)
        nw, nh = max(1, round(w * scale)), max(1, round(h * scale))
        resized = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_LANCZOS4)
        canvas = np.zeros((out_h, out_w, 3), dtype=np.uint8)
        x, y = (out_w - nw) // 2, (out_h - nh) // 2
        canvas[y:y+nh, x:x+nw] = resized
        return canvas
    scale = max(out_w / w, out_h / h)
    nw, nh = max(out_w, round(w * scale)), max(out_h, round(h * scale))
    resized = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_LANCZOS4)
    x, y = (nw - out_w) // 2, (nh - out_h) // 2
    return resized[y:y+out_h, x:x+out_w]

# Optional AI model setup. AI dependencies are installed via requirements-ai.txt.
MODEL_DIR = Path("models")
MODEL_DIR.mkdir(exist_ok=True)
REALESRGAN_URL = "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/RealESRGAN_x4plus.pth"
GFPGAN_URL = "https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.3.pth"

def download_model(url, path):
    if path.exists() and path.stat().st_size > 1_000_000:
        return
    request = urllib.request.Request(url, headers={"User-Agent": "NAXCY-AI"})
    with urllib.request.urlopen(request, timeout=90) as response, open(path, "wb") as target:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            target.write(chunk)
    if path.stat().st_size <= 1_000_000:
        path.unlink(missing_ok=True)
        raise RuntimeError("AI model download अधूरा है। फिर कोशिश करें।")

@st.cache_resource(show_spinner=False)
def load_realesrgan():
    try:
        import torch
        from basicsr.archs.rrdbnet_arch import RRDBNet
        from realesrgan import RealESRGANer
    except Exception as exc:
        raise RuntimeError(
            "Real-ESRGAN dependencies उपलब्ध नहीं हैं या आपस में compatible नहीं हैं। "
            "पहले requirements-ai.txt की dependencies install करके app redeploy करें। Details: " + str(exc)
        ) from exc
    weights = MODEL_DIR / "RealESRGAN_x4plus.pth"
    download_model(REALESRGAN_URL, weights)
    network = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=4)
    return RealESRGANer(
        scale=4, model_path=str(weights), model=network, tile=256, tile_pad=10,
        pre_pad=0, half=bool(torch.cuda.is_available())
    )

@st.cache_resource(show_spinner=False)
def load_gfpgan():
    try:
        from gfpgan import GFPGANer
    except Exception as exc:
        raise RuntimeError(
            "GFPGAN dependencies उपलब्ध नहीं हैं या compatible नहीं हैं। requirements-ai.txt देखें। Details: " + str(exc)
        ) from exc
    weights = MODEL_DIR / "GFPGANv1.3.pth"
    download_model(GFPGAN_URL, weights)
    return GFPGANer(model_path=str(weights), upscale=2, arch="clean", channel_multiplier=2, bg_upsampler=None)

def ai_enhance(frame, face_restore, denoise, sharpness, contrast):
    """Run neural upscaling; optional face restoration. Input/output are OpenCV BGR frames."""
    upsampler = load_realesrgan()
    result, _ = upsampler.enhance(frame, outscale=4)
    if face_restore:
        restorer = load_gfpgan()
        _, _, restored = restorer.enhance(result, has_aligned=False, only_center_face=False, paste_back=True)
        if restored is not None:
            result = restored
    result = conventional_enhance(result, denoise, sharpness, contrast)
    return result

def conventional_enhance(frame, denoise, sharpness, contrast):
    """Conventional enhancement, not generative AI."""
    result = frame
    if denoise > 0:
        result = cv2.fastNlMeansDenoisingColored(
            result, None, denoise, denoise, 7, 21
        )
    if sharpness > 0:
        blur = cv2.GaussianBlur(result, (0, 0), 1.0)
        result = cv2.addWeighted(result, 1.0 + sharpness, blur, -sharpness, 0)
    if contrast != 1.0:
        result = cv2.convertScaleAbs(result, alpha=contrast, beta=0)
    return result

def ffmpeg_path():
    return imageio_ffmpeg.get_ffmpeg_exe()

def ffprobe_info(path):
    """Read width/height/duration/audio stream info using OpenCV and FFmpeg where possible."""
    cap = cv2.VideoCapture(path)
    info = {
        "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        "fps": float(cap.get(cv2.CAP_PROP_FPS)),
        "frames": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
    }
    cap.release()
    if not info["fps"] or not np.isfinite(info["fps"]) or info["fps"] <= 0 or info["fps"] > 240:
        info["fps"] = 30.0
    return info

def remux_audio(silent_video, original_video, output_video, timeout_seconds=900):
    """Copy processed video and original audio (if any); fail loudly instead of silently dropping audio."""
    cmd = [
        ffmpeg_path(), "-hide_banner", "-loglevel", "error", "-y",
        "-i", silent_video, "-i", original_video,
        "-map", "0:v:0", "-map", "1:a:0?",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-af", "aresample=async=1:first_pts=0",
        "-movflags", "+faststart", output_video,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_seconds)
    if result.returncode != 0 or not os.path.isfile(output_video) or os.path.getsize(output_video) == 0:
        detail = (result.stderr or "Unknown FFmpeg error")[-1800:]
        raise RuntimeError(
            "ऑडियो/वीडियो मर्ज नहीं हो पाया। बिना आवाज़ वाली फाइल को सफल आउटपुट नहीं माना गया। "
            + detail
        )

def process_image(upload, quality, ratio_name, fit_mode, engine, face_restore, denoise, sharpness, contrast):
    raw = np.frombuffer(upload.getvalue(), dtype=np.uint8)
    image = cv2.imdecode(raw, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Image खुल नहीं पाई। JPG, PNG या WEBP फाइल आज़माएँ।")
    if engine == "Real-ESRGAN AI":
        result = ai_enhance(image, face_restore, denoise, sharpness, contrast)
    else:
        result = conventional_enhance(image, denoise, sharpness, contrast)
    out_w, out_h = output_size(result.shape[1], result.shape[0], quality, ratio_name)
    result = fit_frame(result, out_w, out_h, fit_mode)

    is_png = upload.name.lower().endswith(".png")
    is_webp = upload.name.lower().endswith(".webp")
    ext = ".png" if is_png else (".webp" if is_webp else ".jpg")
    if ext == ".png":
        params, mime = [cv2.IMWRITE_PNG_COMPRESSION, 3], "image/png"
    elif ext == ".webp":
        params, mime = [cv2.IMWRITE_WEBP_QUALITY, 95], "image/webp"
    else:
        params, mime = [cv2.IMWRITE_JPEG_QUALITY, 95], "image/jpeg"
    ok, encoded = cv2.imencode(ext, result, params)
    if not ok:
        raise RuntimeError("Enhanced image encode नहीं हो पाई।")
    return encoded.tobytes(), out_w, out_h, mime, ext

def process_video(upload, quality, ratio_name, fit_mode, engine, face_restore, denoise, sharpness, contrast, progress):
    suffix = Path(upload.name).suffix.lower() or ".mp4"
    with tempfile.TemporaryDirectory(prefix="naxcy_") as workdir:
        source = os.path.join(workdir, "source" + suffix)
        silent = os.path.join(workdir, "processed_silent.mp4")
        output = os.path.join(workdir, "naxcy_enhanced.mp4")
        with open(source, "wb") as f:
            f.write(upload.getvalue())

        meta = ffprobe_info(source)
        if meta["width"] <= 0 or meta["height"] <= 0:
            raise ValueError("Video dimensions नहीं पढ़ पाए। दूसरी MP4/MOV फाइल आज़माएँ।")
        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            raise ValueError("Video decode नहीं हो पाया।")
        ok, first_frame = cap.read()
        if not ok:
            cap.release()
            raise ValueError("Video में पढ़ने योग्य frame नहीं मिला।")
        if engine == "Real-ESRGAN AI":
            first_frame = ai_enhance(first_frame, face_restore, denoise, sharpness, contrast)
        else:
            first_frame = conventional_enhance(first_frame, denoise, sharpness, contrast)
        out_w, out_h = output_size(first_frame.shape[1], first_frame.shape[0], quality, ratio_name)
        first_frame = fit_frame(first_frame, out_w, out_h, fit_mode)

        # Encode processed frames via FFmpeg stdin. The stderr pipe is drained safely after process completion.
        command = [
            ffmpeg_path(), "-hide_banner", "-loglevel", "error", "-y",
            "-f", "rawvideo", "-pixel_format", "bgr24",
            "-video_size", f"{out_w}x{out_h}", "-framerate", str(meta["fps"]),
            "-i", "-", "-an", "-c:v", "libx264", "-preset", "veryfast",
            "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            silent,
        ]
        log_file = open(os.path.join(workdir, "encode.log"), "wb")
        writer = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=log_file)
        total = meta["frames"]
        count = 0
        try:
            writer.stdin.write(np.ascontiguousarray(first_frame).tobytes())
            count = 1
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                if engine == "Real-ESRGAN AI":
                    frame = ai_enhance(frame, face_restore, denoise, sharpness, contrast)
                else:
                    frame = conventional_enhance(frame, denoise, sharpness, contrast)
                frame = fit_frame(frame, out_w, out_h, fit_mode)
                writer.stdin.write(np.ascontiguousarray(frame).tobytes())
                count += 1
                if total > 0 and (count % 3 == 0 or count == total):
                    progress.progress(min(count / total, 0.99), text=f"फ्रेम प्रोसेस हो रहे हैं: {count}/{total}")
            writer.stdin.close()
            writer.wait(timeout=900)
        except Exception:
            if writer.poll() is None:
                writer.kill()
                writer.wait()
            raise
        finally:
            cap.release()
            if not writer.stdin.closed:
                try:
                    writer.stdin.close()
                except Exception:
                    pass
            log_file.close()

        if writer.returncode != 0 or not os.path.isfile(silent) or os.path.getsize(silent) == 0:
            try:
                log_text = Path(os.path.join(workdir, "encode.log")).read_text(errors="replace")[-1800:]
            except Exception:
                log_text = "FFmpeg encoder error"
            raise RuntimeError("वीडियो encode नहीं हो पाया: " + log_text)

        remux_audio(silent, source, output)
        progress.progress(1.0, text="पूरा हुआ")
        with open(output, "rb") as f:
            data = f.read()
        return data, out_w, out_h, count

# ---------- User interface ----------
st.sidebar.header("⚙️ NAXCY Core Settings")
media_type = st.sidebar.radio("Media type", ["Video Enhancer", "Image Enhancer"])

quality = st.sidebar.selectbox("Output quality", list(QUALITY.keys()), index=2)
ratio_name = st.sidebar.selectbox("Aspect ratio", list(RATIOS.keys()), index=0)
fit_mode = st.sidebar.radio(
    "Fit method for selected ratio",
    ["Crop to fill", "Pad (show entire image)"],
    help="Original ratio preserves the source ratio. Crop removes edges; Pad adds black bars without stretching."
)

st.sidebar.subheader("Enhancement")
denoise = st.sidebar.slider("Noise reduction", 0, 10, 2)
sharpness = st.sidebar.slider("Sharpening", 0.0, 0.8, 0.25, 0.05)
contrast = st.sidebar.slider("Contrast", 0.8, 1.3, 1.0, 0.05)
engine = st.sidebar.radio(
    "Enhancement engine",
    ["Real-ESRGAN AI", "Standard (fast)"],
    help="Real-ESRGAN AI improves details using a neural model; Standard mode uses conventional sharpening."
)
face_restore = st.sidebar.checkbox("AI face restoration (GFPGAN)", value=False)

st.warning(
    "AI mode के लिए requirements-ai.txt की compatible dependencies और पहली बार model weights download जरूरी हैं। "
    "Free hosting में लंबे वीडियो/4K पर RAM या timeout आ सकता है। Standard mode तेजी से conventional enhancement करता है।"
)

if media_type == "Image Enhancer":
    upload = st.file_uploader("अपनी इमेज अपलोड करें", type=["jpg", "jpeg", "png", "webp"])
    if upload:
        left, right = st.columns(2)
        with left:
            st.subheader("Original")
            st.image(upload, use_container_width=True)
        if st.button("✨ Enhance image", type="primary"):
            try:
                with st.spinner("इमेज प्रोसेस हो रही है..."):
                    data, w, h, mime, ext = process_image(
                        upload, quality, ratio_name, fit_mode, engine, face_restore, denoise, sharpness, contrast
                    )
                with right:
                    st.subheader("Enhanced")
                    st.image(data, use_container_width=True)
                st.success(f"आउटपुट: {w} × {h} px | इंजन: {engine}")
                st.download_button(
                    "⬇️ Download enhanced image", data=data,
                    file_name=f"naxcy_enhanced{ext}", mime=mime, type="primary"
                )
            except Exception as exc:
                st.error(f"इमेज प्रोसेसिंग में समस्या: {exc}")
else:
    upload = st.file_uploader("अपना वीडियो अपलोड करें", type=["mp4", "mov", "avi", "mkv", "webm"])
    if upload:
        st.video(upload)
        st.caption(f"File size: {upload.size / (1024*1024):.1f} MB")
        if upload.size > 200 * 1024 * 1024:
            st.warning("यह फाइल 200 MB से बड़ी है। Streamlit hosting पर processing timeout या memory limit आ सकती है।")
        if st.button("✨ Enhance video (preserve audio)", type="primary"):
            progress = st.progress(0.0, text="शुरू हो रहा है...")
            try:
                data, w, h, frames = process_video(
                    upload, quality, ratio_name, fit_mode, engine, face_restore, denoise, sharpness, contrast, progress
                )
                st.success(f"पूरा हुआ: {w} × {h} px, {frames} फ्रेम | इंजन: {engine}। मूल ऑडियो उपलब्ध होने पर जोड़ा गया है।")
                st.video(data)
                st.download_button(
                    "⬇️ Download enhanced video", data=data,
                    file_name="naxcy_enhanced.mp4", mime="video/mp4", type="primary"
                )
            except Exception as exc:
                st.error(f"वीडियो प्रोसेसिंग में समस्या: {exc}")

with st.expander("AI restoration के बारे में"):
    st.write(
        "Real-ESRGAN AI neural upscaling करता है और GFPGAN optional face restoration देता है। पहली बार model weights download होंगे। "
        "AI कभी-कभी चेहरे की कुछ detail अनुमान से बना सकता है। Free hosting में model dependency conflicts या memory limits आ सकती हैं। "
        "यदि AI dependencies install नहीं हैं तो Standard (fast) mode चुनें।"
    )
