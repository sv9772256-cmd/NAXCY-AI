import io
import os
import shutil
import subprocess
import tempfile
import urllib.request
from pathlib import Path

import numpy as np
import streamlit as st
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

st.set_page_config(page_title="NAXCY AI", page_icon="⚡", layout="wide")

st.markdown("""
<style>
.block-container {max-width: 1120px; padding-top: 1.2rem;}
.hero {padding: 22px; border-radius: 18px; background: linear-gradient(120deg,#07111f,#073b4c);
       color: white; text-align: center; border: 1px solid #16d6c2; margin-bottom: 18px;}
.hero h1 {color: #27f4d2; margin-bottom: 4px;}
div.stButton > button, div.stDownloadButton > button {width: 100%; border-radius: 12px; font-weight: 700;}
</style>
<div class="hero"><h1>⚡ NAXCY AI</h1>
<div>FREE IMAGE & VIDEO ENHANCER</div>
<p>Classic enhancement + optional AI super-resolution</p></div>
""", unsafe_allow_html=True)

MODEL_DIR = Path("models")
MODEL_PATH = MODEL_DIR / "EDSR_x4.pb"
MODEL_URL = "https://github.com/Saafke/EDSR_Tensorflow/raw/master/models/EDSR_x4.pb"

def ffmpeg_ready():
    return bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))

def download_edsr_model():
    if MODEL_PATH.exists() and MODEL_PATH.stat().st_size > 10_000_000:
        return str(MODEL_PATH)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    try:
        request = urllib.request.Request(MODEL_URL, headers={"User-Agent": "NAXCY-AI"})
        with urllib.request.urlopen(request, timeout=90) as response, open(MODEL_PATH, "wb") as output:
            shutil.copyfileobj(response, output)
        if MODEL_PATH.stat().st_size < 10_000_000:
            MODEL_PATH.unlink(missing_ok=True)
            raise RuntimeError("Model download incomplete.")
        return str(MODEL_PATH)
    except Exception as exc:
        MODEL_PATH.unlink(missing_ok=True)
        raise RuntimeError(
            "Free AI model download nahi ho paya. Internet, hosting restrictions, ya disk limit ho sakti hai. "
            "Filhaal Free Classic mode use karein."
        ) from exc

def create_super_resolution():
    import cv2
    if not hasattr(cv2, "dnn_superres"):
        raise RuntimeError("OpenCV Super Resolution module missing hai. requirements.txt check karein.")
    model_path = download_edsr_model()
    sr = cv2.dnn_superres.DnnSuperResImpl_create()
    sr.readModel(model_path)
    sr.setModel("edsr", 4)
    return sr

def output_dimensions(width, height, resolution, ratio, fit):
    target_heights = {"720p": 720, "1080p": 1080, "2K": 1440, "4K": 2160}
    out_h = target_heights[resolution]
    if ratio == "Original ratio":
        out_w = round((width * out_h / height) / 2) * 2
        return max(2, out_w), out_h
    ratios = {"9:16": 9/16, "16:9": 16/9, "1:1": 1.0, "4:3": 4/3}
    out_w = max(2, round((out_h * ratios[ratio]) / 2) * 2)
    return out_w, out_h

def crop_to_ratio(image, target_w, target_h):
    target_ratio = target_w / target_h
    source_ratio = image.width / image.height
    if source_ratio > target_ratio:
        new_w = max(1, round(image.height * target_ratio))
        left = (image.width - new_w) // 2
        return image.crop((left, 0, left + new_w, image.height))
    new_h = max(1, round(image.width / target_ratio))
    top = (image.height - new_h) // 2
    return image.crop((0, top, image.width, top + new_h))

def apply_classic_filters(image, sharpness, denoise, contrast, saturation, brightness):
    if denoise > 0:
        image = image.filter(ImageFilter.MedianFilter(size=3 if denoise < 55 else 5))
    image = ImageEnhance.Sharpness(image).enhance(1 + sharpness / 50)
    image = ImageEnhance.Contrast(image).enhance(1 + contrast / 100)
    image = ImageEnhance.Color(image).enhance(1 + saturation / 100)
    image = ImageEnhance.Brightness(image).enhance(1 + brightness / 100)
    return image

