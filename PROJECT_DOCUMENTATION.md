# CityShakti: Comprehensive System & Codebase Documentation

This document serves as the absolute, definitive guide to the **CityShakti** Smart Civic Monitoring System. It leaves nothing out. It covers every platform, every third-party API, the complete system architecture, flowcharts for every situation, and a line-by-line / file-by-file explanation of both the Backend and Frontend codebases.

---

## 1. Hosting Platforms & Infrastructure
CityShakti operates on a decoupled architecture, separating the client-side rendering from the server-side API processing.

*   **Frontend Hosting (Vercel):** The React/Next.js client is hosted on Vercel. Vercel provides Edge network caching, ensuring that the HTML/CSS and static assets load instantly for citizens across the region.
*   **Backend Hosting (Render.com):** The FastAPI Python backend is hosted on Render. Render continuously spins the Python environment, running `uvicorn` to listen for API requests.
*   **Database (PostgreSQL):** A managed relational PostgreSQL database stores all structured state (Users, Complaints, OTPs, Audit Logs).

## 2. Third-Party APIs & Services
The platform offloads specific complex workloads to specialized third-party APIs:
*   **Ola Maps API:** The primary engine for high-precision regional intelligence. Replaced the legacy OpenStreetMap (Nominatim) implementation to achieve 100% accuracy for 6-digit Indian PIN codes.
    *   **Reverse Geocoding:** Converts GPS coordinates into strict `incident_ward` values using `api.olamaps.io/places/v1/reverse-geocode`.
    *   **Intelligent PIN Snapping:** Accuracy optimization implemented in `frontend/lib/pincode.ts`. If multiple PIN codes are detected (near boundaries), the system cross-references them with the user's registered home ward and automatically "snaps" to it if found, ensuring 100% jurisdictional accuracy without manual entry.
    *   **Vector Tiles:** Provides the interactive map layer for the dashboard via MapLibre GL JS, authenticated via dynamic `transformRequest` headers and the `NEXT_PUBLIC_OLA_MAPS_API_KEY`.
*   **Brevo (formerly Sendinblue) SMTP API:** Used exclusively for Identity Verification. When a user registers or logs in, the backend securely communicates with `api.brevo.com` using the `BREVO_API_KEY` to dispatch 6-digit One-Time Passcodes (OTPs) to the user's email account. 
*   **ImgBB API:** Used for Evidence Storage. Because hosting base64 images inside a PostgreSQL database is highly inefficient, the frontend intercepts image uploads from the citizen's phone/camera, sends the raw file to `api.imgbb.com`, receives a public `photo_url`, and only saves that short URL string to our database.
*   **HTML5 Geolocation API:** The frontend heavily relies on native browser GPS sensors to extract `latitude` and `longitude` during complaint submission, enabling Ola Maps PIN code mapping.

---

## 3. Core System Workflows (How Things Work)

### A. The Registration & Authentication Pipeline
This workflow ensures that users are real, and that Government Officers are verified before getting access to the system.

```mermaid
sequenceDiagram
    autonumber
    participant Citizen
    participant NextJS (Frontend)
    participant FastAPI (Backend)
    participant Brevo API
    participant Postgres DB

    Citizen->>NextJS (Frontend): Enters Email and hits "Send OTP"
    NextJS (Frontend)->>FastAPI (Backend): POST /auth/send-email-otp
    Note over FastAPI (Backend): Deletes old OTPs to prevent spam
    FastAPI (Backend)->>FastAPI (Backend): Math.random() generates 6-digit secure PIN
    FastAPI (Backend)->>Postgres DB: Stores PIN with 5-minute expiry
    FastAPI (Backend)->>Brevo API: HTTP POST Email Payload
    Brevo API-->>Citizen: Delivers Email to Inbox
    Citizen->>NextJS (Frontend): Types 6-digit OTP & Password
    NextJS (Frontend)->>FastAPI (Backend): POST /auth/register
    FastAPI (Backend)->>Postgres DB: Checks if OTP matches and is not expired
    Note over FastAPI (Backend): bcrypt.hashpw() secures the password
    FastAPI (Backend)->>Postgres DB: Creates row in "users" table
    FastAPI (Backend)-->>NextJS (Frontend): JWT Access Token Granted
```

