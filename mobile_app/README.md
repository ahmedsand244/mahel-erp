# النماء ERP & POS - تطبيق Flutter للهواتف المحمولة

تطبيق Flutter أصلي (Native) مطابق 100% لموقع Django SaaS، يعمل **بلا إنترنت (Offline-First)** مع مزامنة ذكية عند عودة الاتصال.

## 🎯 المميزات الرئيسية

### 🔐 نظام المصادقة والشركات (Multi-Tenant SaaS)
- تسجيل دخول بـ `username` + `password` + `tenant_slug`
- JWT tokens مع Auto-refresh آمن
- دعم الشركات المتعددة مع باقات (Trial / Basic / Pro)
- قفل PIN سريع + Biometric (بصمة/وجه)
- التحقق من صلاحية الاشتراك تلقائياً

### 💰 شاشة البيع POS (مطابقة للموقع)
- شبكة منتجات مع صور، بحث فوري، فلترة
- ماسح باركود بالكاميرا (Barcode Scanner)
- سلة مشتريات تفاعلية (كميات، حذف، إجماليات)
- 3 طرق دفع: نقدي / فيزا / آجل (شكك)
- عملاء: اختيار موجود + إنشاء سريع + كشف حساب
- **طباعة حرارية عربية** (Bluetooth ESC/POS)
- **Offline Mode**: إنشاء فواتير محلياً → Queue → Sync تلقائي عند النت
- خصومات سطر/فاتورة، إرجاع مبيعات

### 📦 إدارة المخزون
- منتجات: اسم، SKU، باركود، سعر شراء/بيع، مخزون، وحدة، صنف، صورة
- تنبيهات ذكية: مخزون منخفض، نفاد، تواريخ انتهاء
- تعديل أسعار جماعي بالنسبة المئوية (+5%، +10%، -5%...)
- استيراد/تصدير Excel/CSV مع قالب جاهز
- جرد دوري + تسوية مخزون
- طلبات بضاعة (Purchase Orders): مسودة → إرسال → استلام جزئي/كامل
- باركود سكانر + طباعة ملصقات باركود

### 👥 الحسابات والديون (Ledger)
- عملاء/موردين: حد ائتمان، رصيد، كشف حساب، طباعة PDF
- سندات: قبض، صرف، قيد يومي، تحويل بنكي
- شيكات: مستحقة، مرتجعة، تحت التحصيل
- تقارير: ميزان مراجعة، أرباح وخسائر، تدفقات نقدية
- كشف حساب عام للعميل (Public URL للمشاركة)

### 🔧 الورشة والصيانة
- كانبان بورد: استلام → صيانة نشطة → جاهز → مسلمة
- تذاكر صيانة: معدات، مصنعية، قطع غيار، حالة
- تركيب قطع غيار من المخزون مع تحديث التكاليف تلقائياً
- تحصيل عند التسليم + طباعة فاتورة

### 💸 المصروفات
- بنود: إيجار، فواتير، رواتب، تسويق، أخرى
- إرفاق صور فواتير (كاميرا/معرض)
- تقارير مصروفات مقارنة بالميزانية

### 📊 التقارير المالية (P&L)
- فترات: اليوم، أمس، هذا الشهر، مخصص
- دخل: مبيعات POS + قطع غيار + مصنعيات
- تكاليف: COGS + قطع غيار + مصروفات
- صافي ربح = دخل - تكاليف
- تقييم مخزون: تكلفة + بيع + ربح محتمل
- ديون عملاء + مستحقات موردين
- **اعتماد وحفظ جلسات جرد** في الأرشيف
- تصدير PDF (RTL عربي) + Excel + مشاركة واتساب

### ⚙️ الإعدادات والأمان
- إعدادات الشركة: شعار، عنوان، ضريبة، تسلسل أرقام، طابعة
- مستخدمين وصلاحيات (RBAC)
- **نسخ احتياطي محلي** (SQLite export) + استعادة
- سجل تدقيق (Audit Log) لكل العمليات الحرجة
- حالة المزامنة + زر "مزامنة الآن" + Progress indicator
- ثيم: Dark/Light + خط Cairo + RTL كامل
- حجم خط قابل للتعديل (XS/S/M/L)

---

## 🏗 Architecture

```
lib/
├── core/
│   ├── database/          # Drift/SQLite - جميع الجداول مطابقة لـ Django
│   ├── network/           # Dio API client + interceptors
│   ├── storage/           # SecureStorage + SharedPreferences
│   ├── sync/              # SyncEngine (Pull/Push + Conflict Resolution)
│   ├── theme/             # AppTheme (Dark/Light, Cairo, RTL)
│   ├── router/            # go_router مع Guards
│   └── utils/             # Formatters, Extensions
├── features/
│   ├── auth/              # Login, JWT, Tenant, Biometric, PIN
│   ├── pos/               # POS Screen, Cart, Checkout, Print
│   ├── inventory/         # Products, Categories, Stock, POs
│   ├── ledger/            # Customers, Suppliers, Transactions
│   ├── maintenance/       # Tickets Kanban, Parts
│   ├── expenses/          # Expenses CRUD
│   ├── reports/           # P&L, Inventory Valuation, Audits
│   └── settings/          # Backup, Sync, Theme, Company
├── shared/
│   ├── widgets/           # AppButton, AppTextField, MainScaffold
│   ├── models/            # Freezed models
│   └── extensions/        # Context, String, DateTime extensions
└── main.dart              # Entry point + ProviderScope
```

