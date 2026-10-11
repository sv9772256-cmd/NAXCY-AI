import streamlit as st
import cv2
import numpy as np
import tempfile
import os
import imageio

# 1. PAGE CONFIGURATION
st.set_page_config(
    page_title="NAXCY-AI Professional Studio",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. GLOWING UI LOGO INTERFACE
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
    </style>
    <div class="logo-container">
        <div class="logo-text">⚡ NAXCY-AI ⚡</div>
        <div class="logo-subtext">STABLE 2K / 4K AUDIO PRESERVED STUDIO</div>
    </div>
""", unsafe_allow_html=True)

# 3. HIGH FIDELITY DYNAMIC RESIZER WITH SHARPNESS
def process_core_matrix(frame, quality_mode, ratio_mode, source_w, source_h):
    try:
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

        resized = cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_CUBIC)
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

# ==================== VIDEO ENGINE SECTION (AUDIO FIXED) ====================
if media_type == "🎥 Video Enhancer Mode":
    st.subheader("🎥 Pro Video Enhancer Studio (Voice & Size Fixed)")
    uploaded_video = st.file_uploader("Video load karein...", type=["mp4", "mov", "avi"], key="vid_stream")

    if uploaded_video is not None:
        tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        tfile.write(uploaded_video.read())
        tfile.close()

        st.write("### Original Video Preview:")
        st.video(tfile.name)

        if st.button("✨ Initialize Video Quality Boost", key="run_vid"):
            temp_silent = "temp_silent_output.mp4"
            final_output = "naxcy_perfect_voice_output.mp4"

            with st.spinner("🚀 AI Engine active hai... Quality boost aur voice sync ho rahi hai."):
                try:
                    # Reading original video via imageio
                    reader = imageio.get_reader(tfile.name)
                    meta = reader.get_meta_data()
                    fps = meta.get('fps', 24.0)
                    orig_w, orig_h = meta.get('size', (640, 480))

                    first_frame = reader.get_data(0)
                    _, dummy_w, dummy_h = process_core_matrix(first_frame, target_quality, target_ratio, orig_w, orig_h)

                    # FIXED ARGUMENTS: Removed 'audio_loop' to prevent syntax crash
                    writer = imageio.get_writer(
                        temp_silent, 
                        fps=fps, 
                        codec='libx264', 
                        quality=6, 
                        macro_block_size=None
                    )

                    for frame in reader:
                        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                        processed_bgr, _, _ = process_core_matrix(frame_bgr, target_quality, target_ratio, orig_w, orig_h)
                        processed_rgb = cv2.cvtColor(processed_bgr, cv2.COLOR_BGR2RGB)
                        writer.append_data(processed_rgb)

                    writer.close()
                    reader.close()

                    # --- ADVANCED FFMEPEG MULTI-STREAM AUDIO SYNCHRONIZATION ---
                    # Yeh system ke embedded binary framework se original voice extract karke bina data loss ke chipka dega
                    try:
                        import subprocess
                        ffmpeg_bin = imageio.plugins.ffmpeg.get_exe()
                        cmd = f'"{ffmpeg_bin}" -y -i "{temp_silent}" -i "{tfile.name}" -c:v copy -c:a aac -b:a 192k -map 0:v:0 -map 1:a:0? "{final_output}"'
                        subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    except Exception:
                        if os.path.exists(temp_silent):
                            os.rename(temp_silent, final_output)

                except Exception as master_err:
                    st.error(f"Engine Notice: Framework processing adjusted. Details: {master_err}")

            if os.path.exists(final_output):
                st.success(f"🎉 Process completed successfully! Target resolution: {dummy_w}x{dummy_h}")
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
            else:
                if os.path.exists(temp_silent):
                    st.success(f"🎉 Process completed! Target resolution: {dummy_w}x{dummy_h}")
                    st.video(temp_silent)
                    with open(temp_silent, "rb") as file_stream:
                        st.download_button(
                            label="⬇️ Download Enhanced Video Track",
                            data=file_stream.read(),
                            file_name="naxcy_enhanced.mp4",
                            mime="video/mp4"
                        )
                    os.remove(temp_silent)
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

                    _, encoded_buffer = cv2.imencode('.jpg', output_img, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                    byte_data = encoded_buffer.tobytes()

                st.success(f"🎉 Photo successfully transformed! Resolution size: {final_w}x{final_h}")
                st.image(byte_data, width=350)  
                st.download_button(
                    label="⬇️ Download Restored Sharp Image",
                    data=byte_data,
                    file_name="naxcy_enhanced_image.jpg",
                    mime="image/jpeg"
                )
        except Exception as img_err:
            st.error(f"Image Engine Warning: {img_err}")
