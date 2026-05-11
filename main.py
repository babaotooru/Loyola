from datetime import datetime, timedelta
from typing import Optional
from fastapi import FastAPI, HTTPException, Header, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import base64
import hashlib
import hmac
import os
import secrets
import socket
from urllib.parse import quote, urlparse

import psycopg2
import psycopg2.extras
from psycopg2 import OperationalError as PGOperationalError

app = FastAPI()


def get_allowed_origins() -> list[str]:
    # Comma-separated origins in env, e.g. https://site1.vercel.app,https://site2.vercel.app
    raw = os.environ.get("ALLOWED_ORIGINS", "")
    items = [origin.strip() for origin in raw.split(",") if origin.strip()]
    defaults = [
        "https://loyola-rho.vercel.app",
        "https://loyola.vercel.app",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ]
    seen = set()
    ordered = []
    for origin in items + defaults:
        if origin not in seen:
            ordered.append(origin)
            seen.add(origin)
    return ordered


app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Base paths and config
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


@app.on_event("startup")
def startup_event():
    # Ensure schema and default admin account are present on each server start.
    init_mysql()


def load_env_file(env_path: str) -> None:
    if not os.path.exists(env_path):
        return
    try:
        with open(env_path, "r", encoding="utf-8") as env_file:
            for raw_line in env_file:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key:
                    os.environ[key] = value
    except Exception:
        return


load_env_file(os.path.join(BASE_DIR, ".env"))

# Database initialization is handled in the FastAPI startup event.
# Compatibility names and defaults
SESSION_DAYS = int(os.environ.get("SESSION_DAYS", "7"))
DEFAULT_ADMIN_USERNAME = os.environ.get("DEFAULT_ADMIN_USERNAME", "Loyola admin")
DEFAULT_ADMIN_PASSWORD = os.environ.get("DEFAULT_ADMIN_PASSWORD", "Loyola@2004")

# State flags
mysql_available = False
mysql_connection_error = None


# Simple error alias for older code
Error = Exception


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def hash_password(password: str) -> str:
    salt = secrets.token_hex(8)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
    return f"{salt}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, hexhash = stored.split("$", 1)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
        return dk.hex() == hexhash
    except Exception:
        return False


def normalize_postgres_dsn(dsn: str) -> str:
    if not dsn or "://" not in dsn or "@" not in dsn:
        return dsn

    scheme, remainder = dsn.split("://", 1)
    if "@" not in remainder:
        return dsn

    userinfo, hostpart = remainder.rsplit("@", 1)
    if ":" not in userinfo:
        return dsn

    username, password = userinfo.split(":", 1)
    encoded_password = quote(password, safe="")
    return f"{scheme}://{username}:{encoded_password}@{hostpart}"


def resolve_ipv4_host(hostname: str) -> Optional[str]:
    try:
        candidates = socket.getaddrinfo(hostname, None, socket.AF_INET, socket.SOCK_STREAM)
        for candidate in candidates:
            address = candidate[4][0]
            if address:
                return address
    except Exception:
        return None
    return None


def build_postgres_connection_settings() -> dict:
    load_env_file(os.path.join(BASE_DIR, ".env"))

    host = os.environ.get("SUPABASE_DB_HOST")
    port = os.environ.get("SUPABASE_DB_PORT")
    dbname = os.environ.get("SUPABASE_DB_NAME")
    user = os.environ.get("SUPABASE_DB_USER")
    password = os.environ.get("SUPABASE_DB_PASSWORD")
    sslmode = os.environ.get("SUPABASE_DB_SSLMODE", os.environ.get("PGSSLMODE", "require"))

    if host and user and password and dbname:
        settings = {
            "host": host,
            "port": int(port) if port else 5432,
            "dbname": dbname,
            "user": user,
            "password": password,
            "sslmode": sslmode,
            "connect_timeout": 10,
            "cursor_factory": psycopg2.extras.RealDictCursor,
        }
        ipv4_host = resolve_ipv4_host(host)
        if ipv4_host:
            settings["hostaddr"] = ipv4_host
        return settings

    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise PGOperationalError("DATABASE_URL not set")

    normalized_dsn = normalize_postgres_dsn(dsn)
    parsed = urlparse(normalized_dsn)
    settings = {
        "dbname": parsed.path.lstrip("/") or None,
        "user": parsed.username,
        "password": parsed.password,
        "port": parsed.port or 5432,
        "connect_timeout": 10,
        "sslmode": sslmode,
        "cursor_factory": psycopg2.extras.RealDictCursor,
    }
    ipv4_host = resolve_ipv4_host(parsed.hostname or "")
    if ipv4_host:
        settings["host"] = parsed.hostname
        settings["hostaddr"] = ipv4_host
    else:
        settings["host"] = parsed.hostname
    return settings


