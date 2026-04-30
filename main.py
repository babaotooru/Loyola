from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure
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


@app.get("/admin")
def admin_page():
    return FileResponse(os.path.join(BASE_DIR, "admin.html"))


@app.get("/static/20200129112722.png")
def college_photo():
    return FileResponse(os.path.join(BASE_DIR, "20200129112722.png"))

# MongoDB configuration with timeout
MONGODB_URI = os.getenv(
    "MONGODB_URI",
    "mongodb+srv://babaotooru_db_user:0bujrmNeprgjfElq@cluster0.emrubdg.mongodb.net/?appName=Cluster0"
)

try:
    client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
    # Test the connection
    client.admin.command('ping')
    db = client["college"]
    collection = db["admissions"]
    mongodb_available = True
    print("✓ MongoDB connected successfully")
except (ServerSelectionTimeoutError, ConnectionFailure, Exception) as e:
    print(f"⚠ MongoDB not available: {e}")
    mongodb_available = False
    collection = None

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
        "mongodb": "connected" if mongodb_available else "disconnected",
        "storage": "file-based" if not mongodb_available else "mongodb"
    }

@app.post("/apply")
def apply(student: Student):
    """Save student application"""
    try:
        student_dict = student.dict()
        student_dict["submitted_at"] = datetime.now().isoformat()
        
        if mongodb_available:
            # Try to save to MongoDB
            try:
                collection.insert_one(student_dict)
                return {
                    "success": True,
                    "message": "Application saved successfully",
                    "storage": "mongodb"
                }
            except Exception as e:
                print(f"MongoDB save error: {e}")
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
        if mongodb_available:
            try:
                data = list(collection.find({}, {"_id": 0}))
                return data
            except Exception as e:
                print(f"MongoDB read error: {e}")
                # Fallback to file
                return load_applications()
        else:
            # Use file-based storage
            return load_applications()
    except Exception as e:
        print(f"Error in get_data: {e}")
        return []
