from datetime import datetime, timedelta
from typing import Optional
import base64
import hashlib
import hmac
import os
import secrets

import mysql.connector
from mysql.connector import Error
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=BASE_DIR), name="static")

DEFAULT_ADMIN_USERNAME = "Loyola admin"
DEFAULT_ADMIN_PASSWORD = "Loyola@2004"
SESSION_DAYS = 30

# MySQL configuration
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "Baba@1531")
MYSQL_DB = os.getenv("MYSQL_DB", "college")

mysql_available = False
mysql_connection_error = None


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    iterations = 120000
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    )
    encoded = base64.b64encode(digest).decode("ascii")
    return f"pbkdf2_sha256${iterations}${salt}${encoded}"



def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations_text, salt, encoded_digest = stored_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False

        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            int(iterations_text),
        )
        candidate = base64.b64encode(digest).decode("ascii")
        return hmac.compare_digest(candidate, encoded_digest)
    except Exception:
        return False



def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()



def get_server_connection():
    return mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        connection_timeout=10,
        autocommit=True,
    )



def get_mysql_connection():
    try:
        return mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DB,
            connection_timeout=5,
        )
    except Error as e:
        print(f"MySQL connection error: {e}")
        return None



def init_mysql():
    """Initialize MySQL connection and create tables if needed."""
    global mysql_available, mysql_connection_error
    try:
        print(f"🔄 Attempting MySQL connection to {MYSQL_HOST}:{MYSQL_DB}...")
        conn = get_server_connection()
        cursor = conn.cursor()

        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{MYSQL_DB}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        cursor.execute(f"USE `{MYSQL_DB}`")

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS accounts (
                id INT AUTO_INCREMENT PRIMARY KEY,
                full_name VARCHAR(255) NOT NULL,
                username VARCHAR(255) UNIQUE,
                email VARCHAR(255) UNIQUE,
                phone VARCHAR(20) UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(20) NOT NULL DEFAULT 'student',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash VARCHAR(64) PRIMARY KEY,
                account_id INT NOT NULL,
                role VARCHAR(20) NOT NULL,
                expires_at DATETIME NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX(account_id),
                INDEX(role)
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS admissions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                account_id INT NOT NULL,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) NOT NULL,
                phone VARCHAR(20) NOT NULL,
                course VARCHAR(255) NOT NULL,
                submitted_at VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cursor.execute(
            "SELECT id FROM accounts WHERE role = 'admin' AND username = %s LIMIT 1",
            (DEFAULT_ADMIN_USERNAME,),
        )
        if not cursor.fetchone():
            cursor.execute(
                """
                INSERT INTO accounts (full_name, username, email, phone, password_hash, role)
                VALUES (%s, %s, %s, %s, %s, 'admin')
                """,
                (
                    DEFAULT_ADMIN_USERNAME,
                    DEFAULT_ADMIN_USERNAME,
                    None,
                    None,
                    hash_password(DEFAULT_ADMIN_PASSWORD),
                ),
            )

        conn.commit()
        cursor.close()
        conn.close()

        mysql_available = True
        mysql_connection_error = None
        print("✅ MySQL connected successfully!")
        return True
    except Error as e:
        mysql_available = False
        mysql_connection_error = str(e)
        print(f"❌ MySQL connection failed: {e}")
        print(f"   Host: {MYSQL_HOST}, User: {MYSQL_USER}, DB: {MYSQL_DB}")
        return False



def create_session(account_id: int, role: str) -> str:
    token = secrets.token_urlsafe(32)
    token_hash = hash_token(token)
    expires_at = datetime.now() + timedelta(days=SESSION_DAYS)

    conn = get_mysql_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="Could not connect to MySQL")

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
    except Error as e:
        conn.close()
        raise HTTPException(status_code=500, detail=f"Failed to create session: {e}")



def get_account_from_token(authorization: Optional[str]) -> dict:
    if not mysql_available:
        raise HTTPException(status_code=503, detail=f"MySQL is not available: {mysql_connection_error}")

    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization token")

    token = authorization.strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()

    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")

    conn = get_mysql_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="Could not connect to MySQL")

    token_hash = hash_token(token)

    try:
        cursor = conn.cursor(dictionary=True)
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
        if expires_at and expires_at < datetime.now():
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


