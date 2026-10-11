import streamlit as st
import cv2
from PIL import Image
import numpy as np
import tempfile
import os

# 1. PC और Android दोनों के लिए पेज सेटअप (रिस्पॉन्सिव लेआउट)
st.set_page_config(
    page_title="Naxcy AI - Media Enhancer",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. कस्टम CSS और UNIQUE AI लोगो (नियॉन थीम) - एरर यहाँ फिक्स कर दिया गया है
st.markdown("""
    <style>
    .logo-container {
        display: flex;
        align-items: center;
        justify-content: center;
        background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
        padding: 20px;
        border-radius: 15px;
        margin-bottom: 25px;
        border: 2px solid #00ffcc;
        box-shadow: 0 0 15px #00ffcc;
    }
    .logo-text {
        font-family: 'Courier New', monospace;
        font-size: 38px;
        font-weight: bold;
        color: #00ffcc;
        text-shadow: 0 0 10px #00ffcc, 0 0 20px #00ffcc;
        letter-spacing: 3px;
    }
    .logo-subtext {
        color: #ffffff;
        font-size: 14px;
        margin-left: 10px;
        font-style: italic;
    }
    /* मोबाइल स्क्रीन के लिए कस्टमाइजेशन */
    @media (max-width: 768px) {
        .logo-text { font-size: 28px; }
        .logo-subtext { display: block; margin-left: 0; }
    }
    </style>
    
    <div class="logo-container">
        <span class="logo-text">⚡ NAXCY AI ⚡</span>
        <span class="logo-subtext">| Next-Gen Media Studio</span>
    </div>
""", unsafe_allow_html=True)

# आस्पेक्ट रेशियो लॉक रखकर रीसाइज करने का फंक्शन
def resize_maintain_aspect(image, target_height):
    h, w = image.shape[:2]
    aspect_ratio = w / h
    target_width = int(target_height * aspect_ratio)
    
    # अगर चौड़ाई विषम (odd) आती है तो वीडियो के लिए उसे सम (even) करना जरूरी है
    if target_width % 2 != 0:
        target_width += 1
        
    return cv2.resize(image, (target_width, target_height), interpolation=cv2.INTER_CUBIC)

# इमेज/वीडियो को उल्टा (Flip) करने का फंक्शन
def flip_media(image, flip_mode):
    if flip_mode == "हॉरिजॉन्टल (Left-Right)":
        return cv2.flip(image, 1)
    elif flip_mode == "वर्टिकल (Upside-Down)":
        return cv2.flip(image, 0)
    elif flip_mode == "180 डिग्री रोटेट":
        return cv2.flip(image, -1)
    return image

# साइडबार ऑप्शन्स
st.sidebar.header("⚙️ कंट्रोल पैनल")
media_type = st.sidebar.radio("मीडिया का प्रकार चुनें:", ["फोटो (Image)", "वीडियो (Video)"])

quality_option = st.sidebar.selectbox(
    "क्वालिटी एन्हांसमेंट चुनें:",
    ["ओरिजिनल क्वालिटी", "2K (High Definition)", "4K (Ultra High Definition)"]
)

flip_option = st.sidebar.selectbox(
    "मीडिया को उल्टा/रोटेट करें:",
    ["नॉर्मल (सीधा)", "हॉरिजॉन्टल (Left-Right)", "वर्टिकल (Upside-Down)", "180 डिग्री रोटेट"]
)

# टारगेट हाइट सेट करना
target_height = None
if quality_option == "2K (High Definition)":
    target_height = 1440
elif quality_option == "4K (Ultra High Definition)":
    target_height = 2160

# --- फोटो प्रोसेसिंग सेक्शन ---
if media_type == "फोटो (Image)":
    st.subheader("📸 फोटो एन्हांसर और रोटेटर")
    uploaded_file = st.file_uploader("अपनी फोटो अपलोड करें", type=["jpg", "jpeg", "png"])
    
    if uploaded_file is not None:
        file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, 1)
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        st.write("⏳ प्रोसेसिंग जारी है...")
        
        # 1. पहले फ्लिप/उल्टा करें
        processed_img = flip_media(img_rgb, flip_option)
        
        # 2. फिर रेशियो लॉक के साथ साइज बढ़ाएं
        if target_height:
            processed_img = resize_maintain_aspect(processed_img, target_height)
            
        st.success("सफलतापूर्वक पूरा हुआ!")
        
        # स्क्रीन पर प्रीव्यू दिखाएं
        st.image(processed_img, caption="प्रोसेस्ड इमेज", use_container_width=True)
        
        # डाउनलोड बटन
        result_pil = Image.fromarray(processed_img)
        tmp_download_path = "naxcy_ai_enhanced.png"
        result_pil.save(tmp_download_path)
        
        with open(tmp_download_path, "rb") as file:
            st.download_button(
                label="📥 एन्हांस्ड फोटो डाउनलोड करें",
                data=file,
                file_name="naxcy_ai_enhanced.png",
                mime="image/png"
            )

