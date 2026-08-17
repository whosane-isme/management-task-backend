# 05 — Authorization

## النموذج المعتمد

نستخدم RBAC للقدرات العامة، Scope للمؤسسة/القسم، وقرائن العلاقة بالمهمة للقرارات الدقيقة. لا نعتمد على مقارنة اسم الدور في endpoints.

### أدوار البداية

| الدور | النطاق المعتاد | الغرض |
|---|---|---|
| Organization Manager | المؤسسة | إدارة ورؤية شاملة، بما فيها المهام الخاصة لأغراض الإدارة والتدقيق |
| Department Manager | قسم | إدارة أعضاء ومهام القسم، مع صلاحية منفصلة لرؤية الخاص داخل القسم |
| Executive Assistant | المؤسسة أو قسم | تنظيم العرض والإسناد والمتابعة حسب permissions الممنوحة |
| Employee | المؤسسة/قسمه | مهامه، إنشاء مهمة لنفسه، التعليق وطلب المساعدة |

يمكن تعديل الأدوار وإنشاء غيرها. `display_order` للعرض فقط ولا يصنع hierarchy أمنية ضمنية.

### أمثلة Permission Codes

- `tasks.create_self`, `tasks.create_department`, `tasks.create_any`
- `tasks.assign_department`, `tasks.assign_any`
- `tasks.view_department`, `tasks.view_private_department`, `tasks.view_all`
- `tasks.manage_department`, `tasks.manage_all`
- `task_preferences.manage_others`
- `users.manage`, `departments.manage`, `roles.manage`

## التنفيذ

- [x] policy functions مركزية يعاد استخدامها في list/detail/write.
- [x] تطبيق filter على query نفسها، وليس جلب السجل ثم إخفاء الاستجابة فقط.
- عدم تسريب وجود سجل سري؛ استخدم 404 عندما يلزم.
- منع mass assignment: schemas منفصلة للإنشاء والتعديل والاستجابة.
- [x] اختبارات policy matrix لكل visibility والنطاقات الأساسية.
- [x] deny by default، وجمع permissions من كل role assignment صالح ضمن نطاق المورد.
- [x] تفضيلات الإخفاء لا تدخل دالة authorization ولا يمكن استعمالها للوصول إلى مهمة.
- [ ] اختبارات permission matrix على كل endpoint بعد إضافة routes.
