import os

import psycopg2
from psycopg2.extras import RealDictCursor

from ..config import MOTOR_IA_SCHEMA

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://sinagersat:12345678@127.0.0.1:5432/db_sinagersat",
)
if "+psycopg2" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("+psycopg2", "", 1)

_CONNECT_OPTIONS = f"-c search_path={MOTOR_IA_SCHEMA},public"


def get_connection():
    return psycopg2.connect(
        DATABASE_URL,
        options=_CONNECT_OPTIONS,
        connect_timeout=10,
        application_name="sinagersat-motor-ia",
    )


def execute_query(query, params=None, fetch=True):
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(query, params)
        result = None
        if fetch:
            result = cur.fetchall()
            result = [dict(row) for row in result]
        conn.commit()
        cur.close()
        return result
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