# --- वीडियो प्रोसेसिंग सेक्शन ---
else:
    st.subheader("🎥 वीडियो एन्हांसर और रोटेटर")
    uploaded_file = st.file_uploader("अपना वीडियो अपलोड करें", type=["mp4", "mov", "avi"])
    
    if uploaded_file is not None:
        # वीडियो को अस्थाई फाइल में सेव करना
        tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        tfile.write(uploaded_file.read())
        tfile.close()
        
        cap = cv2.VideoCapture(tfile.name)
        
        # ऑरिजनल वीडियो की जानकारी निकालना
        fps = cap.get(cv2.CAP_PROP_FPS)
        orig_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        orig_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # नया साइज तय करना आस्पेक्ट रेशियो के अनुसार
        if target_height:
            new_height = target_height
            aspect_ratio = orig_width / orig_height
            new_width = int(new_height * aspect_ratio)
            if new_width % 2 != 0: new_width += 1
        else:
            new_width, new_height = orig_width, orig_height
            
        # आउटपुट फाइल पाथ
        output_path = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4').name
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (new_width, new_height))
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        frame_idx = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
                
            # 1. उल्टा/फ्लिप करें
            frame = flip_media(frame, flip_option)
            
            # 2. आस्पेक्ट रेशियो लॉक रखकर रीसाइज करें
            if target_height:
                frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
                
            out.write(frame)
            
            frame_idx += 1
            progress = int((frame_idx / total_frames) * 100)
            progress_bar.progress(progress)
            status_text.text(f"प्रोग्रेस: {progress}% फ्रेम प्रोसेसिंग जारी है...")
            
        cap.release()
        out.release()
        os.unlink(tfile.name) # अस्थाई फाइल डिलीट करना
        
        st.success(f"वीडियो सफलतापूर्वक एन्हांस हो गया! नया साइज: {new_width}x{new_height}")
        
        # वीडियो डाउनलोड बटन
        with open(output_path, "rb") as file:
            st.download_button(
                label="📥 एन्हांस्ड वीडियो डाउनलोड करें",
                data=file,
                file_name="naxcy_ai_enhanced_video.mp4",
                mime="video/mp4"
            )


On Sun, Oct 11, 2026, 10:39 PM vipin prajapati <kvmvipin27996@gmail.com> wrote:
import streamlit as st
import cv2
from PIL import Image
import numpy as np
import tempfile
import os