### Offline-First Sync Engine
- **Local DB**: Drift (SQLite) مع schema مطابق 100% لـ Django
- **Sync Queue**: جداول `sync_queue` للعمليات الحرجة (فواتير، عملاء، منتجات)
- **Pull**: GET `/api/v1/sync/pull?since=last_sync` → Upsert محلي
- **Push**: POST `/api/v1/sync/push` batch → Server يعيد conflicts
- **Conflict Resolution**: Last-Write-Wins افتراضي، Server wins للفواتير
- **Background**: WorkManager كل 15 دقيقة + Event-driven عند عودة النت
- **Retry**: Exponential backoff + Dead Letter Queue

---

## 🚀 التشغيل والبناء

### المتطلبات
- Flutter SDK >= 3.3.0
- Dart >= 3.3.0
- Android Studio / VS Code
- جهاز Android أو محاكي (API 24+)

### التثبيت
```bash
cd mobile_app
flutter pub get
flutter packages pub run build_runner build --delete-conflicting-outputs
```

### التشغيل (Debug)
```bash
flutter run
```

### بناء APK للإنتاج
```bash
# ARM64 فقط (أحدث الأجهزة)
flutter build apk --release --split-per-abi --target-platform android-arm64

# جميع المعماريات
flutter build apk --release --split-per-abi

# App Bundle للـ Play Store
flutter build appbundle --release
```

### متغيرات البيئة
أنشئ ملف `.env` في جذر `mobile_app/`:
```env
API_BASE_URL=https://webservises.pythonanywhere.com
DEFAULT_TENANT_SLUG=mahel
```

---

## 📱 API Contract (يجب توافقه مع Django)

### Authentication
```
POST   /api/v1/login/
  Body: {username, password, tenant_slug}
  Response: {success, access, refresh, user, tenant}

POST   /api/v1/token/refresh/
  Body: {refresh}
  Response: {access}
```

### Data Sync
```
GET    /api/v1/products/?tenant_slug=X
GET    /api/v1/customers/?tenant_slug=X
POST   /api/v1/invoices/sync/
  Body: {tenant_slug, invoices: [{client_id, order_number, payment_method, customer_id, items, total_amount, created_at}]}
POST   /api/v1/sync/full/
  Body: {tenant_slug, customers, suppliers, products, invoices, expenses}
GET    /api/v1/dashboard/?tenant_slug=X
```

---

## 🔑 مفاتيح الترخيص

| الميزة | الحزمة |
|----------|---------|
| قاعدة البيانات | `drift`, `sqlite3_flutter_libs` |
| الشبكة | `dio`, `connectivity_plus` |
| التخزين الآمن | `flutter_secure_storage` |
| المزامنة الخلفية | `workmanager`, `flutter_local_notifications` |
| UI | `google_fonts`, `go_router`, `fl_chart`, `intl` |
| الباركود | `mobile_scanner` |
| الطباعة الحرارية | `esc_pos_bluetooth`, `esc_pos_usb` |
| PDF | `pdf`, `printing` |
| State Management | `flutter_riverpod`, `freezed`, `json_serializable` |

---

## 📂 هيكل قاعدة البيانات المحلي (Drift)

جميع الجداول تحتوي على حقول المزامنة:
- `server_id` - المعرف على السيرفر (nullable)
- `sync_status` - 'synced' | 'pending' | 'conflict'
- `last_modified` - آخر تعديل محلي
- `deleted_at` - Soft delete

**الجداول الرئيسية:**
- `tenants`, `tenant_users`, `users`
- `categories`, `products`, `stock_alerts`
- `customers`, `suppliers`, `transactions`
- `orders`, `order_items`
- `purchase_orders`, `purchase_order_items`
- `expenses`
- `maintenance_tickets`, `ticket_part_consumptions`
- `store_audits`
- `sync_queue`

---

## 🧪 الاختبارات

```bash
# Unit tests
flutter test

# Integration tests
flutter test integration_test/

# Static analysis
flutter analyze
dart format --set-exit-if-changed .
```

---

## 📦 النشر

### Android
1. وقّع التطبيق: `flutter build apk --release --split-per-abi`
2. أو ابني App Bundle: `flutter build appbundle --release`
3. ارفع `build/app/outputs/bundle/release/app-release.aab` إلى Google Play Console

### تحديثات OTA (اختياري)
استخدم **Shorebird** أو **CodePush** للتحديثات السريعة بدون مراجعة المتجر.

---

## 🐛 استكشاف الأخطاء

| المشكلة | الحل |
|----------|-------|
| `drift` migration error | امسح بيانات التطبيق أو زد `schemaVersion` |
| `build_runner` conflicts | `flutter clean && flutter pub get && build_runner build --delete-conflicting-outputs` |
| طباعة حرارية لا تعمل | تأكد من إقران الطابعة Bluetooth ومن دعمها ESC/POS |
| مزامنة لا تعمل | تحقق من `API_BASE_URL` ومن صحة JWT token |
| خط Cairo لا يظهر | تأكد من وجود ملفات الخط في `assets/fonts/` |

---

## 📄 الترخيص

هذا المشروع ملك لشركة **النماء** - جميع الحقوق محفوظة.

---

## 🤝 المساهمة

1. Fork المشروع
2. أنشئ branch للميزة: `git checkout -b feature/amazing-feature`
3. Commit التغييرات: `git commit -m 'Add amazing feature'`
4. Push للـ branch: `git push origin feature/amazing-feature`
5. افتح Pull Request

---

**تم بناء هذا التطبيق بـ ❤️ ليكون نسخة طبق الأصل من موقع النماء ERP يعمل بلا إنترنت**