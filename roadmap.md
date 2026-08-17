# خارطة طريق Management Task Backend

## الهدف

بناء Backend داخلي سريع وآمن لإدارة مهام مؤسسة واحدة في النسخة الأولى. ينشئ المديرون المهام ويسندونها إلى موظف أو أكثر، ويتابع الموظفون العمل والتعليقات، ويسجل النظام تاريخ التغييرات تلقائيًا.

## قرارات V1 المعتمدة

- Modular monolith باستخدام FastAPI، وليس microservices.
- PostgreSQL مع SQLAlchemy 2 async وAlembic للمهاجرات.
- API تحت `/api/v1` منذ البداية.
- لا يوجد تسجيل عام ولا كلمات مرور محلية.
- Google OpenID Connect هو مزود الدخول الأول؛ GitHub مؤجل.
- هوية OAuth منفصلة عن سجل المستخدم حتى يمكن ربط أكثر من مزود مستقبلًا.
- جلسة خادمية عشوائية داخل Cookie محمية (`HttpOnly`, `Secure`, `SameSite`) بدل حفظ access token في `localStorage`.
- المؤسسة واحدة في V1. التحويل إلى SaaS متعدد المؤسسات يحتاج قرارًا وتصميمًا مستقلًا قبل الإنتاج.
- صلاحيات الواجهة لا تكفي؛ كل endpoint يفرض التفويض من الخادم.
- الحالات والقيم المقيدة تخزن كسلاسل مع قيود DB قابلة للمهاجرة.
- كل التواريخ UTC وtimezone-aware.

## ترتيب التنفيذ

| المرحلة | القسم | الحالة | شرط البدء |
|---|---|---:|---|
| 0 | [Foundation](docs/roadmaps/00-foundation.md) | مكتمل | — |
| 1 | [Data Model](docs/roadmaps/01-data-model.md) | مكتمل ومتحقق على PostgreSQL 17 | Foundation |
| 2 | [Users & Departments](docs/roadmaps/02-users-departments.md) | API الإدارة الأساسية منفذة ومتحققة | Data Model |
| 3 | [Authentication](docs/roadmaps/03-authentication.md) | مكتمل ومتحقق end-to-end محليًا | Users |
| 4 | [Tasks & Assignments](docs/roadmaps/04-tasks-assignments.md) | مكتمل ومتحقق على PostgreSQL 17 | Auth |
| 5 | [Authorization](docs/roadmaps/05-authorization.md) | مطبق على Admin API وكل عمليات المهام | Tasks |
| 6 | [Comments & Activity](docs/roadmaps/06-comments-activity.md) | مخطط | Authorization |
| 7 | [Security & Testing](docs/roadmaps/07-security-testing.md) | مستمر | كل مرحلة |
| 8 | [Deployment](docs/roadmaps/08-deployment.md) | مخطط | اكتمال V1 |

## معالم التسليم

### M0 — مشروع قابل للتشغيل

- [x] بنية الحزم، الإعدادات، logging، health endpoints.
- [x] اتصال PostgreSQL وجلسة DB لكل request.
- [x] فحوص lint واختبارات آلية أولية.
- [x] تعليمات تشغيل من جهاز جديد.

### M1 — قاعدة البيانات

- [x] Models وعلاقات وقيود وفهارس.
- [x] أول Alembic migration قابل للصعود والرجوع نظريًا وSQL offline.
- [x] تشغيل upgrade على PostgreSQL 17 حقيقي والوصول إلى Alembic head.
- [x] لا يستخدم التطبيق `create_all()` في التشغيل العادي.

### M2 — الهوية والإدارة

- [x] إنشاء الأقسام والمستخدمين وإيقافهم بواسطة manager فقط.
- [x] أمر آمن وidempotent لإنشاء أول Organization Manager قبل Google Login.
- [x] Google Authorization Code Flow مع PKCE و`state` و`nonce` في الكود.
- [x] ربط المستخدم المدعو بهوية Google ذات بريد موثّق في الكود.
- [x] جلسات قابلة للإبطال وتسجيل خروج فعلي في الكود.
- [x] اختبار end-to-end مع Google credentials وPostgreSQL حقيقيين.
- [x] تنقية query strings من access logs لحماية OAuth authorization codes.

### M3 — المهام والصلاحيات

- [x] إنشاء وقراءة وتعديل المهام والإسنادات مع pagination/filtering؛ الإلغاء بدل الحذف الصلب لحماية سجل التدقيق.
- [x] انتقالات حالة محددة وليست تحديثًا حرًا، وتشمل `IN_REVIEW` لمطابقة تدفق الواجهة.
- [x] تطبيق `PUBLIC / DEPARTMENT / PRIVATE` على كل قراءة وكتابة.
- [x] منع IDOR حتى عند تخمين IDs، مع إعادة `404` للمهمة غير المرئية.
- [x] طلب المساعدة وقبوله وحله دون توسيع visibility المهمة.
- [x] عروض `focus/all/hidden/pinned` وتفضيلات شخصية للعرض.

### M4 — التعاون والتدقيق

- [ ] تعليقات مرتبطة بالمهمة.
- [ ] Activity timeline غير قابل للتعديل عبر API عادي.
- [x] عمليات المهام والإسناد والمساعدة والتفضيلات تسجل audit event ضمن transaction واحدة.

### M5 — جاهزية الإنتاج

- [x] اختبارات integration حقيقية لمسارات المهام على PostgreSQL 17.
- [ ] فحص dependencies وsecrets وpermissions.
- [ ] HTTPS، migrations كخطوة نشر، backups، logging ومراقبة.
- [ ] runbook للاستعادة والrollback.

## ميزات مؤجلة بعد V1

- البريد والتنبيهات والمهام المجدولة.
- المرفقات، approvals، realtime chat، HR، التقارير، automations.
- GitHub login، SSO لمزودين إضافيين، ودعم عدة مؤسسات.

## قرارات المنتج المثبتة

1. V1 لمؤسسة واحدة وليست SaaS متعددة المؤسسات.
2. `PRIVATE` للمنشئ والمكلفين، مع وصول إداري صريح عبر `tasks.view_all` أو `tasks.view_private_department` ضمن النطاق.
3. الأدوار والصلاحيات قابلة للتخصيص، وإسناد الدور يكون للمؤسسة كلها أو لقسم.
4. الموظف يستطيع إنشاء مهمة لنفسه، ويحتاج صلاحية إضافية لإنشائها أو إسنادها للفريق.
5. تفضيلات hidden/pinned تنظم العرض ولا تغير authorization.
6. `IN_REVIEW` جزء من V1 لمطابقة لوحة العمل؛ `BLOCKED` ما زالت مؤجلة.

## بوابة قرار متبقية قبل Auth/Production

- تحديد frontend origins وأسماء النطاقات لتثبيت CORS وCookie وOAuth redirects بدقة.

## قاعدة الإنجاز لكل قسم

لا يعد القسم مكتملًا إلا عند وجود: migration عند الحاجة، validation، authorization، اختبارات نجاح وفشل، logging آمن، وتحديث الوثائق.
