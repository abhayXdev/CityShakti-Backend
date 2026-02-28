# CityShakti: Smart Public Service CRM - Backend

Welcome to the backend infrastructure for **CityShakti**, an enterprise-grade municipal ecosystem designed to revolutionize how citizens report civic issues and how governments resolve them.

This application is built using **FastAPI**, **PostgreSQL**, **SQLAlchemy**, and **Machine Learning** auto-categorization engines.

---

## 🏗️ Core Features
1. **Machine Learning Categorization**: NLP models automatically route complaints (e.g., "Water Leak" seamlessly to the proper entity like the Jal Board).
2. **AI Duplicate Detection**: Cosine similarity automatically discovers duplicate complaints and merges them based on geographic wards to reduce departmental clutter.
3. **Automated SLA Intelligence**: API chron jobs detect delayed complaints, flagging breaches and bubbling them up priority queues to enforce Service Level Agreements.
4. **Immutable Audit Trails**: State mutation delta-tracking to ensure deep, historic government accountability for every action performed by an admin. 
5. **Open Transparency Endpoints**: Civic telemetry via public unauthenticated endpoints offering live systemic resolution metrics to data journalists and the public.
6. **Strict RBAC Security**: JWT Authorization explicitly restricting data streams between standard `citizens` and municipal `admins`.

## 🛠️ Tech Stack
*   **Web Framework:** FastAPI (Python)
*   **Database:** PostgreSQL
*   **ORM:** SQLAlchemy 
*   **Migrations:** Alembic
*   **Security:** OAuth2 (JWT), bcrypt hashing, SlowAPI rate limiting
*   **Deployment:** Docker & Docker Compose

## 🚀 Quick Start (Deployment)

To launch this backend locally or on a production server, it is fully Dockerized.

### 1. Configure the Environment
Ensure a `.env` file exists with the following values:
```env
DATABASE_URL=postgresql://city:citypass@db:5432/citydb
POSTGRES_USER=city
POSTGRES_PASSWORD=citypass
POSTGRES_DB=citydb
SECRET_KEY=your_secure_random_string_here
```

### 2. Build and Start the Cluster
```bash
docker-compose up -d --build
```

### 3. Generate the Database Tables
Because this project utilizes zero-downtime schema migrations, you must safely initialize the tables via Alembic from within the container:
```bash
docker-compose exec web alembic upgrade head
```

The API will now be fully running and accessible at `http://localhost:8000/docs` (Interactive Swagger UI).

## 📄 Full Documentation
Please read the comprehensive architectural design file located at [PROJECT_DOCUMENTATION.md](PROJECT_DOCUMENTATION.md) for detailed blueprints of the real-life behavioral scenarios, exact security constraints, and full file-system mappings.
