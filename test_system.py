#!/usr/bin/env python
"""
Test script to verify the admissions system is working properly.
Tests MySQL connectivity, data submission, and retrieval.
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    print("\n" + "="*60)
    print("📋 TEST 1: Health Check")
    print("="*60)
    try:
        response = requests.get(f"{BASE_URL}/health")
        data = response.json()
        print(f"✅ Status: {data['status']}")
        print(f"🔗 MySQL: {data['mysql']}")
        print(f"💾 Storage: {data['storage']}")
        print(f"📅 Timestamp: {data['timestamp']}")
        if data.get('mysql_error'):
            print(f"⚠️  Error: {data['mysql_error']}")
        return data['mysql'] == 'connected'
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_mysql_status():
    """Test MySQL debug status endpoint"""
    print("\n" + "="*60)
    print("📊 TEST 2: MySQL Debug Status")
    print("="*60)
    try:
        response = requests.get(f"{BASE_URL}/debug/mysql-status")
        data = response.json()
        print(f"Status: {data['status']}")
        print(f"Host: {data['host']}")
        print(f"Database: {data['database']}")
        print(f"User: {data['user']}")
        if 'total_applications' in data:
            print(f"📝 Total Applications in Database: {data['total_applications']}")
        if 'error' in data:
            print(f"❌ Error: {data['error']}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_get_applications():
    """Get all applications"""
    print("\n" + "="*60)
    print("📥 TEST 3: Get All Applications")
    print("="*60)
    try:
        response = requests.get(f"{BASE_URL}/applications")
        data = response.json()
        print(f"✅ Retrieved {len(data)} applications")
        if data:
            print("\n📋 Applications List:")
            for i, app in enumerate(data, 1):
                print(f"  {i}. {app.get('name')} - {app.get('course')}")
        else:
            print("ℹ️  No applications in database yet")
        return data
    except Exception as e:
        print(f"❌ Error: {e}")
        return []

def test_submit_application():
    """Submit a test application"""
    print("\n" + "="*60)
    print("✍️  TEST 4: Submit Test Application")
    print("="*60)
    
    test_student = {
        "name": f"Test User {datetime.now().strftime('%H%M%S')}",
        "email": f"test{datetime.now().strftime('%H%M%S')}@test.com",
        "phone": "9876543210",
        "course": "B.Sc Quantum Technologies"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/apply", json=test_student)
        result = response.json()
        print(f"✅ Submission Status: {result.get('success')}")
        print(f"📝 Name: {test_student['name']}")
        print(f"📧 Email: {test_student['email']}")
        print(f"📱 Phone: {test_student['phone']}")
        print(f"🎓 Course: {test_student['course']}")
        print(f"💾 Storage Used: {result.get('storage', 'N/A')}")
        print(f"⏰ Message: {result.get('message')}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Run all tests"""
    print("\n" + "🧪 ADMISSIONS SYSTEM TEST SUITE 🧪".center(60))
    
    # Test 1: Health Check
    mysql_connected = test_health()
    
    # Test 2: MySQL Status
    test_mysql_status()
    
    # Test 3: Get Applications (before submit)
    apps_before = test_get_applications()
    
    # Test 4: Submit Application
    test_submit_application()
    
    # Test 5: Get Applications (after submit)
    print("\n" + "="*60)
    print("🔄 TEST 5: Verify Data Was Saved")
    print("="*60)
    apps_after = test_get_applications()
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    print(f"MySQL Connected: {'✅ YES' if mysql_connected else '❌ NO'}")
    print(f"Applications Before: {len(apps_before)}")
    print(f"Applications After: {len(apps_after)}")
    print(f"New Applications: {len(apps_after) - len(apps_before)}")
    
    if mysql_connected and len(apps_after) > len(apps_before):
        print("\n✅ SUCCESS: System is working correctly!")
        print("   - MySQL is connected")
        print("   - Data is being saved to database")
        print("   - All users will see the same data in real-time")
    else:
        print("\n⚠️  ISSUES DETECTED:")
        if not mysql_connected:
            print("   - MySQL is not connected")
        if len(apps_after) <= len(apps_before):
            print("   - Data was not saved to database")
    
    print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    main()
