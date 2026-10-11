import streamlit as st
import cv2
import numpy as np
import tempfile
import os
import subprocess

st.set_page_config(page_title="NAXCY-AI Ultimate 4K Enhancer", page_icon="🎬", layout="centered")

# Header Logo
st.markdown("<h1 style='text-align: center; font-size: 80px;'>🎬</h1>", unsafe_allow_html=True)
st.title("🚀 NAXCY-AI Multi-Media 4K Ultra Enhancer")
st.write("Apni Video ya Image ko true 4K resolution aur sharp details me instant convert karein!")

tab1, tab2 = st.tabs(["🎥 Video Enhancer (4K & Audio Fix)", "📸 Image Enhancer (True 4K Ultra HD)"])

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
            
            with st.spinner("🚀 AI Processing Engine active hai... Video 4K format me render ho rahi hai."):
                cap = cv2.VideoCapture(tfile.name)
                fps = cap.get(cv2.CAP_PROP_FPS)
                if fps == 0 or not fps: fps = 24.0
                
                # Dynamic 4K Scale
                target_width = 3840
                target_height = 2160
                
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                out = cv2.VideoWriter(temp_output, fourcc, fps, (target_width, target_height))
                
                while cap.isOpened():
                    ret, frame = cap.read()
                    if not ret: break
                    
                    upscaled_frame = cv2.resize(frame, (target_width, target_height), interpolation=cv2.INTER_CUBIC)
                    denoised = cv2.fastNlMeansDenoisingColored(upscaled_frame, None, 4, 4, 7, 21)
                    kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]], dtype=np.float32)
                    final_frame = cv2.filter2D(denoised, -1, kernel)
                    out.write(final_frame)
                    
                cap.release()
                out.release()
                
                try:
                    cmd = f"ffmpeg -y -i {temp_output} -i {tfile.name} -c:v copy -c:a aac -map 0:v:0 -map 1:a:0? {final_output}"
                    subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception:
                    os.rename(temp_output, final_output)
                    
            if os.path.exists(final_output):
                st.success("🎉 Video successfully 4K me convert ho gayi!")
                st.video(final_output)
                with open(final_output, "rb") as video_file:
                    st.download_button(label="⬇️ 4K Video Download Karein", data=video_file.read(), file_name="naxcy_4k_video.mp4", mime="video/mp4")
                if os.path.exists(temp_output): os.remove(temp_output)
                if os.path.exists(final_output): os.remove(final_output)
        os.unlink(tfile.name)

# ==================== TAB 2: IMAGE ENHANCER ENGINE (TRUE 4K FIXED) ====================
with tab2:
    st.header("True 4K Image Ultra Sharpener")
    uploaded_image = st.file_uploader("Photo (Image) select karein...", type=["jpg", "jpeg", "png"], key="img_up")
    
    if uploaded_image is not None:
        file_bytes = np.asarray(bytearray(uploaded_image.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, 1)
        
        st.write("### Original Image Preview:")
        st.image(uploaded_image, use_container_width=True)
        
        if st.button("✨ Convert Image to True 4K Ultra HD", key="img_btn"):
            with st.spinner("🔮 AI 4K Resolution Engine pixel structure rebuild kar raha hai... Please wait."):
                
                # --- TRUE 4K RESOLUTION MATHEMATICAL TARGET (3840 x 2160) ---
                target_4k_w = 3840
                target_4k_h = 2160
                
                # 1. Advanced Bicubic Scaling se image ko precise 4K blocks me resize karna
                img_4k = cv2.resize(img, (target_4k_w, target_4k_h), interpolation=cv2.INTER_CUBIC)
                
                # 2. Digital Denoising & Color Correction
                img_clean = cv2.fastNlMeansDenoisingColored(img_4k, None, 4, 4, 7, 21)
                
                # 3. High-Pass Unsharp Masking Matrix (4K Textures ko ultra-clear aur crisp banane ke liye)
                gaussian_blur = cv2.GaussianBlur(img_clean, (5, 5), 0)
                img_sharp = cv2.addWeighted(img_clean, 1.6, gaussian_blur, -0.6, 0)
                
                # Final structure encoding for PNG download stream
                _, encoded_img = cv2.imencode('.png', img_sharp)
                img_bytes = encoded_img.tobytes()
                
            st.success(f"🎉 Photo successfully true 4K Ultra HD ({target_4k_w}x{target_4k_h}) me upscale ho chuki hai!")
            st.write("### Enhanced 4K Ultra HD Output Image:")
            st.image(img_bytes, use_container_width=True)
            st.download_button(label="⬇️ True 4K Ultra HD Photo Download Karein", data=img_bytes, file_name="naxcy_true_4k_image.png", mime="image/png")
