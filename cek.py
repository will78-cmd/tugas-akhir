import streamlit as st
import firebase_admin
from firebase_admin import credentials
import mysql.connector

firebase_config = dict(st.secrets["firebase"])
cred = credentials.Certificate(firebase_config)

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

mysql_conf = st.secrets["mysql"]

conn = mysql.connector.connect(
    host=mysql_conf["host"],
    port=mysql_conf["port"],
    database=mysql_conf["database"],
    user=mysql_conf["user"],
    password=mysql_conf["password"]
)
cursor = conn.cursor()
cursor.execute("SELECT DATABASE();")
db_name = cursor.fetchone()[0]

st.success(f"Terkoneksi ke MySQL: {db_name}")
cursor.close()
conn.close()

st.success("Firebase & MySQL sukses dikoneksikan menggunakan secrets.toml!")
