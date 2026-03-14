# beit-shabab-management
# 🏨 نظام إدارة بيت شباب محمدي يوسف – قالمة

**نسخة 2026 المحسنة** – تطوير: رضا مرزوق (ridhamerz)

### المميزات:
- تسجيل دخول آمن (مدير / عون استقبال)
- خريطة تفاعلية للغرف (اضغط على سرير مشغول لرؤية الاسم + تاريخ الخروج)
- حجز جديد مع منع التداخل الزمني
- إخلاء + تعديل حجوزات
- إحصائيات + رسوم بيانية (Plotly)
- إدارة عدد الأسرّة (زيادة/نقص مع فحص أمان)
- تصدير Excel + Word + نسخ احتياطي للداتابيز

### كيف تشغّل المشروع:
```bash
git clone https://github.com/ridhamerz/beit-shabab-management.git
cd beit-shabab-management
pip install -r requirements.txt
streamlit run app.py
