Loyola Admissions Portal (MySQL + Auth)
======================================

Overview
--------
This project now uses a login-first admissions workflow:
1. Student creates account (email + phone + password) in MySQL.
2. Student logs in with email or phone + password.
3. Student submits admission form.
4. Loyola admin logs in and sees live data in admin dashboard.

All records are stored in MySQL. No JSON fallback is used.

Key Files
---------
- main.py: FastAPI backend (auth + admissions + admin APIs)
- index.html: Login portal + student application workspace
- admin.html: Admin-only dashboard (applications + account list)
- config.js: Backend URL resolution
- frontend/index.html and frontend/admin.html: synced copies for static hosting

Required Software
-----------------
- Python 3.10+
- MySQL server

Install
-------
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -r requirements.txt
```

MySQL Setup
-----------
Set environment variables (or edit system env):

```powershell
$env:MYSQL_HOST = 'localhost'
$env:MYSQL_USER = 'root'
$env:MYSQL_PASSWORD = 'Baba@1531'
$env:MYSQL_DB = 'college'
```

Run the backend once; tables are auto-created:
- accounts
- sessions
- admissions

Default Admin Credentials
-------------------------
- User ID: Loyola admin
- Password: Loyola@2004

These are auto-seeded in MySQL if not present.

Run
---
```powershell
net start MySQL80
.\.venv\Scripts\Activate.ps1
uvicorn main:app --host 127.0.0.1 --port 8002 --reload
```

Open
----
- Portal: http://127.0.0.1:8002
- Admin dashboard: http://127.0.0.1:8002/admin
- Health: http://127.0.0.1:8002/health
- MySQL status: http://127.0.0.1:8002/debug/mysql-status

Authentication API
------------------
- POST /auth/register
- POST /auth/login
- POST /admin/login
- GET /auth/me
- POST /auth/logout

Admissions API
--------------
- POST /apply (student token required)
- GET /applications (admin token required)
- GET /admin/accounts (admin token required)

Storage Behavior
----------------
- Student accounts are saved in MySQL accounts table.
- Session tokens are saved in MySQL sessions table (hashed tokens).
- Application records are saved in MySQL admissions table.
- Old admissions seed rows were removed; new rows come only from logged-in student submissions.

Notes
-----
- Keep the public backend URL first in config.js for production.
- Local fallback includes http://127.0.0.1:8002.
