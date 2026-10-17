import streamlit as st
import subprocess
import os
import time
from PIL import Image, ImageEnhance, ImageFilter

st.set_page_config(
    page_title="NAXCY AI Ultra Enhancer",
    page_icon="✨",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("<h1 style='text-align: center; color: #FF4B4B;'>✨ NAXCY AI Ultra Enhancer</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center;'>Optimized for Cloud Server Stability</p>", unsafe_allow_html=True)

def safe_remove(file_path):
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception:
            pass

tab1, tab2 = st.tabs(["📸 Image Enhancer", "🎥 Video Enhancer"])

# Safe Resolutions to prevent 1GB RAM OOM Crashes on Streamlit Cloud
res_dimensions = {
    "720p (HD - Fast)": (1280, 720),
    "1080p (Full HD - Standard)": (1920, 1080)
}

# ==========================================
# 1. IMAGE ENHANCER TAB
# ==========================================
with tab1:
    st.header("Upload Image")
    uploaded_image = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png", "webp"], key="img_uploader")

    if uploaded_image is not None:
        img = Image.open(uploaded_image)
        st.image(img, caption="Original Image Preview", use_container_width=True)
        
        st.subheader("Enhancement Settings")
        img_res_choice = st.selectbox("Target Image Resolution", list(res_dimensions.keys()), key="img_res")
        sharp_val = st.slider("Image Sharpness", 0.0, 3.0, 1.5, step=0.1)
        contrast_val = st.slider("Image Contrast", 0.5, 2.0, 1.1, step=0.1)
        
        if st.button("Enhance Image 🚀", key="btn_img"):
            with st.spinner("Processing image safely..."):
                target_w, target_h = res_dimensions[img_res_choice]
                enhanced_img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
                
                contrast = ImageEnhance.Contrast(enhanced_img)
                enhanced_img = contrast.enhance(contrast_val)
                enhanced_img = enhanced_img.filter(ImageFilter.UnsharpMask(radius=2, percent=int(sharp_val * 100), threshold=3))
                
                out_img_path = "enhanced_output.png"
                enhanced_img.save(out_img_path, format="PNG")
                
                st.success(f"Image Enhanced to {img_res_choice} successfully!")
                st.image(enhanced_img, use_container_width=True)
                
                with open(out_img_path, "rb") as file:
                    st.download_button("Download Enhanced Image 📥", data=file, file_name="naxcy_enhanced.png", mime="image/png")
                safe_remove(out_img_path)

# ==========================================
# 2. VIDEO ENHANCER TAB
# ==========================================
with tab2:
    st.header("Upload Video")
    uploaded_video = st.file_uploader("Choose a small video (Max 30MBแนะนำ)...", type=["mp4", "mov", "avi", "mkv"], key="vid_uploader")

    if uploaded_video is not None:
        st.video(uploaded_video)
        
        st.subheader("Upscaling Settings")
        video_res_choice = st.selectbox("Target Video Resolution", list(res_dimensions.keys()), key="vid_res")
        keep_audio = st.checkbox("Keep Original Audio Stream", value=True)
        
        w, h = res_dimensions[video_res_choice]
        scale_dim = f"{w}:{h}"

        if st.button("Enhance Video 🚀", key="btn_vid"):
            in_video_path = f"temp_in_{int(time.time())}.mp4"
            out_video_path = f"naxcy_enhanced_{int(time.time())}.mp4"
            
            with open(in_video_path, "wb") as f:
                f.write(uploaded_video.read())
                
            with st.spinner("Processing video..."):
                # Balanced filters for 1GB RAM constraint
                filter_complex = f"scale={scale_dim}:flags=lanczos,unsharp=3:3:0.5:3:3:0.0"
                
                cmd = [
                    "ffmpeg", "-y",
                    "-i", in_video_path,
                    "-vf", filter_complex,
                    "-c:v", "libx264",
                    "-crf", "24",            # Balanced bitrate to reduce RAM pressure
                    "-preset", "ultrafast"   # Max speed to avoid timeout
                ]
                
                if keep_audio:
                    cmd.extend(["-c:a", "aac"])
                else:
                    cmd.append("-an")
                    
                cmd.append(out_video_path)
                
                try:
                    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
                    
                    if os.path.exists(out_video_path) and os.path.getsize(out_video_path) > 0:
                        st.success(f"Video Enhanced to {video_res_choice}!")
                        st.video(out_video_path)
                        
                        with open(out_video_path, "rb") as file:
                            st.download_button("Download Enhanced Video 📥", data=file, file_name="naxcy_enhanced.mp4", mime="video/mp4")
                    else:
                        st.error("Processing failed due to server limit.")
                except subprocess.CalledProcessError as e:
                    st.error("Server Error during processing.")
                finally:
                    safe_remove(in_video_path)
                    safe_remove(out_video_path)
                
