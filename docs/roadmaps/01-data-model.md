# 01 — Data Model

## الجداول الأساسية

- `departments`
- `users`
- `auth_identities`
- `roles`, `permissions`, `role_permissions`, `user_role_assignments`
- `tasks`
- `task_assignments`
- `task_view_preferences`
- `task_help_requests`
- `task_comments`
- `activity_logs`
- `sessions` عند تنفيذ المصادقة

## تصحيحات المخطط الأولي

- فصل `auth_provider/provider_id` إلى `auth_identities` يسمح بأكثر من مزود للمستخدم.
- استبدال enum الدور الثابت بأدوار وصلاحيات قابلة للتخصيص وإسناد ذي نطاق عام/قسم.
- إضافة Foreign Keys الناقصة من `activity_logs` إلى `tasks` و`users`.
- إضافة `is_active` للمستخدم بدل حذفه وفقدان التاريخ.
- إضافة unique مركب على `(provider, subject)` و`(task_id, user_id)`.
- إضافة فهارس على مفاتيح العلاقات وحقول البحث: status، due date، department، assignee.
- استخدام `TIMESTAMPTZ` وUTC، وقيود CHECK للقيم المقيدة.
- تحديد سياسات `ON DELETE`: غالبًا RESTRICT للسجلات ذات التاريخ، وCASCADE فقط للروابط التابعة الآمنة.

## المهام

- [x] تنفيذ SQLAlchemy models typed بأسلوب 2.0.
- [x] كتابة أول migration يدوي المراجعة.
- [x] إضافة قيود invariants، ومنها أن `DEPARTMENT` تتطلب `department_id`.
- [ ] اختبار upgrade من DB فارغة وdowngrade ثم upgrade.
- [x] إضافة diagram محدث بعد تثبيت المخطط.

## معيار الانتهاء

كل علاقة وnullable/delete policy لها سبب مكتوب، والمهاجرة تعمل على PostgreSQL حقيقي لا SQLite فقط.
