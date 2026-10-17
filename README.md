# NAXCY AI — Free Enhancement build

## Included
- `app.py`: Streamlit image/video enhancer with classic filters and optional EDSR x4 AI super-resolution.
- `requirements.txt`: Python dependencies.
- `packages.txt`: FFmpeg system package for Streamlit Community Cloud.

## Install in your GitHub repository
1. Download and unzip this package.
2. Open your `NAXCY-AI` GitHub repository.
3. Replace the existing root `app.py` with the included `app.py`.
4. Add or replace `requirements.txt` and `packages.txt` in the same root folder.
5. Commit the changes. Wait for Streamlit Cloud to rebuild, then test a small image first.

## Important limitations
- AI mode downloads an open-source EDSR x4 model on first use. The download needs outbound internet access and enough disk space.
- AI video processing runs frame by frame. Free CPU hosting may be slow or run out of memory/time, especially for 2K/4K or long videos.
- Classic mode uses standard filters; it does not reconstruct missing details like an AI model.
- The app tries to preserve original audio when processing video. Some unusual codecs/files may still fail.
- Test with a copy of your current project first.
- 
