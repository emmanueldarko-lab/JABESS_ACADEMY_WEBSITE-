# JABESS ACADEMY Website

Flask school website with public pages, admissions, contact messages, library catalogue, student sign-in and an administrator dashboard.

## Deployment compatibility

The application now has entry points/configuration for:
- **Vercel** — `api/index.py` and `vercel.json` (serverless).
- **Render, Railway, Fly.io and other Python hosts** — `Procfile` / `gunicorn run:app`.
- **Docker-compatible hosts** — `Dockerfile`.
- **Windows, macOS and Linux** — local Python run instructions below.

A hosted deployment should use a managed PostgreSQL database. SQLite is supported for local development and single-instance testing, but is not suitable for persistent data on Vercel: its serverless filesystem is temporary and may be reset between deployments/instances. If Vercel is used without `DATABASE_URL`, the app uses `/tmp/jabess.db` only so the site can boot; records there are temporary and must not be used for real school data.

## Local setup

Python 3.10+ is required.

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate
python -m pip install -r requirements.txt
python run.py
```

Open `http://127.0.0.1:5000`.

## Required production environment variables

Set these in the hosting provider's environment-variable settings:

- `SECRET_KEY` — long, random, private value used to sign sessions.
- `DATABASE_URL` — PostgreSQL connection URL. Use the provider's private/internal URL where available.
- `ADMIN_PASSWORD` — strong initial administrator password. This is applied when the admin account is first created; changing the environment variable later does not change an existing database password.
- `FLASK_ENV=production` — enables production secret-key validation.
- `COOKIE_SECURE=1` — secure HTTPS-only session cookies (default on Vercel/production).

Optional:
- `INITIAL_STUDENT_PASSWORD` — creates the starter Emmanuel Darko student account only if it does not already exist. This is intended for initial setup; do not leave a shared temporary password active.
- `SQLITE_PATH` — override the local SQLite file path when not using PostgreSQL.
- `PORT` — hosting platform port; defaults to 5000 for local development.

Do not use the sample development administrator password on a public deployment. Set `ADMIN_PASSWORD` before the first database initialization, then change the password immediately after first login.

## Vercel setup

1. Push the complete project folder to GitHub. The repository root must contain `vercel.json`, `requirements.txt`, `api/` and `app/`.
2. Import the repository into Vercel.
3. Add a managed PostgreSQL database (for example, a Vercel Postgres-compatible provider or Neon) and set its connection string as `DATABASE_URL`.
4. Set `SECRET_KEY`, `ADMIN_PASSWORD`, and `FLASK_ENV=production` in Vercel project environment variables.
5. Deploy. The Python function is `api/index.py`; `vercel.json` routes requests to it.
6. Test the public pages, admissions submission, contact form, admin login and student login after deployment.

Do not rely on the SQLite `/tmp` fallback for production records. The app's schema is initialized automatically when the application starts.

## Other platforms

- **Render/Railway/Fly.io:** deploy from the repository and use the `Procfile` start command, or configure `gunicorn run:app --bind 0.0.0.0:$PORT`. Add the same environment variables and PostgreSQL database.
- **Docker:** build with `docker build -t jabess-academy .` and run with `docker run -p 8000:8000 -e SECRET_KEY=... -e ADMIN_PASSWORD=... -e DATABASE_URL=... jabess-academy`.
- **Local:** use `python run.py`; SQLite is created under `instance/`.

## Initial accounts and data

- Admin username: `admin`; initial password comes from `ADMIN_PASSWORD` (development fallback: `ChangeMe123!`).
- The optional starter student account is created only when `INITIAL_STUDENT_PASSWORD` is set. Username: `emmanuel.darko`; display name: `Emmanuel Darko`.
- Three sample library records are inserted when the catalogue is empty.

The starter build does not include student grades, attendance, assignments, timetable management, self-service password recovery, production-grade audit logs or complete school administration. Verify school details and sample library records before publishing.

## Security and privacy

This website can collect personal information about children and guardians. Before real use, complete a security and privacy review, add CSRF protection and rate limiting, configure backups and monitoring, restrict administrator access, establish a retention policy, and ensure compliance with applicable Ghanaian data-protection requirements. Do not collect real student data until these controls and the hosting/database arrangements have been reviewed.