# Initialize MySQL on startup
init_mysql()


class ApplicationRequest(BaseModel):
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
        "mysql": "connected" if mysql_available else "disconnected",
        "mysql_error": mysql_connection_error,
        "storage": "mysql",
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/debug/mysql-status")
def mysql_status():
    """Debug endpoint to check MySQL status"""
    if mysql_available:
        try:
            conn = get_mysql_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) as count FROM admissions")
                applications_count = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) as count FROM accounts WHERE role = 'student'")
                students_count = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) as count FROM accounts WHERE role = 'admin'")
                admins_count = cursor.fetchone()[0]
                cursor.close()
                conn.close()
                return {
                    "status": "✅ Connected",
                    "host": MYSQL_HOST,
                    "database": MYSQL_DB,
                    "user": MYSQL_USER,
                    "total_applications": applications_count,
                    "total_students": students_count,
                    "total_admins": admins_count,
                    "timestamp": datetime.now().isoformat(),
                }
        except Error as e:
            return {
                "status": "❌ Connection failed",
                "error": str(e),
                "host": MYSQL_HOST,
                "database": MYSQL_DB,
            }
    else:
        return {
            "status": "❌ Not connected",
            "error": mysql_connection_error,
            "host": MYSQL_HOST,
            "database": MYSQL_DB,
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
    if not mysql_available:
        raise HTTPException(status_code=503, detail=f"MySQL is not available: {mysql_connection_error}")

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
        raise HTTPException(status_code=503, detail="Could not connect to MySQL")

    try:
        cursor = conn.cursor(dictionary=True)
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
            VALUES (%s, %s, %s, %s, 'student')
            """,
            (full_name, email, phone, hash_password(password)),
        )
        account_id = cursor.lastrowid
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
    if not mysql_available:
        raise HTTPException(status_code=503, detail=f"MySQL is not available: {mysql_connection_error}")

    identifier = payload.identifier.strip()
    password = payload.password.strip()

    if not identifier or not password:
        raise HTTPException(status_code=400, detail="Identifier and password are required")

    conn = get_mysql_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="Could not connect to MySQL")

    try:
        cursor = conn.cursor(dictionary=True)
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
    if not mysql_available:
        raise HTTPException(status_code=503, detail=f"MySQL is not available: {mysql_connection_error}")

    username = payload.username.strip()
    password = payload.password.strip()

    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password are required")

    conn = get_mysql_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="Could not connect to MySQL")

    try:
        cursor = conn.cursor(dictionary=True)
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
    if not authorization or not mysql_available:
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
    """Save student application data to MySQL."""
    try:
        submitted_at = datetime.now().isoformat()

        conn = get_mysql_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Could not connect to MySQL")

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO admissions (account_id, name, email, phone, course, submitted_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    current_account["id"],
                    current_account["full_name"],
                    current_account["email"],
                    current_account["phone"],
                    application.course.strip(),
                    submitted_at,
                ),
            )
            conn.commit()
            cursor.close()
            conn.close()

            print(f"✅ Application saved to MySQL: {current_account['full_name']} ({current_account['email']})")
            return {
                "success": True,
                "message": "Application saved successfully to database",
                "storage": "mysql",
                "submitted_at": submitted_at,
            }
        except Error as e:
            conn.close()
            print(f"❌ MySQL save error: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to save application to MySQL: {e}")
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
            raise HTTPException(status_code=503, detail="Could not connect to MySQL")

        cursor = conn.cursor(dictionary=True)
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
        print(f"📊 Retrieved {len(data)} applications from MySQL")
        return [serialize_application(row) for row in data]
    except Exception as e:
        print(f"❌ Error in get_data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin/accounts")
def get_accounts(_current_account: dict = Depends(require_admin_account)):
    if not mysql_available:
        raise HTTPException(status_code=503, detail=f"MySQL is not available: {mysql_connection_error}")

    conn = get_mysql_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="Could not connect to MySQL")

    try:
        cursor = conn.cursor(dictionary=True)
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
        raise HTTPException(status_code=503, detail="Could not connect to MySQL")

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

        cursor.execute("SELECT COUNT(*) FROM admissions")
        after_count = cursor.fetchone()[0]

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

