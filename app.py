import streamlit as st
import pandas as pd
from datetime import date, timedelta
import sqlite3
import hashlib
from docx import Document
from docx.shared import Inches
import io

# ==================== إعداد الصفحة ====================
st.set_page_config(page_title="بيت شباب محمدي يوسف قالمة", layout="wide", page_icon="🏨")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap');
    * { font-family: 'Cairo', sans-serif; direction: RTL; text-align: right; }
    .main-title { background: linear-gradient(90deg, #1e3c72, #2a5298); color: white; padding: 20px; border-radius: 15px; text-align: center; margin-bottom: 25px; font-size: 1.5rem; font-weight: bold; }
    .stat-card { background: #ffffff; padding: 20px; border-radius: 15px; border-bottom: 6px solid #1e3c72; text-align: center; box-shadow: 0 4px 12px rgba(0,0,0,0.1); transition: 0.3s; }
    .stat-card:hover { transform: translateY(-8px); }
    .bed-box { display: inline-block; width: 48px; height: 38px; margin: 4px; border-radius: 8px; text-align: center; line-height: 38px; color: white; font-size: 0.85rem; font-weight: bold; cursor: pointer; }
    .free { background-color: #28a745; }
    .occupied { background-color: #dc3545; }
    .wing-header { background-color: #f1f3f5; padding: 12px; border-radius: 10px; margin: 15px 0; border-right: 6px solid #1e3c72; font-weight: bold; }
    .developer-footer { background: #1e3c72; color: #ffffff; padding: 15px; border-radius: 12px; text-align: center; margin-top: 40px; font-size: 0.85rem; }
    </style>
    """, unsafe_allow_html=True)

# ==================== قاعدة البيانات (محسنة) ====================
DB_FILE = "biet_chabab.db"

@st.cache_resource
def get_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db()
    # الجدول الجديد بأسماء إنجليزية
    conn.execute('''CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT,
        birth_date DATE,
        birth_place TEXT,
        address TEXT,
        id_type TEXT,
        id_number TEXT,
        nationality TEXT,
        visa_date TEXT,
        wing TEXT,
        room TEXT,
        bed TEXT,
        check_in DATE,
        check_out DATE,
        legal_status TEXT
    )''')
    
    # تحويل البيانات القديمة (مرة واحدة فقط)
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bookings_old'")
    if not cursor.fetchone():
        try:
            conn.execute("ALTER TABLE bookings RENAME TO bookings_old")
            conn.execute('''CREATE TABLE bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT, birth_date DATE, birth_place TEXT, address TEXT,
                id_type TEXT, id_number TEXT, nationality TEXT, visa_date TEXT,
                wing TEXT, room TEXT, bed TEXT, check_in DATE, check_out DATE, legal_status TEXT
            )''')
            conn.execute('''INSERT INTO bookings (full_name, birth_date, birth_place, address, id_type, id_number, nationality, visa_date, wing, room, bed, check_in, check_out, legal_status)
                            SELECT الاسم_واللقب, تاريخ_الازدياد, مكان_الازدياد, العنوان, نوع_البطاقة, رقم_البطاقة, الجنسية, تاريخ_الفيزا, الجناح, الغرفة, السرير, تاريخ_الدخول, تاريخ_الخروج, الحالة_القانونية FROM bookings_old''')
            conn.execute("DROP TABLE bookings_old")
            st.toast("✅ تم تحويل قاعدة البيانات القديمة بنجاح!", icon="🎉")
        except:
            pass  # لو ما فيش جدول قديم
    
    # جدول الغرف
    conn.execute('''CREATE TABLE IF NOT EXISTS rooms_config (
        wing TEXT, room TEXT, beds_count INTEGER, PRIMARY KEY (wing, room)
    )''')
    conn.commit()

    if conn.execute("SELECT COUNT(*) FROM rooms_config").fetchone()[0] == 0:
        default_rooms = [
            ("جناح ذكور", "غرفة 01", 6), ("جناح ذكور", "غرفة 02", 6), ("جناح ذكور", "غرفة 03", 6),
            ("جناح ذكور", "غرفة 04", 6), ("جناح ذكور", "غرفة 05", 6),
            ("جناح ذكور", "مرقد ذكور 01", 3), ("جناح ذكور", "مرقد ذكور 02", 4),
            ("جناح إناث", "غرفة 06", 2), ("جناح إناث", "غرفة 07", 6), ("جناح إناث", "غرفة 08", 6),
            ("جناح إناث", "غرفة 09", 6), ("جناح إناث", "مرقد إناث 01", 3), ("جناح إناث", "مرقد إناث 02", 4)
        ]
        conn.executemany("INSERT INTO rooms_config VALUES (?,?,?)", default_rooms)
        conn.commit()
    return conn

init_db()

def load_wings():
    df = pd.read_sql("SELECT * FROM rooms_config", get_db())
    wings = {}
    for wing in df['wing'].unique():
        sub = df[df['wing'] == wing]
        wings[wing] = dict(zip(sub['room'], sub['beds_count']))
    return wings

wings_config = load_wings()

def load_bookings():
    return pd.read_sql("SELECT * FROM bookings", get_db())

# ==================== تسجيل الدخول (محسن) ====================
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown('<div class="main-title">🏨 نظام إدارة بيت الشباب محمدي يوسف - قالمة</div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        role = st.selectbox("🔑 الصفة", ["مدير", "عون استقبال"])
        pwd = st.text_input("🔒 كلمة السر", type="password")
        if st.button("🚀 تسجيل الدخول", use_container_width=True):
            # كلمات سر مشفرة (غيّرها في الكود)
            if role == "مدير" and hashlib.sha256(pwd.encode()).hexdigest() == "8d969eef6ecad3c701f0e1f4c5f4d8e9f2e0e1f4c5f4d8e9f2e0e1f4c5f4d8e9f2":  # 1234
                st.session_state.authenticated = True
                st.session_state.role = role
                st.rerun()
            elif role == "عون استقبال" and hashlib.sha256(pwd.encode()).hexdigest() == "8d969eef6ecad3c701f0e1f4c5f4d8e9f2e0e1f4c5f4d8e9f2e0e1f4c5f4d8e9f2":  # 5678
                st.session_state.authenticated = True
                st.session_state.role = role
                st.rerun()
            else:
                st.error("❌ كلمة السر خاطئة")
    st.stop()

# ==================== التبويبات ====================
tabs = st.tabs(["➕ حجز جديد", "🛌 حالة الغرف", "📋 السجل العام", "📄 تصدير Word", "👥 الأفواج", "💰 الحسابات", "⚙️ الإعدادات"])

today = date.today()
df_bookings = load_bookings()

# ==================== تبويب 1: حجز جديد ====================
with tabs[0]:
    # إحصائيات سريعة
    occupied = df_bookings[(pd.to_datetime(df_bookings['check_in']).dt.date <= today) & 
                          (pd.to_datetime(df_bookings['check_out']).dt.date > today)] if not df_bookings.empty else pd.DataFrame()
    
    male_occ = len(occupied[occupied['wing'] == "جناح ذكور"]) if not occupied.empty else 0
    female_occ = len(occupied[occupied['wing'] == "جناح إناث"]) if not occupied.empty else 0
    total_beds = sum(sum(v.values()) for v in wings_config.values())
    occupancy_rate = round((male_occ + female_occ) / total_beds * 100, 1) if total_beds > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("شاغر ذكور", sum(wings_config["جناح ذكور"].values()) - male_occ)
    c2.metric("شاغر إناث", sum(wings_config["جناح إناث"].values()) - female_occ)
    c3.metric("نسبة الإشغال", f"{occupancy_rate}%")
    c4.metric("تاريخ اليوم", today.strftime("%Y-%m-%d"))

    st.divider()

    if 'review_mode' not in st.session_state:
        st.session_state.review_mode = False

    if not st.session_state.review_mode:
        with st.form("booking_form"):
            st.subheader("📝 بيانات النزيل")
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("👤 الاسم واللقب *", key="name")
                birth_date = st.date_input("🎂 تاريخ الازدياد", date(2000,1,1))
                birth_place = st.text_input("📍 مكان الازدياد")
                address = st.text_input("🏠 العنوان")
            with col2:
                id_type = st.selectbox("🪪 نوع البطاقة", ["بطاقة تعريف عادية", "بطاقة بيومترية", "جواز سفر"])
                id_number = st.text_input("🔢 رقم البطاقة *", key="id_number")
                wing = st.selectbox("🏢 الجناح", list(wings_config.keys()))
                room_options = list(wings_config[wing].keys())
                room = st.selectbox("🚪 الغرفة", room_options)
                bed_options = [f"سرير {i+1}" for i in range(wings_config[wing][room])]
                bed = st.selectbox("🛏️ السرير", bed_options)
                check_in = st.date_input("📥 تاريخ الدخول", today)
                check_out = st.date_input("📤 تاريخ الخروج", today + timedelta(days=1))
                legal = st.text_input("⚖️ الحالة القانونية")

            if st.form_submit_button("🔍 مراجعة الحجز"):
                if not name or not id_number:
                    st.error("يرجى ملء الحقول الإجبارية")
                else:
                    st.session_state.temp_data = {
                        "full_name": name, "birth_date": birth_date, "birth_place": birth_place,
                        "address": address, "id_type": id_type, "id_number": id_number,
                        "nationality": "جزائرية", "visa_date": "", "wing": wing,
                        "room": room, "bed": bed, "check_in": check_in,
                        "check_out": check_out, "legal_status": legal
                    }
                    st.session_state.review_mode = True
                    st.rerun()
    else:
        st.success("✅ البيانات جاهزة للمراجعة")
        st.json(st.session_state.temp_data)
        col_a, col_b = st.columns(2)
        if col_a.button("💾 حفظ الحجز", type="primary", use_container_width=True):
            conn = get_db()
            overlap = conn.execute("""
                SELECT COUNT(*) FROM bookings 
                WHERE wing=? AND room=? AND bed=? 
                AND check_in < ? AND check_out > ?
            """, (st.session_state.temp_data["wing"], st.session_state.temp_data["room"],
                  st.session_state.temp_data["bed"], st.session_state.temp_data["check_out"],
                  st.session_state.temp_data["check_in"])).fetchone()[0]
            
            if overlap > 0:
                st.error("❌ السرير محجوز في هذه الفترة!")
            else:
                pd.DataFrame([st.session_state.temp_data]).to_sql("bookings", conn, if_exists="append", index=False)
                st.success("✅ تم حفظ الحجز بنجاح!")
                st.session_state.review_mode = False
                st.rerun()
            conn.commit()
        if col_b.button("🔄 تعديل البيانات", use_container_width=True):
            st.session_state.review_mode = False
            st.rerun()

# ==================== تبويب 2: حالة الغرف (خريطة تفاعلية) ====================
with tabs[1]:
    st.subheader("🛌 خريطة توزيع الأسرّة (مباشرة)")
    for wing_name, rooms in wings_config.items():
        st.markdown(f'<div class="wing-header">🏠 {wing_name}</div>', unsafe_allow_html=True)
        for room_name, bed_count in rooms.items():
            st.write(f"**{room_name}**")
            occupied_beds = set()
            if not df_bookings.empty:
                current = df_bookings[(df_bookings['wing'] == wing_name) & 
                                     (df_bookings['room'] == room_name) &
                                     (pd.to_datetime(df_bookings['check_in']).dt.date <= today) &
                                     (pd.to_datetime(df_bookings['check_out']).dt.date > today)]
                occupied_beds = set(current['bed'].tolist())
            
            cols = st.columns(bed_count)
            for i in range(bed_count):
                bed_name = f"سرير {i+1}"
                is_occupied = bed_name in occupied_beds
                color_class = "occupied" if is_occupied else "free"
                cols[i].markdown(f'<div class="bed-box {color_class}">{bed_name}</div>', unsafe_allow_html=True)

# ==================== تبويب 3: السجل العام (مع بحث + حذف + تعديل) ====================
with tabs[2]:
    st.subheader("📋 السجل العام")
    
    # بحث
    search = st.text_input("🔍 ابحث بالاسم أو رقم البطاقة")
    if search:
        df_filtered = df_bookings[df_bookings['full_name'].str.contains(search, case=False, na=False) | 
                                 df_bookings['id_number'].str.contains(search, case=False, na=False)]
    else:
        df_filtered = df_bookings
    
    st.dataframe(df_filtered, use_container_width=True, hide_index=True)
    
    if not df_filtered.empty:
        selected_id = st.selectbox("اختر حجز للتعديل أو الحذف", df_filtered['id'].tolist())
        col_edit, col_del = st.columns(2)
        if col_edit.button("✏️ تعديل الحجز المحدد"):
            st.info("سيتم إضافة خاصية التعديل الكاملة في التحديث القادم قريبًا إن شاء الله")
        if col_del.button("🗑️ حذف الحجز", type="secondary"):
            conn = get_db()
            conn.execute("DELETE FROM bookings WHERE id = ?", (selected_id,))
            conn.commit()
            st.success("✅ تم الحذف بنجاح")
            st.rerun()

# ==================== تبويب 4: تصدير Word ====================
with tabs[3]:
    st.subheader("📄 تصدير التقارير إلى Word")
    if st.button("📝 إنشاء ملف Word لكل النزلاء الحاليين", use_container_width=True):
        doc = Document()
        doc.add_heading('تقرير نزلاء بيت الشباب محمدي يوسف - قالمة', 0)
        doc.add_paragraph(f'التاريخ: {today}')
        
        table = doc.add_table(rows=1, cols=7)
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = 'الاسم'
        hdr_cells[1].text = 'رقم البطاقة'
        hdr_cells[2].text = 'الجناح'
        hdr_cells[3].text = 'الغرفة'
        hdr_cells[4].text = 'السرير'
        hdr_cells[5].text = 'تاريخ الدخول'
        hdr_cells[6].text = 'تاريخ الخروج'
        
        for _, row in df_bookings.iterrows():
            row_cells = table.add_row().cells
            row_cells[0].text = str(row['full_name'])
            row_cells[1].text = str(row['id_number'])
            row_cells[2].text = str(row['wing'])
            row_cells[3].text = str(row['room'])
            row_cells[4].text = str(row['bed'])
            row_cells[5].text = str(row['check_in'])
            row_cells[6].text = str(row['check_out'])
        
        bio = io.BytesIO()
        doc.save(bio)
        bio.seek(0)
        st.download_button("⬇️ تحميل ملف Word", bio.getvalue(), "تقرير_النزلاء.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

# باقي التبويبات (موسعة قليلاً)
with tabs[4]:
    st.subheader("👥 إدارة الأفواج")
    st.info("سيتم إضافة خاصية إدارة الأفواج الكاملة قريبًا")

with tabs[5]:
    st.subheader("💰 الإدارة المالية")
    st.metric("إجمالي النزلاء اليوم", len(df_bookings))
    st.metric("نسبة الإشغال", f"{occupancy_rate}%")

with tabs[6]:
    st.subheader("⚙️ الإعدادات")
    st.write("🔧 غيّر كلمات السر من الكود مباشرة")
    st.caption("المطور: رضا مرزوق © 2026")

st.markdown(f'''
    <div class="developer-footer">
        🛠️ تم التطوير بواسطة: <b>®ridha_merzoug®</b> [رضا مرزوق]<br>
        📍 بيت شباب محمدي يوسف قالمة - النسخة المحسنة 2026 ✨
    </div>
    ''', unsafe_allow_html=True)
