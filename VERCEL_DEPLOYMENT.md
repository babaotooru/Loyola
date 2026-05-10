# Vercel Deployment Guide - Loyola Admissions System

## Quick Start for Vercel + Supabase Deployment

### Step 1: Prepare Your Project for Vercel

1. **Install Vercel CLI** (optional but recommended):
   ```bash
   npm install -g vercel
   ```

2. **Push your code to GitHub**:
   - Create a GitHub repository
   - Push your Loyola project to GitHub
   - Vercel will auto-detect it

### Step 2: Set Up Supabase Database

1. **Create Supabase Account**:
   - Go to https://supabase.com
   - Sign up with GitHub (recommended)
   - Create a new project
   - Select your region (closest to your users)

2. **Get Database Credentials**:
   - In Supabase dashboard → Settings → Database
   - Copy the connection string or note down:
     - Host: `db.XXXXX.supabase.co`
     - User: `postgres`
     - Password: (from "Reveal" button)
     - Database: `postgres`

### Step 3: Connect Your Project to Vercel

1. **Via Vercel Dashboard**:
   - Go to https://vercel.com/new
   - Select your GitHub repository
   - Click "Import"

2. **Or via Vercel CLI**:
   ```bash
   vercel
   ```

### Step 4: Set Environment Variables in Vercel

1. **Go to Vercel Dashboard** → Your Project → Settings → Environment Variables
2. **Preferred: set `DATABASE_URL`** (recommended)

   - Supabase provides a full connection URL. Add it to Vercel as `DATABASE_URL`.
   - Example (replace with your values):
     ```
     DATABASE_URL=postgresql://postgres:YourPassword@db.rcmzlebdcgysjdusgexq.supabase.co:5432/postgres
     ```

   Using `DATABASE_URL` enables the app to use Postgres (`psycopg2`) on deployment.

3. **Alternative: MySQL-style envs (backwards compatibility)**

   ```
   MYSQL_HOST=db.XXXXX.supabase.co
   MYSQL_USER=postgres
   MYSQL_PASSWORD=your-supabase-password
   MYSQL_DB=postgres
   ```

   These are accepted for compatibility, but `DATABASE_URL` is preferred.

### Step 5: Update Backend (if using PostgreSQL)

**Option A: Switch to PostgreSQL (Recommended)**

Replace your `main.py` database connection code:
```python
# Old MySQL:
# import mysql.connector

# New PostgreSQL:
import psycopg2

# Update connection:
conn = psycopg2.connect(
    host=os.getenv("DATABASE_URL"),  # Full connection string from Supabase
    database=os.getenv("MYSQL_DB", "postgres"),
    user=os.getenv("MYSQL_USER", "postgres"),
    password=os.getenv("MYSQL_PASSWORD"),
    connection_timeout=5
)
```

Add to requirements.txt:
```
psycopg2-binary
```

**Option B: Use MySQL-compatible Proxy (Keep existing code)**
- Supabase offers MySQL compatibility layer
- Keep your MySQL connection code unchanged
- Update credentials to point to Supabase MySQL proxy endpoint

### Step 6: Deploy and Test

1. **Trigger Deployment**:
   ```bash
   git push
   ```
   Vercel will automatically deploy

2. **Monitor Deployment**:
   - Check Vercel dashboard for build status
   - View logs if deployment fails

3. **Test Your App**:
   - Open your Vercel URL (https://your-project.vercel.app)
   - You should see the setup page if database isn't ready
   - Once environment variables are set, refresh and test login

### Step 7: Initialize Database Tables

On your **first successful deployment**:

1. **Access Backend Logs**:
   - Vercel Dashboard → Your Project → Deployments → Logs
   - Look for database initialization messages

2. **Or Manually Initialize** (if needed):
   - Connect via Supabase SQL Editor
   - Run setup SQL for tables (available in main.py)

## Troubleshooting

### Issue: "Can't connect to MySQL server on localhost:3306"

**Cause**: Environment variables not set or incorrect credentials

**Solution**:
1. Double-check Supabase credentials
2. Go to Vercel Settings → Environment Variables
3. Verify all 4 variables are set (MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB)
4. Redeploy by pushing new code or clicking "Redeploy" in Vercel dashboard

### Issue: "PostgreSQL: operator does not exist"

**Cause**: Still using MySQL connector code with PostgreSQL

**Solution**: Convert to PostgreSQL driver (Option A above) or use MySQL compatibility mode

### Issue: Connection Pool Exhausted

**Cause**: Too many concurrent connections

**Solution**: Add connection pooling or upgrade Supabase tier

## Environment Variable Reference

| Variable | Example | Where to Get |
|----------|---------|--------------|
| MYSQL_HOST | db.xyz.supabase.co | Supabase → Settings → Database |
| MYSQL_USER | postgres | Usually "postgres" for Supabase |
| MYSQL_PASSWORD | your-secure-password | Supabase → Database Password |
| MYSQL_DB | postgres | Usually "postgres" for Supabase |

## Local Testing Before Deployment

**Test locally with Supabase credentials**:

1. Update your `.env` file (if using python-dotenv):
   ```
   MYSQL_HOST=db.xyz.supabase.co
   MYSQL_USER=postgres
   MYSQL_PASSWORD=your-password
   MYSQL_DB=postgres
   ```

2. Start backend locally:
   ```bash
   python main.py
   ```

3. If connects successfully, you're ready to deploy!

## Need Help?

- **Supabase Documentation**: https://supabase.com/docs
- **Vercel Documentation**: https://vercel.com/docs
- **Python MySQL Docs**: https://dev.mysql.com/doc/connector-python/en/
- **PostgreSQL Docs**: https://www.postgresql.org/docs/

---

**Mobile Testing After Deployment**:
- Open your Vercel URL on mobile (https://your-project.vercel.app)
- Use Student/Admin login to test all flows
- Data should sync real-time across devices via cloud database
