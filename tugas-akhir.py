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

# ------------ BAGIAN ATAS ------------
firebase_config = dict(st.secrets["firebase"])
cred = credentials.Certificate(firebase_config)
FIREBASE_DATABASE_URL = st.secrets["firebase"]["database_url"]

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred, {
        'databaseURL': FIREBASE_DATABASE_URL
    })

# Listener untuk sensor tanah
def listen_soil_moisture():
    def callback(event):
        if event.data == "ideal":
            send_browser_notification("Kelembaban Tanah Ideal", "Kelembaban Tanah Anda Sudah Ideal")
    db.reference('/sensor/tanah').listen(callback)

listen_soil_moisture()

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
    @media (max-width: 600px) {
        .sensor-row {flex-direction: column; gap: 4px;}
        .sensor-box {flex: 1 1 100%; font-size: 15px; margin-bottom: 6px;}
        .switch-row {flex-direction: column;}
        .notif-bar {flex-direction:column;}
        .notif-right {justify-content:center;}
    }
    </style>
""", unsafe_allow_html=True)

st.components.v1.html("""
<script>
if ('Notification' in window && Notification.permission !== "granted") {
    Notification.requestPermission();
}
</script>
""", height=0)

st.markdown("<h4 style='text-align: center;'>Data Sensor Terbaru</h4>", unsafe_allow_html=True)

data = get_latest_sensor_data()

def send_browser_notification(title, message):
    st.components.v1.html(f"""
    <script>
    if (Notification.permission === "granted") {{
        var notif = new Notification("{title}", {{
            body: "{message}",
            icon: "",
            requireInteraction: true
        }});
    }}
    </script>
    """, height=0)

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

if notif_firebase.get("kebakaran") != st.session_state['last_notif_kebakaran']:
    val = notif_firebase.get("kebakaran")
    if val == "iya":
        send_browser_notification("Kebakaran!", "Terjadi kebakaran di lahan")
    elif val == "mungkin":
        send_browser_notification("Potensi Kebakaran", "Terdapat potensi kebakaran di lahan")
    st.session_state['last_notif_kebakaran'] = val

if notif_firebase.get("tanah") != st.session_state['last_notif_tanah']:
    val = notif_firebase.get("tanah")
    if val == "kering":
        send_browser_notification("Tanah Kering", "Tanah terlalu kering, segera lakukan irigasi pada lahan")
    elif val == "basah":
        send_browser_notification("Tanah Basah", "Tanah terlalu basah, segera lakukan drainase pada lahan")
    st.session_state['last_notif_tanah'] = val

if otomatis_status and notif_firebase.get("kebakaran") == "iya" and pompa_status == "off":
    key = "notif_otomatis_error"
    if not st.session_state.get(key, False):
        send_browser_notification("Masalah Sistem Otomatis", "Terjadi masalah saat menghidupkan pompa dalam mode otomatis, hidupkan pompa menggunakan mode manual")
        st.session_state[key] = True
else:
    st.session_state["notif_otomatis_error"] = False

if manual_status and notif_firebase.get("kebakaran") == "iya" and pompa_status == "off":
    key = "notif_manual_error"
    if not st.session_state.get(key, False):
        send_browser_notification("Pompa Tidak Bisa Menyala", "Tidak bisa menghidupkan pompa, segera lakukan penanganan kebakaran pada lahan")
        st.session_state[key] = True
else:
    st.session_state["notif_manual_error"] = False

if 'api_counter' not in st.session_state:
    st.session_state.api_counter = 0
if 'last_api_check' not in st.session_state:
    st.session_state.last_api_check = time.time()

is_kebakaran = notif_firebase.get("kebakaran") == "iya"
status_pompa_on = pompa_status == "on"
sensor_api_aktif = data['api'] == "iya"

if is_kebakaran and status_pompa_on and sensor_api_aktif:
    now = time.time()
    if now - st.session_state.last_api_check > 3:
        latest_api = db.reference('/sensor/api').get()
        if str(latest_api).strip().lower() == "iya":
            send_browser_notification("Masalah pada Pompa", "Terdapat masalah pada pompa, segera lakukan penanganan")
        st.session_state.last_api_check = now
else:
    st.session_state.last_api_check = time.time()

if is_kebakaran and not otomatis_status and not manual_status:
    if not st.session_state.get('notif_pompa_off', False):
        send_browser_notification("Kebakaran: Pompa Mati", "Terjadi kebakaran di lahan, hidupkan pompa untuk memadamkan api")
        st.session_state['notif_pompa_off'] = True
else:
    st.session_state['notif_pompa_off'] = False

if "last_kebakaran_teratasi" not in st.session_state:
    st.session_state.last_kebakaran_teratasi = False

is_pompa_was_on = (st.session_state.get('last_pompa_status', 'off') == "on")
kebakaran_now = notif_firebase.get("kebakaran")
api_now = data.get("api", "tidak")

if (is_pompa_was_on and
    kebakaran_now == "tidak" and
    api_now == "tidak" and
    st.session_state.last_kebakaran_teratasi is False):
    send_browser_notification(
        "Kebakaran Teratasi",
        "Kebakaran teratasi, api berhasil dipadamkan"
    )
    st.session_state.last_kebakaran_teratasi = True
elif kebakaran_now == "iya" or api_now == "iya":
    st.session_state.last_kebakaran_teratasi = False

st.session_state.last_pompa_status = pompa_status

if "sensor_fault_notif_sent" not in st.session_state:
    st.session_state.sensor_fault_notif_sent = False

sensor_error = False
sensor_cek = {
    'api': data.get('api', None),
    'asap': data.get('asap', None),
    'suhu': data.get('suhu', None),
    'tanah': data.get('kelembaban_tanah', None)
}
for k, v in sensor_cek.items():
    if v is None or str(v).strip() == "0":
        sensor_error = True

if sensor_error and not st.session_state.sensor_fault_notif_sent:
    send_browser_notification(
        "Sensor Bermasalah",
        "Sensor bermasalah, segera lakukan pengecekan atau penggantian sensor"
    )
    st.session_state.sensor_fault_notif_sent = True
elif not sensor_error:
    st.session_state.sensor_fault_notif_sent = False

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
col1, col2, col3 = st.columns([2,2,1])
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

colA, colB = st.columns([3,2])
with colA:
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
                icon: "",
                requireInteraction: true
            });
        } else if (izin === "denied") {
            alert("Kamu menolak notifikasi. Aktifkan dari setting browser jika ingin menerima.");
        }
    }
    </script>
    """, height=48)
