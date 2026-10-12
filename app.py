import os
import subprocess
import tempfile
import shutil
from pathlib import Path
import cv2
import numpy as np
import streamlit as st
import imageio_ffmpeg
from PIL import Image

# ==========================================
# PAGE CONFIGURATION & CUSTOM DARK THEME
# ==========================================
st.set_page_config(
    page_title="NAXCY-AI PRO | Ultra Video & Image Enhancer",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.stApp { background:#0a0f1d; color:#e2e8f0; }
.logo-container {
  text-align:center; padding:30px 15px; margin:10px 0 30px;
  border-radius:20px; border:1px solid #00ffcc;
  background:linear-gradient(135deg, #020b14, #0b1e36);
  box-shadow:0 0 30px rgba(0, 255, 204, 0.2);
}
.logo-text { font:900 42px 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; letter-spacing:5px;
  color:#00ffcc; text-shadow:0 0 15px rgba(0, 255, 204, 0.6); }
.logo-subtext { font-size:13px; letter-spacing:3px; color:#94a3b8; margin-top:8px; font-weight:600; }
.section-header { color:#00ffcc; font-weight:700; margin-top:15px; border-bottom:1px solid #1e293b; padding-bottom:5px;}
</style>
<div class="logo-container">
  <div class="logo-text">⚡ NAXCY-AI PRO ⚡</div>
  <div class="logo-subtext">ULTRA VIDEO & IMAGE ENHANCEMENT STUDIO</div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# CORE ENHANCEMENT PIPELINE (ULTRA CLEAN)
# ==========================================
def enhance_frame(frame, denoise_strength, sharpness_strength, use_clahe, contrast_val, brightness_val, detail_enhance):
    """
    Advanced multi-stage frame enhancement for crisp, clean, and professional output.
    """
    # 1. Color Space Conversion
    result = frame.copy()
    
    # 2. Advanced Denoising (Removes digital grain/noise cleanly)
    if denoise_strength > 0:
        # Adjusted for balanced speed and clean results
        h_lum = denoise_strength
        h_chroma = denoise_strength
        result = cv2.fastNlMeansDenoisingColored(result, None, h_lum, h_chroma, 7, 15)
        
    # 3. Smart Contrast (CLAHE - Localized Contrast Enhancement)
    if use_clahe:
        lab = cv2.cvtColor(result, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        cl = clahe.apply(l)
        lab = cv2.merge((cl, a, b))
        result = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        
    # 4. Standard Contrast & Brightness Tuning
    if contrast_val != 1.0 or brightness_val != 0:
        result = cv2.convertScaleAbs(result, alpha=contrast_val, beta=brightness_val)
        
    # 5. Non-Photorealistic Detail Enhancement
    if detail_enhance:
        result = cv2.detailEnhance(result, sigma_s=10, sigma_r=0.15)
        
    # 6. High-Pass Sharpness Filter (Crisp edges without artifacts)
    if sharpness_strength > 0:
        gaussian = cv2.GaussianBlur(result, (0, 0), 2.0)
        result = cv2.addWeighted(result, 1.0 + sharpness_strength, gaussian, -sharpness_strength, 0)
        
    return result

def even_dim(v):
    v = max(2, int(round(v)))
    return v if v % 2 == 0 else v + 1

def output_size(src_w, src_h, quality, ratio_name, ratios, quality_dict):
    ratio = ratios[ratio_name]
    requested_h = quality_dict[quality]
    
    if ratio is None:
        scale = 1.0 if requested_h is None else requested_h / src_h
        return even_dim(src_w * scale), even_dim(src_h * scale)

    rw, rh = ratio
    base_h = requested_h if requested_h is not None else src_h
    out_h = even_dim(base_h)
    out_w = even_dim(out_h * rw / rh)
    return out_w, out_h

def fit_frame(frame, out_w, out_h, fit_mode):
    h, w = frame.shape[:2]
    if w == out_w and h == out_h:
        return frame
        
    # High quality Lanczos4 interpolation for crisp rescaling
    if fit_mode == "Pad (Show Entire Frame)":
        scale = min(out_w / w, out_h / h)
        nw, nh = max(1, round(w * scale)), max(1, round(h * scale))
        resized = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_LANCZOS4)
        canvas = np.zeros((out_h, out_w, 3), dtype=np.uint8)
        x, y = (out_w - nw) // 2, (out_h - nh) // 2
        canvas[y:y+nh, x:x+nw] = resized
        return canvas
    else:
        scale = max(out_w / w, out_h / h)
        nw, nh = max(out_w, round(w * scale)), max(out_h, round(h * scale))
        resized = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_LANCZOS4)
        x, y = (nw - out_w) // 2, (nh - out_h) // 2
        return resized[y:y+out_h, x:x+out_w]

# ==========================================
# INTERFACE & PRESETS DICTIONARIES
# ==========================================
QUALITY = {
    "Original Resolution": None,
    "720p HD": 720,
    "1080p Full HD": 1080,
    "2K QHD (1440p)": 1440,
    "4K Ultra HD (2160p)": 2160,
}
RATIOS = {
    "Original Aspect Ratio": None,
    "16:9 — YouTube / Landscape": (16, 9),
    "9:16 — Reels / Shorts / TikTok": (9, 16),
    "1:1 — Square Post": (1, 1),
    "4:5 — Portrait Post": (4, 5),
}

# ==========================================
# SIDEBAR CONTROLS (THE ULTIMATE TOOLKIT)
# ==========================================
st.sidebar.markdown('<div class="section-header">📁 MEDIA SOURCE</div>', unsafe_allow_html=True)
mode = st.sidebar.radio("Select Media Type:", ["Image Studio", "Video Studio"])
uploaded_file = st.sidebar.file_uploader("Upload File", type=["jpg", "jpeg", "png", "mp4", "mov", "avi"])

st.sidebar.markdown('<div class="section-header">📐 RESOLUTION & FRAMING</div>', unsafe_allow_html=True)
quality_choice = st.sidebar.selectbox("Target Resolution:", list(QUALITY.keys()), index=2) # Default 1080p
ratio_choice = st.sidebar.selectbox("Aspect Ratio:", list(RATIOS.keys()))
fit_mode = st.sidebar.radio("Framing Mode:", ["Crop & Fill (No Black Bars)", "Pad (Show Entire Frame)"])

st.sidebar.markdown('<div class="section-header">✨ ENHANCEMENT SLIDERS</div>', unsafe_allow_html=True)
denoise = st.sidebar.slider("Denoise / Grain Removal (Clean Smoothness)", 0, 15, 3)
sharpness = st.sidebar.slider("Ultra Sharpness (Crisp Edges)", 0.0, 2.0, 0.4, step=0.1)
contrast = st.sidebar.slider("Manual Contrast Adjust", 0.5, 2.0, 1.0, step=0.1)
brightness = st.sidebar.slider("Brightness Finetune", -50, 50, 0, step=5)

st.sidebar.markdown('<div class="section-header">⚙️ ADVANCED PRO ENHANCERS</div>', unsafe_allow_html=True)
use_clahe = st.sidebar.checkbox("Enable CLAHE (Smart Local Contrast)", value=True)
detail_enhance = st.sidebar.checkbox("Enable Pro Detail Enhancement", value=False)

# ==========================================
# EXECUTION LOGIC
# ==========================================
if uploaded_file is not None:
    tfile = tempfile.NamedTemporaryFile(delete=False)
    tfile.write(uploaded_file.read())
    tfile.close()
    
    if mode == "Image Studio":
        st.subheader("📸 Image Enhancement Processing")
        
        # Load Image
        file_bytes = np.asarray(bytearray(open(tfile.name, "rb").read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        
        if img is not None:
            h_src, w_src = img.shape[:2]
            out_w, out_h = output_size(w_src, h_src, quality_choice, ratio_choice, RATIOS, QUALITY)
            
            # Process
            processed_img = enhance_frame(img, denoise, sharpness, use_clahe, contrast, brightness, detail_enhance)
            final_img = fit_frame(processed_img, out_w, out_h, fit_mode)
            
            # Layout Columns for Comparison
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Original Image Preview:**")
                st.image(cv2.cvtColor(img, cv2.COLOR_BGR2RGB), use_container_width=True)
                st.caption(f"Dimensions: {w_src}x{h_src}")
            with col2:
                st.markdown("**✨ Enhanced Clean Output:**")
                st.image(cv2.cvtColor(final_img, cv2.COLOR_BGR2RGB), use_container_width=True)
                st.caption(f"Enhanced Dimensions: {out_w}x{out_h}")
                
            # Download Button
            is_success, buffer = cv2.imencode(".png", final_img)
            if is_success:
                st.download_button(
                    label="📥 Download Clean Image",
                    data=buffer.tobytes(),
                    file_name="naxcy_enhanced.png",
                    mime="image/png"
                )
                
    elif mode == "Video Studio":
        st.subheader("🎬 Video Enhancement Processing")
        
        cap = cv2.VideoCapture(tfile.name)
        w_src = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h_src = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        if total_frames > 0:
            out_w, out_h = output_size(w_src, h_src, quality_choice, ratio_choice, RATIOS, QUALITY)
            
            st.write(f"📊 **Original Video Info:** {w_src}x{h_src} @ {fps:.2f} FPS | **Target Out:** {out_w}x{out_h}")
            
            if st.button("🚀 Start Ultra Clean Enhancement"):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Setup temp output video paths
                video_out_raw = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False).name
                
                # Setup VideoWriter with clean mp4v codec
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                out_writer = cv2.VideoWriter(video_out_raw, fourcc, fps, (out_w, out_h))
                
                frame_idx = 0
                while cap.isOpened():
                    ret, frame = cap.read()
                    if not ret:
                        break
                        
                    # Apply pristine enhancement pipeline frame-by-frame
