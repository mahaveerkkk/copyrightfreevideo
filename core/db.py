"""
SQLite Persistent Database Layer.
Zero-RAM overhead persistent storage for:
- User registration and authentication (PBKDF2-HMAC-SHA256)
- Persistent sessions (30-day cookie tokens)
- Render Jobs persistence across page reloads and browser closures
"""

import os
import sqlite3
import hashlib
import secrets
import json
import time
from typing import Optional, Dict, Any, List

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage", "cr_shield.db")

def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes SQLite database schema."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Users Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Sessions Table (Persistent 30-day login)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                expires_at REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)

        # Persistent Render Jobs Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS render_jobs (
                job_id TEXT PRIMARY KEY,
                user_id INTEGER,
                filename TEXT NOT NULL,
                preset TEXT NOT NULL,
                mode TEXT NOT NULL,
                status TEXT NOT NULL,
                progress REAL DEFAULT 0.0,
                message TEXT DEFAULT '',
                error TEXT,
                download_url TEXT,
                original_meta TEXT,
                transformed_meta TEXT,
                elapsed_seconds REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
            )
        """)
        conn.commit()

# --- Password Hashing & Auth ---

def _hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    if not salt:
        salt = secrets.token_hex(16)
    pw_hash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        iterations=100_000
    ).hex()
    return pw_hash, salt

def create_user(username: str, password: str) -> Dict[str, Any]:
    username = username.strip()
    if len(username) < 3:
        raise ValueError("Username must be at least 3 characters")
    if len(password) < 4:
        raise ValueError("Password must be at least 4 characters")

    pw_hash, salt = _hash_password(password)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO users (username, password_hash, salt) VALUES (?, ?, ?)",
                (username, pw_hash, salt)
            )
            conn.commit()
            user_id = cursor.lastrowid
            return {"id": user_id, "username": username}
        except sqlite3.IntegrityError:
            raise ValueError(f"Username '{username}' already exists. Please login instead.")

def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    username = username.strip()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, password_hash, salt FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        if not row:
            return None
        
        expected_hash, _ = _hash_password(password, row["salt"])
        if secrets.compare_digest(expected_hash, row["password_hash"]):
            return {"id": row["id"], "username": row["username"]}
        return None

def create_session(user_id: int, duration_days: int = 30) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = time.time() + (duration_days * 86400)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
            (token, user_id, expires_at)
        )
        conn.commit()
    return token

def get_user_by_session(token: str) -> Optional[Dict[str, Any]]:
    if not token:
        return None
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.id, u.username, s.expires_at 
            FROM sessions s
            JOIN users u ON s.user_id = u.id
            WHERE s.token = ?
        """, (token,))
        row = cursor.fetchone()
        if not row:
            return None
        if row["expires_at"] < time.time():
            cursor.execute("DELETE FROM sessions WHERE token = ?", (token,))
            conn.commit()
            return None
        return {"id": row["id"], "username": row["username"]}

def delete_session(token: str):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()

# --- Render Jobs Persistence ---

def db_save_job(
    job_id: str,
    user_id: Optional[int],
    filename: str,
    preset: str,
    mode: str,
    status: str = "queued",
    message: str = "Enqueued in processing pipeline",
    download_url: Optional[str] = None
):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO render_jobs (
                job_id, user_id, filename, preset, mode, status, progress, message, download_url, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, 0.0, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(job_id) DO UPDATE SET
                status = excluded.status,
                message = excluded.message,
                download_url = excluded.download_url,
                updated_at = CURRENT_TIMESTAMP
        """, (job_id, user_id, filename, preset, mode, status, message, download_url))
        conn.commit()

def db_update_job_status(
    job_id: str,
    status: str,
    progress: float,
    message: str,
    error: Optional[str] = None,
    download_url: Optional[str] = None,
    original_meta: Optional[dict] = None,
    transformed_meta: Optional[dict] = None,
    elapsed_seconds: Optional[float] = None
):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE render_jobs SET
                status = ?,
                progress = ?,
                message = ?,
                error = COALESCE(?, error),
                download_url = COALESCE(?, download_url),
                original_meta = COALESCE(?, original_meta),
                transformed_meta = COALESCE(?, transformed_meta),
                elapsed_seconds = COALESCE(?, elapsed_seconds),
                updated_at = CURRENT_TIMESTAMP
            WHERE job_id = ?
        """, (
            status,
            progress,
            message,
            error,
            download_url,
            json.dumps(original_meta) if original_meta else None,
            json.dumps(transformed_meta) if transformed_meta else None,
            elapsed_seconds,
            job_id
        ))
        conn.commit()

def db_get_job(job_id: str) -> Optional[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM render_jobs WHERE job_id = ?", (job_id,))
        row = cursor.fetchone()
        if not row:
            return None
        res = dict(row)
        if res.get("original_meta"):
            try: res["original_meta"] = json.loads(res["original_meta"])
            except Exception: pass
        if res.get("transformed_meta"):
            try: res["transformed_meta"] = json.loads(res["transformed_meta"])
            except Exception: pass
        return res

def db_get_user_jobs(user_id: int, limit: int = 30) -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT job_id, filename, preset, mode, status, progress, message, download_url, 
                   elapsed_seconds, error, created_at, updated_at
            FROM render_jobs
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (user_id, limit))
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

def db_delete_job(job_id: str, user_id: Optional[int] = None) -> bool:
    """Deletes a job from the database."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if user_id is not None:
            cursor.execute("DELETE FROM render_jobs WHERE job_id = ? AND user_id = ?", (job_id, user_id))
        else:
            cursor.execute("DELETE FROM render_jobs WHERE job_id = ?", (job_id,))
        conn.commit()
        return cursor.rowcount > 0

# Initialize tables on import
init_db()
