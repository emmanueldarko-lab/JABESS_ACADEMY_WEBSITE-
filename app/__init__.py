import os
import sqlite3
from pathlib import Path
from flask import Flask, g, current_app
from werkzeug.security import generate_password_hash

BASE = Path(__file__).resolve().parent.parent


class PostgresConnection:
    """Small compatibility wrapper for the qmark SQL used by the app."""
    def __init__(self, connection):
        self.connection = connection

    def execute(self, sql, params=()):
        return self.connection.execute(sql.replace("?", "%s"), params)

    def commit(self):
        self.connection.commit()

    def close(self):
        self.connection.close()


def _database_url():
    return os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.update(
        SECRET_KEY=os.getenv("SECRET_KEY", "development-only-change-me"),
        DATABASE_URL=_database_url(),
        DATABASE=os.getenv("SQLITE_PATH", "/tmp/jabess.db" if os.getenv("VERCEL") else str(Path(app.instance_path) / "jabess.db")),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.getenv("COOKIE_SECURE", "1" if (os.getenv("VERCEL") or os.getenv("FLASK_ENV") == "production") else "0") == "1",
        PERMANENT_SESSION_LIFETIME=60 * 60 * 8,
    )
    if os.getenv("FLASK_ENV") == "production" and not os.getenv("SECRET_KEY"):
        raise RuntimeError("SECRET_KEY must be configured in production.")
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    from .routes import bp
    app.register_blueprint(bp)

    @app.teardown_appcontext
    def close_db(error=None):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    with app.app_context():
        init_db()
    return app


def get_db():
    if "db" not in g:
        url = current_app.config.get("DATABASE_URL")
        if url:
            try:
                import psycopg
                from psycopg.rows import dict_row
            except ImportError as exc:
                raise RuntimeError("PostgreSQL support requires psycopg[binary].") from exc
            conn = psycopg.connect(url, row_factory=dict_row, connect_timeout=10)
            g.db = PostgresConnection(conn)
        else:
            conn = sqlite3.connect(current_app.config["DATABASE"], timeout=20)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            g.db = conn
    return g.db


def init_db():
    url = current_app.config.get("DATABASE_URL")
    if url:
        import psycopg
        from psycopg.rows import dict_row
        conn = psycopg.connect(url, row_factory=dict_row, connect_timeout=10)
        db = PostgresConnection(conn)
        id_type = "BIGSERIAL PRIMARY KEY"
    else:
        db = sqlite3.connect(current_app.config["DATABASE"], timeout=20)
        db.row_factory = sqlite3.Row
        id_type = "INTEGER PRIMARY KEY"

    db.execute(f"""CREATE TABLE IF NOT EXISTS users(
        id {id_type}, full_name TEXT NOT NULL, username TEXT UNIQUE,
        password_hash TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'student',
        class_name TEXT, must_change_password INTEGER DEFAULT 0, active INTEGER DEFAULT 1)""")
    db.execute(f"""CREATE TABLE IF NOT EXISTS admissions(
        id {id_type}, reference TEXT UNIQUE, student_name TEXT, dob TEXT, gender TEXT,
        nationality TEXT, address TEXT, previous_school TEXT, class_applied TEXT,
        academic_year TEXT, guardian_name TEXT, relationship TEXT, phone TEXT,
        alt_phone TEXT, email TEXT, emergency_name TEXT, emergency_phone TEXT,
        extra TEXT, status TEXT DEFAULT 'Submitted', created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
    db.execute(f"""CREATE TABLE IF NOT EXISTS news(
        id {id_type}, title TEXT NOT NULL, category TEXT, body TEXT NOT NULL,
        image TEXT, published INTEGER DEFAULT 1, created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
    db.execute(f"""CREATE TABLE IF NOT EXISTS books(
        id {id_type}, title TEXT NOT NULL, author TEXT, category TEXT,
        reading_level TEXT, available INTEGER DEFAULT 1)""")
    db.execute(f"""CREATE TABLE IF NOT EXISTS messages(
        id {id_type}, name TEXT, email TEXT, phone TEXT, subject TEXT, message TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP, read INTEGER DEFAULT 0)""")

    # Seed accounts only on an empty users table. Override passwords with environment variables.
    if not db.execute("SELECT id FROM users WHERE username='admin'").fetchone():
        admin_password = os.getenv("ADMIN_PASSWORD", "ChangeMe123!")
        db.execute(
            "INSERT INTO users(full_name,username,password_hash,role,must_change_password) VALUES(?,?,?,?,1)",
            ("School Administrator", "admin", generate_password_hash(admin_password), "admin"),
        )
    if os.getenv("INITIAL_STUDENT_PASSWORD") and not db.execute(
        "SELECT id FROM users WHERE username='emmanuel.darko'"
    ).fetchone():
        db.execute(
            "INSERT INTO users(full_name,username,password_hash,role,class_name,must_change_password) VALUES(?,?,?,?,?,1)",
            ("Emmanuel Darko", "emmanuel.darko", generate_password_hash(os.getenv("INITIAL_STUDENT_PASSWORD")), "student", "To be assigned"),
        )
    if not db.execute("SELECT id FROM books LIMIT 1").fetchone():
        books = [
            ("The African Storybook Collection", "Various Authors", "Storybooks", "KG–Primary"),
            ("Oxford Primary English", "Oxford", "English", "Primary"),
            ("Basic Science for JHS", "Various Authors", "Science", "JHS"),
        ]
        if url:
            for book in books:
                db.execute("INSERT INTO books(title,author,category,reading_level,available) VALUES(?,?,?,?,1)", book)
        else:
            db.executemany("INSERT INTO books(title,author,category,reading_level,available) VALUES(?,?,?,?,1)", books)
    db.commit()
    db.close()
