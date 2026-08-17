# 04 — Tasks & Assignments

## الحالة

مكتمل ومتحقق باختبارات تكامل على PostgreSQL 17.

## API المنفذ

- `GET/POST /api/v1/tasks`
- `GET/PATCH /api/v1/tasks/{id}`
- `POST /api/v1/tasks/{id}/status`
- `POST /api/v1/tasks/{id}/assignments`
- `DELETE /api/v1/tasks/{id}/assignments/{user_id}`
- `POST/DELETE /api/v1/tasks/{id}/help-request`
- `POST /api/v1/tasks/{id}/help-request/accept`
- `POST /api/v1/tasks/{id}/help-request/resolve`
- `PUT /api/v1/task-preferences/{task_id}`

## قواعد العمل

- الحالات: `TODO`, `IN_PROGRESS`, `IN_REVIEW`, `DONE`, `CANCELLED`. بقيت `BLOCKED` مؤجلة.
- الأولويات: `LOW`, `MEDIUM`, `HIGH`, `URGENT`.
- الانتقالات المسموحة معرفة مركزيًا وتراعي الدور والإسناد.
- الإسناد لا يتكرر، والمكلف يجب أن يكون نشطًا.
- مهمة `DEPARTMENT` تحتاج قسمًا، والمكلف من القسم نفسه ما لم يملك المدير `tasks.assign_any` بنطاق المؤسسة.
- تحديث المهمة يستخدم transaction واحدة ويسجل ActivityLog.
- القوائم تدعم cursor أو limit/offset محدود، filters، وفرزًا مسموحًا فقط.
- الموظف يملك افتراضيًا إنشاء مهمة لنفسه؛ إسنادها إلى الفريق يحتاج permission ذات نطاق مناسب.
- طلب المساعدة لا يوسع الرؤية بنفسه: إعلان مهمة خاصة يبقى خاصًا، وإعلان مهمة قسم يظهر للقسم.
- `hidden/pinned` تفضيلات عرض شخصية ولا تسحب الوصول الحقيقي للمهمة.
- الشاشة الافتراضية تستخدم `view=focus`: مهامي، ما أنشأته، وما ثبّتّه، مع استبعاد المخفي. `view=all` خيار صريح لمن يملك صلاحية الرؤية الشاملة.

لا يوجد حذف صلب للمهمة في V1 لأن ذلك يكسر سجل التدقيق؛ يستخدم `CANCELLED` ويمكن إعادة فتحها بانتقال مضبوط.

## الاختبارات المنفذة

- validation للتواريخ والحقول الإلزامية وتعارض hidden/pinned.
- رؤية المهمة الخاصة للمنشئ والمكلف فقط ومنع IDOR عن المستخدم غير المرتبط.
- انتقال `TODO → IN_PROGRESS → IN_REVIEW → DONE` ورفض الانتقال غير الصالح.
- إنشاء مهمة شخصية تلقائيًا وإسنادها إلى المنشئ.
- منع الموظف من إسناد زميل دون صلاحية.
- دورة طلب المساعدة وقبوله وحله.
- فلاتر focus/hidden/pinned على PostgreSQL حقيقي.
- downgrade/upgrade للمهاجرة `20260818_0003` على PostgreSQL 17.
