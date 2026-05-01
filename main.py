from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import mysql.connector
from mysql.connector import Error
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import json
import os
from datetime import datetime

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


@app.get("/static/20200129112722.png")
def college_photo():
    return FileResponse(os.path.join(BASE_DIR, "20200129112722.png"))


@app.get("/config.js")
def config_js():
    return FileResponse(os.path.join(BASE_DIR, "config.js"))

# MySQL configuration
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "Baba@1531")
MYSQL_DB = os.getenv("MYSQL_DB", "college")

mysql_available = False

def init_mysql():
    """Initialize MySQL connection and create table if needed"""
    global mysql_available
    try:
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DB,
            connection_timeout=5
        )
        cursor = conn.cursor()
        
        # Create admissions table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admissions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) NOT NULL,
                phone VARCHAR(20) NOT NULL,
                course VARCHAR(255) NOT NULL,
                submitted_at VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        cursor.close()
        conn.close()
        
        mysql_available = True
        print("✓ MySQL connected successfully")
        return True
    except Error as e:
        print(f"⚠ MySQL not available: {e}")
        mysql_available = False
        return False

def get_mysql_connection():
    """Get a MySQL connection"""
    try:
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DB,
            connection_timeout=5
        )
        return conn
    except Error as e:
        print(f"MySQL connection error: {e}")
        return None

# Initialize MySQL on startup
init_mysql()

# JSON file for fallback storage
DATA_FILE = "applications.json"

def load_applications():
    """Load applications from JSON file"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def save_applications(applications):
    """Save applications to JSON file"""
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(applications, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving to file: {e}")
        return False

class Student(BaseModel):
    name: str
    email: str
    phone: str
    course: str

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "mysql": "connected" if mysql_available else "disconnected",
        "storage": "file-based" if not mysql_available else "mysql"
    }

@app.post("/apply")
def apply(student: Student):
    """Save student application"""
    try:
        student_dict = student.dict()
        student_dict["submitted_at"] = datetime.now().isoformat()
        
        if mysql_available:
            # Try to save to MySQL
            try:
                conn = get_mysql_connection()
                if conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO admissions (name, email, phone, course, submitted_at)
                        VALUES (%s, %s, %s, %s, %s)
                    ''', (student_dict['name'], student_dict['email'], student_dict['phone'], 
                          student_dict['course'], student_dict['submitted_at']))
                    conn.commit()
                    cursor.close()
                    conn.close()
                    
                    return {
                        "success": True,
                        "message": "Application saved successfully",
                        "storage": "mysql"
                    }
                else:
                    # Fallback to file
                    applications = load_applications()
                    applications.append(student_dict)
                    if save_applications(applications):
                        return {
                            "success": True,
                            "message": "Application saved successfully",
                            "storage": "file"
                        }
                    else:
                        raise HTTPException(status_code=500, detail="Failed to save application")
            except Error as e:
                print(f"MySQL save error: {e}")
                # Fallback to file
                applications = load_applications()
                applications.append(student_dict)
                if save_applications(applications):
                    return {
                        "success": True,
                        "message": "Application saved successfully",
                        "storage": "file"
                    }
                else:
                    raise HTTPException(status_code=500, detail="Failed to save application")
        else:
            # Use file-based storage
            applications = load_applications()
            applications.append(student_dict)
            if save_applications(applications):
                return {
                    "success": True,
                    "message": "Application saved successfully",
                    "storage": "file"
                }
            else:
                raise HTTPException(status_code=500, detail="Failed to save application")
                
    except Exception as e:
        print(f"Error in apply: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/applications")
def get_data():
    """Get all applications"""
    try:
        if mysql_available:
            try:
                conn = get_mysql_connection()
                if conn:
                    cursor = conn.cursor(dictionary=True)
                    cursor.execute('SELECT * FROM admissions ORDER BY created_at DESC')
                    data = cursor.fetchall()
                    cursor.close()
                    conn.close()
                    return data
                else:
                    return load_applications()
            except Error as e:
                print(f"MySQL read error: {e}")
                # Fallback to file
                return load_applications()
        else:
            # Use file-based storage
            return load_applications()
    except Exception as e:
        print(f"Error in get_data: {e}")
        return []


@app.post("/cleanup-applications")
def cleanup_applications():
    """Remove applications that are not part of the current three B.Sc programs."""
    allowed_courses = {
        "B.Sc Quantum Technologies",
        "B.Sc Data Science",
        "B.Sc Computer Science",
    }

    if not mysql_available:
        raise HTTPException(status_code=503, detail="MySQL is not available")

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
