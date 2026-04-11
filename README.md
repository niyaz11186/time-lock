# Time-Lock

A Flask web application that allows authenticated users to create **time-locked secrets** — text content accessible only through a shareable link within a defined UTC datetime window. Viewers see a "not yet available" message before the window opens and an "expired" message after it closes.

---

## Table of Contents

- [Time-Lock](#time-lock)
  - [Table of Contents](#table-of-contents)
  - [Overview](#overview)
  - [Features](#features)
  - [Technology Stack](#technology-stack)
  - [Project Structure](#project-structure)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Configuration](#configuration)
    - [Environment Variable Reference](#environment-variable-reference)
  - [Running the Application](#running-the-application)
  - [Running Tests](#running-tests)
  - [Routes Reference](#routes-reference)
    - [Auth Blueprint](#auth-blueprint)
    - [Main Blueprint](#main-blueprint)
  - [Database Schema](#database-schema)
    - [`users`](#users)
    - [`secrets`](#secrets)
  - [Security Design](#security-design)
    - [Known Gaps](#known-gaps)
  - [Google OAuth Setup](#google-oauth-setup)
  - [Deployment](#deployment)
  - [Known Limitations](#known-limitations)

---

## Overview

Time-Lock lets you write a secret message, set an open and close time in any IANA timezone, and share the generated link with anyone. The recipient can only read the content during the allowed time window. Outside the window, the page shows a status message but never reveals the content.

Access enforcement is handled at the application layer by comparing the current UTC time against the stored `start_utc` and `end_utc` values on every request to the public view route.

---

## Features

- Create secrets with a configurable availability window (start datetime to end datetime)
- Full IANA timezone support — all timezones are grouped by region in a dropdown, with the browser's local timezone auto-selected
- All times stored and compared in UTC; displayed in the viewer's local timezone via the browser's `Intl.DateTimeFormat` API
- Three publicly visible states for a secret link: **Not Yet Available**, **Available**, and **Expired**
- User dashboard listing all owned secrets with live status badges
- Owner-scoped secret deletion
- Email and password registration and login
- Optional Google OAuth 2.0 login (silently disabled if credentials are not configured)
- Google accounts linked to existing email/password accounts by matching email at OAuth callback time
- Cryptographically random 128-bit token used as secret ID — no sequential enumeration possible
- Parameterized SQL queries throughout — no string interpolation in database calls
- Owner-gated delete — the SQL `WHERE` clause includes both the secret ID and the authenticated user ID

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Web framework | Flask |
| Session management | Flask-Login |
| OAuth 2.0 client | Authlib |
| Database | PostgreSQL (tested against Supabase) |
| Database driver | psycopg2-binary |
| Password hashing | Werkzeug security (PBKDF2/scrypt) |
| Environment config | python-dotenv |
| Timezone data | zoneinfo + tzdata |
| Production server | Gunicorn |
| Testing | pytest, hypothesis |

---

## Project Structure

```
time-lock/
├── app/
│   ├── __init__.py          # Application factory (create_app)
│   ├── access_controller.py # Time-window enforcement logic
│   ├── auth.py              # Auth blueprint (signup, login, logout, Google OAuth)
│   ├── db.py                # Database connection and schema initialization
│   ├── models.py            # User model for Flask-Login
│   ├── routes.py            # Main blueprint (create, view, list, delete secrets)
│   ├── secret_store.py      # Data access layer for the secrets table
│   └── templates/
│       ├── create.html      # Secret creation form
│       ├── view.html        # Public secret view (all three states)
│       ├── my_secrets.html  # Owner dashboard
│       ├── success.html     # Post-creation shareable link display
│       ├── login.html       # Login form
│       ├── signup.html      # Signup form
│       └── 404.html         # Custom 404 page
├── tests/
│   ├── __init__.py
│   └── test_db.py           # Integration tests for database initialization
├── run.py                   # Development entry point
├── test_connection.py       # Standalone DB connectivity check
├── requirements.txt
└── .env                     # Local environment variables (not committed)
```

---

## Prerequisites

- Python 3.11 or later (required for `zoneinfo` with full IANA support)
- A PostgreSQL database (Supabase free tier works out of the box)
- pip

---

## Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/your-username/time-lock.git
   cd time-lock
   ```

2. **Create and activate a virtual environment**

   ```bash
   python -m venv venv

   # Windows
   venv\Scripts\activate

   # macOS / Linux
   source venv/bin/activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

---

## Configuration

Create a `.env` file in the project root. Never commit this file to version control.

```dotenv
# Required — generate with: python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=your_secret_key_here

# PostgreSQL connection details
DB_HOST=your-db-host
DB_PORT=5432
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=your_db_password

# Optional — set to 'require' for SSL-enforced connections
# DB_SSLMODE=require

# Optional — Google OAuth credentials
# Leave both blank to disable Google login entirely
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
```

### Environment Variable Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | Yes | Flask session signing key. Must be a long, random string. |
| `DB_HOST` | Yes | PostgreSQL host (e.g., Supabase session pooler hostname) |
| `DB_PORT` | Yes | PostgreSQL port (default: 5432) |
| `DB_NAME` | Yes | Database name (default: `postgres`) |
| `DB_USER` | Yes | Database username |
| `DB_PASSWORD` | Yes | Database password |
| `DB_SSLMODE` | No | SSL mode for psycopg2 (`require`, `disable`, etc.) |
| `GOOGLE_CLIENT_ID` | No | Google OAuth client ID from Google Cloud Console |
| `GOOGLE_CLIENT_SECRET` | No | Google OAuth client secret |

---

## Running the Application

**Verify database connectivity first:**

```bash
python test_connection.py
```

**Development server** (auto-reloads on code changes, debug mode enabled):

```bash
python run.py
```

The app will be available at `http://localhost:5000`.

**Production server** (Gunicorn):

```bash
gunicorn "app:create_app()"
```

The database schema (`users` and `secrets` tables) is created automatically on startup via `init_db()` using `CREATE TABLE IF NOT EXISTS` — safe to run against an existing database.

---

## Running Tests

The test suite contains integration tests that require a live PostgreSQL database.

```bash
pytest tests/
```

Tests are automatically skipped if the `DATABASE_URL` environment variable is not set. The tests verify:

- `init_db()` is idempotent (safe to call multiple times)
- The `users` table exists with the correct columns after initialization
- The `secrets` table exists with the correct columns after initialization

---

## Routes Reference

### Auth Blueprint

| Method | Path | Auth Required | Description |
|--------|------|---------------|-------------|
| `GET` | `/signup` | No | Renders the signup form |
| `POST` | `/signup` | No | Creates a new user account |
| `GET` | `/login` | No | Renders the login form |
| `POST` | `/login` | No | Authenticates with email and password |
| `GET` | `/logout` | Yes | Ends the session and redirects to `/login` |
| `GET` | `/auth/google/login` | No | Initiates the Google OAuth redirect |
| `GET` | `/auth/google/callback` | No | Handles the Google OAuth callback |

### Main Blueprint

| Method | Path | Auth Required | Description |
|--------|------|---------------|-------------|
| `GET` | `/` | Yes | Renders the secret creation form |
| `POST` | `/` | Yes | Creates a new secret and redirects to the success page |
| `GET` | `/success` | No | Displays the newly created shareable link |
| `GET` | `/my-secrets` | Yes | Lists all secrets owned by the current user |
| `POST` | `/secret/<id>/delete` | Yes | Deletes a secret (owner only) |
| `GET` | `/secret/<id>` | No | Public time-locked view of a secret |

---

## Database Schema

Tables are created automatically on startup. All datetime values are stored as ISO-format UTC strings.

### `users`

| Column | Type | Notes |
|--------|------|-------|
| `id` | `BIGSERIAL PRIMARY KEY` | Auto-incrementing integer |
| `email` | `TEXT NOT NULL UNIQUE` | Lowercased on input |
| `name` | `TEXT` | Optional display name |
| `password_hash` | `TEXT` | Null for Google-only accounts |
| `google_id` | `TEXT UNIQUE` | Null for email/password-only accounts |
| `created_at` | `TEXT NOT NULL` | ISO-format UTC datetime |

### `secrets`

| Column | Type | Notes |
|--------|------|-------|
| `id` | `TEXT PRIMARY KEY` | 32-character hex token (128-bit random via `secrets.token_hex(16)`) |
| `user_id` | `BIGINT REFERENCES users(id)` | Owner foreign key |
| `content` | `TEXT NOT NULL` | Plaintext secret content (max 10,000 characters) |
| `start_utc` | `TEXT NOT NULL` | ISO-format UTC datetime — window open time |
| `end_utc` | `TEXT NOT NULL` | ISO-format UTC datetime — window close time |
| `created_at` | `TEXT NOT NULL` | ISO-format UTC datetime |

---

## Security Design

| Concern | Implementation |
|---------|---------------|
| Password storage | `werkzeug.security.generate_password_hash` — stores an adaptive hash (PBKDF2 or scrypt depending on Werkzeug version) |
| Session integrity | Flask signed cookie session using `SECRET_KEY` |
| Access control | `@login_required` decorator on all write and list routes |
| Object-level authorization | Delete SQL includes `AND user_id = %s` to prevent insecure direct object reference (IDOR) |
| SQL injection | All database calls use parameterized queries with `%s` placeholders — no string interpolation |
| Secret ID entropy | 128-bit random token generated with Python's `secrets` module — unpredictable and not enumerable |
| Input validation | Content capped at 10,000 characters; `end_utc` must be after `start_utc`; timezone validated against the IANA list |
| Google OAuth | Account linking guards against duplicate accounts for the same email address; OAuth is disabled at startup if credentials are absent |

### Known Gaps

- **No CSRF protection** on the delete form. The delete button uses a JavaScript `confirm()` dialog but does not use a CSRF token. Adding Flask-WTF or a manual CSRF token is recommended before deploying to a public-facing environment.
- **No at-rest encryption** for secret content. Content is stored as plaintext in the database. If the database is compromised, all secret content is exposed. Field-level encryption or database-level encryption at rest should be considered for sensitive deployments.

---

## Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project (or select an existing one).
3. Navigate to **APIs & Services > Credentials**.
4. Click **Create Credentials > OAuth 2.0 Client ID**.
5. Set the application type to **Web application**.
6. Add the following to **Authorized redirect URIs**:
   - `http://localhost:5000/auth/google/callback` (development)
   - `https://your-domain.com/auth/google/callback` (production)
7. Copy the **Client ID** and **Client Secret** into your `.env` file.

If `GOOGLE_CLIENT_ID` or `GOOGLE_CLIENT_SECRET` are left blank, the Google login option is silently disabled and all other functionality continues to work normally.

---

## Deployment

The application is compatible with any platform that supports Python and Gunicorn. General steps:

1. Set all required environment variables on the host (do not deploy `.env` directly).
2. Ensure the PostgreSQL database is reachable from the host.
3. Start the app with Gunicorn:

   ```bash
   gunicorn "app:create_app()" --bind 0.0.0.0:8000 --workers 2
   ```

4. Put a reverse proxy (Nginx, Caddy, etc.) in front of Gunicorn to handle TLS termination.

For platforms like Railway, Render, or Fly.io, set the start command to:

```bash
gunicorn "app:create_app()"
```

---

## Known Limitations

- Secret content is stored as plaintext. No application-layer encryption is applied.
- Time-window enforcement is application-layer only. Direct database access bypasses all access control.
- The delete endpoint has no CSRF token.
- Secrets cannot currently be edited after creation — only deleted and recreated.
