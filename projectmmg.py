import streamlit as st
import firebase_admin
from firebase_admin import credentials, db
import time

if not firebase_admin._apps:
    cred = credentials.Certificate({
        "type": st.secrets["firebase"]["type"],
        "project_id": st.secrets["firebase"]["project_id"],
        "private_key_id": st.secrets["firebase"]["private_key_id"],
        "private_key": st.secrets["firebase"]["private_key"],
        "client_email": st.secrets["firebase"]["client_email"],
        "client_id": st.secrets["firebase"]["client_id"],
        "auth_uri": st.secrets["firebase"]["auth_uri"],
        "token_uri": st.secrets["firebase"]["token_uri"],
        "auth_provider_x509_cert_url": st.secrets["firebase"]["auth_provider_x509_cert_url"],
        "client_x509_cert_url": st.secrets["firebase"]["client_x509_cert_url"]
    })
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://tugas-akhir-8ec00-default-rtdb.asia-southeast1.firebasedatabase.app/'
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

# ==== NOTIFIKASI BROWSER ====
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

# ==== TOMBOL KIRIM NOTIFIKASI ALARM BUZZER ====
def trigger_local_notification():
    st.components.v1.html(f"""
    <script>
    if (Notification.permission === "granted") {{
        new Notification("Alarm Pompa Aktif!", {{
            body: "Buzzer menyala otomatis karena tombol diklik.",
            icon: ""
        }});
    }}
    </script>
    """, height=0)

st.markdown("---")
st.subheader("Kirim Alarm Buzzer + Notifikasi")

if st.button("Kirim Notifikasi Alarm & Nyalakan Buzzer"):
    st.success("Buzzer dinyalakan & notifikasi dikirim!")
    ref_status.set("on")
    trigger_local_notification()
    time.sleep(60)  # Tunggu 1 menit (blocking, tapi hanya pada klik ini)
    ref_status.set("off")
    st.success("Buzzer dimatikan setelah 1 menit.")
