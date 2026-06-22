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

