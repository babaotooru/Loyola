# 🚀 QUICK START REFERENCE

## ⚡ Start Backend (1 Command)

```bash
# In VS Code Terminal:
cd e:\Desktop\Loyola
.\.venv\Scripts\Activate.ps1
uvicorn main:app --host 127.0.0.1 --port 8001
```

Wait for:
```
✅ MySQL connected successfully!
INFO:     Uvicorn running on http://127.0.0.1:8001
```

## 🌐 Access Your System

- **Main Website**: http://127.0.0.1:8001
- **Admin Panel**: http://127.0.0.1:8001/admin
- **Health Check**: http://127.0.0.1:8001/health
- **Debug Status**: http://127.0.0.1:8001/debug/mysql-status

## 📋 What the System Does

1. **User submits form** on main website
2. **Backend saves to MySQL database** (not JSON file)
3. **Admin panel shows ALL applications** in real-time
4. **Data updates every 5 seconds** automatically
5. **All users see the same data**

## ✅ How to Verify It Works

### Step 1: Check Backend Health
```
curl http://127.0.0.1:8001/health
```
Should show: `"mysql": "connected"`

### Step 2: Submit Test Application
Go to: http://127.0.0.1:8001
- Fill out form
- Click Submit
- Should see: "✓ (MySQL Database)"

### Step 3: Check Admin Panel
Go to: http://127.0.0.1:8001/admin
- Should see your new application appear
- May take up to 5 seconds to show (auto-refresh)

## 📊 Test Data Currently in Database

```
✅ 1. Babao - babao@gmail.com - B.Sc Quantum Technologies
✅ 2. John Smith - john@example.com - B.Sc Computer Science
```

## 🔧 Common Commands

| Task | Command |
|------|---------|
| Start backend | `uvicorn main:app --host 127.0.0.1 --port 8001` |
| Check MySQL status | Visit `/debug/mysql-status` |
| Get all applications | Visit `/applications` endpoint or check admin panel |
| Submit application | Use form at `/` |
| View admin dashboard | Visit `/admin` |

## 🛑 Stop Backend

```bash
# In Terminal: Press Ctrl+C
```

## 🎯 Main Points

- ✅ MySQL is **CONNECTED**
- ✅ Data is stored in **DATABASE** (not JSON)
- ✅ Admin sees **ALL user data**
- ✅ Updates happen **REAL-TIME** (every 5 seconds)
- ✅ Each user sees **SAME data**

## 📝 Database Connection Details

- **Host**: localhost
- **User**: root  
- **Password**: Baba@1531
- **Database**: college
- **Table**: admissions

## ⚠️ If Something Goes Wrong

1. Check MySQL is running: `net start MySQL80`
2. Check port 8001 is free: `netstat -ano | findstr :8001`
3. Check `/debug/mysql-status` endpoint
4. Look at backend console logs for errors
5. Restart backend (Ctrl+C, then run start command again)

---

**Status**: ✅ READY TO USE
**Time to Use**: < 1 minute (start backend + go to http://127.0.0.1:8001)
