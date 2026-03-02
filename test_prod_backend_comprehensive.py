import time
import requests
import json

BASE_URL = "https://cityshakti-backend.onrender.com/api"


def run_prod_tests():
    print("=== RUNNING COMPREHENSIVE E2E TESTS ON PRODUCTION ===")

    # 1. Edge Auth
    print("\n[1] Testing Authentication Edge Cases...")
    r = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": "nobody@test.com", "password": "password123"},
    )
    if r.status_code == 401 and r.json().get("detail") == "Invalid credentials":
        print("    [PASSED] Unregistered login rejected correctly.")
    else:
        print(
            f"    [FAILED] Expected 401 Invalid credentials, got {r.status_code}: {r.text}"
        )

    # Register Citizen & Admin
    email_cit = f"cit_{int(time.time())}@example.com"
    email_adm = f"adm_{int(time.time())}@example.com"

    requests.post(
        f"{BASE_URL}/auth/register",
        json={
            "full_name": "Cit P",
            "email": email_cit,
            "password": "password123",
            "role": "citizen",
            "ward": "North",
        },
    )
    requests.post(
        f"{BASE_URL}/auth/register",
        json={
            "full_name": "Adm P",
            "email": email_adm,
            "password": "password123",
            "role": "admin",
            "ward": "South",
        },
    )

    cit_tokens = requests.post(
        f"{BASE_URL}/auth/login", json={"email": email_cit, "password": "password123"}
    ).json()
    adm_tokens = requests.post(
        f"{BASE_URL}/auth/login", json={"email": email_adm, "password": "password123"}
    ).json()

    cit_hdr = {"Authorization": f"Bearer {cit_tokens['access_token']}"}
    adm_hdr = {"Authorization": f"Bearer {adm_tokens['access_token']}"}

    r_refresh = requests.post(
        f"{BASE_URL}/auth/refresh", json={"refresh_token": cit_tokens["refresh_token"]}
    )
    if r_refresh.status_code == 200 and "access_token" in r_refresh.json():
        print("    [PASSED] Token Refresh Succeeded.")
    else:
        print("    [FAILED] Token Refresh Failed.")

    # 2. Complaints Extended & Auto-Assignment
    print("\n[2] Testing Complaints & Merging...")
    import uuid

    uniq = str(uuid.uuid4())
    uniq2 = str(uuid.uuid4())
    uniq3 = str(uuid.uuid4())
    c1 = requests.post(
        f"{BASE_URL}/complaints",
        json={"title": f"M1 {uniq}", "description": f"{uniq} " * 15, "ward": "East"},
        headers=cit_hdr,
    ).json()
    c2 = requests.post(
        f"{BASE_URL}/complaints",
        json={"title": f"M2 {uniq2}", "description": f"{uniq2} " * 15, "ward": "East"},
        headers=cit_hdr,
    ).json()
    c3 = requests.post(
        f"{BASE_URL}/complaints",
        json={"title": f"M3 {uniq3}", "description": f"{uniq3} " * 15, "ward": "West"},
        headers=cit_hdr,
    ).json()

    time.sleep(3)  # Wait for AI background job to categorize them

    # Try merging cross wards
    merge_fail = requests.post(
        f"{BASE_URL}/complaints/merge",
        json={"source_complaint_id": c2["id"], "target_complaint_id": c3["id"]},
        headers=adm_hdr,
    )
    if merge_fail.status_code == 400 and "ward" in merge_fail.text.lower():
        print("    [PASSED] Cross-ward merge correctly blocked.")
    else:
        print("    [FAILED] Cross-ward merge should be 400.")

    # Proper merge
    merge_pass = requests.post(
        f"{BASE_URL}/complaints/merge",
        json={"source_complaint_id": c1["id"], "target_complaint_id": c2["id"]},
        headers=adm_hdr,
    )
    if merge_pass.status_code == 200:
        print("    [PASSED] Valid merge succeeded.")
    else:
        print(f"    [FAILED] Merge failed: {merge_pass.text}")

    # 3. Pagination Bounds
    print("\n[3] Testing Pagination & Filtering Bounds...")
    r_pag = requests.get(f"{BASE_URL}/complaints?limit=300", headers=adm_hdr)
    if r_pag.status_code == 422 or "less than or equal to 100" in r_pag.text:
        print("    [PASSED] Standardized Pagination limit hard-capped at 100.")
    else:
        print("    [FAILED] Pagination missing hard cap.")

    # 4. Auto Assignment Feature Check
    print("\n[4] Testing Auto-Assignment Background Trigger...")
    salt = str(uuid.uuid4()) * 5
    c_auto = requests.post(
        f"{BASE_URL}/complaints",
        json={
            "title": f"P {salt[:5]}",
            "description": f"pothole asphalt {salt}",
            "ward": "North",
        },
        headers=cit_hdr,
    ).json()

    print(
        "    [~] Waiting 15 seconds for Render background NLP workers to finish processing..."
    )
    time.sleep(15)

    fetched_auto = requests.get(
        f"{BASE_URL}/complaints/{c_auto['id']}", headers=adm_hdr
    ).json()
    if (
        fetched_auto.get("assigned_department") == "Public Works Department"
        and fetched_auto.get("status") == "Assigned"
    ):
        print(
            "    [PASSED] Complaint auto-categorized and auto-assigned by Background AI Job."
        )
    else:
        print(f"    [FAILED] Auto assign missing or incorrect.")
        print(
            f"      -> Expected: Department: Public Works Department, Status: Assigned"
        )
        print(
            f"      -> Actual: Department: {fetched_auto.get('assigned_department')}, Status: {fetched_auto.get('status')}"
        )
        print(f"      -> AI Category Result: {fetched_auto.get('category')}")

    # 5. Dashboard Metrics Structure
    print("\n[5] Testing RBAC & Dashboard Metric Aggregations...")
    dash_cit = requests.get(f"{BASE_URL}/dashboard/summary", headers=cit_hdr)
    if dash_cit.status_code == 403:
        print("    [PASSED] Citizen Blocked from Dashboard.")

    dash_adm = requests.get(f"{BASE_URL}/dashboard/summary", headers=adm_hdr)
    if dash_adm.status_code == 200 and "ward_stats" in dash_adm.json():
        print("    [PASSED] Admin Fetched Metric Vectors successfully.")
    else:
        print("    [FAILED] Dashboard crash or missing arrays.")

    print("\nPRODUCTION E2E COMPREHENSIVE SUITE FINISHED.")


if __name__ == "__main__":
    run_prod_tests()
