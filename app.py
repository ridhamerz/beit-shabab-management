import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# 1. إعداد الصفحة والتنسيق
st.set_page_config(page_title="بيت شباب محمدي يوسف قالمة", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap');
    * { font-family: 'Cairo', sans-serif; direction: RTL; text-align: right; }
    .main-title { background: linear-gradient(90deg, #1e3c72, #2a5298); color: white; padding: 15px; border-radius: 12px; text-align: center; margin-bottom: 20px; font-size: 1.3rem; font-weight: bold; }
    .bed-box { display: inline-block; width: 40px; height: 35px; margin: 3px; border-radius: 5px; text-align: center; line-height: 35px; color: white; font-size: 0.8rem; font-weight: bold; }
    .free { background-color: #28a745; }
    .occupied { background-color: #dc3545; }
    .wing-header { background-color: #f1f3f5; padding: 10px; border-radius: 8px; margin-top: 15px; border-right: 5px solid #1e3c72; font-weight: bold; }
    .developer-footer { background: #1e3c72; color: #ffffff; padding: 8px; border-radius: 10px; text-align: center; margin-top: 40px; font-size: 0.75rem; }
    </style>
    """, unsafe_allow_html=True)

# 2. إدارة الحالة (السرية والبيانات)
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user_role' not in st.session_state:
    st.session_state.user_role = None
if 'passwords' not in st.session_state:
    st.session_state.passwords = {"مدير": "1234", "عون استقبال": "5678"}
if 'db' not in st.session_state:
    st.session_state.db = pd.DataFrame(columns=['الاسم واللقب', 'تاريخ الازدياد', 'العنوان', 'رقم البطاقة', 'المهنة', 'الجناح', 'الغرفة', 'السرير', 'تاريخ الخروج'])

wings = {
    "جناح ذكور": {"غرفة 01": 6, "غرفة 02": 6, "غرفة 03": 6, "غرفة 04": 6, "غرفة 05": 6, "مرقد ذكور 01": 3, "مرقد ذكور 02": 4},
    "جناح إناث": {"غرفة 06": 2, "غرفة 07": 6, "غرفة 08": 6, "غرفة 09": 6, "مرقد إناث 01": 3, "مرقد إناث 02": 4}
}

# --- 3. بوابة تسجيل الدخول ---
if not st.session_state.authenticated:
    st.markdown('<div class="main-title">®® برنامج بيت الشباب محمدي يوسف قالمة®®</div>', unsafe_allow_html=True)
    with st.container():
        st.subheader("🔐 الدخول للنظام")
        role = st.selectbox("اختر الصفة", ["مدير", "عون استقبال"])
        pwd = st.text_input("كلمة السر", type="password")
        if st.button("تسجيل الدخول", use_container_width=True):
            if pwd == st.session_state.passwords[role]:
                st.session_state.authenticated = True
                st.session_state.user_role = role
                st.rerun()
            else:
                st.error("❌ كلمة السر خاطئة")
    st.stop()

# --- 4. تخصيص التبويبات بناءً على الصلاحية ---
st.markdown('<div class="main-title">®® برنامج بيت الشباب محمدي يوسف قالمة®®</div>', unsafe_allow_html=True)
st.sidebar.info(f"👤 المستخدم الحالي: {st.session_state.user_role}")
if st.sidebar.button("خروج"):
    st.session_state.authenticated = False
    st.rerun()

# تحديد القائمة المتاحة لكل رتبة
if st.session_state.user_role == "مدير":
    tabs = st.tabs(["➕ حجز جديد", "📊 عدد الغرف", "📋 السجل العام", "⚙️ الإعدادات"])
else:
    # عون الاستقبال يرى فقط حجز جديد وعدد الغرف
    tabs = st.tabs(["➕ حجز جديد", "📊 عدد الغرف"])

# --- التبويب: حجز جديد (متاح للجميع) ---
with tabs[0]:
    st.subheader("📝 استمارة الحجز")
    with st.form("booking", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("الاسم واللقب")
            birth = st.text_input("تاريخ ومكان الازدياد")
            addr = st.text_input("العنوان الكامل")
        with c2:
            id_info = st.text_input("رقم بطاقة التعريف")
            job = st.text_input("المهنة")
            w_c = st.selectbox("الجناح", list(wings.keys()))
            r_c = st.selectbox("الغرفة", list(wings[w_c].keys()))
            b_c = st.selectbox("السرير", [f"سرير {i+1}" for i in range(wings[w_c][r_c])])
        
        if st.form_submit_button("💾 حفظ الحجز"):
            new_data = {'الاسم واللقب': name, 'تاريخ الازدياد': birth, 'العنوان': addr, 'رقم البطاقة': id_info, 
                        'المهنة': job, 'الجناح': w_c, 'الغرفة': r_c, 'السرير': b_c, 'تاريخ الخروج': datetime.now().date() + timedelta(days=1)}
            st.session_state.db = pd.concat([st.session_state.db, pd.DataFrame([new_data])], ignore_index=True)
            st.success("✅ تم الحجز بنجاح")

# --- التبويب: عدد الغرف (متاح للجميع) ---
with tabs[1]:
    st.subheader("📊 حالة الأسرة والأجنحة")
    for wing, rooms in wings.items():
        st.markdown(f'<div class="wing-header">{wing}</div>', unsafe_allow_html=True)
        for room, count in rooms.items():
            cols = st.columns([1, 5])
            cols[0].write(f"**{room}**")
            html = ""
            for b in range(1, count + 1):
                b_name = f"سرير {b}"
                is_occ = not st.session_state.db[(st.session_state.db['الجناح'] == wing) & (st.session_state.db['الغرفة'] == room) & (st.session_state.db['السرير'] == b_name)].empty
                status = "occupied" if is_occ else "free"
                html += f'<div class="bed-box {status}">{b}</div>'
            cols[1].markdown(html, unsafe_allow_html=True)

# --- التبويبات الخاصة بالمدير فقط ---
if st.session_state.user_role == "مدير":
    with tabs[2]:
        st.subheader("📋 سجل النزلاء الكامل")
        st.dataframe(st.session_state.db, use_container_width=True)
        if st.button("🗑️ مسح السجل بالكامل"):
            st.session_state.db = st.session_state.db.iloc[0:0]
            st.rerun()

    with tabs[3]:
        st.subheader("⚙️ إعدادات كلمات السر")
        target = st.selectbox("تغيير كلمة سر لـ", ["مدير", "عون استقبال"])
        new_pwd = st.text_input("أدخل كلمة السر الجديدة", type="password")
        if st.button("تحديث كلمة السر"):
            if new_pwd:
                st.session_state.passwords[target] = new_pwd
                st.success(f"✔️ تم تغيير كلمة سر {target} بنجاح!")

# تذييل المطور
st.markdown(f"""
    <div class="developer-footer">
        Developer <span style="color:#00d4ff;">®ridha_merzoug®</span> [رضا مرزوق]
    </div>
    """, unsafe_allow_html=True)
