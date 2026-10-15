import os, subprocess, tempfile, time
from pathlib import Path
import cv2
import numpy as np
import streamlit as st
import imageio_ffmpeg
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(page_title="NAXCY AI PRO", page_icon="⚡", layout="wide")
st.markdown("""
<style>
.stApp{background:#080e1b;color:#eef5ff}
.nx{text-align:center;padding:24px;border:1px solid #00e6c3;border-radius:18px;
background:linear-gradient(135deg,#03111e,#092b43)}
.nx h1{color:#00ffd0;letter-spacing:3px}
</style>
<div class="nx"><h1>⚡ NAXCY AI PRO ⚡</h1><p>VIDEO & IMAGE ENHANCEMENT STUDIO</p></div>
""", unsafe_allow_html=True)

RES = {"Original resolution":None,"720p HD":720,"1080p Full HD":1080,"2K QHD (1440p)":1440,"4K UHD (2160p)":2160}
RATIOS = {"Original aspect ratio":None,"9:16 — Reels / Shorts":(9,16),"16:9 — YouTube":(16,9),"1:1 — Square":(1,1),"4:5 — Portrait":(4,5),"3:2 — Photo":(3,2)}

def even(v):
    v=max(2,int(round(v)))
    return v if v%2==0 else v+1

def target_size(w,h,res_name,ratio_name):
    if len(w) > 2: h, w = w[0], w[1] # Fix tuple issue
    rh=RES[res_name]; ratio=RATIOS[ratio_name]
    if ratio is None:
        scale=1 if rh is None else rh/float(h)
        return even(w*scale),even(h*scale)
    rw,rrh=ratio
    oh=even(h if rh is None else rh)
    return even(oh*rw/rrh),oh

def fit_frame(frame,ow,oh,mode):
    h,w=frame.shape[:2]
    if (w,h)==(ow,oh): return frame
    scale=min(ow/w,oh/h) if mode=="Pad (show entire image)" else max(ow/w,oh/h)
    nw,nh=max(1,round(w*scale)),max(1,round(h*scale))
    resized=cv2.resize(frame,(nw,nh),interpolation=cv2.INTER_LANCZOS4)
    if mode=="Pad (show entire image)":
        canvas=np.zeros((oh,ow,3),np.uint8); x=(ow-nw)//2; y=(oh-nh)//2
        canvas[y:y+nh,x:x+nw]=resized
        return canvas
    x=(nw-ow)//2; y=(nh-oh)//2
    return resized[y:y+oh,x:x+ow]

def enhance_frame(frame,denoise_strength,sharpness,color_intensity,brightness,contrast):
    out=frame.copy()
    if denoise_strength>0:
        n=int(denoise_strength)
        # Fast processing ke liye photo Denoise template-window sizes optimize kiya gaya hai
        out=cv2.fastNlMeansDenoisingColored(out,None,n,n,5,15)
    if color_intensity!=1:
        hsv=cv2.cvtColor(out,cv2.COLOR_BGR2HSV).astype(np.float32)
        hsv[:,:,1]=np.clip(hsv[:,:,1]*color_intensity,0,255)
        out=cv2.cvtColor(hsv.astype(np.uint8),cv2.COLOR_HSV2BGR)
    if contrast!=1 or brightness:
        out=cv2.convertScaleAbs(out,alpha=float(contrast),beta=int(brightness))
    if sharpness>0:
        blurred=cv2.GaussianBlur(out,(0,0),1.0)
        strength=sharpness*1.1
        out=cv2.addWeighted(out,1+strength,blurred,-strength,0)
    return np.clip(out,0,255).astype(np.uint8)

def process_single_frame(frame, den, sharp, color, bright, cont, ow, oh, mode):
    f = enhance_frame(frame, den, sharp, color, bright, cont)
    return fit_frame(f, ow, oh, mode)

def ffmpeg():
    return imageio_ffmpeg.get_ffmpeg_exe()

def process_image(upload,settings):
    raw=np.frombuffer(upload.getvalue(),np.uint8)
    img=cv2.imdecode(raw,cv2.IMREAD_COLOR)
    if img is None: raise ValueError("Image read nahi ho payi. JPG, PNG ya WEBP chune.")
    den,sharp,color,bright,cont,res,ratio,mode=settings
    img=enhance_frame(img,den,sharp,color,bright,cont)
    w,h=target_size(img.shape,img.shape,res,ratio)
    img=fit_frame(img,w,h,mode)
    ext=Path(upload.name).suffix.lower()
    if ext not in (".png",".webp",".jpg",".jpeg"): ext=".jpg"
    if ext==".png": params,mime=[cv2.IMWRITE_PNG_COMPRESSION,3],"image/png"
    elif ext==".webp": params,mime=[cv2.IMWRITE_WEBP_QUALITY,95],"image/webp"
    else: ext=".jpg"; params,mime=[cv2.IMWRITE_JPEG_QUALITY,95],"image/jpeg"
    ok,enc=cv2.imencode(ext,img,params)
    if not ok: raise RuntimeError("Enhanced image save nahi ho pai.")
    return enc.tobytes(),w,h,mime,ext

def video_info(path):
    cap=cv2.VideoCapture(path)
    info={"w":int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),"h":int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
          "fps":float(cap.get(cv2.CAP_PROP_FPS)),"n":int(cap.get(cv2.CAP_PROP_FRAME_COUNT))}
    cap.release()
    if not np.isfinite(info["fps"]) or info["fps"]<=0 or info["fps"]>240: info["fps"]=30.0
    return info