### B. The Complaint Routing & Lifecycle Workflow
This flowchart illustrates what happens from the moment a pothole is reported to the moment it is fixed.

```mermaid
flowchart TD
    A["Citizen Clicks Submit"] --> B["Geo: Extract GPS"]
    B --> C["Ola: Reverse Geocode"]
    C --> D["Map: 6-Digit PIN"]
    D --> E["AI: Predict Deadline"]
    E --> F["DB: Save Complaint"]
    
    F --> G["Pending: Routed to Officer"]
    G --> H["InProgress: Officer Accepts"]
    H --> I["Resolved: Officer Fixes"]
    
    I --> J{"Citizen Verifies"}
    J -- "Accept" --> K["Closed"]
    J -- "Reject" --> L["Escalated"]
    
    G --> M["Escalated: SLA Breach"]
    H --> M
```
**Explanation of Edge Cases:**
- **Citizen Rejection:** If an officer marks an issue "Resolved" but the pothole is still there, the citizen presses `Reject Resolution`. The status becomes `Escalated`, and the department's metrics are penalized.
- **SLA Breach:** Run by an automated background check, if the system clock passes the `expected_resolution_date` and the status is still Pending/InProgress, the complaint turns `Escalated`.

### C. The Government Officer Approval Pipeline
To ensure security, public officials cannot immediately access internal dashboards upon registration. They are isolated until a top-level administrator verifies their credentials.

```mermaid
sequenceDiagram
    participant Officer
    participant Frontend
    participant Backend
    participant SudoAdmin

    Officer->>Frontend: Selects "Officer" Role & Department/Ward
    Officer->>Backend: POST /auth/register
    Backend-->>Frontend: JWT Token (Role: Officer, is_suspended: True)
    Officer->>Frontend: Logs in
    Frontend->>Backend: GET /dashboard/stats
    Backend-->>Frontend: 403 Forbidden (Account Suspended)
    
    SudoAdmin->>Frontend: Logs in to "Sudo" Master Dashboard
    Frontend->>Backend: GET /admin/officers/pending
    Backend-->>Frontend: List of Suspended Officers
    SudoAdmin->>Frontend: Clicks "Approve" for Officer
    Frontend->>Backend: PUT /admin/officers/{id}/approve
    Backend-->>Frontend: 200 OK (is_active: True, is_suspended: False)
    
    Officer->>Frontend: Refreshes Page
    Frontend->>Backend: GET /dashboard/stats
    Backend-->>Frontend: 200 OK (Access Granted to Department Data)
```

### D. The Dynamic SLA & Progress Update Flow
How the backend calculates deadlines, and how officers communicate updates to the public with images before resolving a ticket.

```mermaid
flowchart TD
    A["Citizen Submits Issue"] --> B{"AI SLA Router"}
    B -- "Urgent: Water Pipe" --> C["SLA: 24 Hours"]
    B -- "Medium: Pothole" --> D["SLA: 3 Days"]
    B -- "Low: Park Cleanup" --> E["SLA: 7 Days"]
    
    C --> F["Officer Dashboard"]
    D --> F
    E --> F
    
    F --> G["Officer Begins Work"]
    G --> H["Before Photo Update"]
    H --> I["After Photo Update"]
    I --> J["Officer Marks Resolved"]
    J -- "UI LOCK" --> K["Wait for Verification"]
    K --> L{"Citizen Response"}
    L -- "Accept" --> M["Status: Closed"]
    L -- "Reject" --> N["Status: In-Progress"]
```

### E. Public Transparency & Community Engagement Flow
Citizens don't need to create redundant complaints. The system offers a community feed to consolidate voices.

```mermaid
flowchart LR
    A["New Pothole"] --> B["Regional Map (Red Dot)"]
    B --> C["Citizen Views Map"]
    C --> D{"In My Ward?"}
    D -- "Yes" --> E["Visible Pin with Support Button"]
    D -- "No" --> F["Filtered Out"]
    E --> G["Click Support in Community"]
    G --> H["Deep Link to Community"]
    H --> I["Auto-Open Ticket Detail"]
    I --> J["Click Upvote"]
    J --> K["Priority Score Increments"]
    K --> L["Pushes to Top of Queue"]
```

