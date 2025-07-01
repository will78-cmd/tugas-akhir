import streamlit as st
import json
import os
import requests
from google.oauth2 import service_account
import google.auth.transport.requests
from fastapi import FastAPI, Request
from streamlit.web.server.websocket_headers import _get_websocket_headers
from streamlit.runtime.scriptrunner import get_script_run_ctx
from streamlit.server.server import Server

st.set_page_config(page_title="Web Push Notifikasi FCM", layout="centered")
st.title("Dashboard Kirim Notifikasi FCM")

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

# ⬇️ Tampilkan link ke GitHub Pages untuk aktifkan notifikasi
st.markdown("### Aktifkan notifikasi:")
st.markdown("[Klik untuk aktifkan notifikasi di perangkat](https://wildan-git78.github.io/my-repo/)", unsafe_allow_html=True)

tokens = load_tokens()
if tokens:
    st.write("### Device yang siap menerima notifikasi:")
    for name, tkn in tokens.items():
        st.write(f"- **{name}**: {tkn[:15]}...")

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
                    st.success("✅ Notifikasi berhasil dikirim.")
                else:
                    st.error(f"❌ Error {resp.status_code}: {resp.text}")
else:
    st.info("Belum ada device yang mendaftar notifikasi.")

# ⬇️ Tambah route handler untuk POST dari GitHub Pages
def register_token_receiver(app: FastAPI):
    @app.post("/save-token")
    async def save_token_api(request: Request):
        data = await request.json()
        token = data.get("token")
        device_name = data.get("device_name", "unknown")
        if token:
            save_token(device_name, token)
            return {"status": "success", "message": "Token saved"}
        return {"status": "error", "message": "No token provided"}

# Integrasi FastAPI dengan Streamlit
register_token_receiver(Server.get_current()._api_app)
