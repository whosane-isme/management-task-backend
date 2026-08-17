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
fastapi dev app/main.py
```

على Linux/macOS استبدل التفعيل بـ`source .venv/bin/activate` والنسخ بـ`cp .env.example .env`.

بعد التشغيل:

- API docs: `http://127.0.0.1:8000/docs`
- Liveness: `http://127.0.0.1:8000/api/v1/health/live`
- Readiness: `http://127.0.0.1:8000/api/v1/health/ready`

## الفحوصات

```powershell
ruff check .
ruff format --check .
pytest
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
