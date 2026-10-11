import streamlit as st
import cv2
import numpy as np
import tempfile
import os
from moviepy.editor import VideoFileClip

# 1. BULLETPROOF PAGE CONFIGURATION
st.set_page_config(
    page_title="NAXCY-AI Ultimate Media Studio",
    page_icon="🎬",
    layout="centered",
    initial_sidebar_state="expanded"
)

# 2. PREMIUM GLOWING UI LOGO INTERFACE
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
        <div class="logo-subtext">AUDIO + SIZE COMPRESSION FULL OPTIMIZED ENGINE</div>
    </div>
""", unsafe_allow_html=True)

# 3. ADVANCED RATIO & SHARPNESS PROCESSOR
def process_core_matrix(frame, quality_mode, ratio_mode, source_w, source_h):
    try:
        if quality_mode == "4K Ultra HD":
            base_h = 2160
        elif quality_mode == "2K Quad HD":
            base_h = 1440
        else:  
            base_h = source_h

        if ratio_mode == "9:16 (Instagram Reel / Short)":
            target_h = base_h
            target_w = int(target_h * (9 / 16))
        elif ratio_mode == "16:9 (YouTube / TV Size)":
            target_h = base_h
            target_w = int(target_h * (16 / 9))
        elif ratio_mode == "1:1 (Square Post)":
            target_h = base_h
            target_w = target_h
        elif ratio_mode == "4:5 (Instagram Portrait Post)":
            target_h = base_h
            target_w = int(target_h * (4 / 5))
        else:  
            scale = 4.0 if quality_mode == "4K Ultra HD" else (2.0 if quality_mode == "2K Quad HD" else 1.0)
            target_w = int(source_w * scale)
            target_h = int(source_h * scale)

        if target_w % 2 != 0: target_w += 1
        if target_h % 2 != 0: target_h += 1

        resized = cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_CUBIC)
        
        # Motion Blur Cleaning System
        gaussian_blur = cv2.GaussianBlur(resized, (5, 5), 0)
        sharp_frame = cv2.addWeighted(resized, 1.7, gaussian_blur, -0.7, 0)
        
        return sharp_frame, target_w, target_h
    except Exception:
        return frame, source_w, source_h

# 4. SIDEBAR CONFIGURATION
st.sidebar.header("⚙️ Core Engine Settings")
media_type = st.sidebar.radio("Select Input Source:", ["🎥 Video Enhancer Mode", "📸 Image Enhancer Mode"])

target_quality = st.sidebar.selectbox(
    "Select Output Quality:",
    ["Ultra Standard Quality", "2K Quad HD", "4K Ultra HD"]
)

target_ratio = st.sidebar.selectbox(
    "Set Target Aspect Ratio:",
    [
        "Keep Original Ratio (Auto Lock)",
        "9:16 (Instagram Reel / Short)",
        "16:9 (YouTube / TV Size)",
        "1:1 (Square Post)",
        "4:5 (Instagram Portrait Post)"
    ]
)

# ==================== VIDEO ENGINE SECTION ====================
if media_type == "🎥 Video Enhancer Mode":
    st.subheader("🎥 Pro Video Enhancer Studio (Voice & Compression Sync)")
    uploaded_video = st.file_uploader("Video load karein...", type=["mp4", "mov", "avi"], key="vid_stream")

    if uploaded_video is not None:
        tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        tfile.write(uploaded_video.read())
        tfile.close()

        st.write("### Original Video Preview:")
        st.sidebar.video(tfile.name) # Sidebar mapping preview safely
        st.video(tfile.name)

        if st.button("✨ Initialize Video Quality Boost", key="run_vid"):
            temp_silent = "temp_silent_enhanced.mp4"
            final_output = "naxcy_compressed_voice.mp4"
            
            with st.spinner("🚀 AI Core active hai... Video process aur compressed size optimize ho raha hai."):
                try:
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
                        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                        out = cv2.VideoWriter(temp_silent, fourcc, fps, (dummy_w, dummy_h))
                        for f in frames_list:
                            out.write(f)
                        out.release()

                        # --- MOVIEPY AUDIO SYNC & DYNAMIC COMPRESSION ENGINE ---
                        # Yeh structure original voice extract karega aur compressed bitstream write karega size chota rakhne ke liye
                        orig_clip = VideoFileClip(tfile.name)
                        enhanced_clip = VideoFileClip(temp_silent)
                        
                        if orig_clip.audio is not None:
                            final_clip = enhanced_clip.set_audio(orig_clip.audio)
                        else:
                            final_clip = enhanced_clip
                            
                        # libx264 codec aur optimized bitrate size control rakhega
                        final_clip.write_videofile(
                            final_output, 
                            codec="libx264", 
                            audio_codec="aac",
                            bitrate="1500k", 
                            preset="medium",
                            logger=None
                        )
                        
                        orig_clip.close()
                        enhanced_clip.close()
                        final_clip.close()

                    if os.path.exists(final_output):
                        st.success(f"🎉 Process successfully complete! Size controlled at standard distribution tier.")
                        st.video(final_output)
                        with open(final_output, "rb") as file_stream:
                            st.download_button(
                                label="⬇️ Download Enhanced Video Track (With Voice)",
                                data=file_stream.read(),
                                file_name="naxcy_perfect_enhanced.mp4",
                                mime="video/mp4"
                            )
                        if os.path.exists(temp_silent): os.remove(temp_silent)
                        if os.path.exists(final_output): os.remove(final_output)
                except Exception as master_err:
                    st.error(f"Engine Alert: Framework integration backup handled safely. Details: {master_err}")
                    if os.path.exists(temp_silent): os.remove(temp_silent)
        os.unlink(tfile.name)

# ==================== IMAGE ENGINE SECTION ====================
else:
    st.subheader("📸 High-Fidelity Image Restoration Studio")
    uploaded_image = st.file_uploader("Image upload karein...", type=["jpg", "jpeg", "png"], key="img_stream")

    if uploaded_image is not None:
        try:
            file_bytes = np.asarray(bytearray(uploaded_image.read()), dtype=np.uint8)
            img = cv2.imdecode(file_bytes, 1)

            st.write("### Original Image Preview:")
            st.image(uploaded_image, width=350)  

            if st.button("✨ Initialize Image Quality Boost", key="run_img"):
                with st.spinner("🔮 Processing high-frequency textures details..."):
                    h, w, _ = img.shape
                    output_img, final_w, final_h = process_core_matrix(img, target_quality, target_ratio, w, h)

                    # High compression format quality control mapping to retain tight sizing limits
                    _, encoded_buffer = cv2.imencode('.jpg', output_img, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                    byte_data = encoded_buffer.tobytes()

                st.success(f"🎉 Photo successfully transformed! Matrix Resolution: {final_w}x{final_h}")
                st.image(byte_data, width=350)  
                st.download_button(
                    label="⬇️ Download Restored Sharp Image",
                    data=byte_data,
                    file_name="naxcy_enhanced_image.jpg",
                    mime="image/jpeg"
                )
        except Exception as img_err:
            st.error(f"Image Engine Warning: {img_err}")
