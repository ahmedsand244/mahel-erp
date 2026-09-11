# دليل مقاسات رولمان البلي — Bearing Dimensions Tool

تطبيق ويب سريع (ملفات ثابتة فقط) — يعمل بفتح `index.html` مباشرة، بدون سيرفر وبدون إنترنت (بعد أول تحميل Tailwind CDN).

## التشغيل
- افتح `bearing-app/index.html` في المتصفح (دبل كليك)، أو:
- `python -m http.server` داخل فولدر `bearing-app` ثم افتح `http://localhost:8000`
- للموبايل: نفس الملف responsive بالكامل (mobile-first).

## المميزات
1. **بحث بالكود (Mode A):** autocomplete لحظي من قاعدة محلية (<10ms)، يدعم اللواحق `6204-2RS / 6301-ZZ / 6205-C3` مع شرح اللاحقة تلقائياً.
2. **بحث بالمقاس (Mode B):** حقول `d × D × B` + تفاوت `±` يعرض كل المطابقات.
3. **جدول شامل:** فلترة حسب النوع/الكود/المقاس.
4. **رسم هندسي SVG تفاعلي:** أسهم `d/D/B` تتحدث بالأرقام الحقيقية.
5. **مطابقات الشركات:** SKF / FAG / NSK / NTN / Koyo / Nachi (نفس المقاس باختلاف كود الغطاء).
6. **مقارنة حتى 3 بليات:** drawer + زر عائم.
7. **نسخ + طباعة/PDF + حفظ PNG + مشاركة WhatsApp.**
8. **عربي/إنجليزي (RTL/LTR) + دارك/لايت** — محفوظة في `localStorage`.
9. **قاعدة بيانات محلية:** `data.js` — سلاسل `6000/6200/6300/6800/6900/16000 + Miniature + Tapered 302/303/320/322 + Angular + Spherical + UC`.

## الملفات
| ملف | دور |
|---|---|
| `index.html` | الواجهة (Tailwind + SVG + RTL) |
| `styles.css` | Glassmorphism + طباعة |
| `data.js` | قاعدة البيانات + اللواحق + الشركات |
| `app.js` | البحث + i18n + المقارنة + التصدير |

## إضافة مقاسات
أضف سطراً في `data.js` داخل `window.BEARINGS`:
```js
{code:"6214", d:70, D:125, B:24, type:"deep"},
```
الأنواع: `deep mini thin thin16000 tapered angular spherical insert`.
