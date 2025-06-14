import streamlit as st
import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime
import time

# FIREBASE SETUP
if not firebase_admin._apps:
    cred = credentials.Certificate("C:/wildan/web/cek/projectmmg.json")
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://projectmmg-faeb5-default-rtdb.asia-southeast1.firebasedatabase.app/'
    })

ref_status = db.reference("/pompa/manual")
ref_otomatis = db.reference("/pompa/otomatis")

if "manual" not in st.session_state:
    st.session_state.manual = False
if "otomatis" not in st.session_state:
    st.session_state.otomatis = False

def handle_manual_toggle():
    st.session_state.otomatis = False
    if st.session_state.manual:
        ref_status.set("on")
        ref_otomatis.set("off")
    else:
        ref_status.set("off")

def handle_otomatis_toggle():
    st.session_state.manual = False
    if st.session_state.otomatis:
        ref_status.set("off")
        ref_otomatis.set("on")
    else:
        ref_otomatis.set("off")

st.title("Kontrol Buzzer ESP32 via Firebase")

col1, col2 = st.columns(2)
with col1:
    st.toggle("Mode Manual", value=st.session_state.manual,
              key="manual", on_change=handle_manual_toggle)
with col2:
    st.toggle("Mode Otomatis", value=st.session_state.otomatis,
              key="otomatis", on_change=handle_otomatis_toggle)

st.markdown("---")
st.subheader("Setel Alarm Otomatis (Format 24 Jam)")
alarm_hour = st.number_input("Jam (0 - 23)", min_value=0, max_value=23, value=10)
alarm_minute = st.number_input("Menit (0 - 59)", min_value=0, max_value=59, value=0)
start_alarm = st.button("Mulai Alarm Otomatis")

# ==== PUSH NOTIFIKASI BROWSER ====
st.subheader("Aktifkan Push Notifikasi Browser (Chrome/Edge/Firefox)")
st.info("Klik tombol di bawah dan pilih Izinkan pada pop-up browser agar notifikasi bisa dikirim ke komputer/HP kamu.")

st.components.v1.html("""
<button onclick="aktifkanNotif()">Aktifkan Notifikasi Browser</button>
<script>
async function aktifkanNotif() {
    if (!('Notification' in window)) {
        alert('Browser tidak support notifikasi.');
        return;
    }
    let izin = await Notification.requestPermission();
    if (izin === "granted") {
        new Notification("Notifikasi aktif!", {
            body: "Kamu akan menerima notifikasi dari website ini.",
            icon: ""
        });
    } else if (izin === "denied") {
        alert("Kamu menolak notifikasi. Aktifkan dari setting browser jika ingin menerima.");
    }
}
</script>
""", height=100)

# ==== NOTIFIKASI ALARM (BROWSER LOCAL) ====
def trigger_local_notification(jam, menit):
    st.components.v1.html(f"""
    <script>
    if (Notification.permission === "granted") {{
        new Notification("Alarm Pompa Aktif!", {{
            body: "Pompa menyala otomatis pada {jam:02d}:{menit:02d}",
            icon: ""
        }});
    }}
    </script>
    """, height=0)

if start_alarm:
    st.success(f"Alarm akan menyala pada pukul {alarm_hour:02d}:{alarm_minute:02d}")
    with st.spinner("Menunggu waktu alarm..."):
        while True:
            now = datetime.now()
            if now.hour == alarm_hour and now.minute == alarm_minute:
                st.success("Waktu alarm tercapai! Menyalakan buzzer...")
                ref_status.set("on")
                trigger_local_notification(alarm_hour, alarm_minute)  # ===> Panggil notif browser
                time.sleep(60)
                ref_status.set("off")
                st.success("Buzzer dimatikan setelah 1 menit.")
                break
            time.sleep(1)
