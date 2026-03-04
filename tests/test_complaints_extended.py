

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


def test_pagination_and_filtering(client):
    admin_token = get_auth_token(client, "admin_pag@test.com", "password123", "admin")
    admin_hdr = {"Authorization": f"Bearer {admin_token}"}
    cit_token = get_auth_token(client, "cit_pag@test.com", "password123", "citizen")
    cit_hdr = {"Authorization": f"Bearer {cit_token}"}

    # Create 3 complaints, 2 in North, 1 in South
    c1 = client.post(
        "/api/complaints",
        json={
            "title": "Complaint 1",
            "description": "Pothole on the street causing traffic issues.",
            "ward": "North",
            "category": "General",
            "priority": 1,
        },
        headers=cit_hdr,
    ).json()
    c2 = client.post(
        "/api/complaints",
        json={
            "title": "Complaint 2",
            "description": "No electricity in the entire block since morning.",
            "ward": "North",
            "category": "General",
            "priority": 2,
        },
        headers=cit_hdr,
    ).json()
    c3 = client.post(
        "/api/complaints",
        json={
            "title": "Complaint 3",
            "description": "Water leak from the main pipe on the highway.",
            "ward": "South",
            "category": "General",
            "priority": 1,
        },
        headers=cit_hdr,
    ).json()

    # 1. Test Limit/Offset
    limit_resp = client.get("/api/complaints?limit=2&offset=0", headers=admin_hdr)
    assert len(limit_resp.json()) == 2

    limit_resp2 = client.get("/api/complaints?limit=2&offset=2", headers=admin_hdr)
    assert len(limit_resp2.json()) >= 1  # At least 1 (C3), maybe more from other tests

    # 2. Test Filtering by Ward
    ward_resp = client.get("/api/complaints?ward=South", headers=admin_hdr)
    assert len(ward_resp.json()) >= 1
    for c in ward_resp.json():
        assert c["ward"] == "South"

    # 3. Test Filtering by Priority
    prio_resp = client.get("/api/complaints?priority=2", headers=admin_hdr)
    for c in prio_resp.json():
        assert c["priority"] == 2


def test_complaint_merging(client):
    admin_token = get_auth_token(client, "admin_merge@test.com", "password123", "admin")
    admin_hdr = {"Authorization": f"Bearer {admin_token}"}
    cit_token = get_auth_token(client, "cit_merge@test.com", "password123", "citizen")
    cit_hdr = {"Authorization": f"Bearer {cit_token}"}

    c1 = client.post(
        "/api/complaints",
        json={
            "title": "Merge 1",
            "description": "Merge source.",
            "ward": "East",
            "category": "General",
            "priority": 0,
        },
        headers=cit_hdr,
    ).json()
    c2 = client.post(
        "/api/complaints",
        json={
            "title": "Merge 2",
            "description": "Merge target.",
            "ward": "East",
            "category": "General",
            "priority": 0,
        },
        headers=cit_hdr,
    ).json()

    # Admin merges c1 into c2
    merge_resp = client.post(
        "/api/complaints/merge",
        json={"source_complaint_id": c1["id"], "target_complaint_id": c2["id"]},
        headers=admin_hdr,
    )
    assert merge_resp.status_code == 200

    # Source should be resolved and merged
    c1_fetch = client.get(f"/api/complaints/{c1['id']}", headers=admin_hdr).json()
    assert c1_fetch["is_merged"] is True
    assert c1_fetch["merged_into_id"] == c2["id"]
    assert c1_fetch["status"] == "Resolved"

    # Target should have higher impact and report count
    c2_fetch = client.get(f"/api/complaints/{c2['id']}", headers=admin_hdr).json()
    assert c2_fetch["reports_count"] >= 2
    assert c2_fetch["impact_score"] > c2["impact_score"]

    # Test trying to merge across wards fails
    c3 = client.post(
        "/api/complaints",
        json={
            "title": "Merge 3",
            "description": "Merge target.",
            "ward": "West",
            "category": "General",
            "priority": 0,
        },
        headers=cit_hdr,
    ).json()
    merge_fail = client.post(
        "/api/complaints/merge",
        json={"source_complaint_id": c2["id"], "target_complaint_id": c3["id"]},
        headers=admin_hdr,
    )
    assert merge_fail.status_code == 400
    assert "ward" in merge_fail.json()["detail"].lower()
