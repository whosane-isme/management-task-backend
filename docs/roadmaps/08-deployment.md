# 08 — Deployment

## المكونات

- حاوية API غير root وصورة صغيرة مثبتة dependencies.
- PostgreSQL managed إن أمكن.
- reverse proxy/load balancer ينهي TLS.
- migrations كخطوة release منفصلة قبل تشغيل النسخة الجديدة.
- secret manager وبيئات منفصلة development/staging/production.

## قبل الإطلاق

- [ ] نطاق HTTPS وGoogle redirect URIs النهائية.
- [ ] `DEBUG=false` وإغلاق docs أو حمايتها حسب سياسة المؤسسة.
- [ ] CORS/Trusted Hosts/Cookie attributes مضبوطة للنطاق الفعلي.
- [ ] health checks لا تكشف تفاصيل.
- [ ] logs ومقاييس وتنبيهات للأخطاء وlatency وفشل login.
- [ ] backup schedule واختبار restore.
- [ ] rollback للتطبيق والمهاجرات التوافقية.
- [ ] إنشاء أول manager بطريقة bootstrap موثقة وآمنة.

## التشغيل

- runbook للحوادث وإبطال الجلسات وتدوير الأسرار.
- سياسة احتفاظ للـactivity/logs والبيانات الشخصية.
- تحديثات dependencies دورية ومراجعة أمنية قبل الترقيات الكبرى.
