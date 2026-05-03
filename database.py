import sqlite3
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = os.getenv('DATABASE_PATH')
if not DB_PATH:
    # Vercel serverless functions can only write safely to /tmp. Locally, keep the
    # database beside the app files so the existing workflow still feels familiar.
    base_dir = '/tmp' if os.getenv('VERCEL') else os.path.dirname(os.path.abspath(__file__))
    DB_PATH = os.path.join(base_dir, 'coursebot.db')


def get_db():
    """Get a database connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create all tables if they don't exist."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS chat_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT DEFAULT 'New Chat',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('user', 'bot')),
            content TEXT NOT NULL,
            msg_type TEXT DEFAULT 'chat',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
        );
    """)

    conn.commit()
    conn.close()
    print("[DB] Database initialized successfully.")


# ── USER OPERATIONS ──

def create_user(username, email, password):
    """Create a new user. Returns (success, message)."""
    conn = get_db()
    try:
        hashed = generate_password_hash(password)
        conn.execute(
            "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
            (username.strip(), email.strip().lower(), hashed)
        )
        conn.commit()
        return True, "Account created successfully!"
    except sqlite3.IntegrityError as e:
        if 'username' in str(e):
            return False, "Username already taken."
        elif 'email' in str(e):
            return False, "Email already registered."
        return False, "Account creation failed."
    finally:
        conn.close()


def authenticate_user(username_or_email, password):
    """Authenticate a user. Returns (success, user_dict or error_message)."""
    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE username = ? OR email = ?",
        (username_or_email, username_or_email.lower())
    ).fetchone()
    conn.close()

    if not user:
        return False, "Account not found."
    if not check_password_hash(user['password'], password):
        return False, "Incorrect password."

    return True, {
        "id": user['id'],
        "username": user['username'],
        "email": user['email']
    }


def get_user_by_id(user_id):
    """Get user info by ID."""
    conn = get_db()
    user = conn.execute("SELECT id, username, email FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    if user:
        return {"id": user['id'], "username": user['username'], "email": user['email']}
    return None


# ── CHAT SESSION OPERATIONS ──

def create_session(user_id, title='New Chat'):
    """Create a new chat session. Returns session_id."""
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO chat_sessions (user_id, title) VALUES (?, ?)",
        (user_id, title)
    )
    session_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return session_id


def get_user_sessions(user_id, limit=30):
    """Get all chat sessions for a user, newest first."""
    conn = get_db()
    sessions = conn.execute(
        "SELECT id, title, created_at FROM chat_sessions WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
        (user_id, limit)
    ).fetchall()
    conn.close()
    return [{"id": s['id'], "title": s['title'], "created_at": s['created_at']} for s in sessions]


def delete_session(session_id, user_id):
    """Delete a chat session (and its messages via CASCADE). Returns success."""
    conn = get_db()
    result = conn.execute(
        "DELETE FROM chat_sessions WHERE id = ? AND user_id = ?",
        (session_id, user_id)
    )
    conn.commit()
    deleted = result.rowcount > 0
    conn.close()
    return deleted


def delete_all_sessions(user_id):
    """Delete all chat sessions for a user."""
    conn = get_db()
    conn.execute("DELETE FROM chat_sessions WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def update_session_title(session_id, title):
    """Update session title (from first user message)."""
    conn = get_db()
    conn.execute(
        "UPDATE chat_sessions SET title = ? WHERE id = ?",
        (title[:80], session_id)
    )
    conn.commit()
    conn.close()


# ── MESSAGE OPERATIONS ──

def save_message(session_id, role, content, msg_type='chat'):
    """Save a message to a chat session."""
    conn = get_db()
    conn.execute(
        "INSERT INTO messages (session_id, role, content, msg_type) VALUES (?, ?, ?, ?)",
        (session_id, role, content, msg_type)
    )
    conn.commit()
    conn.close()


def get_session_messages(session_id):
    """Get all messages in a chat session."""
    conn = get_db()
    messages = conn.execute(
        "SELECT role, content, msg_type, created_at FROM messages WHERE session_id = ? ORDER BY created_at ASC",
        (session_id,)
    ).fetchall()
    conn.close()
    return [{"role": m['role'], "content": m['content'], "msg_type": m['msg_type'], "created_at": m['created_at']} for m in messages]


# Initialize DB on import
init_db()
