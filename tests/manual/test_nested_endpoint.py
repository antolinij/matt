#!/usr/bin/env python3
"""Test script for nested student account-status endpoint"""
import json

import requests

BASE_URL = "http://localhost:8000"

# 1. Login to get token
print("=" * 60)
print("1. Getting authentication token...")
print("=" * 60)
login_response = requests.post(
    f"{BASE_URL}/api/auth/login",
    data={"username": "testuser", "password": "testpass123"},
    headers={"Content-Type": "application/x-www-form-urlencoded"},
)
if login_response.status_code != 200:
    print(f"Login failed: {login_response.status_code}")
    print(login_response.text)
    exit(1)
token = login_response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}
print("✓ Token obtained successfully\n")

# 2. Test valid student in correct school
print("=" * 60)
print("2. Test: Valid student (8) in correct school (11)")
print("=" * 60)
print("GET /api/schools/11/students/8/account-status")
response = requests.get(
    f"{BASE_URL}/api/schools/11/students/8/account-status", headers=headers
)
print(f"Status Code: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"✓ SUCCESS - Student: {data.get('student_name')}")
    print(f"  Total Invoiced: ${data.get('total_invoiced')}")
    print(f"  Total Paid: ${data.get('total_paid')}")
    print(f"  Total Pending: ${data.get('total_pending')}")
else:
    print(f"✗ FAILED")
    print(json.dumps(response.json(), indent=2))
print()

# 3. Test valid student in WRONG school
print("=" * 60)
print("3. Test: Valid student (8) in WRONG school (5)")
print("=" * 60)
print("GET /api/schools/5/students/8/account-status")
response = requests.get(
    f"{BASE_URL}/api/schools/5/students/8/account-status", headers=headers
)
print(f"Status Code: {response.status_code}")
if response.status_code == 404:
    print("✓ SUCCESS - Correctly returned 404")
    print(f"  Message: {response.json().get('detail')}")
else:
    print(f"✗ FAILED - Expected 404, got {response.status_code}")
    print(json.dumps(response.json(), indent=2))
print()

# 4. Test invalid school
print("=" * 60)
print("4. Test: Invalid school (999) with valid student (8)")
print("=" * 60)
print("GET /api/schools/999/students/8/account-status")
response = requests.get(
    f"{BASE_URL}/api/schools/999/students/8/account-status", headers=headers
)
print(f"Status Code: {response.status_code}")
if response.status_code == 404:
    print("✓ SUCCESS - Correctly returned 404")
    print(f"  Message: {response.json().get('detail')}")
else:
    print(f"✗ FAILED - Expected 404, got {response.status_code}")
    print(json.dumps(response.json(), indent=2))
print()

# 5. Test invalid student
print("=" * 60)
print("5. Test: Valid school (11) with invalid student (999)")
print("=" * 60)
print("GET /api/schools/11/students/999/account-status")
response = requests.get(
    f"{BASE_URL}/api/schools/11/students/999/account-status", headers=headers
)
print(f"Status Code: {response.status_code}")
if response.status_code == 404:
    print("✓ SUCCESS - Correctly returned 404")
    print(f"  Message: {response.json().get('detail')}")
else:
    print(f"✗ FAILED - Expected 404, got {response.status_code}")
    print(json.dumps(response.json(), indent=2))
print()

print("=" * 60)
print("Testing complete!")
print("=" * 60)
