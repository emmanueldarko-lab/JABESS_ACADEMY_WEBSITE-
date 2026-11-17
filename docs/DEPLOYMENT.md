# Deployment checklist

- Deploy from repository root; keep `api/index.py`, `vercel.json`, `requirements.txt` and `app/` at the root.
- Set `SECRET_KEY`, `ADMIN_PASSWORD`, `FLASK_ENV=production` and a persistent PostgreSQL `DATABASE_URL`.
- Do not use Vercel `/tmp` SQLite for real records; it is ephemeral.
- Enable HTTPS and secure cookies.
- Configure PostgreSQL backups, monitoring and access restrictions.
- Verify admin credentials, admissions, contact form, student login and all public pages.
- Complete CSRF, rate-limit, security and privacy reviews before collecting children's information.
- Verify school contact details, official location, admissions policy and all sample library records.
