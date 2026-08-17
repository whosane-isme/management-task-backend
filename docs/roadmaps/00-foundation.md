# 00 — Foundation

## النتيجة المطلوبة

تطبيق FastAPI صغير قابل للتشغيل والاختبار، مع إعدادات typed، API versioning، اتصال DB async، وإغلاق الموارد بصورة سليمة.

## المهام

- [x] إعداد `pyproject.toml` وحزم runtime/dev.
- [x] إنشاء `app/main.py` وapplication factory وlifespan.
- [x] إنشاء `/health/live` و`/health/ready`.
- [x] إعداد `pydantic-settings` و`.env.example` مع منع تسريب secrets.
- [x] إعداد SQLAlchemy async engine وsession مستقلة لكل request.
- [x] إعداد CORS بقائمة صريحة ومنع wildcard مع credentials.
- [x] إعداد pytest وRuff.
- [x] README للتشغيل على Windows/Linux.
- [x] تهيئة Git محليًا وإضافة `.gitignore`.

## اختبارات القبول

- import للتطبيق لا يتصل بقاعدة البيانات.
- `/health/live` يعيد 200 بلا DB.
- `/health/ready` يعيد 200 عند توفر DB و503 دون كشف تفاصيل عند تعذرها.
- OpenAPI يعرض المسارات تحت `/api/v1`.
- `ruff check`, `ruff format --check`, و`pytest` تنجح.

## خارج النطاق

Models العمل، OAuth، وCRUD.
