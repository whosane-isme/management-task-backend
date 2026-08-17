# 03 — Authentication

## التصميم

Google OIDC باستخدام Authorization Code Flow مع PKCE. Google يثبت الهوية، لكن قاعدة بياناتنا تقرر السماح والدور.

## حالة التنفيذ

- [x] Login/callback عبر Authlib وGoogle discovery.
- [x] PKCE S256 و`state` و`nonce` والتحقق المشفر من ID token.
- [x] قبول `email_verified=true` فقط وربط `sub` بمستخدم مدعو.
- [x] جلسة خادمية opaque؛ لا نخزن Google tokens ولا raw session token.
- [x] Cookie HttpOnly للجلسة وdouble-submit CSRF للطلبات المغيرة.
- [x] `/auth/me` وlogout مع إبطال سجل الجلسة.
- [x] Google OAuth Client credentials مضبوطة محليًا من صاحب المشروع.
- [x] تشغيل migrations على PostgreSQL حقيقي.
- [x] اختبار callback كامل بحساب Google بعد bootstrap لأول مدير.
- [x] منع تسجيل query string لمسار callback في Uvicorn access logs.

## التدفق

1. `/auth/google/login` ينشئ `state`, `nonce`, وPKCE verifier داخل Cookie قصيرة العمر موقعة وHttpOnly.
2. Google يعيد authorization code إلى callback مسجل حرفيًا.
3. الخادم يبدل code ويتحقق من توقيع ID token و`iss/aud/exp/nonce`.
4. يقبل فقط `email_verified=true` ويستخدم `sub` كهوية المزود الدائمة.
5. يربط الهوية بمستخدم نشط مدعو مسبقًا، ثم ينشئ session عشوائية مخزنة hash في DB.
6. المتصفح يستلم Cookie محمية؛ logout يبطل الجلسة في DB.

## متطلبات أمنية

- عدم قبول access token كإثبات هوية.
- عدم استخدام email وحده كمعرف Google الدائم.
- منع account-linking التلقائي إذا كانت الهوية مرتبطة بمستخدم آخر.
- تدوير session بعد login وتغيير الصلاحية، مع idle/absolute expiry.
- `Secure`, `HttpOnly`, `SameSite=Lax/Strict`, `Path=/` واسم `__Host-` في الإنتاج.
- حماية CSRF للعمليات المغيرة للحالة إذا كان frontend cross-origin.
- rate limiting لمسارات auth وعدم تسجيل tokens في logs.
- لا تُخزن access token أو ID token أو refresh token بعد اكتمال callback.

## الاختبارات

حالات state/nonce/audience/issuer/expiry الخاطئة، بريد غير موثق، مستخدم غير مدعو أو معطل، replay، logout، وانتهاء session.