with colB:
    if "auto_save" not in st.session_state:
        st.session_state.auto_save = False
    colB1, colB2 = st.columns([2,1])
    with colB1:
        st.toggle("Simpan Otomatis", value=st.session_state.auto_save, key="auto_save")
    with colB2:
        st.button("Refresh", on_click=refresh_data)

def save_sensor_to_mysql(data):
    conn = mysql.connector.connect(**mysql_conf)
    cursor = conn.cursor()
    now = pd.Timestamp.now(tz=pytz.timezone('Asia/Jakarta'))
    query = ("INSERT INTO sensor (suhu, asap, api, tanah, tanggal, jam) VALUES (%s,%s,%s,%s,%s,%s)")
    cursor.execute(query, (
        data["suhu"], data["asap"], data["api"], data["kelembaban_tanah"],
        now.date(), now.strftime("%H:%M:%S")
    ))
    conn.commit()
    cursor.close()
    conn.close()

if st.session_state.auto_save:
    last_save = st.session_state.get('last_sensor_save', "")
    current_hour = pd.Timestamp.now(tz=pytz.timezone('Asia/Jakarta')).strftime('%Y-%m-%d %H')
    if last_save != current_hour:
        save_sensor_to_mysql(data)
        st.session_state['last_sensor_save'] = current_hour
    for topik, kolom in [("kebakaran", "kebakaran"), ("tanah", "tanah"), ("status", "pompa")]:
        topik_ref = db.reference(f"/notif/{topik}" if topik != "status" else "/pompa/status")
        topik_val = topik_ref.get() or ""
        last_val = st.session_state.get(f"last_notif_{kolom}", None)
        if last_val != topik_val:
            conn = mysql.connector.connect(**mysql_conf)
            cursor = conn.cursor()
            now = pd.Timestamp.now(tz=pytz.timezone('Asia/Jakarta'))
            cursor.execute(
                "INSERT INTO notif (kebakaran, tanah, pompa, tanggal, jam) VALUES (%s,%s,%s,%s,%s)",
                (
                    notif_firebase.get("kebakaran", ""),
                    notif_firebase.get("tanah", ""),
                    pompa_status,
                    now.date(),
                    now.strftime("%H:%M:%S")
                )
            )
            conn.commit()
            cursor.close()
            conn.close()
            st.session_state[f"last_notif_{kolom}"] = topik_val