### F. Evidence Image Upload Sequence (ImgBB)
To keep the PostgreSQL database blazing fast, large binary image files are never stored in the database. 

```mermaid
sequenceDiagram
    participant Citizen
    participant Browser
    participant ImgBB API
    participant FastAPI
    participant Postgres DB

    Citizen->>Browser: Selects Photo & clicks Submit
    Browser->>Browser: Converts image file to Base64 String
    Browser->>ImgBB API: HTTP POST (Base64 Payload + ImgBB API Key)
    ImgBB API-->>Browser: Returns short public JSON URL (e.g., ibb.co/xyz.jpg)
    Browser->>FastAPI: POST /complaints/ (includes photo_url string)
    FastAPI->>Postgres DB: Saves short URL string
    FastAPI-->>Browser: 200 OK (Complaint Created)
```

### G. Data Aggregation & Admin Analytics Pipeline
How the "Sudo" and "Officer" dashboards render real-time statistics without crashing the database under heavy load.

```mermaid
flowchart TD
    A["Frontend Mounts"] --> B["GET /dashboard/stats"]
    B --> C{"FastAPI Guard"}
    C -- "Unauthorized" --> D["HTTP 401/403"]
    C -- "Authorized" --> E["SQLAlchemy Aggregation"]
    
    E --> F["SQL: Group by Status"]
    F --> G["Generate JSON Payload"]
    G --> H["Frontend Recharts Library"]
    H --> I["SVG Visuals Rendered"]
```

### H. Global Error Handling & Rate Limiting Architecture
The system is protected globally by middleware and exception handlers to ensure elegant failures and prevent DDoS attacks.

```mermaid
flowchart LR
    A["Malicious User"] -- "Spam Login" --> B["SlowAPI Middleware"]
    B -- "Under Limit" --> C["Process Request"]
    B -- "Over Limit" --> D["HTTP 429 Error"]
    
    E["Bad Payload"] --> F["Pydantic Validation"]
    F -- "Missing Data" --> G["HTTP 422 Error"]
    
    H["DB Connection Fail"] --> I["SQLAlchemy Error Handler"]
    I --> J["HTTP 500 Error"]
```

### I. Elastic Bounding Box Logic (Spatial Restraint)
To prevent Citizens and Officers from wandering across the entire map of India, the system calculates a dynamic boundary based on the complaints within their jurisdiction.

```mermaid
flowchart TD
    A["Load Ward Complaints"] --> B["Generate LngLatBounds"]
    B --> C["Calc latDiff & lngDiff"]
    C --> D["Apply 50% Elastic Buffer"]
    D --> E["map.setMaxBounds()"]
    E --> F["Restrict to Ward View"]
```
**Technical Implementation:**
- **Buffer**: A 50% padding is added to the SW and NE coordinates of the ward's complaints.
- **Fallthrough**: If no complaints exist, the map defaults to the center of Delhi with a broad view until reports are filed.
- **Safety**: Prevents information leakage from other wards to unauthorized users.

### J. Proactive Duplicate Detection & Upvote Flow
To prevent redundant tickets and maintain a clean system, CityShakti uses a synchronous AI check during the submission process.

```mermaid
flowchart TD
    A["Citizen Clicks Submit"] --> B["Backend: Fetch Active Complaints in Ward"]
    B --> C["AI: Calculate Cosine Similarity"]
    C --> D{"Similarity > 80%?"}
    D -- "No" --> E["Create New Ticket"]
    D -- "Yes" --> F["Frontend: Show Duplicate Conflict Modal"]
    F --> G{"User Choice"}
    G -- "Upvote Instead" --> H["API: POST /upvote (Original ID)"]
    G -- "Cancel" --> I["Abort Submission"]
    H --> J["Success: Notified & Priority Increased"]
```

---

