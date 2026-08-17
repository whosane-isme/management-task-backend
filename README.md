# Management Task Backend

FastAPI backend لإدارة مهام مؤسسة صغيرة. حالة المشروع وخطة كل قسم موثقة في [roadmap.md](roadmap.md).

## المتطلبات

- Python 3.12–3.14
- PostgreSQL

## تشغيل بيئة التطوير

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
docker compose up -d
.\.venv\Scripts\alembic.exe upgrade head
python -m app --reload
```

على Linux/macOS استبدل التفعيل بـ`source .venv/bin/activate` والنسخ بـ`cp .env.example .env`
وشغّل Alembic عبر `.venv/bin/alembic upgrade head`. أمر `python -m app` يضمن استخدام event loop
متوافق مع Psycopg على Windows أيضًا. يستخدم إعداد التطوير `127.0.0.1` لقاعدة البيانات عمدًا
لتفادي تعارض حلّ `localhost` مع Psycopg async على Windows.

بعد التشغيل:

- API docs: `http://127.0.0.1:8000/docs`
- Liveness: `http://127.0.0.1:8000/api/v1/health/live`
- Readiness: `http://127.0.0.1:8000/api/v1/health/ready`

قبل أول تسجيل دخول، أنشئ المدير مرة واحدة بالبريد نفسه المستخدم في حساب Google:

```powershell
python -m app.cli.bootstrap_manager --email manager@example.com --name "First Manager"
```

الأمر idempotent لنفس المدير، ويرفض إنشاء مدير ثانٍ؛ بعد ذلك تستخدم واجهة الأدوار المحمية.

## Admin API الأساسية

- `GET/POST /api/v1/departments`
- `GET/POST /api/v1/users`
- `POST /api/v1/users/{id}/deactivate`
- `POST /api/v1/users/{id}/role-assignments`
- `GET/POST /api/v1/roles`
- `GET /api/v1/roles/permissions`
- `PUT /api/v1/roles/{id}/permissions`

كل عمليات الكتابة تتطلب Cookie جلسة صالحة و`X-CSRF-Token`. إسناد الأدوار يتطلب
`users.manage` و`roles.manage` معًا.

## Tasks API

- `GET/POST /api/v1/tasks`
- `GET/PATCH /api/v1/tasks/{id}`
- `POST /api/v1/tasks/{id}/status`
- `POST /api/v1/tasks/{id}/assignments`
- `DELETE /api/v1/tasks/{id}/assignments/{user_id}`
- `POST/DELETE /api/v1/tasks/{id}/help-request`
- `POST /api/v1/tasks/{id}/help-request/accept`
- `POST /api/v1/tasks/{id}/help-request/resolve`
- `PUT /api/v1/task-preferences/{task_id}`

القائمة الافتراضية تستخدم `view=focus`. القيم الأخرى هي `all`, `hidden`, و`pinned`، مع فلاتر
للحالة والأولوية والرؤية والقسم والمنشئ والمكلّف والبحث. كل قراءة تمر أولًا عبر authorization
predicate، لذلك لا يستطيع فلتر العرض توسيع صلاحية الوصول.

حالات المهام هي `todo`, `in_progress`, `in_review`, `done`, و`cancelled`. لا يوجد حذف صلب
للمهمة في V1 حفاظًا على ActivityLog.

## الفحوصات

```powershell
ruff check .
ruff format --check .
pytest
```

اختبارات PostgreSQL التكاملية تعمل عند تعيين قاعدة اختبار مهاجرة ومنفصلة:

```powershell
$env:MANAGEMENT_TASK_TEST_DATABASE_URL="postgresql+psycopg://user:password@127.0.0.1:5432/management_task_test"
pytest -m integration
```

لا ترفع ملف `.env` أو أي OAuth secret إلى Git.

## إعداد Google Login

التطبيق يعمل دون Google credentials، لكن `/api/v1/auth/google/login` سيعيد `503` حتى إعدادها.

1. أنشئ OAuth Client من نوع **Web application** في Google Cloud Console.
2. أضف redirect URI للتطوير حرفيًا:
   `http://localhost:8000/api/v1/auth/google/callback`
3. ضع القيم في `.env` فقط:

```dotenv
APP_GOOGLE_CLIENT_ID=...
APP_GOOGLE_CLIENT_SECRET=...
APP_GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback
APP_OAUTH_STATE_SECRET=replace-with-a-long-random-value
```

لا ترسل الـclient secret في المحادثة ولا ترفعه إلى GitHub.

قيم `POSTGRES_*` و`APP_DATABASE_URL` في `.env.example` مخصصة للتطوير المحلي فقط؛ استخدم
أسرارًا مُدارة ومستخدم قاعدة محدود الصلاحيات في staging/production.