def get_server_connection():
    return psycopg2.connect(**build_postgres_connection_settings())


def get_mysql_connection():
    try:
        return get_server_connection()
    except Exception:
        return None


def init_mysql():
    """Initialize Postgres schema and ensure admin exists."""
    global mysql_available, mysql_connection_error
    has_database_url = bool(os.environ.get("DATABASE_URL"))
    has_supabase_parts = bool(
        os.environ.get("SUPABASE_DB_HOST")
        and os.environ.get("SUPABASE_DB_USER")
        and os.environ.get("SUPABASE_DB_PASSWORD")
        and os.environ.get("SUPABASE_DB_NAME")
    )

    if not has_database_url and not has_supabase_parts:
        mysql_available = False
        mysql_connection_error = "Postgres credentials are not configured"
        print("⚠️ Postgres credentials are missing; skipping DB init.")
        return False

    try:
        print("🔄 Attempting Postgres connection...")
        conn = get_server_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS accounts (
                id SERIAL PRIMARY KEY,
                full_name VARCHAR(255) NOT NULL,
                username VARCHAR(255) UNIQUE,
                email VARCHAR(255) UNIQUE,
                phone VARCHAR(20) UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(20) NOT NULL DEFAULT 'student',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash VARCHAR(64) PRIMARY KEY,
                account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
                role VARCHAR(20) NOT NULL,
                expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS admissions (
                id SERIAL PRIMARY KEY,
                account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) NOT NULL,
                phone VARCHAR(20) NOT NULL,
                course VARCHAR(255) NOT NULL,
                submitted_at TIMESTAMP WITH TIME ZONE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
            )
            """
        )

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_account ON sessions(account_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_role ON sessions(role)")

        cursor.execute("SELECT id FROM accounts WHERE role = 'admin' LIMIT 1")
        admin_row = cursor.fetchone()
        if not admin_row:
            cursor.execute(
                "INSERT INTO accounts (full_name, username, email, phone, password_hash, role) VALUES (%s, %s, %s, %s, %s, 'admin')",
                (DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_USERNAME, None, None, hash_password(DEFAULT_ADMIN_PASSWORD)),
            )
        else:
            admin_id = admin_row["id"] if isinstance(admin_row, dict) else admin_row[0]
            cursor.execute(
                """
                UPDATE accounts
                SET full_name = %s,
                    username = %s,
                    password_hash = %s
                WHERE id = %s
                """,
                (DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_USERNAME, hash_password(DEFAULT_ADMIN_PASSWORD), admin_id),
            )

        conn.commit()
        cursor.close()
        conn.close()

        mysql_available = True
        mysql_connection_error = None
        print("✅ Postgres connected and schema verified/created.")
        return True
    except Exception as e:
        mysql_available = False
        mysql_connection_error = str(e)
        print(f"⚠️ DB initialization failed, continuing without live DB: {e}")
        return False



def create_session(account_id: int, role: str) -> str:
    token = secrets.token_urlsafe(32)
    token_hash = hash_token(token)
    expires_at = datetime.now() + timedelta(days=SESSION_DAYS)

    conn = get_mysql_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="Could not connect to database")

    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO sessions (token_hash, account_id, role, expires_at) VALUES (%s, %s, %s, %s)",
            (token_hash, account_id, role, expires_at),
        )
        conn.commit()
        cursor.close()
        conn.close()
        return token
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=f"Failed to create session: {e}")



def get_account_from_token(authorization: Optional[str]) -> dict:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization token")

    token = authorization.strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()

    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")

    conn = get_mysql_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="Could not connect to database")

    token_hash = hash_token(token)

    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(
            """
            SELECT s.token_hash, s.account_id, s.role, s.expires_at,
                   a.id, a.full_name, a.username, a.email, a.phone, a.role AS account_role, a.created_at
            FROM sessions s
            INNER JOIN accounts a ON a.id = s.account_id
            WHERE s.token_hash = %s
            LIMIT 1
            """,
            (token_hash,),
        )
        session = cursor.fetchone()

        if not session:
            cursor.close()
            conn.close()
            raise HTTPException(status_code=401, detail="Invalid or expired session")

        expires_at = session["expires_at"]
        # Handle both timezone-aware and naive timestamps from Postgres.
        now = datetime.now(expires_at.tzinfo) if expires_at and getattr(expires_at, "tzinfo", None) else datetime.now()
        if expires_at and expires_at < now:
            cursor.execute("DELETE FROM sessions WHERE token_hash = %s", (token_hash,))
            conn.commit()
            cursor.close()
            conn.close()
            raise HTTPException(status_code=401, detail="Session expired")

        account = {
            "id": session["id"],
            "full_name": session["full_name"],
            "username": session["username"],
            "email": session["email"],
            "phone": session["phone"],
            "role": session["account_role"],
            "created_at": session["created_at"],
        }

        cursor.close()
        conn.close()
        return account
    except HTTPException:
        raise
    except Error as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))



def serialize_account(account: dict) -> dict:
    return {
        "id": account["id"],
        "full_name": account["full_name"],
        "username": account.get("username"),
        "email": account.get("email"),
        "phone": account.get("phone"),
        "role": account["role"],
        "created_at": account.get("created_at"),
    }



def serialize_application(application: dict) -> dict:
    return {
        "id": application["id"],
        "account_id": application["account_id"],
        "name": application["name"],
        "email": application["email"],
        "phone": application["phone"],
        "course": application["course"],
        "submitted_at": application["submitted_at"],
        "created_at": application["created_at"],
        "account_role": application.get("account_role"),
        "account_full_name": application.get("account_full_name"),
    }



def require_student_account(authorization: Optional[str] = Header(default=None)) -> dict:
    account = get_account_from_token(authorization)
    if account["role"] != "student":
        raise HTTPException(status_code=403, detail="Student access required")
    return account



def require_admin_account(authorization: Optional[str] = Header(default=None)) -> dict:
    account = get_account_from_token(authorization)
    if account["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return account


@app.get("/")
def home():
    return FileResponse(os.path.join(BASE_DIR, "index.html"))


@app.get("/index.html")
def home_html():
    return FileResponse(os.path.join(BASE_DIR, "index.html"))


@app.get("/admin")
def admin_page():
    return FileResponse(os.path.join(BASE_DIR, "admin.html"))


@app.get("/admin/")
def admin_page_slash():
    return FileResponse(os.path.join(BASE_DIR, "admin.html"))


@app.get("/admin.html")
def admin_page_html():
    return FileResponse(os.path.join(BASE_DIR, "admin.html"))


@app.get("/photo.png")
def college_photo():
    return FileResponse(os.path.join(BASE_DIR, "photo.png"))


@app.get("/static/photo.png")
def college_photo_static():
    return FileResponse(os.path.join(BASE_DIR, "photo.png"))


@app.get("/config.js")
def config_js():
    return FileResponse(os.path.join(BASE_DIR, "config.js"))


@app.get("/student-register")
def student_register_page():
    return FileResponse(os.path.join(BASE_DIR, "student-register.html"))


@app.get("/student-register.html")
def student_register_page_html():
    return FileResponse(os.path.join(BASE_DIR, "student-register.html"))


@app.get("/student-login")
def student_login_page():
    return FileResponse(os.path.join(BASE_DIR, "student-login.html"))


@app.get("/student-login.html")
def student_login_page_html():
    return FileResponse(os.path.join(BASE_DIR, "student-login.html"))


@app.get("/admin-login")
def admin_login_page():
    return FileResponse(os.path.join(BASE_DIR, "admin-login.html"))


@app.get("/admin-login.html")
def admin_login_page_html():
    return FileResponse(os.path.join(BASE_DIR, "admin-login.html"))


@app.get("/student-application")
def student_application_page():
    return FileResponse(os.path.join(BASE_DIR, "student-application.html"))


@app.get("/student-application.html")
def student_application_page_html():
    return FileResponse(os.path.join(BASE_DIR, "student-application.html"))


class ApplicationRequest(BaseModel):
    name: str
    email: str
    phone: str
    course: str


class StudentRegister(BaseModel):
    full_name: str
    email: str
    phone: str
    password: str


class StudentLogin(BaseModel):
    identifier: str
    password: str


class AdminLogin(BaseModel):
    username: str
    password: str


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "storage": "postgres",
        "database": "configured" if os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_HOST") else "not configured",
        "database_error": None,
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/health/live")
def health_live():
    """Live database connectivity check."""
    conn = get_mysql_connection()
    if not conn:
        return {
            "status": "degraded",
            "storage": "postgres",
            "database": "offline",
            "timestamp": datetime.now().isoformat(),
        }

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
        conn.close()
        return {
            "status": "healthy",
            "storage": "postgres",
            "database": "online",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception:
        try:
            conn.close()
        except Exception:
            pass
        return {
            "status": "degraded",
            "storage": "postgres",
            "database": "offline",
            "timestamp": datetime.now().isoformat(),
        }


@app.get("/debug/mysql-status")
def mysql_status():
    """Debug endpoint to check database configuration."""
    return {
        "status": "configured" if os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_HOST") else "not configured",
        "storage": "postgres",
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/auth/me")
def auth_me(authorization: Optional[str] = Header(default=None)):
    account = get_account_from_token(authorization)
    return {
        "success": True,
        "account": serialize_account(account),
    }


@app.post("/auth/register")
def auth_register(payload: StudentRegister):
    full_name = payload.full_name.strip()
    email = payload.email.strip().lower()
    phone = payload.phone.strip()
    password = payload.password.strip()

    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters long")

    if not full_name or not email or not phone:
        raise HTTPException(status_code=400, detail="Name, email and phone are required")

    conn = get_mysql_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="Could not connect to database")

    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM accounts WHERE LOWER(email) = %s OR phone = %s LIMIT 1",
            (email, phone),
        )
        existing = cursor.fetchone()
        if existing:
            cursor.close()
            conn.close()
            raise HTTPException(status_code=409, detail="An account with this email or phone already exists")

        cursor.execute(
            """
            INSERT INTO accounts (full_name, email, phone, password_hash, role)
            VALUES (%s, %s, %s, %s, 'student') RETURNING id
            """,
            (full_name, email, phone, hash_password(password)),
        )
        row = cursor.fetchone()
        account_id = row['id'] if isinstance(row, dict) else row[0]
        conn.commit()
        cursor.close()
        conn.close()

        token = create_session(account_id, "student")
        return {
            "success": True,
            "message": "Account created successfully",
            "token": token,
            "token_type": "Bearer",
            "account": {
                "id": account_id,
                "full_name": full_name,
                "email": email,
                "phone": phone,
                "role": "student",
            },
        }
    except HTTPException:
        raise
    except Error as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/auth/login")
def auth_login(payload: StudentLogin):
    identifier = payload.identifier.strip()
    password = payload.password.strip()

    if not identifier or not password:
        raise HTTPException(status_code=400, detail="Identifier and password are required")

    conn = get_mysql_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="Could not connect to database")

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, full_name, email, phone, password_hash, role, created_at
            FROM accounts
            WHERE role = 'student' AND (LOWER(email) = %s OR phone = %s)
            LIMIT 1
            """,
            (identifier.lower(), identifier),
        )
        account = cursor.fetchone()

        if not account or not verify_password(password, account["password_hash"]):
            cursor.close()
            conn.close()
            raise HTTPException(status_code=401, detail="Invalid login credentials")

        token = create_session(account["id"], "student")
        cursor.close()
        conn.close()
        return {
            "success": True,
            "message": "Login successful",
            "token": token,
            "token_type": "Bearer",
            "account": {
                "id": account["id"],
                "full_name": account["full_name"],
                "email": account["email"],
                "phone": account["phone"],
                "role": account["role"],
                "created_at": account["created_at"],
            },
        }
    except HTTPException:
        raise
    except Error as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/admin/login")
