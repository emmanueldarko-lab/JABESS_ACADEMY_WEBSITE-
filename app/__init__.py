import os
import sqlite3
from pathlib import Path

from flask import Flask, g, current_app
from werkzeug.security import generate_password_hash


BASE = Path(__file__).resolve().parent.parent


class PostgresConnection:
    """Compatibility wrapper for qmark SQL used by the application."""

    def __init__(self, connection):
        self.connection = connection

    def execute(self, sql, params=()):
        return self.connection.execute(
            sql.replace("?", "%s"), params
        )

    def executemany(self, sql, params):
        return self.connection.executemany(
            sql.replace("?", "%s"), params
        )

    def commit(self):
        self.connection.commit()

    def close(self):
        self.connection.close()


def _database_url():
    return os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")


def create_app():

    # --------------------------------------------------
    # 1. Configure writable instance directory
    # --------------------------------------------------

    is_vercel = bool(os.getenv("VERCEL"))

    if is_vercel:
        # Vercel application directories are read-only.
        instance_dir = Path("/tmp/jabess-academy")
    else:
        # Local Windows/Linux development.
        instance_dir = BASE / "instance"

    instance_dir.mkdir(parents=True, exist_ok=True)

    # --------------------------------------------------
    # 2. Create Flask application
    # --------------------------------------------------

    app = Flask(
        __name__,
        instance_path=str(instance_dir),
        instance_relative_config=True
    )

    is_production = (
        is_vercel
        or os.getenv("FLASK_ENV") == "production"
    )

    secret_key = os.getenv("SECRET_KEY")

    if is_production and not secret_key:
        raise RuntimeError(
            "SECRET_KEY must be configured in production."
        )

    app.config.update(
        SECRET_KEY=secret_key or "development-only-change-me",

        DATABASE_URL=_database_url(),

        DATABASE=os.getenv(
            "SQLITE_PATH",
            str(instance_dir / "jabess.db")
        ),

        SESSION_COOKIE_HTTPONLY=True,

        SESSION_COOKIE_SAMESITE="Lax",

        SESSION_COOKIE_SECURE=(
            os.getenv(
                "COOKIE_SECURE",
                "1" if is_production else "0"
            ) == "1"
        ),

        PERMANENT_SESSION_LIFETIME=60 * 60 * 8,
    )

    # --------------------------------------------------
    # 3. Register application routes
    # --------------------------------------------------

    from .routes import bp

    app.register_blueprint(bp)

    # --------------------------------------------------
    # 4. Close database connections after requests
    # --------------------------------------------------

    @app.teardown_appcontext
    def close_db(error=None):

        db = g.pop("db", None)

        if db is not None:
            db.close()

    # --------------------------------------------------
    # 5. Initialize database
    # --------------------------------------------------

    with app.app_context():
        init_db()

    return app


# ======================================================
# DATABASE CONNECTION
# ======================================================

def get_db():

    if "db" not in g:

        url = current_app.config.get("DATABASE_URL")

        if url:

            try:
                import psycopg
                from psycopg.rows import dict_row

            except ImportError as exc:
                raise RuntimeError(
                    "PostgreSQL support requires psycopg[binary]."
                ) from exc

            conn = psycopg.connect(
                url,
                row_factory=dict_row,
                connect_timeout=10
            )

            g.db = PostgresConnection(conn)

        else:

            database_path = Path(
                current_app.config["DATABASE"]
            )

            database_path.parent.mkdir(
                parents=True,
                exist_ok=True
            )

            conn = sqlite3.connect(
                str(database_path),
                timeout=20
            )

            conn.row_factory = sqlite3.Row

            conn.execute("PRAGMA foreign_keys = ON")

            g.db = conn

    return g.db


# ======================================================
# DATABASE INITIALIZATION
# ======================================================