# 1. PC और Android दोनों के लिए पेज सेटअप (रिस्पॉन्सिव लेआउट)
st.set_page_config(
    page_title="Naxcy AI - Media Enhancer",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. कस्टम CSS और UNIQUE AI लोगो (नियॉन थीम) - एरर यहाँ फिक्स कर दिया गया है
st.markdown("""
    <style>
    .logo-container {
        display: flex;
        align-items: center;
        justify-content: center;
        background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
        padding: 20px;
        border-radius: 15px;
        margin-bottom: 25px;
        border: 2px solid #00ffcc;
        box-shadow: 0 0 15px #00ffcc;
    }
    .logo-text {
        font-family: 'Courier New', monospace;
        font-size: 38px;
        font-weight: bold;
        color: #00ffcc;
        text-shadow: 0 0 10px #00ffcc, 0 0 20px #00ffcc;
        letter-spacing: 3px;
    }
    .logo-subtext {
        color: #ffffff;
        font-size: 14px;
        margin-left: 10px;
        font-style: italic;
    }
    /* मोबाइल स्क्रीन के लिए कस्टमाइजेशन */
    @media (max-width: 768px) {
        .logo-text { font-size: 28px; }
        .logo-subtext { display: block; margin-left: 0; }
    }
    </style>
    
    <div class="logo-container">
        <span class="logo-text">⚡ NAXCY AI ⚡</span>
        <span class="logo-subtext">| Next-Gen Media Studio</span>
    </div>
""", unsafe_allow_html=True)

# आस्पेक्ट रेशियो लॉक रखकर रीसाइज करने का फंक्शन
def resize_maintain_aspect(image, target_height):
    h, w = image.shape[:2]
    aspect_ratio = w / h
    target_width = int(target_height * aspect_ratio)
    
    # अगर चौड़ाई विषम (odd) आती है तो वीडियो के लिए उसे सम (even) करना जरूरी है
    if target_width % 2 != 0:
        target_width += 1
        
    return cv2.resize(image, (target_width, target_height), interpolation=cv2.INTER_CUBIC)

# इमेज/वीडियो को उल्टा (Flip) करने का फंक्शन
def flip_media(image, flip_mode):
    if flip_mode == "हॉरिजॉन्टल (Left-Right)":
        return cv2.flip(image, 1)
    elif flip_mode == "वर्टिकल (Upside-Down)":
        return cv2.flip(image, 0)
    elif flip_mode == "180 डिग्री रोटेट":
        return cv2.flip(image, -1)
    return image

# साइडबार ऑप्शन्स
st.sidebar.header("⚙️ कंट्रोल पैनल")
media_type = st.sidebar.radio("मीडिया का प्रकार चुनें:", ["फोटो (Image)", "वीडियो (Video)"])

quality_option = st.sidebar.selectbox(
    "क्वालिटी एन्हांसमेंट चुनें:",
    ["ओरिजिनल क्वालिटी", "2K (High Definition)", "4K (Ultra High Definition)"]
)

flip_option = st.sidebar.selectbox(
    "मीडिया को उल्टा/रोटेट करें:",
    ["नॉर्मल (सीधा)", "हॉरिजॉन्टल (Left-Right)", "वर्टिकल (Upside-Down)", "180 डिग्री रोटेट"]
)

# टारगेट हाइट सेट करना
target_height = None
if quality_option == "2K (High Definition)":
    target_height = 1440
elif quality_option == "4K (Ultra High Definition)":
    target_height = 2160

# --- फोटो प्रोसेसिंग सेक्शन ---
if media_type == "फोटो (Image)":
    st.subheader("📸 फोटो एन्हांसर और रोटेटर")
    uploaded_file = st.file_uploader("अपनी फोटो अपलोड करें", type=["jpg", "jpeg", "png"])
    
    if uploaded_file is not None:
        file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, 1)
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        st.write("⏳ प्रोसेसिंग जारी है...")
        
        # 1. पहले फ्लिप/उल्टा करें
        processed_img = flip_media(img_rgb, flip_option)
        
        # 2. फिर रेशियो लॉक के साथ साइज बढ़ाएं
        if target_height:
            processed_img = resize_maintain_aspect(processed_img, target_height)
            
        st.success("सफलतापूर्वक पूरा हुआ!")
        
        # स्क्रीन पर प्रीव्यू दिखाएं
        st.image(processed_img, caption="प्रोसेस्ड इमेज", use_container_width=True)
        
        # डाउनलोड बटन
        result_pil = Image.fromarray(processed_img)
        tmp_download_path = "naxcy_ai_enhanced.png"
        result_pil.save(tmp_download_path)
        
        with open(tmp_download_path, "rb") as file:
            st.download_button(
                label="📥 एन्हांस्ड फोटो डाउनलोड करें",
                data=file,
                file_name="naxcy_ai_enhanced.png",
                mime="image/png"
            )

