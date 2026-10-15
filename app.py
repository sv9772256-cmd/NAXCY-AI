import os, subprocess, tempfile
from pathlib import Path
import cv2
import numpy as np
import streamlit as st
import imageio_ffmpeg

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
        out=cv2.fastNlMeansDenoisingColored(out,None,n,n,7,21)
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

def ffmpeg():
    return imageio_ffmpeg.get_ffmpeg_exe()

def process_image(upload,settings):
    raw=np.frombuffer(upload.getvalue(),np.uint8)
    img=cv2.imdecode(raw,cv2.IMREAD_COLOR)
    if img is None: raise ValueError("इमेज पढ़ नहीं पाए। JPG, PNG या WEBP चुनें।")
    den,sharp,color,bright,cont,res,ratio,mode=settings
    img=enhance_frame(img,den,sharp,color,bright,cont)
    w,h=target_size(img.shape[1],img.shape[0],res,ratio)
    img=fit_frame(img,w,h,mode)
    ext=Path(upload.name).suffix.lower()
    if ext not in (".png",".webp",".jpg",".jpeg"): ext=".jpg"
    if ext==".png": params,mime=[cv2.IMWRITE_PNG_COMPRESSION,3],"image/png"
    elif ext==".webp": params,mime=[cv2.IMWRITE_WEBP_QUALITY,95],"image/webp"
    else: ext=".jpg"; params,mime=[cv2.IMWRITE_JPEG_QUALITY,95],"image/jpeg"
    ok,enc=cv2.imencode(ext,img,params)
    if not ok: raise RuntimeError("Enhanced image save नहीं हो पाई।")
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
        raise RuntimeError("Original audio जोड़ने में समस्या: "+(p.stderr or "FFmpeg error")[-1000:])

def process_video(upload,settings,progress):
    den,sharp,color,bright,cont,res,ratio,mode=settings
    suffix=Path(upload.name).suffix.lower() or ".mp4"
    with tempfile.TemporaryDirectory(prefix="naxcy_") as td:
        source=os.path.join(td,"source"+suffix); silent=os.path.join(td,"silent.mp4"); out=os.path.join(td,"naxcy.mp4")
        with open(source,"wb") as f: f.write(upload.getvalue())
        meta=video_info(source)
        if meta["w"]<1 or meta["h"]<1: raise ValueError("वीडियो पढ़ नहीं पाए।")
        cap=cv2.VideoCapture(source); ok,frame=cap.read()
        if not ok: cap.release(); raise ValueError("वीडियो में पढ़ने योग्य फ्रेम नहीं मिला।")
        frame=enhance_frame(frame,den,sharp,color,bright,cont)
        ow,oh=target_size(frame.shape[1],frame.shape[0],res,ratio); frame=fit_frame(frame,ow,oh,mode)
        cmd=[ffmpeg(),"-hide_banner","-loglevel","error","-y","-f","rawvideo","-pixel_format","bgr24",
             "-video_size",f"{ow}x{oh}","-framerate",str(meta["fps"]),"-i","-","-an","-c:v","libx264",
             "-preset","veryfast","-crf","18","-pix_fmt","yuv420p","-movflags","+faststart",silent]
        logpath=os.path.join(td,"ffmpeg.log")
        with open(logpath,"wb") as log:
            writer=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=log)
            count=0
            try:
                writer.stdin.write(np.ascontiguousarray(frame).tobytes()); count=1
                while True:
                    ok,frame=cap.read()
                    if not ok: break
                    frame=enhance_frame(frame,den,sharp,color,bright,cont)
                    frame=fit_frame(frame,ow,oh,mode)
                    writer.stdin.write(np.ascontiguousarray(frame).tobytes()); count+=1
                    if meta["n"]>0 and count%5==0:
                        progress.progress(min(count/meta["n"],.99),text=f"Frames: {count}/{meta['n']}")
                writer.stdin.close(); writer.wait(timeout=900)
            except Exception:
                if writer.poll() is None: writer.kill(); writer.wait()
                raise
            finally:
                cap.release()
                try:
                    if writer.stdin and not writer.stdin.closed: writer.stdin.close()
                except Exception: pass
        if writer.returncode or not os.path.exists(silent) or os.path.getsize(silent)==0:
            raise RuntimeError("वीडियो encode नहीं हुआ: "+Path(logpath).read_text(errors="replace")[-1000:])
        add_original_audio(silent,source,out)
        progress.progress(1.0,text="Complete")
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
st.info("यह stable OpenCV enhancement baseline है। 4K output dimensions बढ़ाता है, लेकिन असली नई detail या पूरी तरह blur/artifact removal की गारंटी नहीं देता।")

if media=="Image Enhancer":
    upload=st.file_uploader("अपनी इमेज अपलोड करें",type=["jpg","jpeg","png","webp"])
    if upload:
        a,b=st.columns(2)
        with a: st.subheader("Original"); st.image(upload,use_container_width=True)
        if st.button("✨ Enhance image",type="primary"):
            try:
                with st.spinner("Image processing..."):
                    data,w,h,mime,ext=process_image(upload,settings)
                with b: st.subheader("Enhanced"); st.image(data,use_container_width=True)
                st.success(f"Output: {w} × {h} px")
                st.download_button("⬇️ Download enhanced image",data=data,file_name="naxcy_enhanced"+ext,mime=mime,type="primary")
            except Exception as e: st.error(f"Image processing error: {e}")
else:
    upload=st.file_uploader("अपना वीडियो अपलोड करें",type=["mp4","mov","avi","mkv","webm"])
    if upload:
        st.video(upload); st.caption(f"File size: {upload.size/(1024*1024):.1f} MB")
        if upload.size>200*1024*1024: st.warning("बड़ी वीडियो पर Cloud timeout या memory limit आ सकती है।")
        if st.button("✨ Enhance video (keep original audio)",type="primary"):
            bar=st.progress(0.0,text="Starting...")
            try:
                data,w,h,n=process_video(upload,settings,bar)
                st.success(f"Output: {w} × {h} px | Frames: {n}. Original audio stream जोड़ी गई है यदि मौजूद थी।")
                st.video(data)
                st.download_button("⬇️ Download enhanced video",data=data,file_name="naxcy_enhanced.mp4",mime="video/mp4",type="primary")
            except Exception as e: st.error(f"Video processing error: {e}")

with st.expander("महत्वपूर्ण जानकारी"):
    st.write("मूल ऑडियो को AAC में दोबारा encode किया जाता है, इसलिए वह bit-for-bit identical नहीं है। Motion blur removal के लिए optical-flow deblur model शामिल नहीं है। लंबे 4K वीडियो के लिए पर्याप्त CPU/RAM और hosting time जरूरी है।")
