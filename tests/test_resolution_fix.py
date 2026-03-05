import pytest
from fastapi.testclient import TestClient
from main import app
from routes.complaints import is_same_dept

def test_is_same_dept_logic():
    # Test cases for the unified matching logic
    assert is_same_dept("Water Department", "Water Supply") == True
    assert is_same_dept("Water", "Water Supply") == True
    assert is_same_dept("Roads and Transport", "Roads") == True
    assert is_same_dept("Sanitation", "General Administration") == False
    assert is_same_dept(None, "Any Dept") == True
    assert is_same_dept("Electricity", "Electric") == True  # "Electri" exists in both

def get_auth_token(client, email, password, role="officer", full_name="Officer", dept=None, ward=None):
    client.post(
        "/api/auth/register",
        json={
            "full_name": full_name,
            "email": email,
            "password": password,
            "role": role,
            "department": dept,
            "ward": ward
        },
    )
    response = client.post(
        "/api/auth/login", json={"email": email, "password": password}
    )
    return response.json()["access_token"]

def test_officer_resolution_with_name_variation(client):
    # 1. Citizen creates a water complaint
    cit_token = get_auth_token(client, "cit@test.com", "pass", role="citizen", full_name="Citizen")
    cit_headers = {"Authorization": f"Bearer {cit_token}"}
    
    resp = client.post(
        "/api/complaints",
        json={
            "title": "Water leak",
            "description": "Leak in the main pipe",
            "ward": "208022",
            "category": "Water Supply",
            "priority": 3,
        },
        headers=cit_headers
    )
    complaint_id = resp.json()["id"]
    
    # 2. Officer from "Water Department" tries to resolve it (it's assigned to "Water Supply")
    off_token = get_auth_token(
        client, "satya@test.com", "pass", 
        role="officer", full_name="Satya Officer", 
        dept="Water Department", ward="208022"
    )
    off_headers = {"Authorization": f"Bearer {off_token}"}
    
    # Try to resolve
    res_resp = client.patch(
        f"/api/complaints/{complaint_id}/status",
        json={
            "status": "Resolved",
            "note": "Fixed the leak",
            "actor": "Satya Officer"
        },
        headers=off_headers
    )
    
    # Before the fix, this would have returned 403. Now it should be 200.
    assert res_resp.status_code == 200
    assert res_resp.json()["status"] == "Resolved"