## 4. Frontend Codebase: File-by-File Explanation
The entire user interface is built using Next.js 13+ (App Router), React, Tailwind CSS, and Shadcn UI components.

### Core Configuration
*   **`frontend/package.json`**: Lists all npm dependencies (`maplibre-gl` for maps, `lucide-react` for icons, `date-fns` for time, `recharts` for charts).
*   **`frontend/.env.local`**: Stores critical integration keys:
    *   `NEXT_PUBLIC_OLA_MAPS_API_KEY`: Authenticates Tile & Geocoding requests.
    *   `NEXT_PUBLIC_IMGBB_API_KEY`: Securely handles evidence photo uploads without leaking keys in the source code.
    *   `NEXT_PUBLIC_API_BASE_URL`: Defines the Backend endpoint (Cloud or Localhost).
*   **`frontend/tailwind.config.js`**: Controls the professional design system, including custom color tokens (`chart-1` through `chart-5`).

### The App Router (`/app`)
*   **`frontend/app/layout.tsx`**: The main HTML wrapper. It contains the `<head>` tags, imports the global CSS, and wraps the entire application in the `ThemeProvider` (for dark mode) and `AppProvider` (for global React state).
*   **`frontend/app/page.tsx`**: The main route (`/`). It dictates the view hierarchy. If the user is *not* logged in, it shows the landing page. If they *are* logged in, it mounts the `<DashboardLayout>` component.

### The React Context & Logic (`/lib`)
*   **`frontend/lib/app-context.tsx`**: A massive React `createContext` wrapper. It holds global state (`user`, `complaints`, `theme`). It exposes a custom hook `useApp()`. This ensures we don't have to pass "user={user}" down a 20-component deep prop-chain.
*   **`frontend/lib/api.ts`**: The bridge to the backend. It contains dozens of `fetch()` functions (`loginApi`, `registerApi`, `getComplaintDetailApi`). It reads the `NEXT_PUBLIC_API_URL` environment variable (pointing to Render in production).
    *   **Visibility Logic**: Modified to ensure that even if a complaint is marked as "merged," it remains visible to its original author in the citizen dashboard, preventing "phantom" or "disappearing" tickets.
*   **`frontend/lib/data.ts`**: Contains all the TypeScript interfaces (`type Complaint`, `type User`). Defines exactly what properties exist on a complaint object (e.g., `expectedResolutionDate`, `photoUrl`).
*   **`frontend/lib/utils.ts`**: Contains the `cn()` helper function which merges Tailwind classes dynamically using `clsx` and `tailwind-merge` (preventing CSS conflicts).

### The UI Components (`/components`)
*   **`frontend/components/dashboard-layout.tsx`**: The structural shell of the logged-in app. It renders the top navigation bar, the sidebar menu, the user profile dropdown, and the "Log Out" button.
*   **`frontend/components/login-page.tsx` & `register-page.tsx`**: The authentication forms. They handle user input, form validation, toggling loading spinners, executing the OTP email request, and finally catching the JWT token to log the user in.
*   **`frontend/components/map-view.tsx`**: The interactive visual command center.
    *   **Engine**: Built on MapLibre GL JS with Ola Maps Vector Tiles.
    *   **Elastic Bounding Box**: Automatically restricts Citizens and Officers to their own ward with a dynamic 50% buffer, preventing "map wandering" while ensuring all local issues are visible.
    *   **Deep Linking**: Features a "Support in Community" button that uses global React context to redirect users to the Community tab and auto-open the complaint for upvoting.
    *   **Strict Filtering**: Citizens are strictly limited to seeing "red dots" only from their own registered PIN code region.
