import streamlit as st
import firebase_admin
from firebase_admin import credentials, db
import pandas as pd
import mysql.connector
from sqlalchemy import create_engine
from datetime import date, datetime, time
import plotly.graph_objs as go
import time
import io
import re
import pytz

# ------------ BAGIAN ATAS  ------------
firebase_config = dict(st.secrets["firebase"])
cred = credentials.Certificate(firebase_config)
FIREBASE_DATABASE_URL = st.secrets["firebase"]["database_url"]

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred, {
        'databaseURL': FIREBASE_DATABASE_URL
    })

ref_status = db.reference("/pompa/manual")
ref_otomatis = db.reference("/pompa/otomatis")

mysql_conf = st.secrets["mysql"]

conn = mysql.connector.connect(
    host=mysql_conf["host"],
    port=mysql_conf["port"],
    database=mysql_conf["database"],
    user=mysql_conf["user"],
    password=mysql_conf["password"]
)

def get_sqlalchemy_engine():
    return create_engine(
        f"mysql+pymysql://{mysql_conf['user']}:{mysql_conf['password']}@{mysql_conf['host']}:{mysql_conf['port']}/{mysql_conf['database']}"
    )

def get_mysql_data():
    engine = get_sqlalchemy_engine()
    df = pd.read_sql("SELECT * FROM sensor", engine)
    engine.dispose()
    return df

def get_notif_data():
    engine = get_sqlalchemy_engine()
    df = pd.read_sql("SELECT * FROM notif", engine)
    engine.dispose()
    return df

def refresh_data():
    st.session_state.last_refresh = time.time()
    st.rerun()
    
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

def get_latest_sensor_data():
    suhu = db.reference('/sensor/suhu').get()
    kelembaban = db.reference('/sensor/tanah').get()
    asap = db.reference('/sensor/asap').get()
    api = db.reference('/sensor/api').get()
    
    def norm_asap(val):
        if val is None:
            return "tidak"
        v = str(val).strip().lower()
        return v
    
    def norm_api(val):
        if val is None:
            return "tidak"
        v = str(val).strip().lower()
        if v == "iya":
            return "iya"
        elif v == "tidak":
            return "tidak"
        return "tidak"
    
    return {
        'suhu': int(suhu) if suhu and str(suhu).isdigit() else 0,
        'kelembaban_tanah': int(kelembaban) if kelembaban and str(kelembaban).isdigit() else 0,
        'asap': norm_asap(asap),
        'api': norm_api(api)
    }

