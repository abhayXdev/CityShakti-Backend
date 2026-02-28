def test_register_and_login(client):
    # 1. Test Registration
    response = client.post(
        "/api/auth/register",
        json={
            "full_name": "Rajesh Kumar",
            "email": "rajesh@test.com",
            "password": "password123",
            "role": "citizen",
        },
    )
    assert response.status_code == 201

    # Check duplicate email
    response = client.post(
        "/api/auth/register",
        json={
            "full_name": "Rajesh Kumar",
            "email": "rajesh@test.com",
            "password": "password123",
            "role": "citizen",
        },
    )
    assert response.status_code == 409

    # 2. Test Login
    response = client.post(
        "/api/auth/login", json={"email": "rajesh@test.com", "password": "password123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data


def test_rate_limiting_login(client):
    # The rate limiter is configured to 10/minute for login
    payload = {"email": "test@test.com", "password": "wrong"}

    # Fire 10 requests, which should be within the limit or hit the 11th
    # It might take a few given slowapi resets. We send 12 just in case.
    for i in range(10):
        response = client.post("/api/auth/login", json=payload)

    # The 11th request MUST be rate limited (429)
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == 429