def init_db():

    url = current_app.config.get("DATABASE_URL")

    if url:

        try:
            import psycopg
            from psycopg.rows import dict_row

        except ImportError as exc:
            raise RuntimeError(
                "PostgreSQL support requires psycopg[binary]."
            ) from exc

        conn = psycopg.connect(
            url,
            row_factory=dict_row,
            connect_timeout=10
        )

        db = PostgresConnection(conn)

        id_type = "BIGSERIAL PRIMARY KEY"

    else:

        database_path = Path(
            current_app.config["DATABASE"]
        )

        database_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        conn = sqlite3.connect(
            str(database_path),
            timeout=20
        )

        conn.row_factory = sqlite3.Row

        conn.execute("PRAGMA foreign_keys = ON")

        db = conn

        id_type = "INTEGER PRIMARY KEY"

    try:

        # USERS
        db.execute(f"""
            CREATE TABLE IF NOT EXISTS users(
                id {id_type},
                full_name TEXT NOT NULL,
                username TEXT UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'student',
                class_name TEXT,
                must_change_password INTEGER DEFAULT 0,
                active INTEGER DEFAULT 1
            )
        """)

        # ADMISSIONS
        db.execute(f"""
            CREATE TABLE IF NOT EXISTS admissions(
                id {id_type},
                reference TEXT UNIQUE,
                student_name TEXT,
                dob TEXT,
                gender TEXT,
                nationality TEXT,
                address TEXT,
                previous_school TEXT,
                class_applied TEXT,
                academic_year TEXT,
                guardian_name TEXT,
                relationship TEXT,
                phone TEXT,
                alt_phone TEXT,
                email TEXT,
                emergency_name TEXT,
                emergency_phone TEXT,
                extra TEXT,
                status TEXT DEFAULT 'Submitted',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # NEWS
        db.execute(f"""
            CREATE TABLE IF NOT EXISTS news(
                id {id_type},
                title TEXT NOT NULL,
                category TEXT,
                body TEXT NOT NULL,
                image TEXT,
                published INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # BOOKS
        db.execute(f"""
            CREATE TABLE IF NOT EXISTS books(
                id {id_type},
                title TEXT NOT NULL,
                author TEXT,
                category TEXT,
                reading_level TEXT,
                available INTEGER DEFAULT 1
            )
        """)

        # MESSAGES
        db.execute(f"""
            CREATE TABLE IF NOT EXISTS messages(
                id {id_type},
                name TEXT,
                email TEXT,
                phone TEXT,
                subject TEXT,
                message TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                read INTEGER DEFAULT 0
            )
        """)

        # --------------------------------------------------
        # ADMIN ACCOUNT
        # --------------------------------------------------

        admin_exists = db.execute(
            "SELECT id FROM users WHERE username='admin'"
        ).fetchone()

        if not admin_exists:

            admin_password = os.getenv(
                "ADMIN_PASSWORD",
                "ChangeMe123!"
            )

            db.execute(
                """
                INSERT INTO users(
                    full_name,
                    username,
                    password_hash,
                    role,
                    must_change_password
                )
                VALUES(?,?,?,?,1)
                """,
                (
                    "School Administrator",
                    "admin",
                    generate_password_hash(admin_password),
                    "admin"
                )
            )

        # --------------------------------------------------
        # INITIAL STUDENT ACCOUNT
        # --------------------------------------------------

        student_password = os.getenv(
            "INITIAL_STUDENT_PASSWORD"
        )

        if student_password:

            student_exists = db.execute(
                """
                SELECT id FROM users
                WHERE username='emmanuel.darko'
                """
            ).fetchone()

            if not student_exists:

                db.execute(
                    """
                    INSERT INTO users(
                        full_name,
                        username,
                        password_hash,
                        role,
                        class_name,
                        must_change_password
                    )
                    VALUES(?,?,?,?,?,1)
                    """,
                    (
                        "Emmanuel Darko",
                        "emmanuel.darko",
                        generate_password_hash(student_password),
                        "student",
                        "To be assigned"
                    )
                )

        # --------------------------------------------------
        # INITIAL LIBRARY BOOKS
        # --------------------------------------------------

        books_exist = db.execute(
            "SELECT id FROM books LIMIT 1"
        ).fetchone()

        if not books_exist:

            books = [
                (
                    "The African Storybook Collection",
                    "Various Authors",
                    "Storybooks",
                    "KG–Primary"
                ),
                (
                    "Oxford Primary English",
                    "Oxford",
                    "English",
                    "Primary"
                ),
                (
                    "Basic Science for JHS",
                    "Various Authors",
                    "Science",
                    "JHS"
                )
            ]

            for book in books:

                db.execute(
                    """
                    INSERT INTO books(
                        title,
                        author,
                        category,
                        reading_level,
                        available
                    )
                    VALUES(?,?,?,?,1)
                    """,
                    book
                )

        db.commit()

    except Exception:
        db.connection.rollback() if isinstance(
            db, PostgresConnection
        ) else db.rollback()

        raise

    finally:
        db.close()