import pytest


def get_auth_token(client, email, password, role="citizen", full_name="User"):
    response = client.post(
        "/api/auth/register",
        json={
            "full_name": full_name,
            "email": email,
            "password": password,
            "role": role,
        },
    )

    # If the email is already registered, this handles it gracefully for test reuse
    if response.status_code == 409:
        pass

    response = client.post(
        "/api/auth/login", json={"email": email, "password": password}
    )
    return response.json()["access_token"]


def test_citizen_constraints(client):
    """
    Test that a citizen can create a complaint and only view their own complaints.
    """
    # 1. Register a citizen
    token1 = get_auth_token(
        client, "rahul@test.com", "password", "citizen", "Rahul Verma"
    )
    headers1 = {"Authorization": f"Bearer {token1}"}

    # 2. Citizen creates a complaint
    client.post(
        "/api/complaints",
        json={
            "title": "Broken street light",
            "description": "The street light in front of my house is broken.",
            "ward": "Andheri East",
            "category": "General",
            "priority": 2,
        },
        headers=headers1,
    )

    # 3. Register a DIFFERENT citizen
    token2 = get_auth_token(
        client, "amit@test.com", "password", "citizen", "Amit Patel"
    )
    headers2 = {"Authorization": f"Bearer {token2}"}

    # 4. Verify Citizen 2 cannot see Citizen 1's complaint in the list
    list_resp = client.get("/api/complaints", headers=headers2)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 0

    # 5. Verify Citizen 1 can see their own complaint
    list_resp1 = client.get("/api/complaints", headers=headers1)
    assert len(list_resp1.json()) == 1

    complaint_id = list_resp1.json()[0]["id"]

    # 6. Verify Citizen 2 gets a 403 Forbidden when trying to access Citizen 1's complaint directly
    fetch_resp = client.get(f"/api/complaints/{complaint_id}", headers=headers2)
    assert fetch_resp.status_code == 403


def test_admin_assignment_and_status(client):
    """
    Test that an admin can view all complaints, assign them to departments, and update their status.
    """
    # 1. Setup a citizen and create a complaint
    cit_token = get_auth_token(
        client, "sneha@test.com", "password", "citizen", "Sneha Rao"
    )
    cit_headers = {"Authorization": f"Bearer {cit_token}"}

    resp = client.post(
        "/api/complaints",
        json={
            "title": "Water Leakage",
            "description": "Massive water pipe burst.",
            "ward": "Bandra West",
            "category": "General",
            "priority": 5,
        },
        headers=cit_headers,
    )
    complaint_id = resp.json()["id"]

    # 2. Register an admin
    admin_token = get_auth_token(
        client, "commissioner@test.com", "password", "admin", "Commissioner Sharma"
    )
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 3. Verify Admin can see the citizen's complaint in the list
    list_resp = client.get("/api/complaints", headers=admin_headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) > 0

    # 4. Admin assigns the complaint to a department
    assign_resp = client.patch(
        f"/api/complaints/{complaint_id}/assign",
        json={
            "assigned_to": "Rakesh Engineer",
            "assigned_department": "Jal Board / Water Supply",
            "actor": "Commissioner Sharma",
        },
        headers=admin_headers,
    )
    assert assign_resp.status_code == 200
    assert assign_resp.json()["assigned_department"] == "Jal Board / Water Supply"

    # Normally, assigning a 'Pending' complaint moves it to 'In Progress'. Verify this.
    assert assign_resp.json()["status"] == "In Progress"

    # 5. Admin updates the status to Resolved
    status_resp = client.patch(
        f"/api/complaints/{complaint_id}/status",
        json={
            "status": "Resolved",
            "note": "The pipe was fixed.",
            "actor": "Commissioner Sharma",
        },
        headers=admin_headers,
    )
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "Resolved"

    # 6. Admin adds a progress update (e.g., attach a photo)
    progress_resp = client.post(
        f"/api/complaints/{complaint_id}/updates",
        json={"phase": "after", "note": "All fixed and dry."},
        headers=admin_headers,
    )
    assert progress_resp.status_code == 201

    # 7. Citizen attempts an admin action (Assign) and fails (403 Forbidden)
    forbidden_assign = client.patch(
        f"/api/complaints/{complaint_id}/assign",
        json={
            "assigned_to": "Ramesh PWD worker",
            "assigned_department": "PWD & Roads",
        },
        headers=cit_headers,
    )
    assert forbidden_assign.status_code == 403
