import io
import os
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path

import cv2
import imageio_ffmpeg
import numpy as np
import streamlit as st
from PIL import Image, ImageOps

st.set_page_config(page_title="NAXCY-AI | KARTIK SINGH", page_icon="⚡", layout="wide")
cv2.setNumThreads(2)
Image.MAX_IMAGE_PIXELS = 12_000_000
MAX_SECONDS = 30
MAX_UPLOAD = 50 * 1024 * 1024
MAX_RUNTIME = 240

st.markdown("""<style>
.stApp{background:#0c111b;color:#f0f8ff}
section[data-testid="stSidebar"]{background:#202430}
.brand{text-align:center;border:1px solid #00e5bc;border-radius:18px;
padding:25px;background:#062333;box-shadow:0 0 20px #00e5bc35;margin-bottom:25px}
.brand h1{color:#1fffd1;letter-spacing:4px;margin:0}
.brand p{letter-spacing:3px}
</style><div class="brand"><h1>⚡ NAXCY-AI ⚡</h1>
<p>KARTIK SINGH</p><small>IMAGE & VIDEO • FSRCNN AI SUPER-RESOLUTION</small></div>""", unsafe_allow_html=True)

RES = {"720p":720, "780p (custom)":780, "1080p":1080,
       "2K / 1440p (QHD)":1440, "4K / 2160p (UHD)":2160}
RATIOS = {"Original":None, "16:9":16/9, "9:16":9/16,
          "1:1":1., "4:3":4/3, "4:5":4/5}

@st.cache_resource
def model_path(factor):
    directory = Path(tempfile.gettempdir()) / "naxcy_models"
    directory.mkdir(exist_ok=True)
    path = directory / f"FSRCNN_x{factor}.pb"
    if not path.exists():
        url = ("https://raw.githubusercontent.com/Saafke/"
               f"FSRCNN_Tensorflow/master/models/FSRCNN_x{factor}.pb")
        with urllib.request.urlopen(url, timeout=45) as response:
            content = response.read(5_000_001)
        if not 1000 < len(content) <= 5_000_000:
            raise RuntimeError("Invalid model download. Please retry.")
        with tempfile.NamedTemporaryFile(dir=directory, delete=False) as f:
            temporary = Path(f.name)
            f.write(content)
        os.replace(temporary, path)
    return str(path)


def load_model(factor):
    model = cv2.dnn_superres.DnnSuperResImpl_create()
    model.readModel(model_path(factor))
    model.setModel("fsrcnn", factor)
    model.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
    model.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
    return model


def check_time(start):
    if time.monotonic() - start > MAX_RUNTIME:
        raise RuntimeError("Processing exceeded the 4-minute safety limit. Try a shorter clip or lower resolution.")


def ai_upscale(image, model, factor, start):
    h, w = image.shape[:2]
    result = np.empty((h*factor, w*factor, 3), dtype=np.uint8)
    tile, overlap = 160, 12
    for y in range(0, h, tile):
        for x in range(0, w, tile):
            check_time(start)
            y1, x1 = max(0, y-overlap), max(0, x-overlap)
            y2, x2 = min(h, y+tile+overlap), min(w, x+tile+overlap)
            block = np.ascontiguousarray(image[y1:y2, x1:x2])
            enlarged = model.upsample(block)
            end_y, end_x = min(h, y+tile), min(w, x+tile)
            result[y*factor:end_y*factor, x*factor:end_x*factor] = enlarged[
                (y-y1)*factor:(end_y-y1)*factor,
                (x-x1)*factor:(end_x-x1)*factor]
    return result


def dimensions(w, h, short, ratio):
    r = ratio if ratio is not None else w/h
    even = lambda n: max(2, int(round(n/2))*2)
    tw, th = (even(short*r), even(short)) if r >= 1 else (even(short), even(short/r))
    if max(tw, th) > 4096 or tw*th > 8_850_000:
        raise ValueError("Output exceeds free-tier safety limits. Choose a standard ratio or lower resolution.")
    return tw, th