# --- वीडियो प्रोसेसिंग सेक्शन ---
else:
    st.subheader("🎥 वीडियो एन्हांसर और रोटेटर")
    uploaded_file = st.file_uploader("अपना वीडियो अपलोड करें", type=["mp4", "mov", "avi"])
    
    if uploaded_file is not None:
        # वीडियो को अस्थाई फाइल में सेव करना
        tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        tfile.write(uploaded_file.read())
        tfile.close()
        
        cap = cv2.VideoCapture(tfile.name)
        
        # ऑरिजनल वीडियो की जानकारी निकालना
        fps = cap.get(cv2.CAP_PROP_FPS)
        orig_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        orig_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # नया साइज तय करना आस्पेक्ट रेशियो के अनुसार
        if target_height:
            new_height = target_height
            aspect_ratio = orig_width / orig_height
            new_width = int(new_height * aspect_ratio)
            if new_width % 2 != 0: new_width += 1
        else:
            new_width, new_height = orig_width, orig_height
            
        # आउटपुट फाइल पाथ
        output_path = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4').name
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (new_width, new_height))
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        frame_idx = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
                
            # 1. उल्टा/फ्लिप करें
            frame = flip_media(frame, flip_option)
            
            # 2. आस्पेक्ट रेशियो लॉक रखकर रीसाइज करें
            if target_height:
                frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
                
            out.write(frame)
            
            frame_idx += 1
            progress = int((frame_idx / total_frames) * 100)
            progress_bar.progress(progress)
            status_text.text(f"प्रोग्रेस: {progress}% फ्रेम प्रोसेसिंग जारी है...")
            
        cap.release()
        out.release()
        os.unlink(tfile.name) # अस्थाई फाइल डिलीट करना
        
        st.success(f"वीडियो सफलतापूर्वक एन्हांस हो गया! नया साइज: {new_width}x{new_height}")
        
        # वीडियो डाउनलोड बटन
        with open(output_path, "rb") as file:
            st.download_button(
                label="📥 एन्हांस्ड वीडियो डाउनलोड करें",
                data=file,
                file_name="naxcy_ai_enhanced_video.mp4",
                mime="video/mp4"
            )


On Sun, Oct 11, 2026, 10:34 PM vipin prajapati <kvmvipin27996@gmail.com> wrote:
import streamlit as st
import cv2
from PIL import Image
import numpy as np
import tempfile
import os

# 1. PC और Android दोनों के लिए पेज सेटअप (रिस्पॉन्सिव लेआउट)
st.set_page_config(
    page_title="Naxcy AI - Media Enhancer",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. कस्टम CSS और UNIQUE AI लोगो (नियॉन थीम)
st.markdown("""
    <style>
    .logo-container {
        display: flex;
        align-items: center;
        justify-content: center;
        background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
        padding: 20px;
        border-radius: 15px;
        margin-bottom: 25px;
        border: 2px solid #00ffcc;
        box-shadow: 0 0 15px #00ffcc;
    }
    .logo-text {
        font-family: 'Courier New', monospace;
        font-size: 38px;
        font-weight: bold;
        color: #00ffcc;
        text-shadow: 0 0 10px #00ffcc, 0 0 20px #00ffcc;
        letter-spacing: 3px;
    }
    .logo-subtext {
        color: #ffffff;
        font-size: 14px;
        margin-left: 10px;
        font-style: italic;
    }
    /* मोबाइल स्क्रीन के लिए कस्टमाइजेशन */
    @media (max-width: 768px) {
        .logo-text { font-size: 28px; }
        .logo-subtext { display: block; margin-left: 0; }
    }
    </style>
    
    <div class="logo-container">
        <span class="logo-text">⚡ NAXCY AI ⚡</span>
        <span class="logo-subtext">| Next-Gen Media Studio</span>
    </div>
""", unsafe_style_allowed=True)

# आस्पेक्ट रेशियो लॉक रखकर रीसाइज करने का फंक्शन
def resize_maintain_aspect(image, target_height):
    h, w = image.shape[:2]
    aspect_ratio = w / h
    target_width = int(target_height * aspect_ratio)
    
    # अगर चौड़ाई विषम (odd) आती है तो वीडियो के लिए उसे सम (even) करना जरूरी है
    if target_width % 2 != 0:
        target_width += 1
        
    return cv2.resize(image, (target_width, target_height), interpolation=cv2.INTER_CUBIC)

# इमेज/वीडियो को उल्टा (Flip) करने का फंक्शन
def flip_media(image, flip_mode):
    if flip_mode == "हॉरिजॉन्टल (Left-Right)":
        return cv2.flip(image, 1)
    elif flip_mode == "वर्टिकल (Upside-Down)":
        return cv2.flip(image, 0)
    elif flip_mode == "180 डिग्री रोटेट":
        return cv2.flip(image, -1)
    return image

# साइडबार ऑप्शन्स
st.sidebar.header("⚙️ कंट्रोल पैनल")
media_type = st.sidebar.radio("मीडिया का प्रकार चुनें:", ["फोटो (Image)", "वीडियो (Video)"])

quality_option = st.sidebar.selectbox(
    "क्वालिटी एन्हांसमेंट चुनें:",
    ["ओरिजिनल क्वालिटी", "2K (High Definition)", "4K (Ultra High Definition)"]
)

flip_option = st.sidebar.selectbox(
    "मीडिया को उल्टा/रोटेट करें:",
    ["नॉर्मल (सीधा)", "हॉरिजॉन्टल (Left-Right)", "वर्टिकल (Upside-Down)", "180 डिग्री रोटेट"]
)

# टारगेट हाइट सेट करना
target_height = None
if quality_option == "2K (High Definition)":
    target_height = 1440
elif quality_option == "4K (Ultra High Definition)":
    target_height = 2160

# --- फोटो प्रोसेसिंग सेक्शन ---
if media_type == "फोटो (Image)":
    st.subheader("📸 फोटो एन्हांसर और रोटेटर")
    uploaded_file = st.file_uploader("अपनी फोटो अपलोड करें", type=["jpg", "jpeg", "png"])
    
    if uploaded_file is not None:
        file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, 1)
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        st.write("⏳ प्रोसेसिंग जारी है...")
        
        # 1. पहले फ्लिप/उल्टा करें
        processed_img = flip_media(img_rgb, flip_option)
        
        # 2. फिर रेशियो लॉक के साथ साइज बढ़ाएं
        if target_height:
            processed_img = resize_maintain_aspect(processed_img, target_height)
            
        st.success(f"सफलतापूर्वक पूरा हुआ! नया साइज: {processed_img.shape[1]}x{processed_img.shape[0]}")
        
        # स्क्रीन पर प्रीव्यू दिखाएं
        st.image(processed_img, caption="प्रोसेस्ड इमेज", use_container_width=True)
        
        # डाउनलोड बटन
        result_pil = Image.fromarray(processed_img)
        tmp_download_path = "naxcy_ai_enhanced.png"
        result_pil.save(tmp_download_path)
        
        with open(tmp_download_path, "rb") as file:
            st.download_button(
                label="📥 एन्हांस्ड फोटो डाउनलोड करें",
                data=file,
                file_name="naxcy_ai_enhanced.png",
                mime="image/png"
            )

