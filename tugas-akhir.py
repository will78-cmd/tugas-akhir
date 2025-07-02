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

# ------------ BAGIAN BAWAH - TABEL NOTIFIKASI ------------
st.write("### Histori Notifikasi")

# Tombol Aksi untuk Tabel Notifikasi - DITAMBAHKAN DI SINI
notif_action_cols = st.columns([1,1,1,1,5])  # 5 kolom kosong untuk spacing
with notif_action_cols[0]:
    if st.button("🔄 Refresh Notifikasi", key="refresh_notif"):
        refresh_data()
with notif_action_cols[1]:
    if st.button("➕ Tambah Notifikasi", key="tambah_notif"):
        st.session_state.show_add_notif_modal = True
with notif_action_cols[2]:
    if st.button("✏️ Edit Notifikasi", key="edit_notif"):
        st.session_state.show_edit_notif_modal = True
with notif_action_cols[3]:
    if st.button("🗑️ Hapus Notifikasi", key="hapus_notif"):
        st.session_state.show_delete_notif_modal = True

# Modal Tambah Notifikasi
if "show_add_notif_modal" not in st.session_state:
    st.session_state.show_add_notif_modal = False

if st.session_state.show_add_notif_modal:
    with st.form("add_notif_form"):
        st.write("### Form Tambah Notifikasi")
        
        cols = st.columns(3)
        with cols[0]:
            tanggal = st.date_input("Tanggal", key="notif_tanggal")
        with cols[1]:
            jam = st.number_input("Jam", min_value=0, max_value=23, value=12, key="notif_jam")
        with cols[2]:
            menit = st.number_input("Menit", min_value=0, max_value=59, value=0, key="notif_menit")
        
        cols2 = st.columns(3)
        with cols2[0]:
            kebakaran = st.selectbox("Status Kebakaran", ["tidak", "iya", "mungkin"], key="notif_kebakaran")
        with cols2[1]:
            pompa = st.selectbox("Status Pompa", ["off", "on"], key="notif_pompa")
        with cols2[2]:
            tanah = st.selectbox("Status Tanah", ["normal", "kering", "basah"], key="notif_tanah")
        
        submit_cols = st.columns([4,1])
        with submit_cols[0]:
            if st.form_submit_button("Simpan Notifikasi"):
                conn = mysql.connector.connect(**mysql_conf)
                cursor = conn.cursor()
                try:
                    cursor.execute(
                        "INSERT INTO notif (tanggal, jam, kebakaran, pompa, tanah) VALUES (%s, %s, %s, %s, %s)",
                        (tanggal, f"{jam:02d}:{menit:02d}:00", kebakaran, pompa, tanah)
                    )
                    conn.commit()
                    st.success("Notifikasi berhasil ditambahkan!")
                    st.session_state.show_add_notif_modal = False
                    refresh_data()
                except Exception as e:
                    st.error(f"Gagal menambahkan: {str(e)}")
                finally:
                    cursor.close()
                    conn.close()
        with submit_cols[1]:
            if st.form_submit_button("Batal"):
                st.session_state.show_add_notif_modal = False
                st.experimental_rerun()

# Modal Edit Notifikasi
if "show_edit_notif_modal" not in st.session_state:
    st.session_state.show_edit_notif_modal = False
    st.session_state.edit_notif_id = None

