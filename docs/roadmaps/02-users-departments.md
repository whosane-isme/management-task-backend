# 02 — Users & Departments

## السلوك

المدير ينشئ الأقسام ويسجل الموظفين المسموح لهم بالدخول مسبقًا. لا يوجد endpoint عام لإنشاء حساب.

## حالة التنفيذ

- [x] Schemas والتحقق والتطبيع.
- [x] خدمات إنشاء الأقسام والمستخدمين والأدوار.
- [x] إسناد دور بنطاق المؤسسة أو قسم ومنع التكرار.
- [x] دور Employee افتراضي لكل مستخدم جديد.
- [x] حماية صلاحيات Organization Manager الحرجة.
- [x] Bootstrap آمن لأول Organization Manager، idempotent ويرفض إنشاء مدير ثانٍ.
- [x] Routes أساسية محمية للمستخدمين والأقسام والأدوار مع pagination وCSRF.
- [x] Integration read tests على PostgreSQL حقيقي بحساب Organization Manager.
- [ ] PATCH للتعديل وقوائم role assignments وحذف الإسناد.

## API مقترح

- `GET/POST /api/v1/departments`
- `GET/PATCH /api/v1/departments/{id}`
- `GET/POST /api/v1/users`
- `GET/PATCH /api/v1/users/{id}`
- `POST /api/v1/users/{id}/deactivate`
- `GET/POST/PATCH /api/v1/roles`
- `PUT /api/v1/roles/{id}/permissions`
- `POST/DELETE /api/v1/users/{id}/role-assignments`

## قواعد

- البريد normalized وفريد case-insensitively.
- تغيير الدور أو القسم عملية إدارية ومسجلة.
- تعطيل مستخدم يبطل جلساته، ولا يحذف نشاطه السابق.
- pagination إلزامية لقوائم المستخدمين والأقسام.
- لا يرجع API بيانات OAuth أو session secrets.
- الدور يمكن إسناده على مستوى المؤسسة أو داخل قسم محدد.
- ترتيب الدور للعرض الإداري لا يمنح صلاحيات تلقائيًا؛ الصلاحيات تأتي من `role_permissions` فقط.

## الاختبارات

- تكرار البريد/اسم القسم يفشل بتعارض مفهوم.
- الموظف لا ينشئ مستخدمًا ولا يرفع دوره.
- المستخدم المعطل لا يستطيع إنشاء جلسة جديدة.
- إسناد الأدوار يتطلب `users.manage` و`roles.manage` معًا لمنع رفع الصلاحيات.
