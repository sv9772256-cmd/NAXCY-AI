import streamlit as st
import subprocess
import os
import time
from PIL import Image, ImageEnhance, ImageFilter

# Page configuration for mobile friendliness
st.set_page_config(
    page_title="NAXCY AI Ultra Enhancer",
    page_icon="✨",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# App Title & Styling
st.markdown("<h1 style='text-align: center; color: #FF4B4B;'>✨ NAXCY AI Ultra Enhancer</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center;'>Enhance and upscale your Images & Videos using Advanced Filtering</p>", unsafe_allow_html=True)

# Helper function to delete temporary files safely
def safe_remove(file_path):
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception as e:
            pass

# Main Tabs for Image and Video
tab1, tab2 = st.tabs(["📸 Image Enhancer", "🎥 Video Enhancer"])

# ==========================================
# 1. IMAGE ENHANCER TAB
# ==========================================
with tab1:
    st.header("Upload Image")
    uploaded_image = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png", "webp"], key="img_uploader")

    if uploaded_image is not None:
        img = Image.open(uploaded_image)
        st.image(img, caption="Original Image Preview", use_container_width=True)
        
        # Enhancement Controls
        st.subheader("Enhancement Settings")
        scale_factor = st.slider("Upscale Factor (Dimensions)", 1.0, 4.0, 2.0, step=0.5)
        sharp_val = st.slider("Image Sharpness", 0.0, 3.0, 1.5, step=0.1)
        contrast_val = st.slider("Image Contrast", 0.5, 2.0, 1.1, step=0.1)
        color_val = st.slider("Color Saturation", 0.5, 2.0, 1.1, step=0.1)
        
        if st.button("Enhance Image 🚀", key="btn_img"):
            with st.spinner("Processing image... Please wait."):
                # 1. Advanced Lanczos Resizing (Better than Bilinear/Nearest)
                w, h = img.size
                new_w = int(w * scale_factor)
                new_h = int(h * scale_factor)
                enhanced_img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                
                # 2. Apply Contrast Enhancement
                contrast = ImageEnhance.Contrast(enhanced_img)
                enhanced_img = contrast.enhance(contrast_val)
                
                # 3. Apply Color Saturation Enhancement
                color = ImageEnhance.Color(enhanced_img)
                enhanced_img = color.enhance(color_val)
                
                # 4. Apply Advanced Unsharp Mask for Edge Details
                enhanced_img = enhanced_img.filter(ImageFilter.UnsharpMask(radius=2, percent=int(sharp_val * 100), threshold=3))
                
                # Save and Output
                out_img_path = "enhanced_output.png"
                enhanced_img.save(out_img_path, format="PNG")
                
                st.success("Image Enhanced Successfully!")
                st.image(enhanced_img, caption="Enhanced Image Preview", use_container_width=True)
                
                # Download Button
                with open(out_img_path, "rb") as file:
                    st.download_button(
                        label="Download Enhanced Image 📥",
                        data=file,
                        file_name="naxcy_enhanced.png",
                        mime="image/png"
                    )
                
                # Cleanup
                safe_remove(out_img_path)

# ==========================================
# 2. VIDEO ENHANCER TAB
# ==========================================
with tab2:
    st.header("Upload Video")
    uploaded_video = st.file_uploader("Choose a video...", type=["mp4", "mov", "avi", "mkv"], key="vid_uploader")

    if uploaded_video is not None:
        st.video(uploaded_video)
        
        # Resolution Choices
        st.subheader("Upscaling & Filter Settings")
        resolution = st.selectbox(
            "Target Resolution",
            ["720p (1280x720)", "1080p (1920x1080)", "2K (2560x1440)", "4K (3840x2160)"]
        )
        
        # Audio Retention Option
        keep_audio = st.checkbox("Keep Original Audio Stream", value=True)
        
        # Dynamic Resolution Dimensions Mapping
        res_map = {
            "720p (1280x720)": "1280:720",
            "1080p (1920x1080)": "1920:1080",
            "2K (2560x1440)": "2560:1440",
            "4K (3840x2160)": "3840:2160"
        }
        scale_dim = res_map[resolution]

        if st.button("Enhance Video 🚀", key="btn_vid"):
            # Save uploaded bytes to temporary file for FFmpeg input
            in_video_path = f"temp_in_{int(time.time())}.mp4"
            out_video_path = f"naxcy_enhanced_{int(time.time())}.mp4"
            
            with open(in_video_path, "wb") as f:
                f.write(uploaded_video.read())
                
            with st.spinner("Processing video... This utilizes FFmpeg Smart Filters (Lanczos + Unsharp + Denoise) and may take time depending on video length."):
                
                # Complex FFmpeg Filter: 
                # 1. scale with lanczos flags (crisp pixel resize)
                # 2. hqdn3d (High Quality 3D Denoise to reduce noise generated by upscaling)
                # 3. unsharp (Sharpening edges to avoid standard blurriness)
                filter_complex = f"scale={scale_dim}:flags=lanczos,hqdn3d=1.5:1.5:6:6,unsharp=5:5:1.0:5:5:0.0"
                
                # Building the FFmpeg command
                cmd = [
                    "ffmpeg", "-y",
                    "-i", in_video_path,
                    "-vf", filter_complex,
                    "-c:v", "libx264",
                    "-crf", "18",         # High Visual Quality Level
                    "-preset", "medium"   # Good compression balance for cloud CPUs
                ]
                
                if keep_audio:
                    cmd.extend(["-c:a", "aac"])
                else:
                    cmd.append("-an")
                    
                cmd.append(out_video_path)
                
                # Execute FFmpeg command
                try:
                    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
                    
                    if os.path.exists(out_video_path) and os.path.getsize(out_video_path) > 0:
                        st.success("Video Enhanced & Upscaled Successfully!")
                        st.video(out_video_path)
                        
                        # Download Button
                        with open(out_video_path, "rb") as file:
                            st.download_button(
                                label="Download Enhanced Video 📥",
                                data=file,
                                file_name="naxcy_enhanced_video.mp4",
                                mime="video/mp4"
                            )
                    else:
                        st.error("Failed to generate the enhanced video file.")
                        
                except subprocess.CalledProcessError as e:
                    st.error("An error occurred during FFmpeg execution.")
                    st.code(e.stderr)
                finally:
                    # Clean up local temporary storage files instantly
                    safe_remove(in_video_path)
                    safe_remove(out_video_path)
                
