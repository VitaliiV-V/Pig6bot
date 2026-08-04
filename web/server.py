"""
Pig-6 / P6T Market — FastAPI-бэкенд с симуляцией живого рынка.

Раз в 3 секунды фоновая задача:
  - случайно меняет availableCodes (имитация покупок/продаж)
  - пересчитывает цену по формуле: Price = Pmin * (1 + A * ((capacity - Q) / Q))
  - с вероятностью ~35% добавляет новую операцию BUY/SELL в ленту

Запуск:
    pip install -r requirements.txt
    uvicorn main:app --reload --port 3000

Фронтенд (marketApi.js) должен указывать:
    const API_BASE_URL = "http://127.0.0.1:3000/api";
    const USE_API = true;
"""

import asyncio
import random
from config.config import *
from economy.pig6economy import *
import time
from fastapi.responses import FileResponse
import uvicorn
from datetime import datetime
from typing import Literal

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="P6T Market API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===========================================================
# Константы формулы (см. блок "Price Formula" во фронтенде)
# ===========================================================

CAPACITY = 100
PMIN = 20.0
A_COEFF = 6.0

TICK_SECONDS = 3  # как часто пересчитывается рынок
NEW_OP_PROBABILITY = 0.35  # вероятность новой операции за тик
HISTORY_LIMIT = 500  # сколько последних точек цены храним
OPERATIONS_LIMIT = 20  # сколько последних операций храним


def calc_price(available: int) -> float:
    """Price = Pmin * (1 + A * ((capacity - Q) / Q))"""
    available = max(available, 1)  # защита от деления на 0
    price = PMIN * (1 + A_COEFF * ((CAPACITY - available) / available))
    return round(price, 2)


state = {
    "available_codes": 87,
    "price": calc_price(87),
    "previous_price": calc_price(87),
}

# список (unix_timestamp, price) — растущий журнал цены
price_history: list[tuple[float, float]] = [(time.time(), state["price"])]

# список последних операций, каждая с реальным timestamp создания
operations: list[dict] = [
    {"type": "BUY", "amount": 12, "total": -1240, "created_at": time.time() - 120},
    {"type": "SELL", "amount": 4, "total": 320, "created_at": time.time() - 360},
    {"type": "BUY", "amount": 1, "total": -25, "created_at": time.time() - 660},
]


def human_time_ago(created_at: float) -> str:
    seconds = int(time.time() - created_at)
    if seconds < 60:
        return f"{seconds} sec ago"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} min ago"
    hours = minutes // 60
    return f"{hours} h ago"


# ===========================================================
# Фоновая задача: имитация живого рынка
# ===========================================================


async def market_tick_loop():

    while True:

        await asyncio.sleep(TICK_SECONDS)

        # Случайное изменение доступных кодов (имитация покупок/продаж рынком)
        delta = random.randint(-4, 4)
        state["available_codes"] = min(
            CAPACITY, max(1, state["available_codes"] + delta)
        )

        state["previous_price"] = state["price"]
        state["price"] = calc_price(state["available_codes"])

        price_history.append((time.time(), state["price"]))
        if len(price_history) > HISTORY_LIMIT:
            price_history.pop(0)

        # Иногда рынок "видит" новую сделку
        if random.random() < NEW_OP_PROBABILITY:

            op_type = random.choice(["BUY", "SELL"])
            amount = random.randint(1, 15)
            total = round(amount * state["price"], 2)
            total = -total if op_type == "BUY" else total

            operations.insert(
                0,
                {
                    "type": op_type,
                    "amount": amount,
                    "total": total,
                    "created_at": time.time(),
                },
            )

            if len(operations) > OPERATIONS_LIMIT:
                operations.pop()


@app.on_event("startup")
async def start_background_loop():
    asyncio.create_task(market_tick_loop())


