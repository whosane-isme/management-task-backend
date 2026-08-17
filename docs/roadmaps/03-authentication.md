# 03 — Authentication

## التصميم

Google OIDC باستخدام Authorization Code Flow مع PKCE. Google يثبت الهوية، لكن قاعدة بياناتنا تقرر السماح والدور.

## التدفق

1. `/auth/google/login` ينشئ `state`, `nonce`, وPKCE verifier ويربطها بمحاولة قصيرة العمر.
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

## الاختبارات

حالات state/nonce/audience/issuer/expiry الخاطئة، بريد غير موثق، مستخدم غير مدعو أو معطل، replay، logout، وانتهاء session.
