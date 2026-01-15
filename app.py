import streamlit as st
import gdown
import os
import subprocess
import threading
import queue
import time
from pathlib import Path
import streamlit.components.v1 as components

# ===============================
# KONFIGURASI
# ===============================
DRIVE_FOLDER_URL = "https://drive.google.com/drive/folders/1d7fpbrOI9q9Yl6w99-yZGNMB30XNyugf"
VIDEO_DIR = "videos"

Path(VIDEO_DIR).mkdir(parents=True, exist_ok=True)

# ===============================
# DOWNLOAD GOOGLE DRIVE
# ===============================
def download_drive_folder():
    gdown.download_folder(
        url=DRIVE_FOLDER_URL,
        output=VIDEO_DIR,
        quiet=False,
        use_cookies=False
    )

# ===============================
# AUTO PLAYLIST + EFEK
# ===============================
def stream_playlist(video_dir, stream_key, is_shorts, log_queue, stop_flag):
    rtmp_url = f"rtmp://a.rtmp.youtube.com/live2/{stream_key}"

    # Filter efek (ringan, aman realtime)
    if is_shorts:
        vf_filter = (
            "scale=720:1280,"
            "fade=t=in:st=0:d=0.5,"
            "fade=t=out:st=2:d=0.5,"
            "zoompan=z='min(zoom+0.0006,1.03)':d=1,"
            "eq=contrast=1.03:brightness=0.01:saturation=1.02,"
            "noise=alls=4:allf=t,"
            "rotate=0.003*sin(2*PI*t)"
        )
    else:
        vf_filter = (
            "fade=t=in:st=0:d=0.5,"
            "fade=t=out:st=2:d=0.5,"
            "zoompan=z='min(zoom+0.0006,1.03)':d=1,"
            "eq=contrast=1.03:brightness=0.01:saturation=1.02,"
            "noise=alls=4:allf=t,"
            "rotate=0.003*sin(2*PI*t)"
        )

    while not stop_flag.is_set():
        videos = sorted([
            f for f in os.listdir(video_dir)
            if f.lower().endswith((".mp4", ".flv"))
        ])

        if not videos:
            log_queue.put("❌ Tidak ada video di folder")
            time.sleep(5)
            continue

        for video in videos:
            if stop_flag.is_set():
                break

            video_path = os.path.join(video_dir, video)
            log_queue.put(f"🎬 Memutar: {video}")

            cmd = [
                "ffmpeg",
                "-re",
                "-i", video_path,
                "-vf", vf_filter,
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-profile:v", "high",
                "-pix_fmt", "yuv420p",
                "-b:v", "3000k",
                "-maxrate", "3000k",
                "-bufsize", "6000k",
                "-g", "60",
                "-keyint_min", "60",
                "-c:a", "aac",
                "-b:a", "128k",
                "-ar", "44100",
                "-f", "flv",
                rtmp_url
            ]

            log_queue.put("CMD: " + " ".join(cmd))

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )

            for line in process.stdout:
                if stop_flag.is_set():
                    process.kill()
                    break
                log_queue.put(line.strip())

            process.wait()
            log_queue.put(f"✅ Selesai: {video}")

        log_queue.put("🔁 Playlist selesai, ulang dari awal")

# ===============================
# STREAMLIT UI
# ===============================
st.set_page_config("Drive → Live YouTube", "📡", layout="wide")
st.title("📡 Google Drive → Live YouTube (Auto Playlist + Efek)")

# ===============================
# IKLAN OPSIONAL
# ===============================
if st.checkbox("Tampilkan Iklan", True):
    components.html(
        """
        <div style="padding:15px;background:#f0f2f6;border-radius:10px;text-align:center">
        <script type='text/javascript'
        src='//pl26562103.profitableratecpm.com/28/f9/95/28f9954a1d5bbf4924abe123c76a68d2.js'>
        </script>
        <p style="color:#888">Slot Iklan</p>
        </div>
        """,
        height=250
    )

# ===============================
# SESSION STATE
# ===============================
if "log_queue" not in st.session_state:
    st.session_state.log_queue = queue.Queue()

if "logs" not in st.session_state:
    st.session_state.logs = []

if "stop_flag" not in st.session_state:
    st.session_state.stop_flag = threading.Event()

# ===============================
# DOWNLOAD
# ===============================
st.subheader("📥 Download Video")

if st.button("Download dari Google Drive"):
    with st.spinner("Mengunduh..."):
        download_drive_folder()
    st.success("Download selesai")

# ===============================
# VIDEO LIST
# ===============================
st.subheader("🎬 Playlist Video")

videos = sorted([
    f for f in os.listdir(VIDEO_DIR)
    if f.lower().endswith((".mp4", ".flv"))
])

if videos:
    st.write(videos)
else:
    st.warning("Belum ada video")

# ===============================
# STREAM SETTING
# ===============================
st.subheader("🔴 Live Setting")

stream_key = st.text_input("Stream Key YouTube", type="password")
is_shorts = st.checkbox("Mode Shorts (9:16 / 720x1280)")

# ===============================
# CONTROL BUTTON
# ===============================
col1, col2 = st.columns(2)

with col1:
    if st.button("🚀 Mulai Auto Live"):
        if not stream_key:
            st.error("Stream Key wajib diisi")
        else:
            st.session_state.stop_flag.clear()
            threading.Thread(
                target=stream_playlist,
                args=(
                    VIDEO_DIR,
                    stream_key,
                    is_shorts,
                    st.session_state.log_queue,
                    st.session_state.stop_flag
                ),
                daemon=True
            ).start()
            st.success("Auto playlist live dimulai")

with col2:
    if st.button("🛑 Stop Live"):
        st.session_state.stop_flag.set()
        os.system("pkill ffmpeg")
        st.warning("Live dihentikan")

# ===============================
# LOG OUTPUT
# ===============================
log_box = st.empty()

while not st.session_state.log_queue.empty():
    st.session_state.logs.append(
        st.session_state.log_queue.get()
    )

log_box.text("\n".join(st.session_state.logs[-20:]))