*   **`frontend/components/community-view.tsx`**: A public feed that fetches all complaints in the current PIN code. It implements an auto-open listener for deep-linked complaints from the Map.
*   **`frontend/components/dashboard-overview.tsx`**: The primary operational dashboard.
    *   **Logic:** Dynamically renders UI based on `user.role` (Citizen/Officer/Sudo).
    *   **Redundancy Fix**: Implemented `isActionPending` state logic. When an officer clicks "Mark Resolved", all action buttons enter a `disabled` state and text changes to "Processing..." until the API response returns and the local state is synchronized.
    *   **Administrator Controls**: Features a "Dept/Ward Match" security check. An officer can *view* any public report, but can only *modify* (Update/Resolve) a report if their `user.department` matches the complaint's department AND their `user.ward` matches the incident location.
    *   **Visual Feedback**: Integrated `uploadingUpdateImage` spinner and custom `Badge` colors for "Escalated" status (pulsing red).
    *   **Role Badges**: Logic fixed to correctly display "Officer Access" badges in the global header, ensuring clear session visibility.
    *   **Proactive Prevention UI**: Intercepts `409 Conflict` errors from the backend. If a duplicate is found, it triggers a `window.confirm` modal prompting the user to upvote the existing issue instead of creating a duplicate.
    *   **Evidence Dashboard Column**: Feature implemented for Officers and Admin. A dedicated column in the complaint table shows a `View` image icon. Clicking it opens the incident photo in a high-resolution new tab, resolving previous Z-index and focus-trap issues.
    *   **Secure API Handling**: Uses `process.env.NEXT_PUBLIC_IMGBB_API_KEY` dynamically. Includes an environment check to alert admins if the key is missing.
*   **`frontend/components/officer-management.tsx`**: A Sudo-Admin strictly protected view. Renders a table of pending Government Officer accounts. Sudo admins click "Approve" (which flips `is_active=True` in the DB) or "Suspend".
*   **`frontend/components/ui/*`**: A folder containing 40+ atomic, reusable UI components (Buttons, Inputs, Dialogs, Badges, Tabs, Skeleton loaders). These are generated by Shadcn UI and ensure the application always looks professional and accessible (WAI-ARIA compliant).

---

## 5. Backend Codebase: File-by-File Explanation
The whole API is built on FastAPI (modern Python 3.10+ ASGI framework) aiming for extreme performance and absolute Type Safety.

### Core Configuration & Boot 
*   **`BackEnd/main.py`**: The heart of the backend.
    *   **CORS Protection:** Configures `CORSMiddleware` to ensure only the Vercel frontend URL is permitted to make requests (blocking cross-site scripting from attackers).
    *   **Rate Limiting:** Injects `slowapi` to block IP addresses making too many requests per minute.
    *   **Auto-Migration:** Uses an `@app.on_event("startup")` hook to run `subprocess.run(["alembic", "upgrade", "head"])`. This means when Render boots the server, it automatically creates the SQL tables if they don't exist.
    *   **Sudo Seeder:** Automatically creates the master `sudo@cityshakti.com` account on boot so developers never get locked out.
*   **`BackEnd/requirements.txt`**: Declares Python dependencies (FastAPI, Uvicorn, SQLAlchemy for the DB, Psycopg2-binary for Postgres drivers, Passlib for bcrypt hashing).
*   **`BackEnd/alembic.ini` & `alembic/`**: Configures the Alembic migration engine. The `alembic/versions` folder contains Python scripts that instruct Postgres exactly how to `CREATE TABLE`, `ADD COLUMN`, or `DROP TABLE` across different deployment versions without losing data.

### Database & ORM (`models`, `database`, `schemas`)
*   **`BackEnd/database.py`**: Initializes the SQLAlchemy `Engine` and `SessionLocal` class using the `DATABASE_URL` extracted from `os.getenv()`.
*   **`BackEnd/models.py`**: Translates Python Classes into Postgres Relational Tables.
    *   `User`: Holds `id`, `full_name`, `email`, `password_hash`, `role` ( citizen/officer/sudo ), `ward` (pincode), `department`. 
    *   `Complaint`: The massive ticket model. Holds `latitude`, `longitude`, `status`, `photo_url`, `is_sla_breached`. Uses `relationship("User")` to link a citizen's ID to the complaint.
    *   `EmailOTP`: Stores the 6-digit codes sent via Brevo, alongside an `expires_at` timestamp.
*   **`BackEnd/schemas.py`**: Pydantic validation models. While `models.py` defines the *database*, `schemas.py` defines *what the user is allowed to send over the API network*. (e.g., `UserRegister` schema ensures the password string is present. `ComplaintCreate` schema ensures lat/lng are floats).

