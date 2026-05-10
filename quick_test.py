#!/usr/bin/env python
"""Quick test to verify MySQL data flow"""

import requests

BASE_URL = "http://127.0.0.1:8001"

# Test 1: Get applications before
print("=" * 60)
print("TEST 1: Check applications BEFORE submission")
print("=" * 60)
r = requests.get(f"{BASE_URL}/applications")
before_count = len(r.json())
print(f"✅ Applications in database: {before_count}")

# Test 2: Submit a new application
print("\n" + "=" * 60)
print("TEST 2: Submit new application to MySQL")
print("=" * 60)
data = {
    'name': 'John Smith',
    'email': 'john@example.com',
    'phone': '8888888888',
    'course': 'B.Sc Computer Science'
}
r = requests.post(f"{BASE_URL}/apply", json=data)
result = r.json()
print(f"✅ Status: {r.status_code}")
print(f"✅ Stored in: {result.get('storage')} DATABASE")
print(f"✅ Message: {result.get('message')}")

# Test 3: Verify it was saved
print("\n" + "=" * 60)
print("TEST 3: Verify application was saved to MySQL")
print("=" * 60)
r = requests.get(f"{BASE_URL}/applications")
after_count = len(r.json())
print(f"✅ Applications in database NOW: {after_count}")
print(f"✅ New applications added: {after_count - before_count}")

if after_count > before_count:
    print("\n🎉 SUCCESS! Data is being saved to MySQL!")
    print("\nLatest application:")
    latest = r.json()[0]
    print(f"  Name: {latest['name']}")
    print(f"  Email: {latest['email']}")
    print(f"  Phone: {latest['phone']}")
    print(f"  Course: {latest['course']}")
else:
    print("\n❌ ERROR: Data was not saved!")