def enhance_image(uploaded_image, mode, resolution, ratio, fit, sharpness, denoise, contrast, saturation, brightness):
    image = ImageOps.exif_transpose(uploaded_image).convert("RGB")
    out_w, out_h = output_dimensions(image.width, image.height, resolution, ratio, fit)

    if ratio != "Original ratio" and fit == "Crop to fill":
        image = crop_to_ratio(image, out_w, out_h)

    if mode == "AI Super-Resolution (EDSR x4)":
        import cv2
        sr = create_super_resolution()
        frame = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        upscaled = sr.upsample(frame)
        image = Image.fromarray(cv2.cvtColor(upscaled, cv2.COLOR_BGR2RGB))

    if ratio != "Original ratio" and fit == "Pad (show entire image)":
        image.thumbnail((out_w, out_h), Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", (out_w, out_h), (0, 0, 0))
        canvas.paste(image, ((out_w - image.width)//2, (out_h - image.height)//2))
        image = canvas
    else:
        image = image.resize((out_w, out_h), Image.Resampling.LANCZOS)

    return apply_classic_filters(image, sharpness, denoise, contrast, saturation, brightness)

def ffmpeg_video(input_path, output_path, mode, resolution, ratio, fit, sharpness, denoise, preset):
    target_heights = {"720p": 720, "1080p": 1080, "2K": 1440, "4K": 2160}
    target_h = target_heights[resolution]

    if mode == "AI Super-Resolution (EDSR x4)":
        import cv2
        sr = create_super_resolution()
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            raise RuntimeError("Video open nahi hua.")
        fps = cap.get(cv2.CAP_PROP_FPS) or 25
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        source_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        source_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        out_w, out_h = output_dimensions(source_w, source_h, resolution, ratio, fit)
        temp_silent = output_path + ".silent.mp4"
        writer = cv2.VideoWriter(temp_silent, cv2.VideoWriter_fourcc(*"mp4v"), fps, (out_w, out_h))
        if not writer.isOpened():
            cap.release()
            raise RuntimeError("Temporary video writer start nahi hua.")
        progress = st.progress(0, text="AI frames process ho rahe hain…")
        index = 0
        try:
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                up = sr.upsample(frame)
                if ratio != "Original ratio" and fit == "Crop to fill":
                    up_h, up_w = up.shape[:2]
                    target_ratio = out_w / out_h
                    if up_w / up_h > target_ratio:
                        crop_w = int(up_h * target_ratio)
                        left = (up_w - crop_w) // 2
                        up = up[:, left:left+crop_w]
                    else:
                        crop_h = int(up_w / target_ratio)
                        top = (up_h - crop_h) // 2
                        up = up[top:top+crop_h, :]
                resized = cv2.resize(up, (out_w, out_h), interpolation=cv2.INTER_LANCZOS4)
                if denoise > 0:
                    resized = cv2.fastNlMeansDenoisingColored(resized, None, 3, 3, 7, 21)
                if sharpness > 0:
                    blur = cv2.GaussianBlur(resized, (0, 0), 1.1)
                    amount = min(1.5, sharpness / 70)
                    resized = cv2.addWeighted(resized, 1 + amount, blur, -amount, 0)
                writer.write(resized)
                index += 1
                if frame_count and index % 3 == 0:
                    progress.progress(min(1.0, index / frame_count), text=f"AI frame {index}/{frame_count}")
        finally:
            cap.release()
            writer.release()
            progress.empty()

        command = [
            "ffmpeg", "-y", "-i", temp_silent, "-i", input_path,
            "-map", "0:v:0", "-map", "1:a?", "-c:v", "libx264",
            "-preset", preset, "-crf", "18", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", output_path
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        try:
            os.remove(temp_silent)
        except OSError:
            pass
        if result.returncode:
            raise RuntimeError((result.stderr or "Audio remux failed")[-1400:])
        return

    # Fast classic FFmpeg enhancement path; no AI detail reconstruction.
    if ratio == "Original ratio":
        video_filter = f"scale=-2:{target_h}"
    else:
        ratios = {"9:16": "9/16", "16:9": "16/9", "1:1": "1", "4:3": "4/3"}
        target_ratio = ratios[ratio]
        if fit == "Crop to fill":
            video_filter = (
                f"scale='if(gt(a,{target_ratio}),-2,{target_h}*({target_ratio}))':"
                f"'if(gt(a,{target_ratio}),{target_h},-2)',"
                "crop='trunc(iw/2)*2':'trunc(ih/2)*2'"
            )
        else:
            video_filter = (
                f"scale='min({target_h}*({target_ratio}),iw*{target_h}/ih)':"
                f"'min({target_h},ih*({target_h}*({target_ratio}))/iw)':force_original_aspect_ratio=decrease,"
                f"pad='trunc({target_h}*({target_ratio})/2)*2':{target_h}:(ow-iw)/2:(oh-ih)/2"
            )
    filters = [video_filter]
    if denoise > 0:
        filters.append("hqdn3d=1.5:1.5:3:3")
    if sharpness > 0:
        filters.append(f"unsharp=5:5:{min(2.0, sharpness/50):.2f}:5:5:0")
    command = [
        "ffmpeg", "-y", "-i", input_path, "-map", "0:v:0", "-map", "0:a?",
        "-vf", ",".join(filters), "-c:v", "libx264", "-preset", preset,
        "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart", output_path
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError((result.stderr or "FFmpeg processing failed")[-1400:])

with st.sidebar:
    st.header("⚙️ Settings")
    media_type = st.radio("Choose media", ["Video Enhancer", "Image Enhancer"])
    mode = st.selectbox(
        "Enhancement mode",
        ["Free Classic Enhancement", "AI Super-Resolution (EDSR x4)"],
        help="AI mode downloads a large open-source model on first use. Free CPU hosting can be slow."
    )
    resolution = st.selectbox("Output resolution", ["720p", "1080p", "2K", "4K"], index=1)
    ratio = st.selectbox("Aspect ratio", ["Original ratio", "9:16", "16:9", "1:1", "4:3"])
    fit = st.radio("Fit method", ["Crop to fill", "Pad (show entire image)"])
    st.divider()
    st.subheader("✨ Tune enhancement")
    sharpness = st.slider("Sharpness", 0, 100, 35)
    denoise = st.slider("Noise reduction", 0, 100, 20)
    contrast = st.slider("Contrast", -30, 50, 5)
    saturation = st.slider("Color enhancement", -30, 50, 5)
    brightness = st.slider("Brightness", -30, 30, 0)
    preset_choice = st.selectbox("Video processing speed", ["Fast", "Balanced", "Better quality"], index=0)
    preset = {"Fast": "ultrafast", "Balanced": "veryfast", "Better quality": "medium"}[preset_choice]

st.info("Classic mode uses normal filters. AI mode uses EDSR x4 super-resolution; it may be slow or hit free-hosting limits.")
if mode == "AI Super-Resolution (EDSR x4)":
    st.warning("Pehle ek small image ya 3–5 second ki video test karein. AI model large hai aur free CPU hosting par video processing slow ho sakti hai.")

if media_type == "Image Enhancer":
    uploaded = st.file_uploader("Upload image", type=["jpg", "jpeg", "png", "webp", "bmp"])
    if uploaded:
        original = Image.open(uploaded)
        left, right = st.columns(2)
        with left:
            st.subheader("Original")
            st.image(original, use_container_width=True)
        if st.button("⚡ Enhance Image"):
            try:
                with st.spinner("Image process ho rahi hai…"):
                    enhanced = enhance_image(original, mode, resolution, ratio, fit, sharpness, denoise, contrast, saturation, brightness)
                    output = io.BytesIO()
                    enhanced.save(output, format="PNG", optimize=True)
                with right:
                    st.subheader("Enhanced")
                    st.image(enhanced, use_container_width=True)
                    st.success(f"Output size: {enhanced.width} × {enhanced.height}")
                    st.download_button("⬇️ Download Enhanced Image", output.getvalue(), "naxcy_enhanced.png", "image/png")
            except Exception as error:
                st.error(f"Enhancement failed: {error}")
else:
    uploaded = st.file_uploader("Upload video", type=["mp4", "mov", "avi", "mkv", "webm"])
    if uploaded:
        st.video(uploaded)
        if not ffmpeg_ready():
            st.error("FFmpeg/ffprobe missing. Repository ke root folder mein packages.txt file mein ffmpeg add karein.")
        if st.button("⚡ Enhance Video", disabled=not ffmpeg_ready()):
            with st.spinner("Video process ho rahi hai. AI mode mein zyada samay lag sakta hai…"):
                with tempfile.TemporaryDirectory() as temp_dir:
                    input_path = os.path.join(temp_dir, "input_video")
                    output_path = os.path.join(temp_dir, "naxcy_enhanced.mp4")
                    with open(input_path, "wb") as handle:
                        handle.write(uploaded.getbuffer())
                    try:
                        ffmpeg_video(input_path, output_path, mode, resolution, ratio, fit, sharpness, denoise, preset)
                        with open(output_path, "rb") as handle:
                            result_bytes = handle.read()
                        st.success("Enhancement complete!")
                        st.video(result_bytes)
                        st.download_button("⬇️ Download Enhanced Video", result_bytes, "naxcy_enhanced.mp4", "video/mp4")
                    except Exception as error:
                        st.error(f"Processing failed: {error}")

st.divider()
st.caption("NAXCY AI • Upscaling increases output resolution but cannot guarantee recovery of all missing original details.")
