import hashlib
import io
import os
import subprocess
import tempfile
import time
from collections import deque
from pathlib import Path

import imageio_ffmpeg
import streamlit as st
from PIL import Image, ImageEnhance, ImageFilter, ImageOps


st.set_page_config(
    page_title="NAXCY-AI | KARTIK SINGH",
    page_icon="⚡",
    layout="wide",
)

MAX_UPLOAD_MB = 200
MAX_IMAGE_PIXELS = 40_000_000
Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS

RESOLUTIONS = {
    "720p": 720,
    "780p (Custom)": 780,
    "1080p": 1080,
    "2K / 1440p (QHD)": 1440,
    "4K / 2160p (UHD)": 2160,
}

RATIOS = {
    "Keep Original": None,
    "16:9": 16 / 9,
    "9:16": 9 / 16,
    "1:1": 1.0,
    "4:3": 4 / 3,
    "4:5": 4 / 5,
}


st.markdown(
    """
    <style>
    .stApp {background:#0d1119;color:#edf8ff;}
    section[data-testid="stSidebar"] {background:#20232d;}
    .brand {
        padding:28px 16px;
        border:1px solid #16e5c2;
        border-radius:18px;
        background:linear-gradient(120deg,#07121d,#08283b);
        box-shadow:0 0 20px #00e6bf30;
        text-align:center;
        margin-bottom:24px;
    }
    .brand h1 {
        color:#21ffd4;
        letter-spacing:5px;
        margin:0;
        text-shadow:0 0 15px #00dcb0;
    }
    .creator {color:#ffffff;letter-spacing:3px;margin-top:10px;}
    .tagline {color:#a9bdcb;font-size:13px;margin-top:8px;}
    div.stButton > button {
        background:#00c9a7;color:#07151a;
        border:0;border-radius:10px;
    }
    </style>
    <div class="brand">
        <h1>⚡ NAXCY-AI ⚡</h1>
        <div class="creator">KARTIK SINGH</div>
        <div class="tagline">VIDEO & IMAGE ENHANCEMENT STUDIO</div>
    </div>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def ffmpeg_executable():
    return imageio_ffmpeg.get_ffmpeg_exe()


@st.cache_resource
def nvenc_available(ffmpeg):
    """Test actual encoding, not merely encoder registration."""
    command = [
        ffmpeg,
        "-hide_banner", "-loglevel", "error", "-nostdin",
        "-f", "lavfi",
        "-i", "color=c=black:s=256x256:r=1",
        "-frames:v", "1",
        "-c:v", "h264_nvenc",
        "-pix_fmt", "yuv420p",
        "-f", "null", "-",
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            timeout=20,
        )
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def even(value):
    return max(2, int(round(value / 2)) * 2)


def target_dimensions(short_side, ratio):
    if ratio >= 1:
        return even(short_side * ratio), even(short_side)
    return even(short_side), even(short_side / ratio)


def resize_image(image, size, fit_mode):
    if fit_mode == "Fit + black padding":
        return ImageOps.pad(
            image,
            size,
            method=Image.Resampling.LANCZOS,
            color=(0, 0, 0),
            centering=(0.5, 0.5),
        )
    return ImageOps.fit(
        image,
        size,
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5),
    )


def enhance_image(data, settings):
    with Image.open(io.BytesIO(data)) as source:
        if source.width * source.height > MAX_IMAGE_PIXELS:
            raise ValueError("Image too large: maximum 40 megapixels.")

        image = ImageOps.exif_transpose(source).convert("RGB")

    ratio = settings["ratio"] or image.width / image.height
    size = target_dimensions(settings["resolution"], ratio)

    if max(size) > 8192:
        raise ValueError(
            "Output side exceeds 8192 pixels. Choose a smaller "
            "resolution or a standard aspect ratio."
        )

    if settings["denoise"]:
        image = image.filter(ImageFilter.MedianFilter(size=3))

    image = resize_image(image, size, settings["fit"])
    image = ImageEnhance.Color(image).enhance(settings["colour"])
    image = ImageEnhance.Contrast(image).enhance(settings["contrast"])
    image = ImageEnhance.Brightness(image).enhance(
        1.0 + settings["brightness"]
    )

    if settings["sharpen"] > 0:
        image = image.filter(
            ImageFilter.UnsharpMask(
                radius=1.2,
                percent=int(settings["sharpen"] * 100),
                threshold=3,
            )
        )

    output = io.BytesIO()
    image.save(output, format="PNG", compress_level=3)
    return output.getvalue(), size


def video_filter(settings):
    filters = []

    # Spatial-only cleanup: no adjacent-frame mixing.
    if settings["denoise"]:
        filters.append("median=radius=1")

    short = settings["resolution"]
    ratio = settings["ratio"]
    scale_algorithm = (
        "bicubic" if settings["speed"] == "Fast" else "lanczos"
    )

    if ratio is None:
        # Normalize display aspect ratio, including non-square pixels.
        filters.append(
            f"scale="
            f"w='if(gte(dar,1),"
            f"min(8192,round({short}*dar/2)*2),{short})':"
            f"h='if(gte(dar,1),{short},"
            f"min(8192,round({short}/dar/2)*2))':"
            f"flags={scale_algorithm}"
        )
        filters.append("setsar=1")
    else:
        width, height = target_dimensions(short, ratio)
        keep = (
            "decrease"
            if settings["fit"] == "Fit + black padding"
            else "increase"
        )
        filters.append(
            f"scale={width}:{height}:"
            f"force_original_aspect_ratio={keep}:"
            f"force_divisible_by=2:"
            f"reset_sar=1:flags={scale_algorithm}"
        )
        if keep == "decrease":
            filters.append(
                f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black"
            )
        else:
            filters.append(
                f"crop={width}:{height}:(iw-ow)/2:(ih-oh)/2"
            )
        filters.append("setsar=1")

    filters.append(
        f"eq=contrast={settings['contrast']}:"
        f"brightness={settings['brightness']}:"
        f"saturation={settings['colour']}"
    )

    if settings["sharpen"] > 0:
        filters.append(
            f"unsharp=5:5:{settings['sharpen']}:5:5:0"
        )

    filters.append("format=yuv420p")
    return ",".join(filters)


def encoding_arguments(settings, use_gpu):
    quality = settings["quality"]

    if use_gpu:
        preset = {
            "Fast": "p1",
            "Balanced": "p4",
            "Quality": "p6",
        }[settings["speed"]]
        return [
            "-c:v", "h264_nvenc",
            "-preset", preset,
            "-rc", "vbr",
            "-cq", str(quality),
            "-b:v", "0",
        ]

    preset = {
        "Fast": "ultrafast",
        "Balanced": "veryfast",
        "Quality": "medium",
    }[settings["speed"]]

    return [
        "-c:v", "libx264",
        "-preset", preset,
        "-crf", str(quality),
        "-threads", str(min(os.cpu_count() or 2, 16)),
    ]


def run_video(ffmpeg, source, output, settings, use_gpu, status):
    command = [
        ffmpeg,
        "-hide_banner",
        "-loglevel", "error",
        "-nostdin",
        "-y",
        "-i", str(source),
        "-map", "0:v:0",
        "-map", "0:a:0?",
        "-vf", video_filter(settings),
        *encoding_arguments(settings, use_gpu),
        "-pix_fmt", "yuv420p",
        "-fps_mode", "passthrough",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        "-max_muxing_queue_size", "4096",
        "-progress", "pipe:1",
        "-nostats",
        str(output),
    ]

    started = time.perf_counter()

    # stderr goes to disk to avoid a full-pipe deadlock.
    with tempfile.TemporaryFile(mode="w+b") as error_log:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=error_log,
            text=True,
            bufsize=1,
        )
        latest = {}
        try:
            for line in process.stdout:
                key, separator, value = line.strip().partition("=")
                if not separator:
                    continue
                latest[key] = value

                if key == "progress":
                    elapsed = time.perf_counter() - started
                    status.info(
                        f"Processed timeline: "
                        f"{latest.get('out_time', '00:00:00')} | "
                        f"Speed: {latest.get('speed', '...')} | "
                        f"Elapsed: {elapsed:.1f}s"
                    )

            code = process.wait()
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
            if process.stdout:
                process.stdout.close()

        if code != 0:
            error_log.seek(0, os.SEEK_END)
            length = error_log.tell()
            error_log.seek(max(0, length - 12000))
            message = error_log.read().decode("utf-8", errors="replace")
            raise RuntimeError(message or "FFmpeg processing failed.")

    if not output.exists() or output.stat().st_size == 0:
        raise RuntimeError("No valid output was created.")


with st.sidebar:
    st.header("⚙️ Core Engine Settings")

    mode = st.radio("Select mode", ["Video", "Image"])

    resolution_label = st.selectbox(
        "Output resolution",
        list(RESOLUTIONS),
        index=2,
    )

    ratio_label = st.selectbox("Aspect ratio", list(RATIOS))

    fit_mode = st.selectbox(
        "Ratio fitting",
        ["Fit + black padding", "Centre crop"],
        help="Padding keeps the full picture. Crop removes the edges.",
    )

    speed = st.selectbox(
        "Processing mode",
        ["Fast", "Balanced", "Quality"],
        index=0,
    )

    st.subheader("Enhancement controls")
    sharpen = st.slider("Sharpen", 0.0, 1.5, 0.5, 0.05)
    colour = st.slider("Colour / saturation", 0.5, 1.5, 1.05, 0.05)
    contrast = st.slider("Contrast", 0.8, 1.3, 1.03, 0.01)
    brightness = st.slider("Brightness", -0.15, 0.15, 0.0, 0.01)
    denoise = st.checkbox(
        "Spatial noise cleanup",
        value=False,
        help="Optional. May soften fine details and slow processing.",
    )

    quality = st.slider(
        "Video compression quality — lower is better",
        16, 28, 19,
    )
    gpu_requested = st.checkbox("Try NVIDIA GPU encoding", value=True)

    st.caption(
        "Fast filter-based enhancement; no neural model is loaded. "
        "GPU encoding does not move all filters onto the GPU."
    )


settings = {
    "resolution": RESOLUTIONS[resolution_label],
    "ratio": RATIOS[ratio_label],
    "fit": fit_mode,
    "speed": speed,
    "sharpen": sharpen,
    "colour": colour,
    "contrast": contrast,
    "brightness": brightness,
    "denoise": denoise,
    "quality": quality,
}

st.subheader(f"🎬 {mode} Enhancement Studio")
st.caption(
    "No frame blending or motion interpolation. "
    "Existing source blur may remain."
)
st.info(
    "Use Fast mode and disable noise cleanup for the fastest attempt. "
    "30-second → 60-second processing is a target, not a guarantee."
)

types = (
    ["mp4", "mov", "mkv", "avi", "webm"]
    if mode == "Video"
    else ["jpg", "jpeg", "png", "webp", "bmp"]
)

upload = st.file_uploader(
    f"Upload {mode.lower()}",
    type=types,
)

if upload is not None:
    if upload.size > MAX_UPLOAD_MB * 1024 * 1024:
        st.error(f"Maximum upload size is {MAX_UPLOAD_MB} MB.")
        st.stop()

    data = upload.getvalue()
    signature = hashlib.sha256(
        data + mode.encode() + repr(settings).encode()
    ).hexdigest()

    with st.expander("Original preview", expanded=False):
        if mode == "Video":
            st.video(data)
        else:
            st.image(data)

    if st.button("⚡ Enhance Now", type="primary"):
        st.session_state.pop("naxcy_result", None)
        started = time.perf_counter()
        status = st.empty()

        try:
            if mode == "Image":
                with st.spinner("Enhancing image..."):
                    result_bytes, size = enhance_image(data, settings)

                result = {
                    "signature": signature,
                    "data": result_bytes,
                    "filename": "NAXCY_AI_enhanced.png",
                    "mime": "image/png",
                    "mode": mode,
                    "details": f"{size[0]} × {size[1]} | PNG",
                }
            else:
                ffmpeg = ffmpeg_executable()
                status.info("Checking encoder...")

                use_gpu = (
                    gpu_requested and nvenc_available(ffmpeg)
                )

                if gpu_requested and not use_gpu:
                    st.warning(
                        "NVIDIA encoding unavailable. Using CPU."
                    )

                suffix = Path(upload.name).suffix.lower()

                with tempfile.TemporaryDirectory(
                    prefix="naxcy_"
                ) as workdir:
                    source = Path(workdir) / f"input{suffix}"
                    output = Path(workdir) / "enhanced.mp4"
                    source.write_bytes(data)

                    try:
                        run_video(
                            ffmpeg, source, output,
                            settings, use_gpu, status,
                        )
                    except RuntimeError:
                        if not use_gpu:
                            raise
                        st.warning(
                            "GPU attempt failed. Retrying on CPU."
                        )
                        use_gpu = False
                        run_video(
                            ffmpeg, source, output,
                            settings, False, status,
                        )

                    result_bytes = output.read_bytes()

                result = {
                    "signature": signature,
                    "data": result_bytes,
                    "filename": "NAXCY_AI_enhanced.mp4",
                    "mime": "video/mp4",
                    "mode": mode,
                    "details": (
                        f"{resolution_label} | "
                        f"{'NVIDIA' if use_gpu else 'CPU'} encoding"
                    ),
                }

            result["elapsed"] = time.perf_counter() - started
            st.session_state["naxcy_result"] = result
            status.empty()

        except Exception as exc:
            status.empty()
            st.error(
                "Enhancement failed. Check the error below."
            )
            st.code(str(exc)[-12000:])

    result = st.session_state.get("naxcy_result")

    if result and result["signature"] == signature:
        st.success(
            f"Completed in {result['elapsed']:.1f} seconds | "
            f"{result['details']}"
        )

        if result["mode"] == "Video":
            st.video(result["data"])
        else:
            st.image(result["data"])

        st.download_button(
            "⬇️ Download Enhanced File",
            data=result["data"],
            file_name=result["filename"],
            mime=result["mime"],
        )
else:
    st.caption("Upload a file to begin.")
