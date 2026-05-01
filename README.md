Loyola Admissions — README
===========================

Overview
--------
This repository contains a small FastAPI backend and static frontend pages for the Loyola Degree College (YSRR) admissions site. The backend stores applications in MySQL and provides endpoints used by the website and admin dashboard.

Files of interest
- `main.py` - FastAPI backend (API endpoints: `/health`, `/apply`, `/applications`, static pages)
- `index.html` - Public admissions form and site
- `admin.html` - Admin dashboard (view/search/export applications)
- `config.js` - Frontend configuration for backend URL(s)
- `requirements.txt` - Python dependencies
- `render.yaml` - (Optional) Render deployment configuration

Prerequisites
-------------
- Windows 10/11 or Linux/macOS
- Python 3.10+ (this workspace used Python 3.14.3)
- MySQL server (local or remote) accessible to the backend
- Git (optional)

Quick setup (Windows PowerShell)
-------------------------------
1. Create & activate virtual environment (if not already created):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -r requirements.txt
```

3. Configure MySQL credentials (examples):

```powershell
$env:MYSQL_HOST = 'localhost'
$env:MYSQL_USER = 'root'
$env:MYSQL_PASSWORD = 'Baba@1531'
$env:MYSQL_DB = 'college'
```

Alternatively, set these environment variables in your system or in the host's process manager.

Database schema (MySQL)
-----------------------
Run this in your MySQL client to create the database and table used by the backend:

```sql
CREATE DATABASE IF NOT EXISTS college;
USE college;
CREATE TABLE IF NOT EXISTS admissions (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  email VARCHAR(255) NOT NULL,
  phone VARCHAR(20) NOT NULL,
  course VARCHAR(255) NOT NULL,
  submitted_at VARCHAR(255),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

Run the app (development)
-------------------------
Start the backend with Uvicorn (auto-reload):

```powershell
.\.venv\Scripts\python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Open pages in a browser:
- Public site: `http://localhost:8000` or `http://<your-laptop-ip>:8000` for mobile on same Wi‑Fi
- Admin dashboard: `http://localhost:8000/admin`

Frontend configuration
----------------------
`config.js` is used by the frontend to locate the backend API. It supports multiple fallback URLs in `window.API_BASE_URLS`.

Example `config.js` entries:

```js
// Try public deployment first, then LAN IP
window.API_BASE_URLS = [
  'https://your-public-backend.example.com',
  'http://10.179.54.212:8000'
];
window.API_BASE_URL = window.API_BASE_URLS[0] || '';
```

If you plan to use the site from different mobiles on the same network, ensure `API_BASE_URLS` includes your laptop LAN IP (e.g. `http://10.179.54.212:8000`). For global access from any mobile, deploy the backend publicly (Render, Heroku, etc.) and put that public URL first in `API_BASE_URLS`.

API endpoints
-------------
- `GET /health` — health status JSON
- `POST /apply` — accept application JSON {name,email,phone,course}
- `GET /applications` — list saved applications (admin)

Example curl (submit an application):

```bash
curl -X POST http://127.0.0.1:8000/apply \
  -H "Content-Type: application/json" \
  -d '{"name":"Test","email":"test@example.com","phone":"9000000000","course":"B.Sc - Data Science"}'

  -d '{"name":"Test","email":"test@example.com","phone":"9000000000","course":"B.Sc Data Science"}'
```

Admin & CSV export
------------------
- Open the admin dashboard at `/admin` to view, search, filter and export applications.
- The CSV exporter in the admin currently exports Name,Email,Phone,Course. You can modify `admin.html` to include `id` and `submitted_at` if needed.

Testing (smoke test)
--------------------
After starting the server, run a quick smoke test in PowerShell:

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8000/apply -Method Post -Body (ConvertTo-Json @{name='Automated Test'; email='auto@test.local'; phone='9990001112'; course='B.Sc Data Science'}) -ContentType 'application/json'
Invoke-RestMethod -UseBasicParsing -Uri http://127.0.0.1:8000/applications | ConvertTo-Json -Depth 5
```

Deployment notes
----------------
- `render.yaml` is included as a starting point for deploying the backend to Render (Python service + requirements install + uvicorn start). If you need, I can help set up a Render service and a managed MySQL/Planetscale/Remote DB and wire the connection string into the Render environment variables.

Contact & Support
-----------------
If you want additional changes (CSV format, remove test records, deploy public backend), tell me which task to perform next.

---
Generated on: 2026-05-01
