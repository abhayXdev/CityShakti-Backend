import requests
import json
import time

BASE_URL = "http://localhost:8000/api"


def test_auto_assign():
    print("Testing Auto-Assignment...")

    # 1. Login to get token
    login_response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": "verified_citizen@test.com", "password": "password123"},
    )

    if login_response.status_code != 200:
        print("Failed to login. Please ensure the server is running and user exists.")
        print(login_response.text)
        return

    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Submit a complaint that should trigger auto-assignment
    complaint_data = {
        "title": "Massive power outage in the whole block",
        "description": "The entire street has been completely dark for the past 4 hours. All streetlights and house electricity are gone.",
        "ward": "South",
        "category": "General",  # Should be overridden by AI
        "priority": 0,  # Should be overridden by AI
    }

    res = requests.post(f"{BASE_URL}/complaints", json=complaint_data, headers=headers)
    print(f"Create Complaint Status: {res.status_code}")
    complaint = res.json()
    complaint_id = complaint["id"]
    print(f"Created Complaint ID: {complaint_id}")

    # 3. Wait for background task to finish
    print("Waiting 3 seconds for AI Categorization background task...")
    time.sleep(3)

    # 4. Fetch the complaint again to check status
    res = requests.get(f"{BASE_URL}/complaints/{complaint_id}", headers=headers)
    updated_complaint = res.json()

    print("\n--- Auto-Assignment Results ---")
    print(
        f"Original Category: General -> New Category: {updated_complaint['category']}"
    )
    print(f"Original Status: Submitted -> New Status: {updated_complaint['status']}")
    print(f"Assigned Department: {updated_complaint.get('assigned_department')}")

    if (
        updated_complaint["category"] == "Electricity Board (DISCOM)"
        and updated_complaint["status"] == "Assigned"
        and updated_complaint["assigned_department"] == "Electricity Department"
    ):
        print(
            "\n✅ SUCCESS: Complaint was automatically categorized and routed to the correct department!"
        )
    else:
        print("\n❌ FAILURE: Auto-assignment did not work as expected.")


if __name__ == "__main__":
    test_auto_assign()