def finish(image, size, fit, sharp, saturation, contrast, brightness, noise):
    if noise:
        image = cv2.bilateralFilter(image, 5, 15, 15)
    w, h = size
    ih, iw = image.shape[:2]
    scale = min(w/iw, h/ih) if fit == "Keep full picture (padding)" else max(w/iw, h/ih)
    nw, nh = max(1, round(iw*scale)), max(1, round(ih*scale))
    image = cv2.resize(image, (nw, nh), interpolation=cv2.INTER_LANCZOS4)
    if fit == "Keep full picture (padding)":
        canvas = np.zeros((h, w, 3), dtype=np.uint8)
        x, y = (w-nw)//2, (h-nh)//2
        canvas[y:y+nh, x:x+nw] = image
        image = canvas
    else:
        x, y = (nw-w)//2, (nh-h)//2
        image = image[y:y+h, x:x+w].copy()
    if sharp > 0:
        blur = cv2.GaussianBlur(image, (0, 0), 1.0)
        image = cv2.addWeighted(image, 1+sharp, blur, -sharp, 0)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[:, :, 1] = np.clip(hsv[:, :, 1]*saturation, 0, 255)
    image = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
    adjusted = (image.astype(np.float32)-127.5)*contrast + 127.5 + brightness
    return np.ascontiguousarray(np.clip(adjusted, 0, 255).astype(np.uint8))


with st.sidebar:
    st.header("⚙️ Enhancement settings")
    mode = st.radio("Media", ["Image", "Video"])
    res = st.selectbox("Resolution", list(RES), index=2)
    ratio_name = st.selectbox("Aspect ratio", list(RATIOS))
    fit = st.selectbox("Fitting", ["Keep full picture (padding)", "Centre crop"])
    ai_choice = st.selectbox("AI scale", ["2× — lighter", "4× — more work"])
    sharp = st.slider("Extra sharpening", 0.0, 1.0, 0.15, 0.05)
    saturation = st.slider("Colour", 0.5, 1.5, 1.0, 0.05)
    contrast = st.slider("Contrast", 0.8, 1.3, 1.0, 0.01)
    brightness = st.slider("Brightness", -25, 25, 0)
    noise = st.checkbox("Mild spatial noise cleanup", False)
    st.caption("Free-tier safeguards: 50 MB upload; video ≤30 s, ≤1280×720 pixels, ≤30 FPS; image ≤3 MP. Processing stops after about 4 minutes.")

st.info("Actual FSRCNN neural upscaling on CPU. No paid API. Not Real-ESRGAN or guaranteed deblurring. 4K may be slow or exceed Cloud limits.")
st.caption("Video frame rate is normalized for encoding. No frame blending/interpolation. Existing blur and frame-to-frame AI flicker may remain.")
if mode == "Video":
    st.warning("Start with a 3–5 second clip at 720p output. Free Streamlit Cloud cannot guarantee fast 4K video enhancement.")

file = st.file_uploader("Upload media", type=["jpg","jpeg","png","webp"] if mode=="Image" else ["mp4","mov","mkv","webm","avi"])
if file is None:
    st.stop()
if file.size > MAX_UPLOAD:
    st.error("Upload limit: 50 MB.")
    st.stop()

factor = 2 if ai_choice.startswith("2") else 4
options = (fit, sharp, saturation, contrast, brightness, noise)