@app.get("/api/market")
def get_market():

    economy = Pig6Economy()

    state = economy.get_market_state()

    q = economy.get_system_codes_count()

    if q == 0:
        return {
            "price": 0,
            "availableCodes": 0,
            "capacity": CAPACITY,
            "priceChange": 0.0,
            "status": "SOLD_OUT",
        }

    config = load_config()

    price = round(config["Pmin"] * (1 + config["constA"] * ((CAPACITY - q) / q)), 2)

    previous_price = state.get("price", price)

    price_change_pct = (
        round(((price - previous_price) / previous_price) * 100, 2)
        if previous_price
        else 0.0
    )

    # сохраняем актуальное состояние рынка
    economy.save_market_state(q, price)

    return {
        "price": int(price),
        "availableCodes": q,
        "capacity": CAPACITY,
        "priceChange": price_change_pct,
        "status": "ACTIVE",
    }


RangeType = Literal["1H", "6H", "24H", "7D", "30D"]

RANGE_SECONDS = {
    "1H": 3600,
    "6H": 6 * 3600,
    "24H": 24 * 3600,
    "7D": 7 * 24 * 3600,
    "30D": 30 * 24 * 3600,
}

MAX_POINTS_RETURNED = 50


@app.get("/api/history")
def get_history(range_: RangeType = Query("24H", alias="range")):

    economy = Pig6Economy()

    window_seconds = RANGE_SECONDS[range_]

    history = economy.get_market_history(limit=MAX_POINTS_RETURNED)

    if not history:
        return [{"timestamp": datetime.now().strftime("%H:%M:%S"), "price": 0}]

    result = []

    now = time.time()

    for item in history:

        try:
            created = datetime.fromisoformat(item["timestamp"])

            age = (datetime.now() - created).total_seconds()

            if age <= window_seconds:
                result.append(
                    {"timestamp": created.strftime("%H:%M:%S"), "price": item["price"]}
                )

        except Exception:
            # если старая запись без нормальной даты
            continue

    if not result:

        state = economy.get_market_state()

        result.append(
            {"timestamp": datetime.now().strftime("%H:%M:%S"), "price": state["price"]}
        )

    return result


@app.get("/api/operations")
def get_operations():

    economy = Pig6Economy()

    economy.cursor.execute("""
        SELECT
            sender,
            receiver,
            amount,
            created_at,
            comment
        FROM transactions
        ORDER BY id DESC
        LIMIT 20
    """)

    transactions = economy.cursor.fetchall()

    result = []

    for sender, receiver, amount, created_at, comment in transactions:

        # покупка у системы
        if sender == 0:
            op_type = "BUY"
            total = -amount

        # продажа системе
        elif receiver == 0:
            op_type = "SELL"
            total = amount

        # обычный перевод
        else:
            op_type = "TRANSFER"
            total = amount

        result.append(
            {
                "type": op_type,
                "amount": amount,
                "total": total,
                "timestamp": human_time_ago(
                    datetime.fromisoformat(created_at).timestamp()
                ),
            }
        )

    return result


from fastapi.responses import HTMLResponse


@app.get("/certificate/{cert_id}", response_class=HTMLResponse)
def certificate(cert_id: str):

    with open(f"certificates/{cert_id}.json", "r", encoding="utf-8") as f:

        cert = json.load(f)

    return f"""

    <html>

    <head>

        <title>Pig-6 Certificate</title>

    </head>

    <body>

        <h2>🐷 Pig-6 Certificate</h2>

        <p><b>Author:</b> {cert['author']['username']}</p>

        <p><b>Created:</b> {cert['created_at']}</p>

        <p><b>Message:</b></p>

        <pre>{cert['message']}</pre>

        <p><b>Signature:</b></p>

        <code>{cert['signature']}</code>

    </body>

    </html>

    """


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


def run_api():
    uvicorn.run(app, host="0.0.0.0", port=2322, log_level="info")


api_thread = threading.Thread(target=run_api, daemon=True)
api_thread.start()
