# تصميم الصلاحيات والرؤية

## المبدأ

وجود صلاحية لرؤية المهمة لا يعني أنها يجب أن تملأ الشاشة دائمًا. لذلك نفصل:

1. **Authorization query** تحدد السجلات التي يحق للمستخدم الوصول إليها.
2. **View query** ترتب وتفلتر السجلات المصرح بها وفق `focus/all/hidden/pinned`.

لا يمكن لفلتر العرض توسيع نتيجة authorization.

## تركيب القرار

```text
permission from role
        +
role assignment scope (global or department)
        +
task attributes (visibility, department)
        +
relationship (creator, assignee)
        =
allow or deny
```

## PRIVATE

يسمح بالقراءة عند تحقق أحد الآتي:

- المستخدم هو المنشئ.
- المستخدم مكلّف بالمهمة.
- يملك `tasks.view_all` بنطاق المؤسسة.
- يملك `tasks.view_private_department` ودوره مسند إلى قسم المهمة.

مدير قسم IT يمكنه بهذا إنشاء مهمة خاصة وإسنادها لموظف واحد. بقية موظفي IT لا يرونها، بينما يبقى مدير المؤسسة قادرًا على التدقيق.

## تنظيم شاشة المدير

- `focus` افتراضي: المكلف بها، المنشأة بواسطته، المثبتة، وغير المخفية.
- `all`: كل ما تسمح به صلاحياته، بطلب صريح وفلاتر.
- `hidden`: العناصر التي أخفاها من شاشة التركيز.
- `pinned`: عناصر متابعة يختارها.

المساعد التنفيذي يستطيع تعديل تفضيلات مدير آخر فقط إذا كان لديه `task_preferences.manage_others`. نسجل المنفذ في `updated_by_id` وActivity/Audit مناسب.

## إنشاء الموظف وطلب المساعدة

- `tasks.create_self`: ينشئ مهمة ويُسند نفسه إليها ضمن transaction واحدة.
- `tasks.create_department`: ينشئ مهمة للقسم.
- الإسناد إلى غيره يحتاج `tasks.assign_department` أو `tasks.assign_any`.
- طلب المساعدة يسجل requester ورسالة وحالة. visibility الأصلية تحدد جمهور الطلب ولا تتحول المهمة الخاصة إلى إعلان عام تلقائيًا.
