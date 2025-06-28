import streamlit as st
import json
import os
import requests
from google.oauth2 import service_account
import google.auth.transport.requests
from streamlit_js_eval import streamlit_js_eval

st.set_page_config(page_title="Web Push Notifikasi FCM", layout="centered")
st.title("Web Push Notification FCM (Format Full TOML)")

# 1. Ambil SEMUA variabel dari [firebase] secrets
firebase = st.secrets["firebase"]

FIREBASE_CONFIG = {
    "apiKey": firebase["FIREBASE_API_KEY"],
    "authDomain": firebase["FIREBASE_AUTH_DOMAIN"],
    "projectId": firebase["FIREBASE_PROJECT_ID"],
    "messagingSenderId": firebase["FIREBASE_MESSAGING_SENDER_ID"],
    "appId": firebase["FIREBASE_APP_ID"]
}
VAPID_KEY = firebase["FIREBASE_VAPID_KEY"]
PROJECT_ID = firebase["FIREBASE_PROJECT_ID"]

# 2. Bangun dict service account info dari secrets TOML
service_account_info = {
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
}

def send_fcm_v1(token, title, body):
    credentials = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=["https://www.googleapis.com/auth/firebase.messaging"],
    )
    request = google.auth.transport.requests.Request()
    credentials.refresh(request)
    access_token = credentials.token

    headers = {
        "Authorization": "Bearer " + access_token,
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
    resp = requests.post(url, headers=headers, data=json.dumps(data))
    return resp

# 3. Simpan token device hanya di server, jangan pernah di repo
TOKENS_FILE = "tokens.json"

def save_token(name, token):
    tokens = {}
    if os.path.exists(TOKENS_FILE):
        with open(TOKENS_FILE, "r") as f:
            tokens = json.load(f)
    tokens[name] = token
    with open(TOKENS_FILE, "w") as f:
        json.dump(tokens, f)

def load_tokens():
    if os.path.exists(TOKENS_FILE):
        with open(TOKENS_FILE, "r") as f:
            return json.load(f)
    return {}

# 4. Komponen HTML/JS frontend untuk register token device (hanya pakai public info dari secrets)
html_code = f"""
<link rel="manifest" href="/manifest.json">
<script src="https://www.gstatic.com/firebasejs/10.12.2/firebase-app-compat.js"></script>
<script src="https://www.gstatic.com/firebasejs/10.12.2/firebase-messaging-compat.js"></script>
<button onclick="getTokenFCM()" id="notif-btn">Izinkan Notifikasi</button>
<p id="notif-status"></p>
<script>
const firebaseConfig = {{
    apiKey: "{FIREBASE_CONFIG['apiKey']}",
    authDomain: "{FIREBASE_CONFIG['authDomain']}",
    projectId: "{FIREBASE_CONFIG['projectId']}",
    messagingSenderId: "{FIREBASE_CONFIG['messagingSenderId']}",
    appId: "{FIREBASE_CONFIG['appId']}"
}};
if (!firebase.apps.length) firebase.initializeApp(firebaseConfig);
const messaging = firebase.messaging();

async function getTokenFCM() {{
    if ('serviceWorker' in navigator) {{
        let reg = await navigator.serviceWorker.register('/firebase-messaging-sw.js');
        messaging.useServiceWorker(reg);
        try {{
            let token = await messaging.getToken({{ vapidKey: '{VAPID_KEY}' }});
            document.getElementById("notif-status").innerText = "Token berhasil diambil dan dikirim ke backend!";
            localStorage.setItem("fcm_token", token);
        }} catch(e) {{
            document.getElementById("notif-status").innerText = "Error: " + e;
            localStorage.setItem("fcm_token", "");
        }}
    }}
}}
messaging.onMessage(function(payload) {{
    alert("Push notification diterima: " + payload.notification.title + "\\n" + payload.notification.body);
}});
</script>
"""
st.components.v1.html(html_code, height=170)

# 5. Ambil token dari localStorage via streamlit-js-eval
token = streamlit_js_eval(js_expressions="localStorage.getItem('fcm_token')", key="fcm_token")

if token and token != "null" and len(token) > 10:
    with st.form("save_token_form"):
        st.success("Token berhasil diterima di backend!")
        device_name = st.text_input("Nama device (misal: HP/Laptop):", "")
        submitted = st.form_submit_button("Simpan Token Device")
        if submitted and device_name.strip():
            save_token(device_name.strip(), token)
            st.success(f"Token {device_name.strip()} berhasil disimpan!")

tokens = load_tokens()
if tokens:
    st.write("### Device yang sudah siap menerima notifikasi:")
    for name, tkn in tokens.items():
        st.write(f"- **{name}**: {tkn[:15]}...")

    # Form kirim notifikasi
    with st.form("send_notif"):
        device_choices = list(tokens.keys()) + ["SEMUA"]
        selected = st.multiselect("Pilih device", device_choices, default="SEMUA")
        notif_title = st.text_input("Judul Notifikasi", "Pesan dari Streamlit")
        notif_body = st.text_input("Isi Notifikasi", "Halo! Ini pesan untuk device-mu.")
        send = st.form_submit_button("Kirim Notifikasi")
        if send and selected:
            if "SEMUA" in selected:
                targets = tokens.values()
            else:
                targets = [tokens[d] for d in selected]
            for tkn in targets:
                resp = send_fcm_v1(tkn, notif_title, notif_body)
                if resp.status_code == 200:
                    st.success("Notifikasi berhasil dikirim ke device.")
                else:
                    st.error(f"Error {resp.status_code}: {resp.text}")
else:
    st.info("Belum ada device yang siap menerima notifikasi. Silakan akses dari HP/laptop dan izinkan notifikasi.")

st.markdown("""
---
**Tips:**
- Semua variabel rahasia harus di secrets [firebase] (format field TOML, bukan JSON).
- Tidak ada file rahasia di repo! Kode hanya baca rahasia dari st.secrets.
- File `firebase-messaging-sw.js`, `manifest.json`, `icon.png` wajib di root/public repo.
- Website **HARUS diakses via HTTPS**.
- Jangan upload `tokens.json` ke repo, hanya untuk penyimpanan sementara di server.
""")
