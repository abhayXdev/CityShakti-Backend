import json
import time
import requests

BASE_URL = "https://cityshakti-backend.onrender.com"

def run_tests():
    print(f"Testing Live API Full Edge Cases at {BASE_URL}...\n")
    
    # 1. Register Citizen 1
    print("[1] Registering Citizen 1...")
    cit_email = f"citizen_edge_{int(time.time())}@example.com"
    r = requests.post(f"{BASE_URL}/api/auth/register", json={
        "full_name": "Edge Citizen",
        "email": cit_email,
        "password": "password123",
        "role": "citizen"
    })
    print(f"  Register Status: {r.status_code}")

    # 2. Duplicate Email Registration (Edge Case)
    print("\n[EDGE CASE] Duplicate Email Registration...")
    r_dup = requests.post(f"{BASE_URL}/api/auth/register", json={
        "full_name": "Duplicate Citizen",
        "email": cit_email,
        "password": "password123",
        "role": "citizen"
    })
    print(f"  Duplicate Register Status (Expected ~400): {r_dup.status_code}")
    print(f"  Response: {r_dup.text}")

    # 3. Invalid Login (Edge Case)
    print("\n[EDGE CASE] Invalid Login...")
    r_inv = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": cit_email,
        "password": "wrongpassword!"
    })
    print(f"  Invalid Login Status (Expected ~401): {r_inv.status_code}")
    print(f"  Response: {r_inv.text}")

    # 4. Login Citizen 1 Correctly
    print("\n[4] Logging in Citizen 1...")
    r = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": cit_email,
        "password": "password123"
    })
    print(f"  Login Status: {r.status_code}")
    cit_token = r.json().get("access_token")
    cit_headers = {"Authorization": f"Bearer {cit_token}"}

    # 5. Create Complaint without Token (Edge Case)
    print("\n[EDGE CASE] Create Complaint without Token...")
    r_no_auth = requests.post(f"{BASE_URL}/api/complaints", json={
        "title": "Unauth Pothole",
        "description": "Massive pothole on the main highway causing traffic.",
        "ward": "Test Ward",
        "category": "General",
        "priority": 0
    })
    print(f"  Unauth Create Status (Expected 401): {r_no_auth.status_code}")

    # 6. Create Complaint properly
    print("\n[5] Citizen Creating Complaint...")
    r = requests.post(f"{BASE_URL}/api/complaints", json={
        "title": "Valid Edge Pothole",
        "description": "Massive pothole on the main highway causing traffic.",
        "ward": "Test Ward",
        "category": "General",
        "priority": 0
    }, headers=cit_headers)
    print(f"  Create Complaint Status: {r.status_code}")
    complaint_id = r.json().get("id")

    # 7. Assign Complaint as Citizen (Edge Case)
    print("\n[EDGE CASE] Assign Complaint as Citizen...")
    r_assign_cit = requests.patch(f"{BASE_URL}/api/complaints/{complaint_id}/assign", json={
        "assigned_to": "Live Tester",
        "assigned_department": "QA"
    }, headers=cit_headers)
    print(f"  Citizen Assign Status (Expected 403): {r_assign_cit.status_code}")
    print(f"  Response: {r_assign_cit.text}")

    # 8. Expired/Invalid Token (Edge Case)
    print("\n[EDGE CASE] Using Invalid Token...")
    invalid_headers = {"Authorization": f"Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.token"}
    r_inv_tok = requests.get(f"{BASE_URL}/api/complaints", headers=invalid_headers)
    print(f"  Invalid Token Status (Expected 401): {r_inv_tok.status_code}")

    print("\n✅ Edge Case Testing Complete!")

if __name__ == "__main__":
    run_tests()
