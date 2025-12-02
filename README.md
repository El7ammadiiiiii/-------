# Smart Sales Agent 🤖

نظام ذكي لإدارة المبيعات عبر واتساب مع توليد الفواتير التلقائي

## 🌟 المميزات

- **رد ذكي على العملاء**: استخدام GPT لفهم الرسائل والرد التلقائي
- **إصدار فواتير فوري**: توليد PDF احترافي خلال ثوانٍ
- **لوحة تحكم للمدير**: إدارة المنتجات ومتابعة الطلبات لحظياً
- **تكلفة صفر**: SQLite + BackgroundTasks (بدون Redis أو Celery)
- **غير متزامن**: FastAPI لمعالجة الطلبات المتوازية

## 🏗️ البنية التقنية

```
SmartSalesAgent/
├── main.py                  # FastAPI server & Twilio webhook
├── database.py              # SQLAlchemy models & DB setup
├── dashboard.py             # Streamlit admin panel
├── services/
│   ├── ai_service.py        # OpenAI integration
│   ├── invoice_service.py   # PDF generation (ReportLab)
│   ├── twilio_service.py    # WhatsApp messaging
│   └── product_service.py   # Product CRUD operations
├── requirements.txt         # Python dependencies
├── .env.example             # Environment template
└── shop.db                  # SQLite database (auto-created)
```

## 📦 المتطلبات

- Python 3.9+
- حساب OpenAI (API Key)
- حساب Twilio (WhatsApp Sandbox أو رقم معتمد)

## 🚀 التثبيت والإعداد

### 1. تثبيت المكتبات

```bash
pip install -r requirements.txt
```

### 2. إعداد ملف البيئة

انسخ `.env.example` إلى `.env` وأضف بياناتك:

```bash
cp .env.example .env
```

افتح `.env` وعدّل:

```env
OPENAI_API_KEY=sk-...
OPENAI_THINKING_MODEL=gpt-5.1
OPENAI_INTENT_MODEL=gpt-5.1
OPENAI_REASONING_EFFORT=medium
INFOBIP_BASE_URL=wg6d18.api.infobip.com
INFOBIP_API_KEY=...
INFOBIP_RESOURCE_ID=...
INFOBIP_WHATSAPP_NUMBER=whatsapp:+447860088970
```

### 3. تهيئة قاعدة البيانات

```bash
python database.py
```

سيتم إنشاء `shop.db` مع منتجات تجريبية.

### 4. تشغيل السيرفر (البوت)

```bash
python main.py
```

أو باستخدام Uvicorn مباشرة:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

السيرفر سيعمل على: `http://localhost:8000`

### 5. تشغيل لوحة التحكم

في نافذة Terminal أخرى:

```bash
streamlit run dashboard.py
```

اللوحة ستفتح على: `http://localhost:8501`

## 🌐 ربط Twilio (للتطوير المحلي)

### استخدام ngrok لعمل نفق (Tunnel)

```bash
ngrok http 8000
```

ستحصل على رابط مثل: `https://abcd1234.ngrok.io`

### إعداد Twilio Webhook

1. اذهب إلى: [Twilio Console](https://console.twilio.com/)
2. WhatsApp → Sandbox Settings
3. ضع في "When a message comes in":
   ```
   https://abcd1234.ngrok.io/bot
   ```
4. Method: `POST`

الآن أرسل رسالة لرقم Sandbox في واتساب!

## 💬 كيفية الاستخدام

### تجربة العميل

1. **السؤال عن الأسعار**:
   ```
   العميل: بكم سعر تصميم اللوجو؟
   البوت: أسعارنا كالتالي:
          📦 تصميم لوجو: 50.0 دينار
          ...
   ```

2. **طلب فاتورة**:
   ```
   العميل: أريد فاتورة لتصميم لوجو باسم أحمد
   البوت: ✅ تم إصدار الفاتورة يا أحمد
          📄 المنتج: تصميم لوجو
          💰 المبلغ: 50.0 دينار
   ```

### تجربة المدير

1. افتح `http://localhost:8501`
2. شاهد الإحصائيات الحية
3. أضف منتج جديد من القائمة الجانبية
4. عدّل الأسعار → سيتحدث البوت فوراً بالسعر الجديد
5. حمّل تقرير الطلبات (CSV)

## 📁 الملفات المولدة

- `shop.db`: قاعدة البيانات (SQLite)
- `invoices/`: مجلد الفواتير PDF

## 🔒 الأمان

- **لا ترفع `.env` على GitHub** (مضاف في `.gitignore`)
- **لا تشارك API Keys علناً**
- للإنتاج: استخدم Secret Manager (AWS Secrets / Azure Key Vault)

## 🆘 استكشاف الأخطاء

### خطأ: "OpenAI API key not found"
✅ تأكد من وجود `OPENAI_API_KEY` في `.env`

### خطأ: "Twilio authentication failed"
✅ راجع `TWILIO_ACCOUNT_SID` و `TWILIO_AUTH_TOKEN`

### خطأ: "No module named 'fastapi'"
✅ نفّذ: `pip install -r requirements.txt`

### البوت لا يرد على واتساب
✅ تأكد من:
- السيرفر يعمل (`python main.py`)
- ngrok يعمل وربط Webhook صحيح
- رقمك مسجل في Twilio Sandbox

## 📊 خارطة الطريق

- [ ] رفع الفواتير على Google Drive / S3
- [ ] دعم الدفع الإلكتروني (Stripe/PayPal)
- [ ] إشعارات تلقرام للمدير
- [ ] تقارير متقدمة (Revenue Analytics)
- [ ] دعم اللغة الإنجليزية
- [ ] Docker deployment

## 🤝 المساهمة

المشروع مفتوح المصدر! Feel free to contribute.

## 📄 الترخيص

MIT License

## 📞 الدعم

للأسئلة أو المشاكل، افتح Issue على GitHub.

---

**تم البناء بـ ❤️ باستخدام FastAPI, OpenAI, Twilio, و Streamlit**
