# CityShakti: Smart Public Service CRM - Comprehensive Architecture & Documentation

Welcome to **CityShakti**, a municipal-grade backend infrastructure designed to revolutionize how citizens report civic issues and how government departments resolve them.

This document serves as the absolute source of truth. It details every feature, the exact real-world behavioral flows of the system, how the underlying architecture is secured, and what future improvements could be made.

---

## �️ 1. Core Feature Set

CityShakti is not a simple CRUD application. It is an intelligent CRM built with Python, FastAPI, and SQLAlchemy.

1.  **Strict Authentication & Authorization (RBAC):** Users are explicitly modeled as either `citizen` or `admin`. 
2.  **Machine Learning Categorization:** NLP models automatically read citizen complaints and silently route them to the correct government department (e.g., PWD, Jal Board).
3.  **AI-Powered Duplicate Detection (Cosine Similarity):** The backend scans text vectors. If two citizens report the same issue in the same ward, the AI merges the second report into the first, preventing database clutter while boosting the original complaint's `Impact Score`.
4.  **Service Level Agreements (SLA) Intelligence:** Complaints have a countdown timer. Background tasks automatically detect when a department is overdue, flagging the complaint as `is_sla_breached` and auto-escalating the priority to alert higher officials.
5.  **Immutable Audit Trails:** Every time an admin touches a complaint (assigning, changing status), the system explicitly records the exact `previous_value` and `new_value` in an un-deletable Audit Log instance to ensure 100% government accountability.
6.  **Performance Analytics:** Endpoints designed explicitly to score admin efficiency (resolution speed vs. breach rate).
7.  **Public Transparency:** Open data endpoints that output the city's overall "Civic Pulse" (Resolution Rates, Average Turnaround Times) for journalists.

---

## 🌟 2. Real-Life Behavioral Flow (Scenario Testing)

The entire application logic is built and verified against these specific Indian municipal scenarios:

### Phase 1: The Citizen Experience (Onboarding & Reporting)
**Actors:** Priya (App User), AI Engine
*   **Registration (`/api/auth/register`):** Priya opens the app. She enters her name, email, and a secure password. The system hashes her password via `bcrypt`, saves her as `role: citizen`, and issues a JWT (JSON Web Token).
*   **Login (`/api/auth/login`):** If Priya enters the wrong password, she gets a `401 Unauthorized`. If a bot tries to brute-force her login, the rate limiter kicks in after 5 attempts, throwing a `429 Too Many Requests`.
*   **Reporting (`/api/complaints`):** Priya logs in successfully. She notices a sparking electrical pole near her house in **Koramangala Ward**. She submits a complaint reading: *"Sparks flying from main street lamp, completely dark and unsafe."*
*   **The AI Background Magic:** The API responds instantly (HTTP 201) so Priya isn't kept waiting. In the background (`services/ai.py`), the AI assigns a High Priority (because it detected "unsafe" and "spark"), calculates an **AI Confidence Score**, and automatically sets the Category to **"Electricity Board (DISCOM)"**. 
*   **Community Gamification:** Two days later, her neighbor Rahul logs in and upvotes her complaint. Priya is awarded +5 community points, and the complaint's `Impact Score` rises dynamically, pushing it higher on the Admin's queue.

### Phase 2: The Government Experience (Triage & Resolution)
**Actors:** Commissioner Sharma (Admin)
*   **The Dashboard (`/api/complaints`):** Commissioner Sharma logs in using an `admin` JWT. Unlike Priya, who can only fetch her own complaints, the Admin fetches *all* complaints city-wide.
*   **Accountability Triggers:** He sees Priya's complaint. He assigns it (`/api/complaints/{id}/assign`) to the "BESCOM Rapid Team". The system immediately logs a permanent Audit Trail showing: `Assigned_To changed from 'Unassigned' -> 'BESCOM Rapid Team'`.
*   **SLA Escalation (`/api/admin/scan-slas`):** The team gets delayed by 7 days. At midnight, the automated SLA scanner runs. It notices the Expected Resolution Date has passed. It flips `is_sla_breached` to `True` and bumps the priority level up to maximum to alert the Commissioner.
*   **Resolution:** The BESCOM team fixes the light, uploads a photograph via (`/api/complaints/{id}/updates`) proving the work is done, and flips the status to **"Resolved"**. 

### Phase 3: The Public Scrutiny (Data Journalism)
**Actors:** Anjali (News Reporter)
*   **Open Access (`/api/transparency/metrics`):** Anjali visits a public dashboard. The backend, mapping all data, informs her without needing a login that the city has an **88% Resolution Rate**, taking an average of **4.2 days** to fix issues, and that "Electricity Board (DISCOM)" is currently the most reported category.

---

## 🛡️ 3. Security Posture

The CityShakti backend implements enterprise-grade security mechanisms:

1.  **Authentication Control (OAuth2 with JWT):** Tokens expire securely.
2.  **Cryptographic Password Storage:** Passwords are never logged or stored in plain text. `bcrypt` hashing is used globally.
3.  **Strict Boundary RBAC (`security.py`):** Decorators (e.g., `Depends(require_role("admin"))`) physically block citizens from executing assignment patches or viewing administrative SLA scans.
4.  **Network Rate Limiting (`SlowAPI`):** Endpoints limit the number of requests per minute per IP address to eliminate Denial of Service (DoS) and Scraping attacks.
5.  **Global Exception Masking:** If a critical database fault occurs, the `app.exception_handler(Exception)` catches it. It prints the detailed traceback safely to the server logs for the developer to read, but returns a generic `500 Server Error` to the user so malicious hackers cannot learn about the internal database schema.

---

## 📂 4. File Architecture Map

*   **`main.py`**: The Web Server, Routers, and Exception catches.
*   **`database.py`**: The Database connection logic.
*   **`models.py`**: User, Complaint, and Audit Log SQL schema definitions.
*   **`schemas.py`**: Pydantic models for incoming/outgoing JSON validation.
*   **`security.py` & `dependencies.py`**: JWT generation and Role-Checking middleware.
*   **`rate_limiter.py`**: The traffic cop.
*   **`services/ai.py`**: Machine Learning categorization, deduplication similarity vectors, and mathematical `Impact Score` formulas.
*   **`routes/auth.py`**: Login & Registration mapping.
*   **`routes/complaints.py`**: Core creation, upvoting, and admin assignment routing.
*   **`routes/admin.py`**: The performance metrics and SLA scanner cron endpoints.
*   **`routes/transparency.py`**: The completely public open-city data endpoint.

---

## 🚀 5. Roadmap & Future Improvements

While structurally sound, real-world deployment would benefit from the following upgrades:

1.  **Dockerization:** Currently, deployment requires manual Python environment setups. Creating a `Dockerfile` and `docker-compose.yml` would allow the entire backend (and database) to be spun up anywhere with a single command.
2.  **Alembic Migrations:** SQL schemas currently build on startup. Alembic tracks versions so database columns can be added or deleted later without losing the existing civic data.
3.  **Real Background Handlers (Celery/Redis):** The current `BackgroundTasks` are processed in FastAPI's memory. In a city of 10 million people, offloading the AI matrix calculations to a dedicated Redis queue system (like Celery) would prevent the main web server from locking up under immense load.
4.  **Geolocation (PostGIS):** Currently, `latitude` and `longitude` are simple floats. Moving to a PostGIS-enabled PostgreSQL database would allow for highly advanced "radius searches" (e.g., "Find all duplicate complaints within 500 meters").
5.  **Production Database:** Transitioning from the current internal test databases to a managed cloud PostgreSQL instance.
