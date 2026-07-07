from datetime import datetime, timezone
from typing import Optional
from contextlib import asynccontextmanager, contextmanager

import sqlite3

from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from pydantic import BaseModel, HttpUrl

DB_FILE = "urls.db"
BASE62_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_table()
    yield
app = FastAPI(title="URL_Shortener", lifespan=lifespan)

class UrlRequest(BaseModel):
    url: HttpUrl
    expiration: Optional[datetime] = None

def get_db_conn():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row

    try:
        yield conn
    finally:
        conn.close()

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

@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>URL Shortener</title>
        <style>
            body {
                font-family: sans-serif;
                max-width: 500px;
                margin: 20px auto;
                padding: 20px;
            }
            
            input,button {
                width: 100%;
                padding: 10px;
                margin: 10px auto;
                font-size: 14px;
            }
            
            button {
                background: blue;
                color: white;
                border: 1px solid black;
                cursor: pointer;
            }
            
            button:hover {
                background: red;
            }
        </style>
    </head>
    <body>
        <h1>URL Shortener</h1>
        
        <form action="/shorten-form" method="post">
            <label>Enter a URL:</label>
            <input type="url" name="url" placeholder="https://example.com" required>
            
            <label>Expiration date:</label>
            <input type="datetime-local" name="expiration">
            
            <button type="submit">Shorten URL</button>
        </form>
    </body>
    </html>
    """

@app.post("/shorten-form", response_class=HTMLResponse)
def shorten_form(
        request: Request,
        url: str = Form(...),
        expiration: Optional[datetime] = Form(None),
):
    expiration_value = expiration.isoformat() if expiration else None

    with get_db_conn() as conn:
        cursor = conn.execute(
            """INSERT INTO urls (url, expiration) VALUES (?, ?)""",
            (url, expiration_value),
        )

        url_id = cursor.lastrowid
        short_code_value = base62_encode(url_id)

        conn.execute(
            """UPDATE urls SET short_code = ? WHERE id = ?""",
            (short_code_value, url_id),
        )

        conn.commit()

    shortened_url = str(request.base_url) + short_code_value

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Short URL Created</title>
        <style>
            body {{
                font-family: sans-serif;
                max-width: 500px;
                margin: 20px auto;
                padding: 20px;
            }}
            
            a {{
                color: blue;
                font-size: 14px;
            }}
        </style>
    </head>
    <body>
        <h1>Short URL Created</h1>
        
        <p>Original URL:</p>
        <p>{url}</p>
        
        <p>Shortened URL:</p>
        <p><a href="{shortened_url}">{shortened_url}</a></p>
        
        <p><a href="/"> Create another short URL</a></p>
    </body>
    </html>
    """
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
            raise HTTPException(status_code=410, detail="URL has expired")

    return RedirectResponse(url=row["url"])