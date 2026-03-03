import requests

BASE_URL = "https://cityshakti-backend.onrender.com/api"
cit_tokens = requests.post(f"{BASE_URL}/auth/login", json={"email": "cit_1709405600@example.com", "password": "password123"}).json() # The specific citizen doesn't matter for fetching a public complaint if RBAC is disabled or we login as admin
r_adm = requests.post(f"{BASE_URL}/auth/login", json={"email": "commissioner@test.com", "password": "password123"}).json() # Let's login using a known registered admin

if r_adm.get("access_token"):
    c = requests.get(f"{BASE_URL}/complaints/13", headers={"Authorization": f"Bearer {r_adm['access_token']}"}).json()
    print("Complaint 13 Status:")
    print(f"Status: {c.get('status')}")
    print(f"Category: {c.get('category')}")
    print(f"Department: {c.get('assigned_department')}")
else:
    print("Could not login as admin.")
