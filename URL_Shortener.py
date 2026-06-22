from datetime import datetime, timezone
from typing import Optional

import sqlite3
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, HttpUrl

DB_FILE = "urls.db"
BASE62_ALPABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

app = FastAPI(title="URL_Shortener")

class UrlRequest(BaseModel):
    url: HttpUrl

def get_db_conn():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def create_table():
    with get_db_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            shortened_url TEXT UNIQUE,
        )
        """
        )
        conn.commit()

def base62_encode(num: int) -> str:
    if num == 0:
        return BASE62_ALPABET[0]

    encoded = ""

    while num > 0:
        num, remainder = divmod(num, 62)
        encoded = BASE62_ALPABET[remainder] + encoded

    return encoded