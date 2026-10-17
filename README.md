NAXCY AI Ultra Enhancer (Streamlit + Android-friendly)
What is included
Responsive Streamlit interface for mobile browsers.
Image resize/enhancement controls.
Video resizing and conventional sharpening/noise reduction through FFmpeg.
Optional audio stream is retained in the output.
Resolution choices: 720p, 1080p, 2K (1440p), 4K (2160p).
Ratio choices: original, 9:16, 16:9, 1:1, 4:3.
Deploy on Streamlit Community Cloud
Create a new GitHub repository and upload app.py, requirements.txt, and packages.txt.
In Streamlit Community Cloud, create an app from that repository and choose app.py.
Once deployed, open the URL on Android Chrome.
Chrome menu (⋮) -> Add to Home screen or Install app (wording varies).
Android APK wrapper (online app)
The APK is a WebView shell around the deployed web app. It needs internet to use the Streamlit server; it does not run the AI/FFmpeg processing locally.
Create a new Android Studio project using Empty Views Activity (Kotlin).
Add Internet permission in AndroidManifest.xml: <uses-permission android:name="android.permission.INTERNET" />
In the Activity layout, use a WebView and load your deployed Streamlit URL. Enable JavaScript and DOM storage. Handle file uploads with a WebChromeClient and onShowFileChooser for media upload.
Build > Build APK(s). For reliable file upload/download behavior, implement WebChromeClient file chooser and download listener.
A ready-to-build Android wrapper project is not bundled in this first starter because the final deployed URL must be inserted and upload/download behavior should be tested on your target device.
Important limitations
This starter uses FFmpeg and Pillow filters, not a trained AI super-resolution model. 2K/4K output means upscaled dimensions; it cannot guarantee recovered true detail.
Motion blur cannot be fully removed with these simple filters. The code does not add interpolated frames, which avoids introducing extra motion artifacts.
Processing time depends on source duration/resolution, server CPU/RAM, and encoding preset. 80–90 seconds in 1 minute is not guaranteed.
Streamlit Community Cloud may have resource, file-size, and execution limits. A dedicated GPU backend is needed for true AI upscaling and fast 4K processing.
