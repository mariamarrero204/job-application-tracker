"""MySQL access helpers for the Job Application Tracker.

All SQL values are bound through mysql-connector placeholders. Credentials are
read from the environment, never stored in source control.
"""
import os
from contextlib import contextmanager

import mysql.connector
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    """Open a new MySQL connection; callers must close it."""
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "job_tracker"),
        connection_timeout=10,
    )


@contextmanager
def cursor_context(commit=False):
    """Manage cursor/connection lifecycle and commit or roll back writes."""
    conn = get_connection()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        yield cursor
        if commit:
            conn.commit()
    except Exception:
        if commit:
            conn.rollback()
        raise
    finally:
        if cursor is not None:
            cursor.close()
        conn.close()


def fetch_all(sql, params=()):
    with cursor_context() as cursor:
        cursor.execute(sql, params)
        return cursor.fetchall()


def fetch_one(sql, params=()):
    with cursor_context() as cursor:
        cursor.execute(sql, params)
        return cursor.fetchone()


def execute(sql, params=()):
    """Execute an INSERT/UPDATE/DELETE and return lastrowid, rowcount."""
    with cursor_context(commit=True) as cursor:
        cursor.execute(sql, params)
        return cursor.lastrowid, cursor.rowcount