# ------------ BAGIAN BAWAH ------------
df = get_mysql_data()
available_sensors = ["api", "asap", "tanah", "suhu"]

tanggal_list = list(df["tanggal"].unique())
today_str = date.today().strftime("%Y-%m-%d")
tanggal_display = ["Hari ini" if t == today_str else t for t in tanggal_list]
tanggal_map = {("Hari ini" if t == today_str else t): t for t in tanggal_list}

col1, col2 = st.columns(2)
with col1:
    sensor_selected = st.selectbox(
        "Pilih Sensor",
        options=available_sensors,
        index=2 if "tanah" in available_sensors else 0,
    )
with col2:
    default_index = tanggal_display.index("Hari ini") if "Hari ini" in tanggal_display else 0
    tanggal_selected_display = st.selectbox(
        "Pilih Tanggal",
        options=tanggal_display,
        index=default_index
    )
    tanggal_selected = tanggal_map[tanggal_selected_display]

excel_name = f"Data Sensor {tanggal_selected}.xlsx"
df_tanggal = df[df["tanggal"] == tanggal_selected]

# Tombol Aksi untuk Tabel Sensor
col_buttons = st.columns([1,1,1,1,1])
with col_buttons[0]:
    if not df_tanggal.empty:
        to_download = df_tanggal.copy()
        output = io.BytesIO()
        to_download.to_excel(output, index=False, engine='xlsxwriter')
        st.download_button(label="Print", data=output.getvalue(), file_name=excel_name, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", on_click=lambda: st.success("Download Data Sensor berhasil!"))

# Modal Tambah Data
if "show_add_modal" not in st.session_state:
    st.session_state.show_add_modal = False

if st.session_state.show_add_modal:
    with st.form("add_form"):
        st.write("### Tambah Data")
        add_cols = st.columns([1,1,1,1,1])
        with add_cols[0]:
            add_tanggal = st.date_input("Tanggal", key="add_tanggal")
        with add_cols[1]:
            st.markdown("<div class='time-input-container'><div>Jam:</div>", unsafe_allow_html=True)
            add_jam = st.selectbox("", list(range(24)), key="add_jam", label_visibility="collapsed")
        with add_cols[2]:
            st.markdown("<div class='time-input-container'><div>Menit:</div>", unsafe_allow_html=True)
            add_menit = st.selectbox("", list(range(60)), key="add_menit", label_visibility="collapsed")
        with add_cols[3]:
            add_kebakaran = st.selectbox("Kebakaran", ["iya", "tidak", "mungkin"], key="add_kebakaran")
        with add_cols[4]:
            add_pompa = st.selectbox("Pompa", ["on", "off"], key="add_pompa")
        
        submitted = st.form_submit_button("Tambah")
        if submitted:
            conn = mysql.connector.connect(**mysql_conf)
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "INSERT INTO notif (tanggal, jam, kebakaran, pompa, tanah) VALUES (%s,%s,%s,%s,%s)",
                    (add_tanggal, f"{add_jam:02d}:{add_menit:02d}:00", add_kebakaran, add_pompa, "ideal")
                )
                conn.commit()
                st.success("Data berhasil ditambahkan!")
                st.session_state.show_add_modal = False
                refresh_data()
            except Exception as e:
                st.error(f"Gagal menambahkan data: {e}")
            finally:
                cursor.close()
                conn.close()

