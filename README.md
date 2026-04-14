# FastAPI Auth Service

A production-ready backend authentication service built with **FastAPI**, featuring JWT-based auth, Google OAuth2, role-based access control, and SMS/Email integrations.

---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Setup Instructions](#setup-instructions)
- [Environment Configuration](#environment-configuration)
- [Running with Docker](#running-with-docker)
- [Database Migrations](#database-migrations)
- [API Documentation](#api-documentation)
- [Running Tests](#running-tests)
- [Security Design](#security-design)
- [Assumptions & Limitations](#assumptions--limitations)

---

## Features

| Category | Details |
|---|---|
| **Authentication** | JWT access tokens (30min TTL) + refresh tokens (7-day TTL) with rotation |
| **Social Auth** | Google OAuth2 (OpenID Connect) |
| **RBAC** | `admin` and `user` roles, enforced at the dependency level |
| **SMS** | Twilio integration — welcome SMS, OTP delivery |
| **Email** | SendGrid integration — welcome, password reset, login alerts |
| **Database** | PostgreSQL via SQLAlchemy 2.x ORM |
| **Migrations** | Alembic with auto-generate support |
| **Validation** | Pydantic v2 schemas with custom validators |
| **Logging** | Structured JSON logs (structlog) with per-request correlation IDs |
| **Rate Limiting** | SlowAPI (configurable per-minute limit) |
| **Docker** | Multi-stage Dockerfile + Docker Compose with health checks |
| **Testing** | pytest with in-memory SQLite, transaction rollback isolation, 70%+ coverage target |

---

## Architecture

```
┌─────────────┐     ┌──────────────────────────────────────────┐
│   Client    │────▶│             FastAPI App                   │
└─────────────┘     │  ┌──────────────┐  ┌──────────────────┐  │
                    │  │  Middleware   │  │   API Routers    │  │
                    │  │  - CORS       │  │  /auth           │  │
                    │  │  - RateLimit  │  │  /users          │  │
                    │  │  - ReqLogging │  └────────┬─────────┘  │
                    │  └──────────────┘           │             │
                    │              ┌──────────────▼──────────┐  │
                    │              │      Service Layer       │  │
                    │              │  auth_service            │  │
                    │              │  email_service (SG)      │  │
                    │              │  sms_service (Twilio)    │  │
                    │              │  google_oauth            │  │
                    │              └──────────────┬──────────┘  │
                    │                             │             │
                    │              ┌──────────────▼──────────┐  │
                    │              │   SQLAlchemy ORM        │  │
                    │              └──────────────┬──────────┘  │
                    └─────────────────────────────┼─────────────┘
                                                  │
                                        ┌─────────▼──────────┐
                                        │   PostgreSQL DB     │
                                        └────────────────────┘
```

**Clean architecture layers:**
1. **Routers** — HTTP concerns only (request parsing, response serialization)
2. **Services** — business logic, no HTTP awareness
3. **Models** — SQLAlchemy ORM, one file per domain entity
4. **Schemas** — Pydantic I/O contracts, separate from ORM models
5. **Core** — cross-cutting concerns (config, security, logging, dependencies)

---

## Project Structure

```
fastapi-auth-service/
├── app/
│   ├── api/v1/
│   │   ├── endpoints/
│   │   │   ├── auth.py          # /auth/* endpoints
│   │   │   └── users.py         # /users/* endpoints
│   │   └── router.py            # Aggregates all routers
│   ├── core/
│   │   ├── config.py            # Pydantic Settings (env vars)
│   │   ├── security.py          # JWT + password hashing
│   │   ├── logging.py           # structlog setup
│   │   └── dependencies.py      # FastAPI auth dependencies + RBAC
│   ├── db/
│   │   └── session.py           # Engine, session factory, get_db
│   ├── middleware/
│   │   └── logging.py           # Request/response logging middleware
│   ├── models/
│   │   └── user.py              # User + RefreshToken ORM models
│   ├── schemas/
│   │   └── user.py              # Pydantic request/response schemas
│   ├── services/
│   │   ├── auth_service.py      # Registration, login, token management
│   │   ├── email_service.py     # SendGrid email gateway
│   │   ├── sms_service.py       # Twilio SMS gateway
│   │   └── google_oauth.py      # Google OAuth2 flow
│   └── main.py                  # App factory, middleware, routers
├── alembic/
│   ├── versions/
│   │   └── 0001_initial.py      # Initial schema migration
│   └── env.py                   # Alembic environment config
├── tests/
│   ├── conftest.py              # Fixtures, test DB, factories
│   ├── unit/
│   │   └── test_security.py     # JWT + hashing unit tests
│   └── integration/
│       ├── test_auth.py         # Auth endpoint tests
│       └── test_users.py        # User/RBAC endpoint tests
├── alembic.ini
├── docker-compose.yml
├── Dockerfile
├── pytest.ini
├── requirements.txt
└── .env.example
```

---

## Setup Instructions

### Prerequisites

- Python 3.12+
- PostgreSQL 14+
- (Optional) Docker & Docker Compose

### 1. Clone the repository

```bash
git clone https://github.com/your-username/fastapi-auth-service.git
cd fastapi-auth-service
```

### 2. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
# Edit .env with your values (see Environment Configuration below)
```

### 5. Create the database

```bash
# In PostgreSQL:
createdb auth_service_db
```

### 6. Run database migrations

```bash
alembic upgrade head
```

### 7. Start the development server

```bash
uvicorn app.main:app --reload
```

The API is now available at **http://localhost:8000**  
Interactive docs: **http://localhost:8000/docs**

---

## Environment Configuration

Copy `.env.example` to `.env` and fill in each value:

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | ✅ | PostgreSQL connection string |
| `JWT_SECRET_KEY` | ✅ | Random secret for signing JWTs (`openssl rand -hex 32`) |
| `JWT_ALGORITHM` | — | Default: `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | — | Default: `30` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | — | Default: `7` |
| `GOOGLE_CLIENT_ID` | For Google login | From Google Cloud Console |
| `GOOGLE_CLIENT_SECRET` | For Google login | From Google Cloud Console |
| `GOOGLE_REDIRECT_URI` | For Google login | Must match Console setting |
| `TWILIO_ACCOUNT_SID` | For SMS | From Twilio dashboard |
| `TWILIO_AUTH_TOKEN` | For SMS | From Twilio dashboard |
| `TWILIO_PHONE_NUMBER` | For SMS | Your Twilio number (E.164 format) |
| `SENDGRID_API_KEY` | For email | From SendGrid dashboard |
| `SENDGRID_FROM_EMAIL` | For email | Verified sender email |
| `ALLOWED_ORIGINS` | — | Comma-separated CORS origins |
| `RATE_LIMIT_PER_MINUTE` | — | Default: `60` |
| `ENVIRONMENT` | — | `development` / `staging` / `production` |
| `DEBUG` | — | `true` enables SQL logging and Swagger UI |

---

## Running with Docker

```bash
# Build and start everything (DB + migrations + API)
docker compose up --build

# With pgAdmin UI at http://localhost:5050
docker compose --profile tools up --build

# Run in background
docker compose up -d

# View logs
docker compose logs -f api

# Tear down
docker compose down -v
```

---

## Database Migrations

```bash
# Apply all pending migrations
alembic upgrade head

# Generate a new migration from model changes
alembic revision --autogenerate -m "add_column_foo"

# Roll back one step
alembic downgrade -1

# View migration history
alembic history --verbose
```

---

## API Documentation

### Base URL
```
http://localhost:8000/api/v1
```

Interactive Swagger UI: `http://localhost:8000/docs`

---

### Authentication Endpoints

#### `POST /auth/register`
Create a new user account.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass1",
  "full_name": "Jane Doe",
  "phone_number": "+919876543210"
}
```

**Response `201`:**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "full_name": "Jane Doe",
  "role": "user",
  "is_active": true,
  "is_verified": false,
  "is_oauth_user": false,
  "created_at": "2025-01-01T00:00:00Z",
  "last_login_at": null
}
```

---

#### `POST /auth/login`
Authenticate with email and password.

**Request:**
```json
{ "email": "user@example.com", "password": "SecurePass1" }
```

**Response `200`:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

---

#### `POST /auth/logout`
Revoke the refresh token. Requires `Authorization: Bearer <access_token>`.

**Request:**
```json
{ "refresh_token": "eyJ..." }
```

**Response `200`:**
```json
{ "message": "Logged out successfully." }
```

---

#### `POST /auth/refresh`
Rotate tokens using a valid refresh token.

**Request:**
```json
{ "refresh_token": "eyJ..." }
```

**Response `200`:** Same shape as login response.

---

#### `GET /auth/google/login`
Redirects to Google's OAuth2 consent screen. Open in a browser.

---

#### `GET /auth/google/callback?code=...`
Handles the OAuth2 callback from Google.

**Response `200`:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "is_new_user": true
}
```

---

### User Endpoints

All `/users/*` endpoints require `Authorization: Bearer <access_token>`.

#### `GET /users/me` — Get own profile
**Response `200`:** UserResponse object.

#### `PATCH /users/me` — Update own profile
```json
{ "full_name": "New Name", "phone_number": "+911234567890" }
```

#### `GET /users/` — List all users 🔒 Admin only
Query params: `skip` (default 0), `limit` (default 50, max 200).

#### `GET /users/{user_id}` — Get user by ID 🔒 Admin only

#### `PATCH /users/{user_id}/role?role=admin` — Change role 🔒 Admin only

#### `DELETE /users/{user_id}` — Deactivate user 🔒 Admin only

---

### Health Check

#### `GET /health` (public)
```json
{ "status": "ok", "version": "1.0.0" }
```

---

## Running Tests

```bash
# Run all tests with coverage
pytest

# Run specific test file
pytest tests/unit/test_security.py -v

# Run integration tests only
pytest tests/integration/ -v

# Generate HTML coverage report
pytest --cov-report=html && open htmlcov/index.html
```

Tests use an **in-memory SQLite** database. Each test runs inside a transaction that is rolled back afterwards — no test data persists between tests and no PostgreSQL instance is required.

---

## Security Design

| Concern | Approach |
|---|---|
| **Password storage** | bcrypt with per-hash salt (via passlib) |
| **JWT signing** | HS256 with configurable secret; RS256 recommended for multi-service |
| **Refresh token storage** | SHA-256 hash of the raw token stored in DB; raw token only on wire |
| **Token rotation** | Refresh tokens are single-use; replaying a used token triggers a 401 |
| **Credential timing attacks** | `authenticate_user` always runs bcrypt even for unknown emails |
| **User ID format** | UUIDs (v4) — prevents enumeration of sequential IDs |
| **Rate limiting** | SlowAPI, configurable, keyed by client IP |
| **CORS** | Explicit origin allowlist |
| **Inactive accounts** | Checked on every authenticated request, not just login |
| **Admin self-protection** | Admins cannot demote or deactivate their own account |
| **Swagger UI** | Disabled in `ENVIRONMENT=production` |

---

## Assumptions & Limitations

### Assumptions
- A single PostgreSQL instance is sufficient (no read replicas needed).
- Refresh tokens are stored in the client (e.g., httpOnly cookie or secure storage). This service does not manage cookies itself.
- The Google OAuth2 callback URL is pre-registered in the Google Cloud Console.
- SMS/email delivery failures are non-fatal — the operation succeeds even if a notification fails to send.

### Limitations
- **CSRF protection** for the Google OAuth2 `state` parameter is logged but not fully enforced in this implementation. In production, the state should be stored in a signed cookie and verified on callback.
- **Email verification** flow (token + verify endpoint) is not implemented; `is_verified` is set to `true` for Google OAuth users automatically.
- **Password reset** endpoint is not implemented, but the email service has a `send_password_reset` method ready for it.
- **Access token revocation** is not supported — tokens remain valid until expiry after logout (mitigated by the 30-minute TTL).
- **Horizontal scaling** of refresh token rotation requires a shared cache (e.g., Redis) to prevent race conditions. The current implementation uses the PostgreSQL DB directly.
- **Async SQLAlchemy** is not used; the app uses synchronous sessions. For high-throughput scenarios, migrating to `asyncpg` + `async_sessionmaker` is recommended.

---

## Bonus Features Included

- ✅ **Docker** — multi-stage Dockerfile + Docker Compose with health checks and migration runner
- ✅ **Testing** — pytest with transaction-isolated fixtures, unit + integration test suites, coverage reporting
- ✅ **Security** — token hashing, rotation, timing-attack resistance, UUID PKs, rate limiting
- ✅ **Logging** — structured JSON logs with per-request correlation IDs via structlog
