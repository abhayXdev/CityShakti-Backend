import time
import requests

BASE_URL = "https://cityshakti-backend.onrender.com"


def run_all_tests():
    print(f"=== CITYSHAKTI v1.0 E2E LIVE VERIFICATION ===\n")

    # 0. Health Check
    print("[0] Testing Health Check endpoint...")
    r = requests.get(f"{BASE_URL}/api/health")
    print(f"  Health Check Status: {r.status_code} - Payload: {r.text}")

    # 1. Registration
    email_cit = f"cit_{int(time.time())}@example.com"
    email_adm = f"adm_{int(time.time())}@example.com"

    print(f"\n[1] Registering Test Citizen & Admin...")
    r_cit = requests.post(
        f"{BASE_URL}/api/auth/register",
        json={
            "full_name": "Test Citizen",
            "email": email_cit,
            "password": "password123",
            "role": "citizen",
            "ward": "Central",
        },
    )
    r_adm = requests.post(
        f"{BASE_URL}/api/auth/register",
        json={
            "full_name": "Test Admin",
            "email": email_adm,
            "password": "password123",
            "role": "admin",
            "ward": "Central",
        },
    )
    print(f"  Citizen Created Status: {r_cit.status_code}")
    print(f"  Admin Created Status: {r_adm.status_code}")

    # 2. Login & Token Generation
    print(f"\n[2] authenticating & Generating JWTs...")
    cit_token = (
        requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": email_cit, "password": "password123"},
        )
        .json()
        .get("access_token")
    )
    adm_token = (
        requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": email_adm, "password": "password123"},
        )
        .json()
        .get("access_token")
    )

    if not cit_token or not adm_token:
        print("  FAILED TO LOGIN!")
        return

    cit_headers = {"Authorization": f"Bearer {cit_token}"}
    adm_headers = {"Authorization": f"Bearer {adm_token}"}
    print("  Tokens Acquired Successfully")

    # 3. Create Specific Complaint (AI High Confidence) & Vague Complaint
    print("\n[3] Submitting Complaints (Testing Photo URLs & Lat/Long)...")

    # Highly specific complaint payload
    r_specific = requests.post(
        f"{BASE_URL}/api/complaints",
        json={
            "title": "Deep Pothole causing traffic",
            "description": "Massive pothole on main road causing accidents. Needs immediate fixing.",
            "ward": "North",
            "photo_url": "https://res.cloudinary.com/cityshakti/image/upload/pothole_test.jpg",
            "latitude": 28.1234,
            "longitude": 77.4567,
        },
        headers=cit_headers,
    )
    print(f"  Specific Complaint Status: {r_specific.status_code}")
    comp_id_specific = r_specific.json().get("id")

    # Vague complaint payload (Should hit <0.40 threshold and default to 'General')
    r_vague = requests.post(
        f"{BASE_URL}/api/complaints",
        json={
            "title": "Please fix this",
            "description": "This is broken in my neighborhood.",
            "ward": "North",
        },
        headers=cit_headers,
    )
    print(f"  Vague Complaint Status: {r_vague.status_code}")
    comp_id_vague = r_vague.json().get("id")

    # 4. Wait for Background Data Science Workers
    print(
        "\n[-] Waiting 5 seconds for AI Auto-Categorizer background workers to finish in the cloud..."
    )
    time.sleep(5)

    detailed_spec = requests.get(
        f"{BASE_URL}/api/complaints/{comp_id_specific}", headers=cit_headers
    ).json()
    detailed_vag = requests.get(
        f"{BASE_URL}/api/complaints/{comp_id_vague}", headers=cit_headers
    ).json()

    print(f"  Specific Complaint AI Result:")
    print(
        f"    -> Category Assign: {detailed_spec.get('category')} (Confidence: {detailed_spec.get('ai_confidence_score')})"
    )
    print(f"    -> Stored Photo: {detailed_spec.get('photo_url')}")
    print(
        f"    -> Location: Lat {detailed_spec.get('latitude')}, Lng {detailed_spec.get('longitude')}"
    )

    print(f"  Vague Complaint AI Result:")
    print(
        f"    -> Category Assign: {detailed_vag.get('category')} (Confidence: {detailed_vag.get('ai_confidence_score')})"
    )

    # 5. Pagination Standardized Error Testing (Exceeding max limit of 100)
    print("\n[5] Testing Pagination Bounds Security (Fetching limit=500)...")
    r_pag = requests.get(f"{BASE_URL}/api/complaints?limit=500", headers=adm_headers)
    print(f"  Standardized Error Caught (Status {r_pag.status_code}): {r_pag.text}")

    # 6. Workflow & Assignment SLA Testing
    print("\n[6] Testing Assignment Workflow & SLA Timestamp Tracking...")
    r_assign = requests.patch(
        f"{BASE_URL}/api/complaints/{comp_id_specific}/assign",
        json={"assigned_to": "Worker Dave", "assigned_department": "PWD & Roads"},
        headers=adm_headers,
    )
    assigned_data = r_assign.json()
    print(
        f"  Assign Status: {r_assign.status_code} -> New Phase: {assigned_data.get('status')}"
    )
    print(f"  Assigned at timestamp logged: {assigned_data.get('assigned_at')}")

    print("\n[-] Simulating 3 seconds of real-world repair work...")
    time.sleep(3)

    r_resolve = requests.patch(
        f"{BASE_URL}/api/complaints/{comp_id_specific}/status",
        json={"status": "Resolved", "note": "Pothole filled with concrete."},
        headers=adm_headers,
    )
    print(
        f"  Resolve Status: {r_resolve.status_code} -> New Phase: {r_resolve.json().get('status')}"
    )

    # 7. Dashboard SLA verification
    print("\n[7] Verifying Admin Dashboard Analytics Engine...")
    r_dash = requests.get(f"{BASE_URL}/api/dashboard/summary", headers=adm_headers)
    print(f"  Dashboard Status: {r_dash.status_code}")
    dash_data = r_dash.json()
    print(f"  Avg Resolution Hours Overall: {dash_data.get('avg_resolution_hours')}")
    print(
        f"  Avg Assignment-to-Resolution Hours (SLA Metric!): {dash_data.get('avg_assignment_to_resolution_hours')}"
    )

    print("\n✅ V1.0 END-TO-END LIVE DEPLOYMENT TEST COMPLETE!")


if __name__ == "__main__":
    run_all_tests()
