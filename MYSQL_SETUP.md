# MySQL Setup Guide - Loyola Admissions System

## Problem & Solution
Your admissions system was falling back to JSON file storage when MySQL wasn't available. **Updated**: The system now prioritizes MySQL for all data operations.

## ✅ What's Fixed
- **Priority Order**: Always uses MySQL when available (→ Fallback to JSON only if MySQL fails)
- **Real-time Admin Updates**: Admin panel refreshes every 5 seconds to show ALL user data from database
- **Better Logging**: Console shows when data is saved to MySQL vs JSON
- **Debug Endpoint**: New `/debug/mysql-status` endpoint to check MySQL connection

## 🔧 Verify MySQL Connection

### 1. Check Backend Health
Open in browser:
```
http://localhost:8000/health
```
or on your deployment URL:
```
https://loyola-rvgj.onrender.com/health
```

Expected response:
```json
{
  "status": "healthy",
  "mysql": "connected",
  "storage": "mysql",
  "timestamp": "2026-05-04T..."
}
```

### 2. Check MySQL Status (Debug)
```
http://localhost:8000/debug/mysql-status
```

Expected response:
```json
{
  "status": "✅ Connected",
  "host": "localhost",
  "database": "college",
  "user": "root",
  "total_applications": 4
}
```

## 🚨 If MySQL Not Connected

If you see:
```json
{
  "mysql": "disconnected",
  "storage": "file-based (JSON)"
}
```

### Solution: Verify MySQL Configuration

#### For Local Development:
1. **Start MySQL Server**:
   ```bash
   # Windows
   net start MySQL80
   
   # Or use XAMPP/WAMP if installed
   ```

2. **Create Database** (if not exists):
   ```sql
   CREATE DATABASE IF NOT EXISTS college;
   ```

3. **Check Credentials in main.py**:
   ```python
   MYSQL_HOST = "localhost"      # Change if on different server
   MYSQL_USER = "root"           # Your MySQL username
   MYSQL_PASSWORD = "Baba@1531"  # Your MySQL password
   MYSQL_DB = "college"          # Database name
   ```

4. **Test Connection**:
   ```bash
   python -c "
   import mysql.connector
   try:
       conn = mysql.connector.connect(
           host='localhost',
           user='root',
           password='Baba@1531',
           database='college'
       )
       print('✅ Connected to MySQL!')
       conn.close()
   except Exception as e:
       print(f'❌ Error: {e}')
   "
   ```

#### For Deployment (Render/Railway/Heroku):
1. **Add MySQL Service** (use Render's managed PostgreSQL or external MySQL)
2. **Set Environment Variables**:
   ```
   MYSQL_HOST=your-host.com
   MYSQL_USER=your-user
   MYSQL_PASSWORD=your-password
   MYSQL_DB=your-database
   ```

3. **Restart Backend**:
   - Push changes to GitHub
   - Render will auto-redeploy

## 📊 Test Data Flow

### 1. Submit Application (User)
- Go to: http://localhost:8000 (or your deployment URL)
- Fill out the form
- Should see: "✓ Your application has been submitted successfully! (MySQL Database)"

### 2. Check Admin Panel (Real-time)
- Go to: http://localhost:8000/admin
- Should see all applications in a table
- Panel **auto-refreshes every 5 seconds**
- All users see the **SAME data** from the database

### 3. Verify Data in Database
```sql
SELECT COUNT(*) FROM admissions;
SELECT * FROM admissions ORDER BY created_at DESC;
```

## 🔄 How It Works Now

```
User Submits Form
    ↓
Backend /apply endpoint
    ↓
✅ Try MySQL first (PRIMARY)
    ├─ Success → Store in Database ✓
    └─ Fail → Fallback to JSON (BACKUP)
    ↓
Admin Panel calls /applications every 5 seconds
    ↓
✅ Reads from MySQL (PRIMARY)
    ├─ Success → Show all database records
    └─ Fail → Fallback to JSON
    ↓
All Users See Same Data 🎯
```

## 📝 Environment Variables

Set these in your deployment platform:

```env
MYSQL_HOST=your-mysql-host
MYSQL_USER=your-username
MYSQL_PASSWORD=your-password
MYSQL_DB=college
```

For **Render.com**:
- Settings → Environment → Add these variables

For **Local Development**:
- Update `main.py` directly or set system environment variables

## 🎯 Key Features
- ✅ All data stored in MySQL database
- ✅ Admin panel shows **ALL user applications** in real-time
- ✅ Each user sees the same data (no isolated JSON files)
- ✅ Auto-refresh every 5 seconds
- ✅ Automatic fallback if MySQL fails
- ✅ Better error logging and debugging

## 📞 Troubleshooting

| Issue | Solution |
|-------|----------|
| Admin shows "No applications found" | Check `/debug/mysql-status` - MySQL may not be connected |
| "MySQL not available" in logs | Check credentials and that MySQL server is running |
| Different data on different clients | MySQL not connected - verify connection settings |
| Admin panel not auto-refreshing | Check browser console for errors, verify `/applications` endpoint works |

