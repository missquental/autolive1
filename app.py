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
BUMPER_FILE_ID = "1ubnMo76yV8gKFe14yezxS86rN77ov6Bw"  # ID dari link Google Drive
BUMPER_VIDEO = "bumper.mp4"

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

def download_bumper():
    """Download bumper video dari Google Drive"""
    try:
        gdown.download(
            id=BUMPER_FILE_ID,
            output=os.path.join(VIDEO_DIR, BUMPER_VIDEO),
            quiet=False
        )
        return True
    except Exception as e:
        print(f"Error downloading bumper: {e}")
        return False

# ===============================
# AUTO PLAYLIST STREAM
# ===============================
def stream_playlist(video_dir, stream_key, is_shorts, log_queue, stop_flag):
    rtmp_url = f"rtmp://a.rtmp.youtube.com/live2/{stream_key}"
    scale = ["-vf", "scale=720:1280"] if is_shorts else []

    while not stop_flag.is_set():
        # Dapatkan daftar video utama
        main_videos = sorted([
            f for f in os.listdir(video_dir)
            if f.lower().endswith((".mp4", ".flv")) and f != BUMPER_VIDEO
        ])

        if not main_videos:
            log_queue.put("❌ Tidak ada video di folder")
            time.sleep(5)
            continue

        # Proses setiap video utama dengan bumper sebelumnya
        for video in main_videos:
            if stop_flag.is_set():
                break

            # 1. Putar video penyanding dulu
            bumper_path = os.path.join(video_dir, BUMPER_VIDEO)
            if os.path.exists(bumper_path):
                log_queue.put("🎬 Memutar video penyanding...")
                
                cmd_bumper = [
                    "ffmpeg",
                    "-re",
                    "-i", bumper_path,
                    "-c:v", "libx264",
                    "-preset", "veryfast",
                    "-b:v", "2500k",
                    "-maxrate", "2500k",
                    "-bufsize", "5000k",
                    "-g", "60",
                    "-keyint_min", "60",
                    "-c:a", "aac",
                    "-b:a", "128k",
                    "-f", "flv",
                    *scale,
                    rtmp_url
                ]

                log_queue.put("CMD Bumper: " + " ".join(cmd_bumper))

                process_bumper = subprocess.Popen(
                    cmd_bumper,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True
                )

                for line in process_bumper.stdout:
                    if stop_flag.is_set():
                        process_bumper.kill()
                        break
                    log_queue.put(line.strip())

                process_bumper.wait()
                log_queue.put("✅ Video penyanding selesai")
            else:
                log_queue.put("⏭️ Video penyanding tidak ditemukan, lewati...")

            # 2. Putar video utama
            if stop_flag.is_set():
                break

            video_path = os.path.join(video_dir, video)
            log_queue.put(f"▶️ Memutar: {video}")

            cmd = [
                "ffmpeg",
                "-re",
                "-i", video_path,
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-b:v", "2500k",
                "-maxrate", "2500k",
                "-bufsize", "5000k",
                "-g", "60",
                "-keyint_min", "60",
                "-c:a", "aac",
                "-b:a", "128k",
                "-f", "flv",
                *scale,
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
            
            # Tambahkan pesan subscribe setelah video utama
            log_queue.put("📢 Jangan Lupa Subscribe!")
            time.sleep(5)  # Jeda untuk melihat pesan

        log_queue.put("🔁 Playlist selesai, mengulang dari awal")

# ===============================
# STREAMLIT UI
# ===============================
st.set_page_config("Drive → Live YouTube", "📡", layout="wide")
st.title("📡 Google Drive → Live YouTube (Auto Playlist)")

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
# DOWNLOAD SECTION
# ===============================
st.subheader("📥 Download Video & Bumper")

col1, col2 = st.columns(2)

with col1:
    if st.button("📥 Download Video dari Google Drive"):
        with st.spinner("Mengunduh video..."):
            download_drive_folder()
        st.success("Download video selesai")

with col2:
    if st.button("📥 Download Video Bumper"):
        with st.spinner("Mengunduh bumper..."):
            if download_bumper():
                st.success("Download bumper berhasil")
            else:
                st.error("Gagal download bumper")

# ===============================
# VIDEO LIST
# ===============================
st.subheader("🎬 Video Playlist")

videos = sorted([
    f for f in os.listdir(VIDEO_DIR)
    if f.lower().endswith((".mp4", ".flv"))
])

if videos:
    st.write("**Videos:**")
    for video in videos:
        if video != BUMPER_VIDEO:
            st.write(f"• {video}")
    if BUMPER_VIDEO in videos:
        st.write(f"**Bumper:** {BUMPER_VIDEO}")
else:
    st.warning("Belum ada video")

# ===============================
# BUMPER INFO
# ===============================
st.subheader("🎬 Video Penyanding (Bumper)")
st.info("""
**Video penyanding akan diputar SEBELUM setiap video utama:**
`bumper.mp4` → `video1.mp4` → `bumper.mp4` → `video2.mp4` → ...

Video bumper diambil dari: https://drive.google.com/file/d/1ubnMo76yV8gKFe14yezxS86rN77ov6Bw/view?usp=sharing
""")

# ===============================
# STREAM SETTING
# ===============================
st.subheader("🔴 Live Setting")

stream_key = st.text_input("Stream Key YouTube", type="password")
is_shorts = st.checkbox("Mode Shorts (9:16)")

# ===============================
# CONTROL BUTTON
# ===============================
col1, col2 = st.columns(2)

with col1:
    if st.button("🚀 Mulai Auto Live"):
        if not stream_key:
            st.error("Stream Key wajib diisi")
        else:
            # Cek apakah bumper ada
            bumper_path = os.path.join(VIDEO_DIR, BUMPER_VIDEO)
            if not os.path.exists(bumper_path):
                st.warning("Video bumper belum didownload. Silakan download bumper terlebih dahulu.")
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

# ===============================
# PETUNJUK PENGGUNAAN
# ===============================
with st.expander("ℹ️ Cara Menggunakan"):
    st.markdown("""
    **Langkah penggunaan:**
    1. Klik "Download Video dari Google Drive" untuk mengambil video utama
    2. Klik "Download Video Bumper" untuk mengambil video penyanding
    3. Masukkan Stream Key YouTube
    4. Klik "Mulai Auto Live"

    **Urutan pemutaran:**
    ```
    bumper.mp4 → video1.mp4 → bumper.mp4 → video2.mp4 → bumper.mp4 → ...
    ```

    **Link bumper:** https://drive.google.com/file/d/1ubnMo76yV8gKFe14yezxS86rN77ov6Bw/view?usp=sharing
    """)