# --- वीडियो प्रोसेसिंग सेक्शन ---
else:
    st.subheader("🎥 वीडियो एन्हांसर और रोटेटर")
    uploaded_file = st.file_uploader("अपना वीडियो अपलोड करें", type=["mp4", "mov", "avi"])
    
    if uploaded_file is not None:
        # वीडियो को अस्थाई फाइल में सेव करना
        tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        tfile.write(uploaded_file.read())
        tfile.close()
        
        cap = cv2.VideoCapture(tfile.name)
        
        # ऑरिजनल वीडियो की जानकारी निकालना
        fps = cap.get(cv2.CAP_PROP_FPS)
        orig_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        orig_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # नया साइज तय करना आस्पेक्ट रेशियो के अनुसार
        if target_height:
            new_height = target_height
            aspect_ratio = orig_width / orig_height
            new_width = int(new_height * aspect_ratio)
            if new_width % 2 != 0: new_width += 1
        else:
            new_width, new_height = orig_width, orig_height
            
        # आउटपुट फाइल पाथ
        output_path = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4').name
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (new_width, new_height))
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        frame_idx = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
                
            # 1. उल्टा/फ्लिप करें
            frame = flip_media(frame, flip_option)
            
            # 2. आस्पेक्ट रेशियो लॉक रखकर रीसाइज करें
            if target_height:
                frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
                
            out.write(frame)
            
            frame_idx += 1
            progress = int((frame_idx / total_frames) * 100)
            progress_bar.progress(progress)
            status_text.text(f"प्रोग्रेस: {progress}% फ्रेम प्रोसेसिंग जारी है...")
            
        cap.release()
        out.release()
        os.unlink(tfile.name) # अस्थाई फाइल डिलीट करना
        
        st.success(f"वीडियो सफलतापूर्वक एन्हांस हो गया! नया साइज: {new_width}x{new_height}")
        
        # वीडियो डाउनलोड बटन
        with open(output_path, "rb") as file:
            st.download_button(
                label="📥 एन्हांस्ड वीडियो डाउनलोड करें",
                data=file,
                file_name="naxcy_ai_enhanced_video.mp4",
                mime="video/mp4"
            )