st.markdown("""
    <style>
    .block-container {padding: 0.5rem !important;}
    .sensor-row {
        display: flex; justify-content: space-between; gap: 12px; margin-bottom: 10px; flex-wrap: wrap;}
    .sensor-box {
        flex: 0 0 48%; padding: 13px 6px; border-radius: 10px; color: black;
        font-size: 17px; text-align: center; margin-bottom: 5px;
        box-shadow: 0 2px 6px rgba(100,100,100,0.10);}
    .switch-row {
        display: flex; gap: 20px; margin-top: 18px; flex-wrap: wrap; justify-content: center; align-items: center;}
    .center-status-circle {
        display: flex; flex-direction: column; align-items: center; justify-content: center;
        margin: 0 8px;
    }
    .notif-bar {
        display: flex; flex-direction: row; gap: 16px; align-items: center; margin-bottom:10px;
    }
    .notif-left {flex:1;}
    .notif-right {flex:1; display:flex; flex-direction:row; justify-content:flex-end; gap:8px;}
    .time-input-container {
        display: flex;
        gap: 8px;
        align-items: center;
    }
    .time-input {
        width: 60px !important;
    }
    .button-row {
        display: flex;
        gap: 8px;
        margin-bottom: 10px;
    }
    @media (max-width: 600px) {
        .sensor-row {flex-direction: column; gap: 4px;}
        .sensor-box {flex: 1 1 100%; font-size: 15px; margin-bottom: 6px;}
        .switch-row {flex-direction: column;}
        .notif-bar {flex-direction:column;}
        .notif-right {justify-content:center;}
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h4 style='text-align: center;'>Data Sensor Terbaru</h4>", unsafe_allow_html=True)

data = get_latest_sensor_data()

notif_ref = db.reference('/notif')
pompa_status_ref = db.reference('/pompa/status')
notif_firebase = notif_ref.get() or {}
pompa_status = pompa_status_ref.get() or "off"
otomatis_status = st.session_state.otomatis
manual_status = st.session_state.manual

for key, val in [("last_notif_kebakaran", notif_firebase.get("kebakaran", "")),
                 ("last_notif_tanah", notif_firebase.get("tanah", "")),
                 ("last_pompa_status", pompa_status),
                 ("last_otomatis_status", otomatis_status),
                 ("last_manual_status", manual_status)]:
    if key not in st.session_state:
        st.session_state[key] = val

suhu = data['suhu']
asap = data['asap']
api_val = data['api']
kelembaban = data['kelembaban_tanah']

warna_suhu = "#0000FF" if suhu < 20 else "#008000" if suhu <= 25 else "#FEB200" if suhu <= 30 else "#FF3108" if suhu <= 35 else "#C21807"
warna_asap = "#D3D3D3" if asap == "tidak" else "#A9A9A9"
warna_api = "#F5F5DC" if api_val == "tidak" else "#C21807"
status_api = "Tidak" if api_val == "tidak" else "Iya"
warna_kelembaban = "#FEB200" if kelembaban < 60 else "#008000" if kelembaban <= 70 else "#0000FF"

st.markdown(f"""
    <div class="sensor-row">
        <div class="sensor-box" style="background-color:{warna_suhu};">
            Suhu<br><b>{suhu}°C</b>
        </div>
        <div class="sensor-box" style="background-color:{warna_asap};">
            Asap<br><b>{asap.capitalize()}</b>
        </div>
    </div>
    <div class="sensor-row">
        <div class="sensor-box" style="background-color:{warna_api};">
            Api<br><b>{status_api}</b>
        </div>
        <div class="sensor-box" style="background-color:{warna_kelembaban};">
            Kelembaban Tanah<br><b>{kelembaban}%</b>
        </div>
    </div>
""", unsafe_allow_html=True)

st.markdown('<div class="switch-row">', unsafe_allow_html=True)
col1, col2, col3, col4 = st.columns([2,2,1,1])
with col1:
    st.toggle(
        "Manual",
        value=st.session_state.manual,
        key="manual",
        on_change=handle_manual_toggle,
    )
with col2:
    st.toggle(
        "Otomatis",
        value=st.session_state.otomatis,
        key="otomatis",
        on_change=handle_otomatis_toggle,
    )
with col3:
    status_pompa_val = db.reference('/pompa/status').get() or "off"
    warna_status = "#44C01A" if status_pompa_val == "on" else "#C21807"
    text_status = "ON" if status_pompa_val == "on" else "OFF"
    st.markdown(f"""
    <div style="width:35px;height:35px;background-color:{warna_status};border-radius:50%;display:flex;flex-direction:column;align-items:center;justify-content:center;">
        <span style="color:white;font-size:15px;font-weight:bold;">{text_status}</span>
    </div>
    """, unsafe_allow_html=True)

# ... [Kode sebelumnya tetap sama sampai bagian bawah] ...

# ------------ BAGIAN BAWAH (Manual refresh) ------------
st.write("### Histori Notifikasi")
notif_df = get_notif_data()
notif_df = notif_df.sort_values(by=["tanggal", "jam"], ascending=False)
notif_df = notif_df.reset_index(drop=True)

# Modal Tambah Notifikasi
if "show_add_notif_modal" not in st.session_state:
    st.session_state.show_add_notif_modal = False

if st.session_state.show_add_notif_modal:
    with st.form("add_notif_form"):
        st.write("### Tambah Notifikasi")
        
        add_cols = st.columns([1,1,1])
        with add_cols[0]:
            add_tanggal = st.date_input("Tanggal", key="add_notif_tanggal")
        with add_cols[1]:
            st.markdown("<div class='time-input-container'><div>Jam:</div>", unsafe_allow_html=True)
            add_jam = st.selectbox("", list(range(24)), key="add_notif_jam", label_visibility="collapsed")
        with add_cols[2]:
            st.markdown("<div class='time-input-container'><div>Menit:</div>", unsafe_allow_html=True)
            add_menit = st.selectbox("", list(range(60)), key="add_notif_menit", label_visibility="collapsed")
        
        add_cols2 = st.columns([1,1,1])
        with add_cols2[0]:
            add_kebakaran = st.selectbox("Status Kebakaran", ["iya", "tidak", "mungkin"], key="add_notif_kebakaran")
        with add_cols2[1]:
            add_pompa = st.selectbox("Status Pompa", ["on", "off"], key="add_notif_pompa")
        with add_cols2[2]:
            add_tanah = st.selectbox("Status Tanah", ["kering", "basah", "normal"], key="add_notif_tanah")
        
        col_button = st.columns([4,1])
        with col_button[0]:
            submitted = st.form_submit_button("Tambah")
        with col_button[1]:
            if st.form_submit_button("Batal"):
                st.session_state.show_add_notif_modal = False
                st.experimental_rerun()
        
        if submitted:
            conn = mysql.connector.connect(**mysql_conf)
            cursor = conn.cursor()
            try:
                # Tidak perlu menyertakan no karena auto increment
                cursor.execute(
                    "INSERT INTO notif (tanggal, jam, kebakaran, pompa, tanah) VALUES (%s,%s,%s,%s,%s)",
                    (add_tanggal, f"{add_jam:02d}:{add_menit:02d}:00", add_kebakaran, add_pompa, add_tanah)
                )
                conn.commit()
                st.success("Notifikasi berhasil ditambahkan!")
                st.session_state.show_add_notif_modal = False
                refresh_data()
            except Exception as e:
                st.error(f"Gagal menambahkan notifikasi: {e}")
            finally:
                cursor.close()
                conn.close()

# Modal Edit Notifikasi
if "show_edit_notif_modal" not in st.session_state:
    st.session_state.show_edit_notif_modal = False
    st.session_state.edit_notif_no = 1

if st.session_state.show_edit_notif_modal:
    # Ambil data yang akan diedit
    conn = mysql.connector.connect(**mysql_conf)
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM notif WHERE no = %s", (st.session_state.edit_notif_no,))
    notif_to_edit = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if notif_to_edit:
        with st.form("edit_notif_form"):
            st.write("### Edit Notifikasi")
            
            # Tampilkan nomor sebagai informasi (readonly)
            st.text_input("No", value=notif_to_edit['no'], disabled=True)
            
            edit_cols = st.columns([1,1,1])
            with edit_cols[0]:
                edit_tanggal = st.date_input("Tanggal", value=notif_to_edit['tanggal'], key="edit_notif_tanggal")
            with edit_cols[1]:
                jam_parts = str(notif_to_edit['jam']).split(':')
                jam_value = int(jam_parts[0]) if len(jam_parts) > 0 else 0
                st.markdown("<div class='time-input-container'><div>Jam:</div>", unsafe_allow_html=True)
                edit_jam = st.selectbox("", list(range(24)), index=jam_value, key="edit_notif_jam", label_visibility="collapsed")
            with edit_cols[2]:
                menit_value = int(jam_parts[1]) if len(jam_parts) > 1 else 0
                st.markdown("<div class='time-input-container'><div>Menit:</div>", unsafe_allow_html=True)
                edit_menit = st.selectbox("", list(range(60)), index=menit_value, key="edit_notif_menit", label_visibility="collapsed")
            
            edit_cols2 = st.columns([1,1,1])
            with edit_cols2[0]:
                kebakaran_options = ["iya", "tidak", "mungkin"]
                kebakaran_index = kebakaran_options.index(notif_to_edit['kebakaran']) if notif_to_edit['kebakaran'] in kebakaran_options else 0
                edit_kebakaran = st.selectbox("Status Kebakaran", kebakaran_options, index=kebakaran_index, key="edit_notif_kebakaran")
            with edit_cols2[1]:
                edit_pompa = st.selectbox("Status Pompa", ["on", "off"], index=0 if notif_to_edit['pompa'] == "on" else 1, key="edit_notif_pompa")
            with edit_cols2[2]:
                tanah_options = ["kering", "basah", "normal"]
                tanah_index = tanah_options.index(notif_to_edit['tanah']) if notif_to_edit['tanah'] in tanah_options else 0
                edit_tanah = st.selectbox("Status Tanah", tanah_options, index=tanah_index, key="edit_notif_tanah")
            
            col_button = st.columns([4,1])
            with col_button[0]:
                submitted = st.form_submit_button("Simpan Perubahan")
            with col_button[1]:
                if st.form_submit_button("Batal"):
                    st.session_state.show_edit_notif_modal = False
                    st.experimental_rerun()
            
            if submitted:
                conn = mysql.connector.connect(**mysql_conf)
                cursor = conn.cursor()
                try:
                    cursor.execute(
                        "UPDATE notif SET tanggal=%s, jam=%s, kebakaran=%s, pompa=%s, tanah=%s WHERE no=%s",
                        (edit_tanggal, f"{edit_jam:02d}:{edit_menit:02d}:00", edit_kebakaran, edit_pompa, edit_tanah, notif_to_edit['no'])
                    )
                    conn.commit()
                    st.success("Notifikasi berhasil diupdate!")
                    st.session_state.show_edit_notif_modal = False
                    refresh_data()
                except Exception as e:
                    st.error(f"Gagal mengupdate notifikasi: {e}")
                finally:
                    cursor.close()
                    conn.close()
    else:
        st.warning(f"Notifikasi dengan no {st.session_state.edit_notif_no} tidak ditemukan")
        st.session_state.show_edit_notif_modal = False
        st.experimental_rerun()

# Modal Hapus Notifikasi
if "show_delete_notif_modal" not in st.session_state:
    st.session_state.show_delete_notif_modal = False
    st.session_state.delete_notif_no = 1

if st.session_state.show_delete_notif_modal:
    with st.form("delete_notif_form"):
        st.write("### Hapus Notifikasi")
        delete_no = st.number_input("No", min_value=1, max_value=len(notif_df), step=1, key="delete_notif_no_input", value=st.session_state.delete_notif_no)
        
        col_button = st.columns([4,1])
        with col_button[0]:
            submitted = st.form_submit_button("Hapus")
        with col_button[1]:
            if st.form_submit_button("Batal"):
                st.session_state.show_delete_notif_modal = False
                st.experimental_rerun()
        
        if submitted:
            conn = mysql.connector.connect(**mysql_conf)
            cursor = conn.cursor()
            try:
                cursor.execute("DELETE FROM notif WHERE no=%s", (delete_no,))
                conn.commit()
                st.success("Notifikasi berhasil dihapus!")
                st.session_state.show_delete_notif_modal = False
                refresh_data()
            except Exception as e:
                st.error(f"Gagal menghapus notifikasi: {e}")
            finally:
                cursor.close()
                conn.close()

# Tombol Aksi untuk Tabel Notifikasi
notif_col_buttons = st.columns([1,1,1,1,1])
with notif_col_buttons[0]:
    if not notif_df.empty:
        output2 = io.BytesIO()
        notif_df.to_excel(output2, index=False, engine='xlsxwriter')
        st.download_button(label="Print", data=output2.getvalue(), 
                         file_name=f"History Notifikasi per {date.today().strftime('%Y-%m-%d')}.xlsx", 
                         mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
                         on_click=lambda: st.success("Download History Notifikasi berhasil!"))
with notif_col_buttons[1]:
    if st.button("Tambah", key="tambah_notif"):
        st.session_state.show_add_notif_modal = True
with notif_col_buttons[2]:
    if st.button("Ubah", key="ubah_notif"):
        st.session_state.show_edit_notif_modal = True
        st.session_state.edit_notif_no = 1
with notif_col_buttons[3]:
    if st.button("Hapus", key="hapus_notif"):
        st.session_state.show_delete_notif_modal = True
        st.session_state.delete_notif_no = 1

# Tampilkan tabel notifikasi
notif_df['No'] = notif_df.index + 1  # Tambahkan nomor urut
notif_df['jam'] = notif_df['jam'].apply(extract_hhmm)  # Format jam

# Urutan kolom untuk ditampilkan
columns_to_show = ["No", "tanggal", "jam", "kebakaran", "pompa", "tanah"]

if not notif_df.empty:
    st.dataframe(notif_df[columns_to_show], hide_index=True, use_container_width=True)
else:
    st.info("Tidak ada data notifikasi yang tersedia")
