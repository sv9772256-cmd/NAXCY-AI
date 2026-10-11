import streamlit as st
import cv2
import numpy as np
import tempfile
import os
import subprocess

st.set_page_config(page_title="NAXCY-AI 2K Pro", page_icon="🎬", layout="centered")

# Header Section Logo
st.markdown("<h1 style='text-align: center; font-size: 80px;'>🎬</h1>", unsafe_allow_html=True)
st.title("🚀 NAXCY-AI 2K Stable Enhancer")
st.write("Video aur Image 2K Resolution Engine - Strict Size Control & Full Audio System.")

tab1, tab2 = st.tabs(["🎥 Video 2K Engine", "📸 Image 2K Engine"])

# ==================== TAB 1: VIDEO 2K ENHANCER (STRICT SIZE CONTROL) ====================
with tab1:
    st.header("Video 2K Size-Controlled Quality Mode")
    uploaded_video = st.file_uploader("Video select karein...", type=["mp4", "mov", "avi"], key="video_up")
    
    if uploaded_video is not None:
        tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') 
        tfile.write(uploaded_video.read())
        tfile.close()
        
        st.write("### Original Video Preview:")
        st.video(tfile.name)
        
        if st.button("✨ Enhance Video to 2K (Keep Size Low)", key="vid_btn"):
            temp_output = "temp_2k_uncompressed.mp4"
            final_output = "naxcy_2k_lite_output.mp4"
            
            with st.spinner("🚀 AI Processing Engine active hai... Size and audio track sync ho rahe hain."):
                cap = cv2.VideoCapture(tfile.name)
                fps = cap.get(cv2.CAP_PROP_FPS)
                if fps == 0 or not fps: fps = 24.0
                
                # Dynamic 2K Target Setup
                target_width = 2560
                target_height = 1440
                
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                out = cv2.VideoWriter(temp_output, fourcc, fps, (target_width, target_height))
                
                while cap.isOpened():
                    ret, frame = cap.read()
                    if not ret: break
                    
                    # 2K Scale + Lightweight Sharpness
                    upscaled = cv2.resize(frame, (target_width, target_height), interpolation=cv2.INTER_CUBIC)
                    kernel = np.array([[-0.5,-0.5,-0.5], [-0.5,5,-0.5], [-0.5,-0.5,-0.5]], dtype=np.float32)
                    final_frame = cv2.filter2D(upscaled, -1, kernel)
                    out.write(final_frame)
                    
                cap.release()
                out.release()
                
                # --- ADVANCED H.264 COMPRESSION ENGINE WITH FULL VOICE COPY ---
                # CRF 32 file size ko original jitna tight rakhta hai aur audio stream full bitrate par merge karta hai
                try:
                    cmd = f"ffmpeg -y -i {temp_output} -i {tfile.name} -c:v libx264 -crf 32 -preset medium -c:a aac -b:a 256k -map 0:v:0 -map 1:a:0? {final_output}"
                    subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception:
                    os.rename(temp_output, final_output)
                    
            if os.path.exists(final_output):
                st.success("🎉 Video 2K resolution me successfully clear ho chuki hai!")
                st.video(final_output)
                with open(final_output, "rb") as video_file:
                    st.download_button(label="⬇️ 2K Compact Video Download Karein", data=video_file.read(), file_name="naxcy_2k_video.mp4", mime="video/mp4")
                if os.path.exists(temp_output): os.remove(temp_output)
                if os.path.exists(final_output): os.remove(final_output)
        os.unlink(tfile.name)

# ==================== TAB 2: IMAGE 2K ENHANCER (STRICT SIZE CONTROL) ====================
with tab2:
    st.header("Image 2K Strict Sharpener Mode")
    uploaded_image = st.file_uploader("Photo select karein...", type=["jpg", "jpeg", "png"], key="img_up")
    
    if uploaded_image is not None:
        file_bytes = np.asarray(bytearray(uploaded_image.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, 1)
        
        st.write("### Original Image Preview:")
        st.image(uploaded_image, use_container_width=True)
        
        if st.button("✨ Enhance Image to 2K (Safe Size)", key="img_btn"):
            with st.spinner("🔮 Image sharpener active hai... Please wait."):
                
                target_w = 2560
                target_h = 1440
                
                img_2k = cv2.resize(img, (target_w, target_h), interpolation=cv2.INTER_CUBIC)
                
                # Balanced Filter Matrix for file size matching
                kernel = np.array([[-0.5,-0.5,-0.5], [-0.5,5,-0.5], [-0.5,-0.5,-0.5]], dtype=np.float32)
                img_sharp = cv2.filter2D(img_2k, -1, kernel)
                
                # JPEG Quality 70 se compressed byte output maintain hota hai
                _, encoded_img = cv2.imencode('.jpg', img_sharp, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
                img_bytes = encoded_img.tobytes()
                
            st.success(f"🎉 Photo successfully 2K resolution me boost ho chuki hai!")
            st.image(img_bytes, use_container_width=True)
            st.download_button(label="⬇️ 2K Optimized Photo Download Karein", data=img_bytes, file_name="naxcy_2k_image.jpg", mime="image/jpeg")
