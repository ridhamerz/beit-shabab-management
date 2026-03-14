import streamlit as st
import pandas as pd
from datetime import date, timedelta, datetime
import sqlite3
import hashlib
from docx import Document
import io
import os
import plotly.express as px

# ==================== إعدادات الصفحة ====================
st.set_page_config(page_title="بيت شباب محمدي يوسف قالمة", layout="wide", page_icon="🏨")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap');
* { font-family: 'Cairo', sans-serif; direction: RTL; text-align: right; }
.main-title { background: linear-gradient(90deg, #1e3c72, #2a5298); color: white; padding: 20px; border-radius: 15px; text-align: center; margin-bottom: 25px; font-size: 1.5rem; font-weight: bold; }
.stat-card { background: #ffffff; padding: 20px; border-radius: 15px; border-right: 6px solid #1e3c72; text-align: center; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
.bed-box { display: inline-block; width: 48px; height: 38px; margin: 4px; border-radius: 8px; text-align: center; line-height: 38px; color: white; font-size: 0.85rem; font-weight: bold; cursor: pointer; }
.free { background-color: #28a745; }
.occupied { background-color: #dc3545; }
.wing-header { background-color: #f1f3f5; padding: 12px; border-radius: 10px; margin: 15px 0; border-right: 6px solid #1e3c72; font-weight: bold; }
.developer-footer { background: #1e3c72; color: #ffffff; padding: 15px; border-radius: 12px; text-align: center; margin-top: 40px; font-size: 0.85rem; }
</style>
""", unsafe_allow_html=True)

# ==================== قاعدة البيانات ====================
DB_FILE = "biet_chabab.db"

def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

@st.cache_resource
def get_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    conn = get_db()
    conn.execute("CREATE TABLE IF NOT EXISTS rooms_config (wing TEXT, room TEXT, beds_count INTEGER, PRIMARY KEY (wing, room))")
    conn.execute("CREATE TABLE IF NOT EXISTS users (role TEXT PRIMARY KEY, password_hash TEXT)")
    conn.execute("""CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT, birth_date DATE, address TEXT, id_number TEXT,
        wing TEXT, room TEXT, bed TEXT, check_in DATE, check_out DATE,
        payment REAL DEFAULT 0, status TEXT DEFAULT 'IN', out_at TIMESTAMP
    )""")

    if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        conn.execute("INSERT INTO users VALUES (?,?)", ("مدير", sha256("1234")))
        conn.execute("INSERT INTO users VALUES (?,?)", ("عون استقبال", sha256("5678")))

    if conn.execute("SELECT COUNT(*) FROM rooms_config").fetchone()[0] == 0:
        default = [
            ("جناح ذكور", "غرفة 01", 6), ("جناح ذكور", "غرفة 02", 6), ("جناح ذكور", "غرفة 03", 6),
            ("جناح ذكور", "غرفة 04", 6), ("جناح ذكور", "غرفة 05", 6),
            ("جناح ذكور", "مرقد 01", 3), ("جناح ذكور", "مرقد 02", 4),
            ("جناح إناث", "غرفة 06", 2), ("جناح إناث", "غرفة 07", 6),
            ("جناح إناث", "غرفة 08", 6), ("جناح إناث", "غرفة 09", 6),
            ("جناح إناث", "مرقد 01", 3), ("جناح إناث", "مرقد 02", 4)
        ]
        conn.executemany("INSERT INTO rooms_config VALUES (?,?,?)", default)
    conn.commit()

init_db()

def load_wings():
    df = pd.read_sql("SELECT * FROM rooms_config", get_db())
    wings = {}
    for wing in df['wing'].unique():
        sub = df[df['wing'] == wing]
        wings[wing] = dict(zip(sub['room'], sub['beds_count']))
    return wings

wings_data = load_wings()

# ==================== تسجيل الدخول ====================
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown('<div class="main-title">🏨 نظام بيت الشباب محمدي يوسف قالمة</div>', unsafe_allow_html=True)
    role = st.selectbox("الصلاحية", ["مدير", "عون استقبال"])
    pwd = st.text_input("كلمة المرور", type="password")
    if st.button("دخول آمن", use_container_width=True):
        user = get_db().execute("SELECT password_hash FROM users WHERE role=?", (role,)).fetchone()
        if user and sha256(pwd) == user[0]:
            st.session_state.authenticated = True
            st.session_state.role = role
            st.rerun()
        else:
            st.error("❌ كلمة المرور خاطئة")
    st.stop()

st.sidebar.title(f"👤 {st.session_state.role}")
if st.sidebar.button("🚪 تسجيل الخروج"):
    st.session_state.authenticated = False
    st.rerun()

tabs = st.tabs(["📊 الإحصائيات", "🛏️ حالة الغرف", "➕ حجز جديد", "🔍 السجل والإخلاء", "📁 الأرشيف", "⚙️ إدارة الغرف"])

today = date.today()

# ==================== تبويب 0: الإحصائيات ====================
with tabs[0]:
    st.subheader("📈 لوحة التحكم")
    df_all = pd.read_sql("SELECT * FROM bookings", get_db())
    current_in = len(df_all[df_all['status'] == 'IN'])
    total_beds = sum(sum(v.values()) for v in wings_data.values())
    occupancy = round(current_in / total_beds * 100, 1) if total_beds else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("نزلاء حاليين", current_in)
    c2.metric("نسبة الإشغال", f"{occupancy}%")
    c3.metric("إجمالي المداخيل", f"{df_all['payment'].sum():,.0f} دج")

    if not df_all.empty:
        fig = px.pie(df_all[df_all['status']=='IN'], names='wing', title="توزيع النزلاء حسب الجناح")
        st.plotly_chart(fig, use_container_width=True)

# ==================== تبويب 1: حالة الغرف (مع popover) ====================
with tabs[1]:
    st.subheader("🛏️ خريطة الغرف (اضغط على السرير المشغول)")
    df_occ = pd.read_sql("SELECT wing, room, bed, full_name, check_out FROM bookings WHERE status='IN'", get_db())
    
    for wing, rooms in wings_data.items():
        st.markdown(f'<div class="wing-header">{wing}</div>', unsafe_allow_html=True)
        for room, count in rooms.items():
            st.write(f"**{room}**")
            cols = st.columns(count)
            for i in range(1, count + 1):
                bed_name = f"سرير {i}"
                occupied = df_occ[(df_occ['wing']==wing) & (df_occ['room']==room) & (df_occ['bed']==bed_name)]
                if not occupied.empty:
                    info = occupied.iloc[0]
                    with cols[i-1].popover(bed_name):
                        st.markdown(f"**👤 {info['full_name']}**")
                        st.caption(f"يخرج: {info['check_out']}")
                    cols[i-1].markdown(f'<div class="bed-box occupied">{bed_name}</div>', unsafe_allow_html=True)
                else:
                    cols[i-1].markdown(f'<div class="bed-box free">{bed_name}</div>', unsafe_allow_html=True)

# ==================== تبويب 2: حجز جديد ====================
with tabs[2]:
    st.subheader("➕ حجز جديد")
    with st.form("booking_form"):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("الاسم واللقب *")
            birth_d = st.date_input("تاريخ الازدياد")
            addr = st.text_input("العنوان")
            pay = st.number_input("المبلغ المدفوع (دج)", min_value=0.0)
        with c2:
            id_num = st.text_input("رقم الهوية *")
            wing = st.selectbox("الجناح", list(wings_data.keys()))
            room = st.selectbox("الغرفة", list(wings_data[wing].keys()))
            bed = st.selectbox("السرير", [f"سرير {i+1}" for i in range(wings_data[wing][room])])
            check_in = st.date_input("تاريخ الدخول", today)
            check_out = st.date_input("تاريخ الخروج", today + timedelta(days=1))

        if st.form_submit_button("✅ حفظ الحجز"):
            if name and id_num:
                conn = get_db()
                overlap = conn.execute("""
                    SELECT COUNT(*) FROM bookings 
                    WHERE wing=? AND room=? AND bed=? AND status='IN'
                    AND check_in < ? AND check_out > ?
                """, (wing, room, bed, check_out, check_in)).fetchone()[0]
                
                if overlap > 0:
                    st.error("⚠️ السرير محجوز في هذه الفترة!")
                else:
                    conn.execute("INSERT INTO bookings (full_name, birth_date, address, id_number, wing, room, bed, check_in, check_out, payment) VALUES (?,?,?,?,?,?,?,?,?,?)",
                                 (name, birth_d, addr, id_num, wing, room, bed, check_in, check_out, pay))
                    conn.commit()
                    st.success(f"✅ تم تسجيل {name}")
                    st.rerun()

# ==================== تبويب 3: السجل والإخلاء ====================
with tabs[3]:
    st.subheader("🔍 السجل والإخلاء")
    df_in = pd.read_sql("SELECT id, full_name, wing, room, bed, payment FROM bookings WHERE status='IN'", get_db())
    st.dataframe(df_in, use_container_width=True)

    if not df_in.empty:
        selected_id = st.selectbox("اختر النزيل للإخلاء", df_in['id'])
        if st.button("🚪 إخلاء النزيل", type="primary"):
            get_db().execute("UPDATE bookings SET status='OUT', out_at=? WHERE id=?", (datetime.now(), selected_id))
            get_db().commit()
            st.success("✅ تم الإخلاء")
            st.rerun()

# ==================== تبويب 4: الأرشيف ====================
with tabs[4]:
    st.subheader("📁 الأرشيف")
    start = st.date_input("من", today - timedelta(days=30))
    end = st.date_input("إلى", today)
    df_arch = pd.read_sql("SELECT * FROM bookings WHERE check_in BETWEEN ? AND ?", get_db(), params=(start, end))
    st.dataframe(df_arch, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        csv = df_arch.to_csv(index=False).encode()
        st.download_button("تحميل CSV", csv, "archive.csv")
    with c2:
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "rb") as f:
                st.download_button("نسخة احتياطية DB", f.read(), "backup.db")

# ==================== تبويب 5: إدارة الغرف (تعديل عدد الأسرّة) ====================
with tabs[5]:
    st.subheader("⚙️ إدارة عدد الأسرّة")
    st.info("يمكنك زيادة أو تقليل عدد الأسرّة. النظام يمنع تقليل العدد إذا كان هناك نزلاء أكثر.")

    col1, col2 = st.columns(2)
    with col1:
        selected_wing = st.selectbox("الجناح", list(wings_data.keys()))
    with col2:
        rooms_list = list(wings_data[selected_wing].keys())
        selected_room = st.selectbox("الغرفة", rooms_list)

    current_count = wings_data[selected_wing][selected_room]
    new_count = st.number_input("العدد الجديد", min_value=1, value=current_count, step=1)

    if st.button("✅ تحديث عدد الأسرّة", type="primary", use_container_width=True):
        if new_count < current_count:
            occupied = get_db().execute(
                "SELECT COUNT(*) FROM bookings WHERE wing=? AND room=? AND status='IN'",
                (selected_wing, selected_room)
            ).fetchone()[0]
            if occupied > new_count:
                st.error(f"❌ لا يمكن تقليل العدد! يوجد {occupied} نزيل حاليًا.")
                st.stop()

        get_db().execute("UPDATE rooms_config SET beds_count = ? WHERE wing=? AND room=?",
                         (new_count, selected_wing, selected_room))
        get_db().commit()
        st.success(f"✅ تم تحديث {selected_room} إلى {new_count} أسرّة")
        st.rerun()

st.markdown(f'<div class="developer-footer">RIDHA MERZOUG LABS © {date.today().year}</div>', unsafe_allow_html=True)
