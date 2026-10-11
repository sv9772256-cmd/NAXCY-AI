import streamlit as st
import cv2
import numpy as np
import tempfile
import os

# 1. Custom Global Config & Mobile Responsive Setup
st.set_page_config(
    page_title="NAXCY-AI Professional Studio",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. UNIQUE GLOWING PREMIUM LOGO DESIGN INTERFACE
st.markdown("""
    <style>
    .logo-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        background: linear-gradient(145deg, #020b14, #05192d, #0b2b45);
        padding: 30px;
        border-radius: 20px;
        margin-bottom: 30px;
        border: 2px solid #00ffcc;
        box-shadow: 0 0 25px rgba(0, 255, 204, 0.4), inset 0 0 15px rgba(0, 255, 204, 0.2);
    }
    .logo-text {
        font-family: 'Courier New', monospace;
        font-size: 42px;
        font-weight: 900;
        color: #00ffcc;
        text-shadow: 0 0 10px #00ffcc, 0 0 30px #00ffcc;
        letter-spacing: 5px;
    }
    .logo-subtext {
        color: #ffffff;
        font-size: 15px;
        margin-top: 8px;
        letter-spacing: 2px;
        font-weight: 300;
        opacity: 0.8;
    }
    @media (max-width: 768px) {
        .logo-text { font-size: 26px; letter-spacing: 2px; }
        .logo-subtext { font-size: 11px; }
    }
    </style>

    <div class="logo-container">
        <div class="logo-text">⚡ NAXCY-AI ⚡</div>
        <div class="logo-subtext">STABLE HIGH-FIDELITY 2K / 4K RESTORATION STUDIO</div>
    </div>
""", unsafe_allow_html=True)

# 3. ADVANCED 2K/4K CUBIC INTERPOLATION & SHARPNESS ENGINE
def process_core_matrix(frame, quality_mode, ratio_mode, source_w, source_h):
    if quality_mode == "4K Ultra HD":
        base_h = 2160
    elif quality_mode == "2K Quad HD":
        base_h = 1440
    else:  
        base_h = source_h

    if ratio_mode == "9:16 (Instagram Reel / Short)":
        target_h = base_h; target_w = int(target_h * (9 / 16))
    elif ratio_mode == "16:9 (YouTube / TV Size)":
        target_h = base_h; target_w = int(target_h * (16 / 9))
    elif ratio_mode == "1:1 (Square Post)":
        target_h = base_h; target_w = target_h
    elif ratio_mode == "4:5 (Instagram Portrait Post)":
        target_h = base_h; target_w = int(target_h * (4 / 5))
    else:  
        scale = 4.0 if quality_mode == "4K Ultra HD" else (2.0 if quality_mode == "2K Quad HD" else 1.0)
        target_w = int(source_w * scale); target_h = int(source_h * scale)

    if target_w % 2 != 0: target_w += 1
    if target_h % 2 != 0: target_h += 1

    # High-Quality Bicubic Upscaling Layer
    resized = cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_CUBIC)
    
    # Advanced Unsharp Masking System (Real HD Textures restore karne ke liye)
    gaussian_blur = cv2.GaussianBlur(resized, (5, 5), 0)
    sharp_frame = cv2.addWeighted(resized, 1.7, gaussian_blur, -0.7, 0)
    
    return sharp_frame, target_w, target_h

# 4. SIDEBAR SELECTION PANEL CONTROLS
st.sidebar.header("⚙️ Core Processing Configuration")
media_type = st.sidebar.radio("Select Processing Target:", ["🎥 Video Enhancement Engine", "📸 Image Restoration Engine"])

target_quality = st.sidebar.selectbox(
    "Choose Quality Profile:",
    ["Ultra Standard Quality", "2K Quad HD", "4K Ultra HD"]
)

target_ratio = st.sidebar.selectbox(
    "Select Video/Image Ratio Size:",
    [
        "Keep Original Ratio (Auto Lock)",
        "9:16 (Instagram Reel / Short)",
        "16:9 (YouTube / TV Size)",
        "1:1 (Square Post)",
        "4:5 (Instagram Portrait Post)"
    ]
)

# ==================== CONTROL MODULE 1: VIDEO ENGINE ====================
if media_type == "🎥 Video Enhancement Engine":
    st.subheader("🎥 Pro Video Enhancer System (High-Fidelity Mode)")
    uploaded_video = st.file_uploader("Video load karein...", type=["mp4", "mov", "avi"], key="vid_stream")

    if uploaded_video is not None:
        tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        tfile.write(uploaded_video.read())
        tfile.close()

        st.write("### Original Video Preview:")
        st.video(tfile.name)

        if st.button("✨ Initialize Video Restoration", key="run_vid"):
            final_output = "naxcy_stable_output.mp4"

            with st.spinner("🚀 AI Core active hai... High-definition textures restore ho rahe hain."):
                cap = cv2.VideoCapture(tfile.name)
                fps = cap.get(cv2.CAP_PROP_FPS)
                if fps == 0 or not fps: fps = 24.0

                orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

                frames_list = []
                
                while cap.isOpened():
                    ret, frame = cap.read()
                    if not ret: break

                    processed_frame, dummy_w, dummy_h = process_core_matrix(frame, target_quality, target_ratio, orig_w, orig_h)
                    frames_list.append(processed_frame)

                cap.release()

                if len(frames_list) > 0:
                    fourcc = cv2.VideoWriter_fourcc(*'MJPG')
                    out = cv2.VideoWriter(final_output, fourcc, fps, (dummy_w, dummy_h))
                    for f in frames_list:
                        out.write(f)
                    out.release()

            if os.path.exists(final_output):
                st.success(f"🎉 Processing complete! Dimensions set to: {dummy_w}x{dummy_h}")
                
                with open(final_output, "rb") as file_stream:
                    st.download_button(
                        label="⬇️ Download Enhanced Video",
                        data=file_stream.read(),
                        file_name="naxcy_enhanced_video.mp4",
                        mime="video/mp4"
                    )
                if os.path.exists(final_output): os.remove(final_output)
            else:
                st.error("Error: Server configuration sync nahi ho paayi.")
        os.unlink(tfile.name)

# ==================== CONTROL MODULE 2: IMAGE ENGINE ====================
else:
    st.subheader("📸 High-Fidelity Image Restoration Studio")
    uploaded_image = st.file_uploader("Image upload karein...", type=["jpg", "jpeg", "png"], key="img_stream")

    if uploaded_image is not None:
        file_bytes = np.asarray(bytearray(uploaded_image.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, 1)

        st.write("### Original Image Preview:")
        st.image(uploaded_image, width=350)  

        if st.button("✨ Initialize Image Restoration", key="run_img"):
            with st.spinner("🔮 Advanced algorithms pixels ko upscale kar rahe hain... Please wait."):
                h, w, _ = img.shape
                
                output_img, final_w, final_h = process_core_matrix(img, target_quality, target_ratio, w, h)

                _, encoded_buffer = cv2.imencode('.jpg', output_img, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
                byte_data = encoded_buffer.tobytes()

            st.success(f"🎉 Photo successfully transformed! Real Size: {final_w}x{final_h}")
            st.image(byte_data, width=350)  
            st.download_button(
                label="⬇️ Download Restored Sharp Image",
                data=byte_data,
                file_name="naxcy_enhanced_image.jpg",
                mime="image/jpeg"
            )