if st.button("⚡ Enhance with AI", type="primary"):
    st.session_state.pop("result", None)
    start = time.monotonic()
    progress = st.progress(0)
    status = st.empty()
    reader = None
    process = None
    try:
        status.info("Loading pretrained FSRCNN model...")
        model = load_model(factor)
        data = file.getvalue()
        if mode == "Image":
            with Image.open(io.BytesIO(data)) as source:
                if source.width*source.height > 3_000_000:
                    raise ValueError("Free setup supports images up to 3 megapixels. Resize the input first.")
                image = np.array(ImageOps.exif_transpose(source).convert("RGB"))
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            h, w = image.shape[:2]
            size = dimensions(w, h, RES[res], RATIOS[ratio_name])
            status.info("Running neural super-resolution...")
            image = ai_upscale(image, model, factor, start)
            progress.progress(0.8)
            image = finish(image, size, *options)
            ok, encoded = cv2.imencode(".png", image)
            if not ok:
                raise RuntimeError("PNG encoding failed.")
            result = (encoded.tobytes(), "image/png", "NAXCY_AI.png", mode)
        else:
            ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
            with tempfile.TemporaryDirectory(prefix="naxcy_") as directory:
                source = Path(directory)/("input"+Path(file.name).suffix.lower())
                output = Path(directory)/"NAXCY_AI.mp4"
                source.write_bytes(data)
                probe = imageio_ffmpeg.read_frames(str(source))
                try:
                    meta = next(probe)
                finally:
                    probe.close()
                w, h = meta["size"]
                fps = float(meta.get("fps", 0))
                duration = float(meta.get("duration", 0))
                if not 0 < duration <= MAX_SECONDS + 0.05:
                    raise ValueError("Use a video with readable duration, maximum 30 seconds.")
                if w*h > 1280*720 or max(w,h)>1920 or not 0 < fps <= 30.05:
                    raise ValueError("Free CPU limit: input up to 1280×720 pixels (portrait also allowed), maximum 30 FPS.")
                size = dimensions(w, h, RES[res], RATIOS[ratio_name])
                ow, oh = size
                reader = imageio_ffmpeg.read_frames(
                    str(source), pix_fmt="rgb24",
                    output_params=["-vf", f"fps={fps:.8f}"])
                next(reader)
                command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
                    "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{ow}x{oh}",
                    "-r", f"{fps:.8f}", "-i", "pipe:0", "-i", str(source),
                    "-map", "0:v:0", "-map", "1:a:0?", "-c:v", "libx264",
                    "-preset", "ultrafast", "-crf", "19", "-threads", "2",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                    "-t", str(duration), "-movflags", "+faststart", str(output)]
                with tempfile.TemporaryFile() as errors:
                    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=errors)
                    count = 0
                    try:
                        for raw in reader:
                            check_time(start)
                            if count >= int(duration*fps)+2:
                                raise RuntimeError("Unexpected frame count; processing stopped for safety.")
                            rgb = np.frombuffer(raw, np.uint8).reshape(h,w,3)
                            frame = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
                            frame = ai_upscale(frame, model, factor, start)
                            frame = finish(frame, size, *options)
                            process.stdin.write(frame.tobytes())
                            count += 1
                            if count % 3 == 0:
                                progress.progress(min(0.98, count/max(1,duration*fps)))
                                status.info(f"AI frames: {count} / approximately {round(duration*fps)} | Elapsed: {time.monotonic()-start:.0f}s")
                        process.stdin.close()
                        process.wait(timeout=60)
                        if process.returncode:
                            raise RuntimeError("Video/audio encoding failed.")
                    except Exception as exc:
                        if process.poll() is None:
                            process.kill()
                            process.wait()
                        errors.seek(0)
                        detail = errors.read().decode(errors="replace")[-2000:]
                        raise RuntimeError(f"{exc}\n{detail}") from exc
                    finally:
                        reader.close()
                        reader = None
                        if process.stdin and not process.stdin.closed:
                            process.stdin.close()
                if count == 0 or not output.exists() or output.stat().st_size == 0:
                    raise RuntimeError("No output produced.")
                if output.stat().st_size > 150*1024*1024:
                    raise RuntimeError("Output exceeds the 150 MB download safety limit.")
                result = (output.read_bytes(), "video/mp4", "NAXCY_AI.mp4", mode)
        progress.progress(1.0)
        status.success(f"Completed in {time.monotonic()-start:.1f} seconds.")
        st.session_state["result"] = result
    except Exception as exc:
        st.error(str(exc))
        st.caption("No silent fallback to basic resizing. Retry with a shorter clip, 2× AI, or a smaller input.")
    finally:
        if reader is not None:
            reader.close()
        if process is not None and process.poll() is None:
            process.kill()
            process.wait()

result = st.session_state.get("result")
if result:
    blob, mime, name, result_mode = result
    st.subheader("Last completed result")
    if result_mode == "Image":
        st.image(blob)
    else:
        st.video(blob)
    st.download_button("⬇️ Download enhanced file", blob, file_name=name, mime=mime)
