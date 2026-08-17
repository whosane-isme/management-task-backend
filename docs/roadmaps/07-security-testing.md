# 07 — Security & Testing

## استراتيجية الاختبار

- Unit: transitions، policies، validation.
- API integration: FastAPI + PostgreSQL مع migrations فعلية.
- Security regression: IDOR، privilege escalation، mass assignment، CSRF/CORS، OAuth failures.
- Migration test: upgrade/downgrade وschema at head.

## ضوابط مستمرة

- أسرار من environment/secret manager فقط، و`.env` خارج Git.
- رسائل أخطاء لا تكشف stack أو DB؛ logs منظمة مع request ID ومن دون credentials.
- CORS origins صريحة، Trusted Hosts، HTTPS/HSTS في production.
- حدود payload وpagination وtimeouts وrate limits لمسارات حساسة.
- dependency scanning وsecret scanning في CI.
- أقل صلاحيات لمستخدم DB، ونسخ احتياطية مشفرة ومختبرة الاستعادة.
- مراجعة OWASP ASVS/API Security قبل الإطلاق.

## بوابات CI

- formatting وlint.
- tests وcoverage للسياسات الحرجة.
- type checking بعد استقرار الواجهات.
- migration check.
- dependency/secret scan.

## معيار الانتهاء

اختبارات الفشل لا تقل أهمية عن happy path، وكل permission bug مصلح يحصل على regression test.
