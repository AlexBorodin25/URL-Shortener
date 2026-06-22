from datetime import datetime, timezone
from typing import Optional

import sqlite3

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, HttpUrl

DB_FILE = "urls.db"
BASE62_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

app = FastAPI(title="URL_Shortener")

class UrlRequest(BaseModel):
    url: HttpUrl
    expiration: Optional[datetime] = None

def get_db_conn():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def create_table():
    with get_db_conn() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS urls (id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL,short_code TEXT UNIQUE, expiration TEXT)"""
        )
        conn.commit()

def base62_encode(num: int) -> str:
    if num == 0:
        return BASE62_ALPHABET[0]

    encoded = ""

    while num > 0:
        num, remainder = divmod(num, 62)
        encoded = BASE62_ALPHABET[remainder] + encoded

    return encoded

@app.on_event("startup")
def startup():
    create_table()

@app.post("/shorten")
def short_code(data: UrlRequest, request: Request):
    expiration = data.expiration.isoformat() if data.expiration else None

    with get_db_conn() as conn:
        cursor = conn.execute(
            """INSERT INTO urls (url, expiration) VALUES (?, ?)""",
            (str(data.url), expiration),
        )

        url_id = cursor.lastrowid
        short_code = base62_encode(url_id)

        conn.execute(
            """UPDATE urls SET short_code = ? WHERE id = ?""",
            (short_code, url_id)
        )

        conn.commit()

    shortened_url = str(request.base_url) + short_code

    return {
        "id": url_id,
        "url": str(data.url),
        "short_code": short_code,
        "shortened_url": shortened_url,
        "expiration": expiration,
    }

@app.get("/{short_code}")
def redirect_url(short_code: str):
    with get_db_conn() as conn:
        row = conn.execute(
            """SELECT url, expiration FROM urls WHERE short_code = ?""",
            (short_code,),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="URL not found")

    if row["expiration"]:
        expiration = datetime.fromisoformat(row["expiration"])

        if expiration.tzinfo is None:
            expiration = expiration.replace(tzinfo=timezone.utc)

        if datetime.now(timezone.utc) > expiration:
            raise HTTPException(status_code=404, detail="URL has expired")

    return RedirectResponse(url=row["url"])