import asyncio
import random
from config.config import *
from economy.pig6economy import *
import time
from jinja2 import Template
from fastapi.responses import FileResponse
import uvicorn
from fastapi.responses import HTMLResponse
from web.api import *
from fastapi.responses import HTMLResponse
import json

from fastapi import Query
from fastapi.responses import HTMLResponse
import json

from datetime import datetime
from typing import Literal
from fastapi import HTTPException
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="P6T Market API")
app.include_router(router, prefix="/api")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


CAPACITY = 100


# =========================

# HISTORY

# =========================

RangeType = Literal["1H", "6H", "24H", "7D", "30D"]


@app.get("/api/history")
def history(range: RangeType = Query("24H")):

    economy = Pig6Economy()

    rows = economy.get_market_history(limit=50)

    result = []

    for row in rows:

        price = float(row["price"])

        move = random.uniform(0.5, 2)

        result.append(
            {
                "timestamp": row["timestamp"],
                "price": round(price, 2),
                "open": round(price - move, 2),
                "high": round(price + move, 2),
                "low": round(price - move, 2),
                "close": round(price, 2),
            }
        )

    return result


@app.get("/check", response_class=HTMLResponse)
def certificate(
    signature: str = Query(...),
    user_id: int | None = Query(None),
):

    with open(f"certificates/{signature}.json", "r", encoding="utf-8") as f:
        cert = json.load(f)

    author = cert["author"]

    author_name_parts = [
        author.get("first_name"),
        author.get("last_name"),
    ]

    author_name = " ".join(part for part in author_name_parts if part)

    if not author_name:
        author_name = "Unknown"

    if author.get("username"):
        author_name += f" ({author['username']})"

        # здесь можешь использовать user_id для новой схемы проверки
        # например:
        # if user_id is not None:
        #     verify_certificate(user_id, ...)
    public_key = "Public key not found"

    public_path = f"keys/public/{author['id']}.public.pem"

    message = cert["message"][:5] + "..."
    if os.path.exists(public_path):

        with open(public_path, "r", encoding="utf-8") as f:

            public_key = f.read()

    html = Template(open("web/check.html", encoding="utf-8").read()).render(
        message=message,
        author_name=author_name,
        created_at=cert["created_at"],
        cert_id=cert["id"],
        signature=cert["signature"],
        public_key=public_key,
    )
    if cert.get("shadow") is True:
        raise HTTPException(status_code=404)
    return html


@app.get("/shadow", response_class=HTMLResponse)
def shadow_certificate(
    signature: str = Query(...),
):

    with open(f"certificates/{signature}.json", "r", encoding="utf-8") as f:
        cert = json.load(f)

    public_key = "Public key not found"

    author_id = cert["author"]["id"]

    public_path = f"keys/public/{author_id}.public.pem"

    message = cert["message"][:5] + "..."
    if os.path.exists(public_path):
        with open(public_path, "r", encoding="utf-8") as f:
            public_key = f.read()
    if cert.get("shadow") is not True:
        raise HTTPException(status_code=404)

    html = Template(open("web/shadow.html", encoding="utf-8").read()).render(
        message=message,
        signature=cert["signature"],
        public_key=public_key,
    )
    return html


@app.get("/market")
def index():
    return FileResponse("web/market.html")


@app.get("/")
def index():
    return FileResponse("web/index.html")


@app.get("/verify")
def index():
    return FileResponse("web/verify.html")


@app.get("/styles.css")
def get_styles():
    return FileResponse("web/styles.css")


@app.get("/api-docs")
def get_styles():
    return FileResponse("web/api-docs.html")


@app.get("/common.css")
def get_styles():
    return FileResponse("web/common.css")


@app.get("/site.js")
def get_styles():
    return FileResponse("web/site.js")


@app.get("/marketApi.js")
def get_market_api():
    return FileResponse("web/marketApi.js")


@app.get("/app.js")
def get_market_api_alias():
    return FileResponse("web/app.js")


import threading
import uvicorn


@app.exception_handler(404)
async def not_found(request, exc):

    return HTMLResponse(
        open("web/404.html", encoding="utf-8").read(),
        status_code=404,
    )


def run_api():
    uvicorn.run(app, host="0.0.0.0", port=2322, log_level="info")


api_thread = threading.Thread(target=run_api, daemon=True)
api_thread.start()
