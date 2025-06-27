import streamlit as st
from streamlit_js_eval import streamlit_js_eval

st.set_page_config(page_title="Tes Push Notifikasi Browser", page_icon="🔔")

st.title("Demo Push Notifikasi Browser di Streamlit")
st.write("""
Aplikasi ini akan meminta izin notifikasi dari browser.  
Setelah diizinkan, klik tombol 'Tes Push Notifikasi' untuk mengirimkan notifikasi ke browser Anda.
""")

notif_status = st.session_state.get("notif_status", "Belum diminta")

if st.button("Izinkan Notifikasi Browser"):
    res = streamlit_js_eval(js_expressions="Notification.requestPermission()", key="notif_perm")
    if res and res["Notification.requestPermission()"]:
        status = res["Notification.requestPermission()"]
        st.session_state["notif_status"] = status
        if status == "granted":
            st.success("Izin notifikasi DIBERI. Sekarang kamu bisa menerima notifikasi push!")
        elif status == "denied":
            st.error("Izin notifikasi DITOLAK. Aktifkan lewat pengaturan browser untuk mencoba lagi.")
        else:
            st.info(f"Status izin: {status}")

status_now = st.session_state.get("notif_status", "Belum diminta")
st.info(f"Status izin notifikasi sekarang: **{status_now}**")

if st.button("Tes Push Notifikasi"):
    notif_js = """
    if (Notification.permission === "granted") {
        new Notification("Notifikasi dari Streamlit!", { 
            body: "Ini adalah notifikasi browser dari Streamlit.",
            icon: "https://streamlit.io/images/brand/streamlit-logo-primary-colormark-darktext.png"
        });
    } else {
        alert("Izin notifikasi belum diberikan. Klik 'Izinkan Notifikasi Browser' dulu!");
    }
    """
    streamlit_js_eval(js_expressions=notif_js, key="push_notif")
