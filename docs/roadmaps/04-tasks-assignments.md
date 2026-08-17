# 04 — Tasks & Assignments

## API مقترح

- `GET/POST /api/v1/tasks`
- `GET/PATCH /api/v1/tasks/{id}`
- `POST /api/v1/tasks/{id}/status`
- `POST /api/v1/tasks/{id}/assignments`
- `DELETE /api/v1/tasks/{id}/assignments/{user_id}`
- `POST/DELETE /api/v1/tasks/{id}/help-request`
- `PUT /api/v1/task-preferences/{task_id}`

## قواعد العمل

- الحالات: `TODO`, `IN_PROGRESS`, `DONE`, `CANCELLED`؛ تضاف `IN_REVIEW/BLOCKED` فقط بطلب مؤكد.
- الأولويات: `LOW`, `MEDIUM`, `HIGH`, `URGENT`.
- الانتقالات المسموحة معرفة مركزيًا وتراعي الدور والإسناد.
- الإسناد لا يتكرر، والمكلف يجب أن يكون نشطًا.
- مهمة `DEPARTMENT` تحتاج قسمًا، والمقترح أن يكون المكلف من القسم نفسه ما لم يملك المدير override واضحًا.
- تحديث المهمة يستخدم transaction واحدة ويسجل ActivityLog.
- القوائم تدعم cursor أو limit/offset محدود، filters، وفرزًا مسموحًا فقط.
- الموظف يملك افتراضيًا إنشاء مهمة لنفسه؛ إسنادها إلى الفريق يحتاج permission ذات نطاق مناسب.
- طلب المساعدة لا يوسع الرؤية بنفسه: إعلان مهمة خاصة يبقى خاصًا، وإعلان مهمة قسم يظهر للقسم.
- `hidden/pinned` تفضيلات عرض شخصية ولا تسحب الوصول الحقيقي للمهمة.
- الشاشة الافتراضية تستخدم `view=focus`: مهامي، ما أنشأته، وما ثبّتّه، مع استبعاد المخفي. `view=all` خيار صريح لمن يملك صلاحية الرؤية الشاملة.

## الاختبارات

إنشاء وتعديل وإسناد، transitions غير الصالحة، assignee معطل، due dates، سباق إسناد مكرر، وفلاتر القوائم.
