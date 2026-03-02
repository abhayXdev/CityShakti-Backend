def test_login_invalid_credentials(client):
    # 1. Unregistered Email
    response = client.post(
        "/api/auth/login", json={"email": "nobody@test.com", "password": "password123"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"

    # 2. Invalid Password
    # First register a user
    client.post(
        "/api/auth/register",
        json={
            "full_name": "Edge Case User",
            "email": "edge@test.com",
            "password": "correctpassword",
            "role": "citizen",
        },
    )
    response = client.post(
        "/api/auth/login", json={"email": "edge@test.com", "password": "wrongpassword"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


def test_missing_registration_fields(client):
    response = client.post(
        "/api/auth/register",
        json={
            "email": "missing@test.com",
            "password": "password123",
            # missing full_name
        },
    )
    assert response.status_code == 422  # Unprocessable Entity


def test_token_refresh(client):
    # Register and login to get both tokens
    client.post(
        "/api/auth/register",
        json={
            "full_name": "Refresh User",
            "email": "refresh@test.com",
            "password": "password123",
            "role": "citizen",
        },
    )
    login_resp = client.post(
        "/api/auth/login", json={"email": "refresh@test.com", "password": "password123"}
    )
    assert login_resp.status_code == 200
    data = login_resp.json()
    refresh_token = data.get("refresh_token")
    assert refresh_token is not None

    import time

    time.sleep(1)  # Ensure JWT issued at timestamp differs

    # Use refresh token to get a new access token
    refresh_resp = client.post(
        "/api/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert refresh_resp.status_code == 200
    new_data = refresh_resp.json()
    assert "access_token" in new_data
    assert new_data["access_token"] != data["access_token"]


def test_me_endpoint(client):
    # Register and login
    client.post(
        "/api/auth/register",
        json={
            "full_name": "Profile User",
            "email": "profile@test.com",
            "password": "password123",
            "role": "citizen",
            "ward": "North",
        },
    )
    login_resp = client.post(
        "/api/auth/login", json={"email": "profile@test.com", "password": "password123"}
    )
    token = login_resp.json()["access_token"]

    # Fetch profile
    me_resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    profile = me_resp.json()
    assert profile["full_name"] == "Profile User"
    assert profile["email"] == "profile@test.com"
    assert profile["role"] == "citizen"
    assert profile["ward"] == "North"
    assert profile["points"] == 0
    assert profile["is_active"] is True
