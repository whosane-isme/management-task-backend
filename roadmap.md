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
| 1 | [Data Model](docs/roadmaps/01-data-model.md) | منفذ؛ تحقق PostgreSQL معلّق | Foundation |
| 2 | [Users & Departments](docs/roadmaps/02-users-departments.md) | Services منفذة؛ API ينتظر Auth | Data Model |
| 3 | [Authentication](docs/roadmaps/03-authentication.md) | مخطط | Users |
| 4 | [Tasks & Assignments](docs/roadmaps/04-tasks-assignments.md) | مخطط | Auth |
| 5 | [Authorization](docs/roadmaps/05-authorization.md) | المحرك الأساسي منفذ | Tasks |
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
- [ ] تشغيل upgrade/downgrade على PostgreSQL حقيقي (غير مثبت على هذا الجهاز).
- [ ] لا يستخدم التطبيق `create_all()` في التشغيل العادي.

### M2 — الهوية والإدارة

- [ ] إنشاء الأقسام والمستخدمين وإيقافهم بواسطة manager فقط.
- [ ] Google Authorization Code Flow مع PKCE و`state` و`nonce`.
- [ ] ربط المستخدم المدعو بهوية Google ذات بريد موثّق.
- [ ] جلسات قابلة للإبطال وتسجيل خروج فعلي.

### M3 — المهام والصلاحيات

- [ ] CRUD للمهام والإسنادات مع pagination/filtering.
- [ ] انتقالات حالة محددة وليست تحديثًا حرًا.
- [ ] تطبيق `PUBLIC / DEPARTMENT / PRIVATE` على كل قراءة وكتابة.
- [ ] منع IDOR حتى عند تخمين IDs.

### M4 — التعاون والتدقيق

- [ ] تعليقات مرتبطة بالمهمة.
- [ ] Activity timeline غير قابل للتعديل عبر API عادي.
- [ ] عمليات business + audit event ضمن transaction واحدة.

### M5 — جاهزية الإنتاج

- [ ] اختبارات integration حقيقية على PostgreSQL.
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

## بوابة قرار متبقية قبل Auth/Production

- تحديد frontend origins وأسماء النطاقات لتثبيت CORS وCookie وOAuth redirects بدقة.

## قاعدة الإنجاز لكل قسم

لا يعد القسم مكتملًا إلا عند وجود: migration عند الحاجة، validation، authorization، اختبارات نجاح وفشل، logging آمن، وتحديث الوثائق.