if st.session_state.show_edit_notif_modal:
    # Ambil data notifikasi untuk diedit
    notif_df = get_notif_data()
    notif_list = notif_df.to_dict('records')
    
    # Pilih notifikasi yang akan diedit
    selected_idx = st.selectbox(
        "Pilih Notifikasi yang akan diedit",
        range(len(notif_list)),
        format_func=lambda x: f"Notifikasi #{notif_list[x]['no']} - {notif_list[x]['tanggal']} {notif_list[x]['jam']}"
    )
    
    if st.button("Muat Data untuk Edit"):
        st.session_state.edit_notif_id = notif_list[selected_idx]['no']
    
    if st.session_state.edit_notif_id:
        # Ambil data dari database
        conn = mysql.connector.connect(**mysql_conf)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM notif WHERE no = %s", (st.session_state.edit_notif_id,))
        notif_data = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if notif_data:
            with st.form("edit_notif_form"):
                st.write(f"### Edit Notifikasi #{notif_data['no']}")
                
                # Parse waktu
                jam, menit, _ = map(int, str(notif_data['jam']).split(':'))
                
                cols = st.columns(3)
                with cols[0]:
                    edit_tanggal = st.date_input("Tanggal", value=notif_data['tanggal'], key="edit_notif_tanggal")
                with cols[1]:
                    edit_jam = st.number_input("Jam", min_value=0, max_value=23, value=jam, key="edit_notif_jam")
                with cols[2]:
                    edit_menit = st.number_input("Menit", min_value=0, max_value=59, value=menit, key="edit_notif_menit")
                
                cols2 = st.columns(3)
                with cols2[0]:
                    edit_kebakaran = st.selectbox(
                        "Status Kebakaran", 
                        ["tidak", "iya", "mungkin"],
                        index=["tidak", "iya", "mungkin"].index(notif_data['kebakaran']),
                        key="edit_notif_kebakaran"
                    )
                with cols2[1]:
                    edit_pompa = st.selectbox(
                        "Status Pompa", 
                        ["off", "on"],
                        index=["off", "on"].index(notif_data['pompa']),
                        key="edit_notif_pompa"
                    )
                with cols2[2]:
                    edit_tanah = st.selectbox(
                        "Status Tanah", 
                        ["normal", "kering", "basah"],
                        index=["normal", "kering", "basah"].index(notif_data['tanah']),
                        key="edit_notif_tanah"
                    )
                
                submit_cols = st.columns([4,1])
                with submit_cols[0]:
                    if st.form_submit_button("Update Notifikasi"):
                        conn = mysql.connector.connect(**mysql_conf)
                        cursor = conn.cursor()
                        try:
                            cursor.execute(
                                """UPDATE notif SET 
                                    tanggal = %s, 
                                    jam = %s, 
                                    kebakaran = %s, 
                                    pompa = %s, 
                                    tanah = %s 
                                WHERE no = %s""",
                                (
                                    edit_tanggal,
                                    f"{edit_jam:02d}:{edit_menit:02d}:00",
                                    edit_kebakaran,
                                    edit_pompa,
                                    edit_tanah,
                                    st.session_state.edit_notif_id
                                )
                            )
                            conn.commit()
                            st.success("Notifikasi berhasil diupdate!")
                            st.session_state.show_edit_notif_modal = False
                            refresh_data()
                        except Exception as e:
                            st.error(f"Gagal mengupdate: {str(e)}")
                        finally:
                            cursor.close()
                            conn.close()
                with submit_cols[1]:
                    if st.form_submit_button("Batal"):
                        st.session_state.show_edit_notif_modal = False
                        st.experimental_rerun()

# Modal Hapus Notifikasi
if "show_delete_notif_modal" not in st.session_state:
    st.session_state.show_delete_notif_modal = False
    st.session_state.delete_notif_id = None

if st.session_state.show_delete_notif_modal:
    # Ambil data notifikasi untuk dihapus
    notif_df = get_notif_data()
    notif_list = notif_df.to_dict('records')
    
    with st.form("delete_notif_form"):
        st.write("### Hapus Notifikasi")
        
        selected_idx = st.selectbox(
            "Pilih Notifikasi yang akan dihapus",
            range(len(notif_list)),
            format_func=lambda x: f"Notifikasi #{notif_list[x]['no']} - {notif_list[x]['tanggal']} {notif_list[x]['jam']}"
        )
        
        submit_cols = st.columns([4,1])
        with submit_cols[0]:
            if st.form_submit_button("Konfirmasi Hapus"):
                conn = mysql.connector.connect(**mysql_conf)
                cursor = conn.cursor()
                try:
                    cursor.execute(
                        "DELETE FROM notif WHERE no = %s",
                        (notif_list[selected_idx]['no'],)
                    )
                    conn.commit()
                    st.success("Notifikasi berhasil dihapus!")
                    st.session_state.show_delete_notif_modal = False
                    refresh_data()
                except Exception as e:
                    st.error(f"Gagal menghapus: {str(e)}")
                finally:
                    cursor.close()
                    conn.close()
        with submit_cols[1]:
            if st.form_submit_button("Batal"):
                st.session_state.show_delete_notif_modal = False
                st.experimental_rerun()

# Tampilkan Tabel Notifikasi
notif_df = get_notif_data()
if not notif_df.empty:
    # Format kolom jam
    notif_df['jam'] = notif_df['jam'].apply(lambda x: str(x)[:8] if x else '')
    
    # Tampilkan dengan kolom yang diinginkan
    st.dataframe(
        notif_df[['no', 'tanggal', 'jam', 'kebakaran', 'pompa', 'tanah']],
        column_config={
            "no": "ID",
            "tanggal": "Tanggal",
            "jam": "Jam",
            "kebakaran": "Kebakaran",
            "pompa": "Pompa",
            "tanah": "Tanah"
        },
        hide_index=True,
        use_container_width=True
    )
else:
    st.info("Tidak ada data notifikasi yang tersedia")
