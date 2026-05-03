import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "jobs.db")

def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            title TEXT,
            company TEXT,
            location TEXT,
            salary TEXT,
            url TEXT,
            source TEXT,
            score INTEGER,
            seen_at TEXT,
            sent INTEGER DEFAULT 0
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS digests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sent_at TEXT,
            offers_count INTEGER
        )
    """)
    conn.commit()
    conn.close()

def is_seen(job_id: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM jobs WHERE id = ?", (job_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def save_job(job: dict):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO jobs (id, title, company, location, salary, url, source, score, seen_at, sent)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
    """, (
        job["id"], job["title"], job["company"], job["location"],
        job.get("salary", ""), job["url"], job["source"],
        job.get("score", 0), datetime.now().isoformat()
    ))
    conn.commit()
    conn.close()

def get_unsent_jobs(min_score: int = 50, limit: int = 5) -> list:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, title, company, location, salary, url, source, score
        FROM jobs
        WHERE sent = 0 AND score >= ?
        ORDER BY score DESC
        LIMIT ?
    """, (min_score, limit))
    rows = cursor.fetchall()
    conn.close()
    return [
        {"id": r[0], "title": r[1], "company": r[2], "location": r[3],
         "salary": r[4], "url": r[5], "source": r[6], "score": r[7]}
        for r in rows
    ]

def mark_as_sent(job_ids: list):
    conn = get_connection()
    cursor = conn.cursor()
    for job_id in job_ids:
        cursor.execute("UPDATE jobs SET sent = 1 WHERE id = ?", (job_id,))
    cursor.execute(
        "INSERT INTO digests (sent_at, offers_count) VALUES (?, ?)",
        (datetime.now().isoformat(), len(job_ids))
    )
    conn.commit()
    conn.close()