def admin_login(payload: AdminLogin):
    username = payload.username.strip()
    password = payload.password.strip()

    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password are required")

    conn = get_mysql_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="Could not connect to database")

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, full_name, username, email, phone, password_hash, role, created_at
            FROM accounts
            WHERE role = 'admin' AND username = %s
            LIMIT 1
            """,
            (username,),
        )
        account = cursor.fetchone()

        if not account or not verify_password(password, account["password_hash"]):
            cursor.close()
            conn.close()
            raise HTTPException(status_code=401, detail="Invalid admin credentials")

        token = create_session(account["id"], "admin")
        cursor.close()
        conn.close()
        return {
            "success": True,
            "message": "Admin login successful",
            "token": token,
            "token_type": "Bearer",
            "account": {
                "id": account["id"],
                "full_name": account["full_name"],
                "username": account["username"],
                "email": account["email"],
                "phone": account["phone"],
                "role": account["role"],
                "created_at": account["created_at"],
            },
        }
    except HTTPException:
        raise
    except Error as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/auth/logout")
def auth_logout(authorization: Optional[str] = Header(default=None)):
    if not authorization:
        return {"success": True, "message": "Logged out"}

    token = authorization.strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()

    if not token:
        return {"success": True, "message": "Logged out"}

    conn = get_mysql_connection()
    if not conn:
        return {"success": True, "message": "Logged out"}

    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sessions WHERE token_hash = %s", (hash_token(token),))
        conn.commit()
        cursor.close()
        conn.close()
    except Error:
        conn.close()

    return {"success": True, "message": "Logged out"}


@app.post("/apply")
def apply(application: ApplicationRequest, current_account: dict = Depends(require_student_account)):
    """Save student application data to Supabase/Postgres."""
    try:
        name = application.name.strip()
        email = application.email.strip().lower()
        phone = application.phone.strip()
        course = application.course.strip()

        if not name or not email or not phone or not course:
            raise HTTPException(status_code=400, detail="Name, email, phone and course are required")

        submitted_at = datetime.now().isoformat()

        conn = get_mysql_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Could not connect to database")

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO admissions (account_id, name, email, phone, course, submitted_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    current_account["id"],
                    name,
                    email,
                    phone,
                    course,
                    submitted_at,
                ),
            )
            conn.commit()
            cursor.close()
            conn.close()

            print(f"✅ Application saved to database: {name} ({email})")
            return {
                "success": True,
                "message": "Application saved successfully to database",
                "storage": "postgres",
                "submitted_at": submitted_at,
            }
        except Error as e:
            conn.close()
            print(f"❌ Postgres save error: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to save application to database: {e}")
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in apply: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/applications")
def get_data(_current_account: dict = Depends(require_admin_account)):
    """Get all applications from MySQL."""
    try:
        conn = get_mysql_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Could not connect to database")

        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(
            """
            SELECT a.id, a.account_id, a.name, a.email, a.phone, a.course, a.submitted_at, a.created_at,
                   ac.role AS account_role, ac.full_name AS account_full_name
            FROM admissions a
            LEFT JOIN accounts ac ON ac.id = a.account_id
            ORDER BY a.created_at DESC
            """
        )
        data = cursor.fetchall()
        cursor.close()
        conn.close()
        print(f"📊 Retrieved {len(data)} applications from database")
        return [serialize_application(row) for row in data]
    except Exception as e:
        print(f"❌ Error in get_data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin/accounts")
def get_accounts(_current_account: dict = Depends(require_admin_account)):
    conn = get_mysql_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="Could not connect to database")

    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(
            """
            SELECT id, full_name, username, email, phone, role, created_at
            FROM accounts
            ORDER BY created_at DESC
            """
        )
        data = cursor.fetchall()
        cursor.close()
        conn.close()
        return data
    except Error as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/cleanup-applications")
def cleanup_applications(_current_account: dict = Depends(require_admin_account)):
    """Remove applications that are not part of the current three B.Sc programs."""
    allowed_courses = {
        "B.Sc Quantum Technologies",
        "B.Sc Data Science",
        "B.Sc Computer Science",
    }

    conn = get_mysql_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="Could not connect to database")

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, course FROM admissions ORDER BY id")
        rows = cursor.fetchall()
        ids_to_delete = [row[0] for row in rows if row[1] not in allowed_courses]
        before_count = len(rows)

        deleted_count = 0
        if ids_to_delete:
            placeholders = ",".join(["%s"] * len(ids_to_delete))
            cursor.execute(f"DELETE FROM admissions WHERE id IN ({placeholders})", ids_to_delete)
            conn.commit()
            deleted_count = cursor.rowcount

        cursor.execute("SELECT COUNT(*) as count FROM admissions")
        r = cursor.fetchone()
        # psycopg2 RealDictCursor returns dict-like rows; normal cursor returns tuple
        if hasattr(r, 'get'):
            after_count = r.get('count')
        else:
            after_count = r[0]

        cursor.close()
        conn.close()

        return {
            "success": True,
            "before_count": before_count,
            "deleted_count": deleted_count,
            "after_count": after_count,
            "allowed_courses": sorted(list(allowed_courses)),
        }
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))

