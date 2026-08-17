# 06 — Comments & Activity

## Comments

- من يرى المهمة يمكنه قراءة تعليقاتها.
- من يرى المهمة ويملك حسابًا نشطًا يمكنه التعليق.
- التعديل للكاتب فقط ضمن سياسة زمنية تحدد لاحقًا؛ الحذف المنطقي أفضل لحفظ سياق التدقيق.
- طول المحتوى محدود، ويعامل كنص غير موثوق؛ تعقيم HTML مسؤولية واضحة بين backend/frontend.

## Activity Log

- أحداث typed بدل جملة حرة فقط: `task.created`, `status.changed`, `assignee.added`…
- `actor_id` nullable للأحداث النظامية، و`task_id` بعلاقة صحيحة.
- `metadata` JSON محدود البنية ولا يخزن tokens أو أسرارًا أو نصوصًا حساسة بلا حاجة.
- لا توجد endpoints عامة لإنشاء/تعديل/حذف activity.
- الحدث وتغيير business يحفظان ضمن transaction واحدة.

## API

- `GET/POST /api/v1/tasks/{id}/comments`
- `PATCH/DELETE /api/v1/tasks/{id}/comments/{comment_id}`
- `GET /api/v1/tasks/{id}/activity`

## الاختبارات

صلاحية رؤية المهمة، ملكية التعليق، ترتيب timeline، pagination، وrollback يزيل التغيير والحدث معًا.
