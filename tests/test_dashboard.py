

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
    if response.status_code == 409:
        pass
    response = client.post(
        "/api/auth/login", json={"email": email, "password": password}
    )
    return response.json()["access_token"]


def test_dashboard_rbac_and_summary(client):
    admin_token = get_auth_token(client, "admin_dash@test.com", "password123", "admin")
    cit_token = get_auth_token(client, "cit_dash@test.com", "password123", "citizen")

    # 1. Citizen Access Denied
    cit_resp = client.get(
        "/api/dashboard/summary", headers={"Authorization": f"Bearer {cit_token}"}
    )
    assert cit_resp.status_code == 403

    # 2. Admin Access Granted
    admin_resp = client.get(
        "/api/dashboard/summary", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert admin_resp.status_code == 200

    data = admin_resp.json()

    # 3. Check payload structure
    keys_needed = [
        "total_complaints",
        "pending_complaints",
        "in_progress_complaints",
        "resolved_complaints",
        "high_priority_complaints",
        "avg_resolution_hours",
        "ward_stats",
        "category_stats",
    ]
    for k in keys_needed:
        assert k in data

    # Check that arrays are actually lists
    assert isinstance(data["ward_stats"], list)
    assert isinstance(data["category_stats"], list)

    # If there is data, check the dict structures
    if len(data["ward_stats"]) > 0:
        assert "ward" in data["ward_stats"][0]
        assert "total" in data["ward_stats"][0]
        assert "resolved" in data["ward_stats"][0]
        assert "pending" in data["ward_stats"][0]

    if len(data["category_stats"]) > 0:
        assert "category" in data["category_stats"][0]
        assert "total" in data["category_stats"][0]
