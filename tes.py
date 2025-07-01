import streamlit as st
import json
import requests
from google.oauth2 import service_account
import google.auth.transport.requests
import firebase_admin
from firebase_admin import credentials, db

# --- SETUP
st.set_page_config(page_title="Notifikasi FCM", layout="centered")
st.title("Dashboard Kirim Notifikasi FCM")

# --- Secrets
firebase = st.secrets["firebase"]
FIREBASE_CONFIG = {
    "apiKey": firebase["FIREBASE_API_KEY"],
    "authDomain": firebase["FIREBASE_AUTH_DOMAIN"],
    "projectId": firebase["FIREBASE_PROJECT_ID"],
    "messagingSenderId": firebase["FIREBASE_MESSAGING_SENDER_ID"],
    "appId": firebase["FIREBASE_APP_ID"]
}
PROJECT_ID = firebase["FIREBASE_PROJECT_ID"]
VAPID_KEY = firebase["FIREBASE_VAPID_KEY"]
DATABASE_URL = firebase["FIREBASE_DATABASE_URL"]

# --- Inisialisasi Firebase Admin
if not firebase_admin._apps:
    cred = credentials.Certificate({
        "type": firebase["type"],
        "project_id": firebase["project_id"],
        "private_key_id": firebase["private_key_id"],
        "private_key": firebase["private_key"],
        "client_email": firebase["client_email"],
        "client_id": firebase["client_id"],
        "auth_uri": firebase["auth_uri"],
        "token_uri": firebase["token_uri"],
        "auth_provider_x509_cert_url": firebase["auth_provider_x509_cert_url"],
        "client_x509_cert_url": firebase["client_x509_cert_url"]
    })
    firebase_admin.initialize_app(cred, {
        'databaseURL': DATABASE_URL
    })

# --- Fungsi kirim FCM
def send_fcm_v1(token, title, body):
    credentials_obj = service_account.Credentials.from_service_account_info(
        cred._service_account_info,
        scopes=["https://www.googleapis.com/auth/firebase.messaging"]
    )
    request = google.auth.transport.requests.Request()
    credentials_obj.refresh(request)
    access_token = credentials_obj.token

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; UTF-8",
    }
    data = {
        "message": {
            "token": token,
            "notification": {
                "title": title,
                "body": body
            }
        }
    }
    url = f"https://fcm.googleapis.com/v1/projects/{PROJECT_ID}/messages:send"
    return requests.post(url, headers=headers, data=json.dumps(data))

# --- Tampilkan link aktivasi
st.markdown("### Aktifkan notifikasi dari perangkat:")
st.markdown("[Klik di sini untuk mengaktifkan notifikasi](https://wildan-git78.github.io/my-repo/)", unsafe_allow_html=True)

# --- Ambil token dari database
st.markdown("### Device yang sudah aktif:")

tokens_ref = db.reference("tokens")
tokens_data = tokens_ref.get()

if tokens_data:
    token_map = {}
    for key, val in tokens_data.items():
        name = val.get("device_name", f"Device-{key}")[:30]
        token = val.get("token")
        if token:
            token_map[name] = token
            st.write(f"- **{name}**: {token[:15]}...")

    with st.form("send_notif"):
        st.write("### Kirim Notifikasi:")
        selected_devices = st.multiselect("Pilih device", list(token_map.keys()), default=list(token_map.keys()))
        notif_title = st.text_input("Judul Notifikasi", "Pesan dari Streamlit")
        notif_body = st.text_input("Isi Notifikasi", "Halo! Ini pesan untuk perangkatmu.")
        send_btn = st.form_submit_button("Kirim")

        if send_btn:
            for name in selected_devices:
                resp = send_fcm_v1(token_map[name], notif_title, notif_body)
                if resp.status_code == 200:
                    st.success(f"✅ Berhasil dikirim ke {name}")
                else:
                    st.error(f"❌ Gagal ke {name}: {resp.text}")
else:
    st.info("Belum ada token yang terdaftar di database.")