with col_buttons[1]:
    if st.button("Tambah"):
        st.session_state.show_add_modal = True

st.write(f"#### Grafik {sensor_selected.capitalize()} (History per Jam)")

if not df_tanggal.empty and "jam" in df_tanggal:
    try:
        x = pd.to_datetime(df_tanggal["jam"], format="%H:%M:%S", errors="coerce").dt.strftime("%H:%M")
    except Exception:
        x = df_tanggal["jam"]
else:
    x = []

if not df_tanggal.empty:
    if sensor_selected in ["tanah", "suhu"]:
        y = df_tanggal[sensor_selected].astype(float)
        fig = go.Figure(
            [go.Scatter(x=x, y=y, mode="lines+markers", name=f"{sensor_selected} {tanggal_selected}")],
            layout=go.Layout(
                title=f"{sensor_selected.capitalize()} - {tanggal_selected_display}",
                xaxis_title="Jam",
                yaxis_title=sensor_selected.capitalize(),
                xaxis=dict(dtick=1)
            )
        )
        st.plotly_chart(fig, use_container_width=True)
    elif sensor_selected in ["api", "asap"]:
        y = df_tanggal[sensor_selected].map(lambda v: 1 if str(v).strip().lower() == "iya" else 0)
        fig = go.Figure(
            [go.Scatter(x=x, y=y, mode="lines+markers", name=f"{sensor_selected} {tanggal_selected}")],
            layout=go.Layout(
                title=f"{sensor_selected.capitalize()} - {tanggal_selected_display}",
                xaxis_title="Jam",
                yaxis_title=sensor_selected.capitalize(),
                xaxis=dict(dtick=1),
                yaxis=dict(
                    tickmode="array",
                    tickvals=[0, 1],
                    ticktext=["tidak", "iya"]
                )
            )
        )
        st.plotly_chart(fig, use_container_width=True)
else:
    fig = go.Figure(
        layout=go.Layout(
            title=f"{sensor_selected.capitalize()} - {tanggal_selected_display}",
            xaxis_title="Jam",
            yaxis_title=sensor_selected.capitalize(),
            xaxis=dict(dtick=1)
        )
    )
    st.plotly_chart(fig, use_container_width=True)

st.write("### Histori Notifikasi")
notif_df = get_notif_data()
notif_df = notif_df.sort_values(by=["tanggal", "jam"], ascending=False)
notif_df = notif_df.reset_index(drop=True)
notif_df["No"] = notif_df.index + 1

def extract_hhmm(x):
    if pd.isnull(x):
        return ""
    x = str(x)
    match = re.search(r"(\d{1,2}:\d{2}:\d{2})", x)
    if match:
        jam = match.group(1)
        try:
            return pd.to_datetime(jam, format='%H:%M:%S').strftime('%H:%M')
        except Exception:
            return ""
    else:
        return ""
notif_df['jam'] = notif_df['jam'].apply(extract_hhmm)

tabel = notif_df[["No", "tanggal", "jam", "kebakaran", "pompa", "tanah"]]

# Modal Edit Data
if "show_edit_modal" not in st.session_state:
    st.session_state.show_edit_modal = False
    st.session_state.edit_no = 1

