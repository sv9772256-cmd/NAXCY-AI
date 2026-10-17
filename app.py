import io, os, tempfile, subprocess, shutil
import streamlit as st
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

st.set_page_config(page_title="NAXCY AI Ultra Enhancer", page_icon="⚡", layout="wide")

st.markdown("""
<style>
.block-container {max-width: 1100px; padding-top: 1.2rem; padding-bottom: 2rem;}
.hero {padding: 22px; border-radius: 18px; background: linear-gradient(120deg,#07111f,#073b4c); color:#fff; text-align:center; border:1px solid #16d6c2;}
.hero h1 {color:#27f4d2; margin-bottom:4px;}
.small-note {font-size: .88rem; opacity:.85}
div.stButton > button {width:100%; border-radius:12px; font-weight:700;}
</style>
<div class="hero">
<h1>⚡ NAXCY-AI</h1>
<div>VIDEO & IMAGE ENHANCEMENT STUDIO</div>
<p class="small-note">Mobile-friendly • Preserve audio • Choose resolution and ratio</p>
</div>
""", unsafe_allow_html=True)

def ffmpeg_available():
    return shutil.which("ffmpeg") is not None

def resize_to_target(w, h, quality, ratio_mode, fit_mode):
    targets = {"720p HD": 720, "1080p Full HD": 1080, "2K QHD": 1440, "4K Ultra HD": 2160}
    if ratio_mode == "Original ratio":
        target_h = targets[quality]
        scale = target_h / h
        return max(2, int(w*scale)//2*2), max(2, int(target_h)//2*2)
    ratios = {"9:16": 9/16, "16:9": 16/9, "1:1": 1, "4:3": 4/3}
    ratio = ratios.get(ratio_mode, w/h)
    target_h = targets[quality]
    target_w = int(target_h * ratio)
    if fit_mode == "Crop to fill":
        return max(2,target_w//2*2), max(2,target_h//2*2)
    scale = min(target_w/w, target_h/h)
    return max(2,int(w*scale)//2*2), max(2,int(h*scale)//2*2)

def enhance_image(img, sharpness, denoise, contrast, color, brightness, quality, ratio_mode, fit_mode):
    img = ImageOps.exif_transpose(img).convert("RGB")
    w, h = img.size
    tw, th = resize_to_target(w, h, quality, ratio_mode, fit_mode)
    if ratio_mode != "Original ratio" and fit_mode == "Crop to fill":
        target_ratio = tw/th
        current_ratio = w/h
        if current_ratio > target_ratio:
            nw = int(h*target_ratio); left = (w-nw)//2
            img = img.crop((left,0,left+nw,h))
        else:
            nh = int(w/target_ratio); top = (h-nh)//2
            img = img.crop((0,top,w,top+nh))
    img = img.resize((tw,th), Image.Resampling.LANCZOS)
    if denoise > 0:
        img = img.filter(ImageFilter.MedianFilter(size=3 if denoise < 60 else 5))
    img = ImageEnhance.Sharpness(img).enhance(1 + sharpness/50)
    img = ImageEnhance.Contrast(img).enhance(1 + contrast/100)
    img = ImageEnhance.Color(img).enhance(1 + color/100)
    img = ImageEnhance.Brightness(img).enhance(1 + brightness/100)
    return img

def run_ffmpeg(input_path, output_path, quality, ratio_mode, fit_mode, sharpness, denoise, preset):
    probe = subprocess.run(
        ["ffprobe","-v","error","-select_streams","v:0","-show_entries","stream=width,height","-of","csv=s=x:p=0",input_path],
        capture_output=True, text=True
    )
    if probe.returncode != 0 or not probe.stdout.strip():
        raise RuntimeError("Video dimensions read nahi ho paaye. FFmpeg/ffprobe check karein.")
    w,h = map(int,probe.stdout.strip().split("x")[:2])
    targets = {"720p HD":720,"1080p Full HD":1080,"2K QHD":1440,"4K Ultra HD":2160}
    target_h = targets[quality]
    if ratio_mode == "Original ratio":
        vf = f"scale=-2:{target_h}"
    else:
        ratios = {"9:16":"9/16","16:9":"16/9","1:1":"1","4:3":"4/3"}
        r = ratios[ratio_mode]
        if fit_mode == "Crop to fill":
            vf = f"scale='if(gt(a,{r}),-2,{target_h}*({r}))':'if(gt(a,{r}),{target_h},-2)',crop='trunc(iw/2)*2':'trunc(ih/2)*2'"
        else:
            vf = f"scale='min({target_h}*({r}),iw*{target_h}/ih)':'min({target_h},ih*({target_h}*({r}))/iw)':force_original_aspect_ratio=decrease,pad='trunc({target_h}*({r})/2)*2':{target_h}:(ow-iw)/2:(oh-ih)/2"
    filters = [vf]
    if denoise > 0:
        filters.append("hqdn3d=1.5:1.5:3:3")
    if sharpness > 0:
        amount = min(2.0, sharpness/50)
        filters.append(f"unsharp=5:5:{amount:.2f}:5:5:0.0")
    cmd = ["ffmpeg","-y","-i",input_path,"-map","0:v:0","-map","0:a?","-vf",",".join(filters),
           "-c:v","libx264","-preset",preset,"-crf","19","-pix_fmt","yuv420p",
           "-c:a","aac","-b:a","192k","-movflags","+faststart",output_path]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError((p.stderr or "FFmpeg processing failed")[-1800:])

with st.sidebar:
    st.header("⚙️ NAXCY Core Settings")
    media_type = st.radio("Media type", ["Video Enhancer", "Image Enhancer"])
    quality = st.selectbox("Output quality", ["720p HD","1080p Full HD","2K QHD","4K Ultra HD"], index=1)
    ratio_mode = st.selectbox("Aspect ratio", ["Original ratio","9:16","16:9","1:1","4:3"])
    fit_mode = st.radio("Fit method", ["Crop to fill","Pad (show entire image)"])
    st.divider()
    st.subheader("✨ Enhancement")
    sharpness = st.slider("Sharpness", 0, 100, 35)
    denoise = st.slider("Noise reduction", 0, 100, 20)
    contrast = st.slider("Contrast", -30, 50, 5)
    color = st.slider("Color enhancement", -30, 50, 5)
    brightness = st.slider("Brightness", -30, 30, 0)
    preset_label = st.selectbox("Processing speed", ["Fast","Balanced","Better quality"], index=0)
    preset = {"Fast":"ultrafast","Balanced":"veryfast","Better quality":"medium"}[preset_label]

st.caption("Upload a file, choose settings in the sidebar, then process it.")
if media_type == "Image Enhancer":
    up = st.file_uploader("Upload image", type=["jpg","jpeg","png","webp","bmp"])
    if up:
        img = Image.open(up)
        c1,c2 = st.columns(2)
        with c1:
            st.subheader("Original")
            st.image(img, use_container_width=True)
        if st.button("⚡ Enhance Image"):
            with st.spinner("Image enhance ho rahi hai..."):
                out = enhance_image(img, sharpness, denoise, contrast, color, brightness, quality, ratio_mode, fit_mode)
                buf = io.BytesIO()
                out.save(buf, format="PNG", optimize=True)
            with c2:
                st.subheader("Enhanced")
                st.image(out, use_container_width=True)
                st.success(f"Output: {out.width} × {out.height}")
                st.download_button("⬇️ Download Enhanced Image", buf.getvalue(), "naxcy_enhanced.png", "image/png")
else:
    up = st.file_uploader("Upload video (MP4, MOV, AVI, MKV, WEBM)", type=["mp4","mov","avi","mkv","webm"])
    if up:
        st.video(up)
        st.info("Audio stream ko output mein copy/re-encode kiya jayega. Video processing server resources par depend karti hai.")
        if not ffmpeg_available():
            st.error("Is server par FFmpeg available nahi hai. packages.txt mein FFmpeg install hona chahiye.")
        if st.button("⚡ Enhance Video", disabled=not ffmpeg_available()):
            with st.spinner("Video process ho rahi hai. Badi/4K files mein samay lag sakta hai..."):
                with tempfile.TemporaryDirectory() as td:
                    inp = os.path.join(td, "input_video")
                    outp = os.path.join(td, "naxcy_enhanced.mp4")
                    with open(inp,"wb") as f: f.write(up.getbuffer())
                    try:
                        run_ffmpeg(inp,outp,quality,ratio_mode,fit_mode,sharpness,denoise,preset)
                        with open(outp,"rb") as f: data=f.read()
                        st.success("Enhancement complete!")
                        st.video(data)
                        st.download_button("⬇️ Download Enhanced Video", data, "naxcy_enhanced.mp4", "video/mp4")
                    except Exception as e:
                        st.error(f"Processing failed: {e}")

st.divider()
st.caption("NAXCY AI • Output quality depends on the source file and server. Resolution upscaling alone cannot recreate missing detail; this starter uses conventional enhancement filters, not a generative AI super-resolution model.")
    
