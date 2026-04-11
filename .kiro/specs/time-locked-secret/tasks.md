# Tasks: Time-Locked Secret

## Task List

- [x] 1. Project scaffold and database setup
  - [x] 1.1 Create project directory structure (`app/`, `tests/`, `templates/`)
  - [x] 1.2 Create `requirements.txt` with Flask, Hypothesis, pytest, and zoneinfo backport (if Python < 3.9)
  - [x] 1.3 Implement `app/db.py`: SQLite connection helper and `init_db()` that creates the `secrets` table
  - [x] 1.4 Write a smoke test that calls `init_db()` and verifies the table exists

- [-] 2. Domain layer — Secret_Store
  - [x] 2.1 Define `Secret` and `AccessResult` dataclasses in `app/models.py`
  - [x] 2.2 Implement `ValidationError` exception class in `app/models.py`
  - [x] 2.3 Implement `SecretStore.create_secret` in `app/secret_store.py`
    - Validate content (non-empty, ≤ 10,000 chars)
    - Validate time window (end > start, both present)
    - Generate cryptographically random token (≥ 128 bits, `secrets.token_hex(16)`)
    - Persist to SQLite and return token
  - [x] 2.4 Implement `SecretStore.get_secret` in `app/secret_store.py`
    - Return `Secret` dataclass or `None` if not found
  - [ ] 2.5 Write property tests in `tests/test_secret_store.py`
    - Property 1: content length boundary (Hypothesis)
    - Property 2: invalid time window rejected (Hypothesis)
    - Property 3: empty/whitespace content rejected (Hypothesis)
    - Property 4: valid creation returns token ≥ 32 hex chars, two calls differ (Hypothesis)
    - Property 8: unknown secret_id returns None (Hypothesis)
    - Property 9: timezone conversion round-trip (Hypothesis)

- [ ] 3. Domain layer — Access_Controller
  - [ ] 3.1 Implement `AccessController.check_access` in `app/access_controller.py`
    - Compare `now_utc` against `secret.start_utc` and `secret.end_utc`
    - Return `AccessResult` with correct status, content, and `available_at`
  - [ ] 3.2 Write property tests in `tests/test_access_controller.py`
    - Property 5: access within window returns content (Hypothesis)
    - Property 6: access before window returns not-yet + available_at (Hypothesis)
    - Property 7: access after window returns expired, no content (Hypothesis)

- [ ] 4. Web layer — Flask routes
  - [ ] 4.1 Create `app/__init__.py` with Flask app factory and `init_db()` call
  - [ ] 4.2 Implement `GET /` route in `app/routes.py` — render creation form
  - [ ] 4.3 Implement `POST /` route in `app/routes.py`
    - Parse form fields (content, start_dt, end_dt, timezone)
    - Convert local datetimes to UTC using `zoneinfo.ZoneInfo`
    - Call `SecretStore.create_secret`
    - On success: redirect to success page with token
    - On `ValidationError`: re-render form with error message
  - [ ] 4.4 Implement `GET /secret/<secret_id>` route in `app/routes.py`
    - Call `SecretStore.get_secret`; return 404 if None
    - Call `AccessController.check_access` with `datetime.utcnow()`
    - Render `view.html` with result

- [ ] 5. Templates
  - [ ] 5.1 Create `templates/create.html` — form with secret textarea, start datetime, end datetime, timezone selector (IANA list), and submit button
  - [ ] 5.2 Create `templates/success.html` — display the full Secret_Link URL
  - [ ] 5.3 Create `templates/view.html` — conditionally show secret content, "not yet available (available at {time})", or "this secret has expired"
  - [ ] 5.4 Create `templates/404.html` — not found page

- [ ] 6. Web layer tests
  - [ ] 6.1 Write example tests in `tests/test_routes.py` using Flask test client
    - Creation form contains required fields (Req 6.1)
    - Valid POST redirects and success page shows secret link (Req 6.2)
    - View page renders correct message for each access status (Req 6.3)
    - Invalid POST re-renders form with validation error (Req 6.4)
    - Non-existent secret_id returns 404 (Req 2.4)

- [ ] 7. Integration and final wiring
  - [ ] 7.1 Create `run.py` entry point (`app.run(debug=True)`)
  - [ ] 7.2 Verify all tests pass (`pytest tests/`)
  - [ ] 7.3 Manual smoke test: create a secret, copy link, view within window, view outside window