if st.session_state.show_edit_modal:
    with st.form("edit_form"):
        st.write("### Edit Data")
        edit_cols = st.columns([1,1,1,1,1])
        with edit_cols[0]:
            edit_no = st.number_input("No", min_value=1, max_value=len(tabel), step=1, key="edit_no_input", value=st.session_state.edit_no)
        with edit_cols[1]:
            edit_tanggal = st.date_input("Tanggal", key="edit_tanggal")
        with edit_cols[2]:
            st.markdown("<div class='time-input-container'><div>Jam:</div>", unsafe_allow_html=True)
            edit_jam = st.selectbox("", list(range(24)), key="edit_jam", label_visibility="collapsed")
        with edit_cols[3]:
            st.markdown("<div class='time-input-container'><div>Menit:</div>", unsafe_allow_html=True)
            edit_menit = st.selectbox("", list(range(60)), key="edit_menit", label_visibility="collapsed")
        with edit_cols[4]:
            edit_kebakaran = st.selectbox("Kebakaran", ["iya", "tidak", "mungkin"], key="edit_kebakaran")
        
        edit_cols2 = st.columns([1,1])
        with edit_cols2[0]:
            edit_pompa = st.selectbox("Pompa", ["on", "off"], key="edit_pompa")
        with edit_cols2[1]:
            edit_tanah = st.selectbox("Tanah", ["kering", "basah", "ideal"], key="edit_tanah")
        
        submitted = st.form_submit_button("Simpan Perubahan")
        if submitted:
            conn = mysql.connector.connect(**mysql_conf)
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "UPDATE notif SET tanggal=%s, jam=%s, kebakaran=%s, pompa=%s, tanah=%s WHERE no=%s",
                    (edit_tanggal, f"{edit_jam:02d}:{edit_menit:02d}:00", edit_kebakaran, edit_pompa, edit_tanah, edit_no)
                )
                conn.commit()
                st.success("Data berhasil diupdate!")
                st.session_state.show_edit_modal = False
                refresh_data()
            except Exception as e:
                st.error(f"Gagal mengupdate data: {e}")
            finally:
                cursor.close()
                conn.close()

# Modal Hapus Data
if "show_delete_modal" not in st.session_state:
    st.session_state.show_delete_modal = False
    st.session_state.delete_no = 1

if st.session_state.show_delete_modal:
    with st.form("delete_form"):
        st.write("### Hapus Data")
        delete_no = st.number_input("No", min_value=1, max_value=len(tabel), step=1, key="delete_no_input", value=st.session_state.delete_no)
        submitted = st.form_submit_button("Hapus")
        if submitted:
            conn = mysql.connector.connect(**mysql_conf)
            cursor = conn.cursor()
            try:
                cursor.execute("DELETE FROM notif WHERE no=%s", (delete_no,))
                conn.commit()
                st.success("Data berhasil dihapus!")
                st.session_state.show_delete_modal = False
                refresh_data()
            except Exception as e:
                st.error(f"Gagal menghapus data: {e}")
            finally:
                cursor.close()
                conn.close()

# Tombol Aksi untuk Tabel Notifikasi
notif_col_buttons = st.columns([1,1,1,1,1])
with notif_col_buttons[0]:
    if not tabel.empty:
        output2 = io.BytesIO()
        tabel.to_excel(output2, index=False, engine='xlsxwriter')
        st.download_button(label="Print", data=output2.getvalue(), file_name=f"History Notifikasi per {date.today().strftime('%Y-%m-%d')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", on_click=lambda: st.success("Download History Notifikasi berhasil!"))
with notif_col_buttons[1]:
    if st.button("Tambah", key="tambah_notif"):
        st.session_state.show_add_modal = True
with notif_col_buttons[2]:
    if st.button("Ubah", key="ubah_notif"):
        st.session_state.show_edit_modal = True
        st.session_state.edit_no = 1
with notif_col_buttons[3]:
    if st.button("Hapus", key="hapus_notif"):
        st.session_state.show_delete_modal = True
        st.session_state.delete_no = 1

if not tabel.empty:
    st.dataframe(tabel, hide_index=True, use_container_width=True)
