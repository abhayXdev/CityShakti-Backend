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

    if response.status_code == 409:
        pass

    response = client.post(
        "/api/auth/login", json={"email": email, "password": password}
    )
    if "access_token" not in response.json():
        print(f"LOGIN FAILED. Status: {response.status_code}, Body: {response.json()}")
    return response.json()["access_token"]


def test_enterprise_features(client):
    # Setup users
    citizen_token = get_auth_token(
        client, "civic1@test.com", "password123", "citizen", "Ravi Mehta"
    )
    admin_token = get_auth_token(
        client, "mayor@test.com", "password123", "admin", "Commissioner Sharma"
    )

    cit_hdr = {"Authorization": f"Bearer {citizen_token}"}
    admin_hdr = {"Authorization": f"Bearer {admin_token}"}

    # 1. Test AI Metatada Extracted
    resp = client.post(
        "/api/complaints",
        json={
            "title": "Broken fire hydrant",
            "description": "The hydrant is physically crushed and spilling water onto the main road causing flooding.",
            "ward": "Koramangala Ward",
            "category": "General",
            "priority": 0,
        },
        headers=cit_hdr,
    )
    assert resp.status_code == 201
    created_complaint_id = resp.json()["id"]

    # Refetch because AI categorization happens in a BackgroundTask after the initial 201 Response
    detail_resp = client.get(f"/api/complaints/{created_complaint_id}", headers=cit_hdr)
    assert detail_resp.status_code == 200
    complaint_data = detail_resp.json()
    complaint_id = complaint_data["id"]

    assert complaint_data["ai_confidence_score"] is not None
    assert complaint_data["is_sla_breached"] is False
    assert complaint_data["escalation_level"] == 0

    # 2. Test Audit Trail (State changes capture old and new values)
    client.patch(
        f"/api/complaints/{complaint_id}/assign",
        json={
            "assigned_to": "Jal Board Team Alpha",
            "assigned_department": "Jal Board / Water Supply",
        },
        headers=admin_hdr,
    )

    # Get details to inspect activity
    detail_resp = client.get(f"/api/complaints/{complaint_id}", headers=admin_hdr)
    activities = detail_resp.json()["activities"]

    # Check that previous and new values are tracked in activities
    assign_activity = next(a for a in activities if a["action"] == "Complaint Assigned")
    assert assign_activity["previous_value"] == "Unassigned"
    assert assign_activity["new_value"] == "Jal Board Team Alpha"

    # 3. Resolve it so it shows in analytics
    client.patch(
        f"/api/complaints/{complaint_id}/status",
        json={
            "status": "Resolved",
        },
        headers=admin_hdr,
    )

    # 4. Test Public Transparency
    transp_resp = client.get("/api/transparency/metrics")
    assert transp_resp.status_code == 200
    pulse = transp_resp.json()["civic_pulse"]
    assert pulse["total_complaints_received"] >= 1
    assert "city_resolution_rate" in pulse
    assert "total_sla_breaches" in pulse

    # 5. Test Admin Analytics
    analytic_resp = client.get("/api/admin/analytics", headers=admin_hdr)
    assert analytic_resp.status_code == 200
    perf = analytic_resp.json()["admin_performance"]
    assert len(perf) > 0
    assert "sla_compliance_rate" in perf[0]

    # 6. Test SLA Escaper (Manually call scan-slas)
    sla_resp = client.post("/api/admin/scan-slas", headers=admin_hdr)
    assert sla_resp.status_code == 200
    assert "SLA Scan Complete" in sla_resp.json()["message"]
