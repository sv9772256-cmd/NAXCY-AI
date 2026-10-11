import streamlit as st
import cv2
import numpy as np
import tempfile
import os
import subprocess

st.set_page_config(page_title="NAXCY-AI Ultimate Enhancer", page_icon="🎬", layout="centered")

# Custom Title & Master App Logo
st.markdown("<h1 style='text-align: center; font-size: 80px;'>🎬</h1>", unsafe_allow_html=True)
st.title("🚀 NAXCY-AI Multi-Media Ultra Enhancer")
st.write("Apni Video ya Image ki quality badhayein bina any data loss aur perfect dynamic processing ke sath!")

# --- MULTI-TAB NAVIGATION SYSTEM ---
tab1, tab2 = st.tabs(["🎥 Video Enhancer (4K & Audio Fix)", "📸 Image Enhancer (Ultra HD)"])

# ==================== TAB 1: VIDEO ENHANCER ENGINE ====================
with tab1:
    st.header("Video Quality Pro Engine")
    uploaded_video = st.file_uploader("Video file select karein...", type=["mp4", "mov", "avi"], key="video_up")
    
    if uploaded_video is not None:
        tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') 
        tfile.write(uploaded_video.read())
        tfile.close()
        
        st.write("### Original Video Preview:")
        st.video(tfile.name)
        
        if st.button("✨ Convert Video to Perfect 4K", key="vid_btn"):
            temp_output = "temp_enhanced.mp4"
            final_output = "naxcy_perfect_4k.mp4"
            
            with st.spinner("🚀 AI Processing Engine active hai... Audio aur Ratio restore ho rahe hain."):
                cap = cv2.VideoCapture(tfile.name)
                
                fps = cap.get(cv2.CAP_PROP_FPS)
                if fps == 0 or not fps:
                    fps = 24.0
                    
                orig_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                orig_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                
                # Dynamic Auto Aspect Ratio Multiplication
                target_width = orig_width * 4
                target_height = orig_height * 4
                
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                out = cv2.VideoWriter(temp_output, fourcc, fps, (target_width, target_height))
                
                while cap.isOpened():
                    ret, frame = cap.read()
                    if not ret:
                        break
                    
                    # Core Processing Layer
                    upscaled_frame = cv2.resize(frame, (target_width, target_height), interpolation=cv2.INTER_CUBIC)
                    denoised = cv2.fastNlMeansDenoisingColored(upscaled_frame, None, 4, 4, 7, 21)
                    kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]], dtype=np.float32)
                    final_frame = cv2.filter2D(denoised, -1, kernel)
                    
                    out.write(final_frame)
                    
                cap.release()
                out.release()
                
                # FFMPEG Audio Sync Engine
                try:
                    cmd = f"ffmpeg -y -i {temp_output} -i {tfile.name} -c:v copy -c:a aac -map 0:v:0 -map 1:a:0? {final_output}"
                    subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception:
                    os.rename(temp_output, final_output)
                    
            if os.path.exists(final_output):
                st.success("🎉 Video successfully enhance ho gayi hai!")
                st.write("### Enhanced Output Video:")
                
                with open(final_output, "rb") as video_file:
                    video_bytes = video_file.read()
                    st.video(video_bytes)
                    st.download_button(label="⬇️ Perfect 4K Video Download Karein", data=video_bytes, file_name="naxcy_perfect_4k.mp4", mime="video/mp4")
                    
                if os.path.exists(temp_output): os.remove(temp_output)
                if os.path.exists(final_output): os.remove(final_output)
            else:
                st.error("Processing me koi dikkat aayi.")
                
        os.unlink(tfile.name)

# ==================== TAB 2: IMAGE ENHANCER ENGINE ====================
with tab2:
    st.header("Image Quality HD Engine")
    uploaded_image = st.file_uploader("Photo (Image) select karein...", type=["jpg", "jpeg", "png"], key="img_up")
    
    if uploaded_image is not None:
        file_bytes = np.asarray(bytearray(uploaded_image.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, 1)
        
        st.write("### Original Image Preview:")
        st.image(uploaded_image, use_container_width=True)
        
        if st.button("✨ Enhance Image Quality", key="img_btn"):
            with st.spinner("🔮 AI Pixel Sharpener photo ko clear kar raha hai... Please wait."):
                h, w, c = img.shape
                
                # Image Super Resolution 4x Scale
                img_resized = cv2.resize(img, (w * 4, h * 4), interpolation=cv2.INTER_CUBIC)
                
                # Image Denoising and Sharpening Filter Matrix
                img_denoised = cv2.fastNlMeansDenoisingColored(img_resized, None, 6, 6, 7, 21)
                kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]], dtype=np.float32)
                img_enhanced = cv2.filter2D(img_denoised, -1, kernel)
                
                # Encoded structure for downlaod format
                _, encoded_img = cv2.imencode('.png', img_enhanced)
                img_bytes = encoded_img.tobytes()
                
            st.success("🎉 Photo quality successfully boost ho gayi hai!")
            st.write("### Enhanced Ultra HD Output Image:")
            st.image(img_bytes, use_container_width=True)
            st.download_button(label="⬇️ Ultra HD Photo Download Karein", data=img_bytes, file_name="naxcy_enhanced_image.png", mime="image/png")