def add_original_audio(silent,source,out):
    cmd=[ffmpeg(),"-hide_banner","-loglevel","error","-y","-i",silent,"-i",source,
         "-map","0:v:0","-map","1:a:0?","-c:v","copy","-c:a","aac","-b:a","192k",
         "-af","aresample=async=1:first_pts=0","-shortest","-movflags","+faststart",out]
    p=subprocess.run(cmd,capture_output=True,text=True,timeout=900)
    if p.returncode or not os.path.exists(out) or os.path.getsize(out)==0:
        raise RuntimeError("Original audio jodne me samasya: "+(p.stderr or "FFmpeg error")[-1000:])

def process_video(upload,settings,progress):
    den,sharp,color,bright,cont,res,ratio,mode=settings
    suffix=Path(upload.name).suffix.lower() or ".mp4"
    with tempfile.TemporaryDirectory(prefix="naxcy_") as td:
        source=os.path.join(td,"source"+suffix); silent=os.path.join(td,"silent.mp4"); out=os.path.join(td,"naxcy.mp4")
        with open(source,"wb") as f: f.write(upload.getvalue())
        meta=video_info(source)
        if meta["w"]<1 or meta["h"]<1: raise ValueError("Video read nahi ho paya.")
        
        cap=cv2.VideoCapture(source)
        ok,first_frame=cap.read()
        if not ok: cap.release(); raise ValueError("Video me valid frame nahi mila.")
        
        ow,oh=target_size(first_frame.shape,first_frame.shape,res,ratio)
        
        cmd=[ffmpeg(),"-hide_banner","-loglevel","error","-y","-f","rawvideo","-pixel_format","bgr24",
             "-video_size",f"{ow}x{oh}","-framerate",str(meta["fps"]),"-i","-","-an","-c:v","libx264",
             "-preset","ultrafast","-crf","20","-pix_fmt","yuv420p","-movflags","+faststart",silent]
        
        logpath=os.path.join(td,"ffmpeg.log")
        start_time = time.time()
        
        with open(logpath,"wb") as log:
            writer=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=log)
            count=0
            
            # Multi-threading frame pre-fetching and processing loop
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = []
                # First frame process
                futures.append(executor.submit(process_single_frame, first_frame, den, sharp, color, bright, cont, ow, oh, mode))
                
                # Fetch all remaining frames immediately into thread pool
                while True:
                    ok, frame = cap.read()
                    if not ok: break
                    futures.append(executor.submit(process_single_frame, frame, den, sharp, color, bright, cont, ow, oh, mode))
                
                cap.release()
                
                try:
                    for future in futures:
                        proc_frame = future.result()
                        writer.stdin.write(np.ascontiguousarray(proc_frame).tobytes())
                        count += 1
                        
                        if meta["n"] > 0 and count % 2 == 0:
                            pct = min(count / meta["n"], 0.99)
                            elapsed = time.time() - start_time
                            eta = (elapsed / pct) - elapsed if pct > 0 else 0
                            progress.progress(pct, text=f"⚡ Processing: {int(pct*100)}% | Frames: {count}/{meta['n']} | Time Left: {int(eta)}s")
                            
                except Exception:
                    if writer.poll() is None: writer.kill(); writer.wait()
                    raise
                finally:
                    try:
                        if writer.stdin and not writer.stdin.closed: writer.stdin.close()
                    except Exception: pass
            
            writer.wait(timeout=900)
            
        if writer.returncode or not os.path.exists(silent) or os.path.getsize(silent)==0:
            raise RuntimeError("Video encode nahi hua: "+Path(logpath).read_text(errors="replace")[-1000:])
        
        add_original_audio(silent,source,out)
        progress.progress(1.0,text="✨ 100% Complete!")
        return Path(out).read_bytes(),ow,oh,count

st.sidebar.header("⚙️ NAXCY Settings")
media=st.sidebar.radio("Media type",["Image Enhancer","Video Enhancer"])
res=st.sidebar.selectbox("Output resolution",list(RES.keys()),index=4)
ratio=st.sidebar.selectbox("Aspect ratio",list(RATIOS.keys()),index=1)
mode=st.sidebar.radio("Framing mode",["Crop to fill","Pad (show entire image)"])
den=st.sidebar.slider("Noise / grain reduction",0,10,3)
sharp_pct=st.sidebar.slider("Sharpness intensity (%)",0,100,100,5)
color_pct=st.sidebar.slider("Color intensity (%)",0,100,100,5)
bright=st.sidebar.slider("Brightness",-50,50,0,5)
cont=st.sidebar.slider("Contrast",0.5,1.5,1.0,0.05)
settings=(den,sharp_pct/100,color_pct/100,bright,cont,res,ratio,mode)

if media=="Image Enhancer":
    upload=st.file_uploader("Apni Image upload kare",type=["jpg","jpeg","png","webp"])
    if upload:
        a,b=st.columns(2)
        with a: 
            st.subheader("Original")
            st.image(upload,use_container_width=True)
        with b:
            st.subheader("Enhanced Output")
            if st.button("✨ Enhance image",type="primary"):
                with st.spinner("Processing..."):
                    try:
                        out_bytes,w,h,mime,ext=process_image(upload,settings)
                        st.image(out_bytes,use_container_width=True)
                        st.success(f"Resolution: {w}x{h}")
                        st.download_button(label="💾 Download Image", data=out_bytes, file_name=f"enhanced_{upload.name}", mime=mime)
                    except Exception as e:
                        st.error(f"Error: {e}")

elif media=="Video Enhancer":
    upload=st.file_uploader("Apna Video upload kare",type=["mp4","mov","avi","mkv"])
