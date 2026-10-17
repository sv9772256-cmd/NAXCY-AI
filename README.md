# ✨ NAXCY AI Ultra Enhancer

A powerful, mobile-friendly web application built with **Streamlit**, **FFmpeg**, and **Pillow** to upscale and enhance the visual quality of your images and videos.

## 🚀 Features
- **Advanced Image Enhancement:** Uses Lanczos Resampling combined with Unsharp Masking, Contrast, and Saturation adjustments.
- **Smart Video Upscaling:** Upscales video dimensions up to 4K using high-quality FFmpeg filters (`lanczos` scaling, `hqdn3d` denoising, and custom sharpening).
- **Storage Optimized:** Automatically cleans up processing files to prevent server crashes.
- **Mobile Friendly:** Fully responsive UI tailored for Android WebView wraps and mobile browsers.

## 📁 Repository Structure
- `app.py` - The core application layout and processing pipeline.
- `requirements.txt` - Python backend dependencies.
- `packages.txt` - Linux system-level dependencies required for FFmpeg.

## 🛠️ Local Installation
1. Clone the repository:
   ```bash
   git clone https://github.com
   ```
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Make sure **FFmpeg** is installed on your system's environment path.
4. Run the app:
   ```bash
   streamlit run app.py
   ```
   
