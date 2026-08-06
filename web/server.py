import asyncio
import random
from config.config import *
from economy.pig6economy import *
import time
from jinja2 import Template
from fastapi.responses import FileResponse
import uvicorn
from fastapi.responses import HTMLResponse

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


CAPACITY = 100


@app.get("/api/market")
def mmarket():

    economy = Pig6Economy()

    available = economy.get_system_codes_count()

    if available <= 0:

        return {
            "price": 0,
            "availableCodes": 0,
            "capacity": CAPACITY,
            "priceChange": 0,
            "status": "SOLD_OUT",
        }

    config = load_config()

    minimum = config.get("Pmin", 10)

    coefficient = config.get("constA", 1)

    price = minimum * (1 + coefficient * ((CAPACITY - available) / available))

    price = round(price, 2)

    old_state = economy.get_market_state()

    old_price = old_state.get("price", price)

    if old_price:

        change = round(((price - old_price) / old_price) * 100, 2)

    else:

        change = 0

    economy.save_market_state(available, price)

    return {
        "price": int(price),
        "availableCodes": available,
        "capacity": CAPACITY,
        "priceChange": change,
        "status": "ACTIVE",
    }


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

    message = cert["message"][:5]
    if os.path.exists(public_path):

        with open(public_path, "r", encoding="utf-8") as f:

            public_key = f.read()

    html = Template(open("web/check.html", encoding="utf-8").read()).render(
        message=cert["message"],
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

    message = cert["message"][:5]
    if os.path.exists(public_path):
        with open(public_path, "r", encoding="utf-8") as f:
            public_key = f.read()
    if cert.get("shadow") is not True:
        raise HTTPException(status_code=404)

    html = Template(open("web/shadow.html", encoding="utf-8").read()).render(
        message=cert["message"],
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


@app.get("/styles.css")
def get_styles():
    return FileResponse("web/styles.css")


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
        """
<!DOCTYPE html>

<html lang="en">

<head>

<meta charset="UTF-8">

<title>404</title>

<style>

:root {

    --bg: #09090b;
    --surface: #111113;
    --surface-2: #18181b;

    --border: #27272a;

    --text: #fafafa;
    --muted: #a1a1aa;

    --radius: 18px;

    --shadow:
        0 12px 40px rgba(0,0,0,.35);

}


* {

    margin:0;
    padding:0;
    box-sizing:border-box;

}


body {

    background:var(--bg);

    color:var(--text);

    font-family:"Inter", sans-serif;

    line-height:1.5;

    height:100vh;

    display:flex;

    align-items:center;

    justify-content:center;

}


#app {

    max-width:600px;

    width:100%;

    padding:32px;

}


.card {

    background:var(--surface);

    border:1px solid var(--border);

    border-radius:var(--radius);

    padding:40px;

    box-shadow:var(--shadow);

    text-align:center;

}


h1 {

    font-size:90px;

    font-weight:700;

    letter-spacing:-4px;

    line-height:1;

    margin-bottom:20px;

}


.title {

    font-size:24px;

    font-weight:700;

    margin-bottom:12px;

}


.text {

    color:var(--muted);

    font-size:16px;

}


footer {

    margin-top:30px;

    text-align:center;

    color:var(--muted);

    font-size:13px;

}


</style>

</head>


<body>


<div id="app">


<div class="card">


<h1>

404

</h1>


<div class="title">

Page not found

</div>


<div class="text">

The requested page does not exist.

</div>


</div>


<footer>

Nothing here.

</footer>


</div>


</body>

</html>
        """,
        status_code=404,
    )


def run_api():
    uvicorn.run(app, host="0.0.0.0", port=2322, log_level="info")


api_thread = threading.Thread(target=run_api, daemon=True)
api_thread.start()