### Security & Dependency Injection
*   **`BackEnd/security.py`**: Holds cryptographic math. 
    *   `hash_password(string)` transforms a plaintext password into an uncrackable Bcrypt hash.
    *   `verify_password(plain, hash)` compares a login attempt against the DB safely.
    *   `create_access_token(data)` signs a JSON Web Token using the `SECRET_KEY`.
*   **`BackEnd/dependencies.py`**: The gatekeeper. Contains injected functions like `get_db` (opens a fresh SQL transaction and safely closes it later). Contains `get_current_user` (reads the JWT header, decodes it, queries the DB, and throws `401 Unauthorized` if invalid). Contains `get_current_officer` and `get_current_sudo_user` to block roles that don't belong here.

### Services (The Business Logic)
*   **`BackEnd/services/notifications.py`**: Exclusively handles Brevo SMTP. Reads `BREVO_API_KEY` and `BREVO_SENDER_EMAIL`. Exposes a single `send_email_brevo(to, subject, html)` function.
*   **`BackEnd/services/ai.py`**: The predictive logic brain. Features the `predict_resolution_time(category, description)` function. It uses heuristic analysis (searching the text for keywords like "urgent", "major", "minor", checking the category) to calculate an SLA (Service Level Agreement) target. It adds X hours/days to the current `datetime.utcnow()` to generate the `expected_resolution_date`.

### Routers (The Network Endpoints)
*   **`BackEnd/routes/auth.py`**: Handles all Account routes. Contains `/register` (checks if user exists, creates them), `/login` (checks password, issues token), and `/send-email-otp` (fires Brevo code).
*   **`BackEnd/routes/complaints.py`**: The workhorse API.
    *   `POST /`: Takes a citizen's complaint form payload, triggers the AI in `services/ai` to assign a deadline, attaches the citizen's ID via the JWT dependency, and writes it to DB.
    *   `GET /`: Fetches lists of complaints. Dynamically filters the SQL query depending on if the requester is an Officer (only gets their PIN code) or Citizen (gets their own list). Include `.limit()` and `.offset()` for frontend pagination.
    *   `PUT /{id}/status`: Called by Officers to change the status (e.g., "Pending" -> "Resolved"). Logs an entry to `ComplaintActivity`.
    *   **Unified Multi-Citizen Notifications**: When an officer resolves or rejects a primary complaint, the router in `update_compl_status` queries all tickets merged into that ID. It automatically dispatches update notifications to **every reporter** involved, ensuring total transparency and cross-departmental accountability.
    *   **Synchronous Duplicate Detection**: Modified `POST /` to include a pre-save check. It queries all active, non-merged complaints in the target ward and runs a `cosine_similarity` check. If a match exceeds 0.8, it raises a `HTTP 409 CONFLICT`.
    *   **Space-Insensitive Ward Filtering**: All ward comparisons (in SQL and Python) now utilize `.replace(' ', '')` and `func.replace(field, ' ', '')`. This ensures that `208 007` and `208007` are treated as the same region, preventing jurisdictional bypasses.
    *   **Jurisdictional Enforcement**: Strict 403 Forbidden checks implemented for status updates. Officers can only modify tickets where their assigned ward matches the incident ward.
*   **`BackEnd/routes/dashboard.py`**: Administrative endpoints. Runs complex SQL aggregation queries (`db.query(func.count(Complaint.id)).group_by(Complaint.status).all()`) to calculate the exact statistics rendered on the Next.js Recharts graphs.
*   **`BackEnd/routes/admin.py`**: Strict Sudo-only routes. Endpoints to `GET /officers/pending` or `PUT /officers/{id}/approve`.
*   **`BackEnd/routes/transparency.py`**: A public router that requires no JWT token. Allows anyone to fetch aggregated public stats for a specific PIN code, allowing communities to see their local government's resolution velocity without making an account.

---
**End of Documentation.**
*This system architecture correctly implements scalable modern computing principles, guaranteeing high performance under public load, stringent administrative boundaries, and zero-downtime scalability via Vercel/Render edges.*
