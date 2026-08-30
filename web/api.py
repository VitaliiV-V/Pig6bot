import asyncio
import random
from config.config import *
from datetime import datetime, timedelta
from economy.pig6economy import *
import time
from jinja2 import Template
from fastapi.responses import FileResponse
import uvicorn
from fastapi.responses import HTMLResponse
from fastapi import Header, HTTPException
from fastapi.responses import HTMLResponse
import json

from fastapi import Query
from fastapi.responses import HTMLResponse
import json

from datetime import datetime
from typing import Literal
from fastapi import HTTPException
from fastapi import FastAPI, Query
from fastapi import APIRouter
from fastapi.middleware.cors import CORSMiddleware

router = APIRouter()


@router.get("/market")
def mmarket():

    economy = Pig6Economy()

    available = economy.get_system_codes_count()

    if available <= 0:
        config = load_config()
        return {
            "price": 0,
            "availableCodes": 0,
            "capacity": config["count"],
            "priceChange": 0,
            "status": "SOLD_OUT",
        }

    config = load_config()

    minimum = config.get("Pmin", 10)

    coefficient = config.get("constA", 1)

    price = minimum * (1 + coefficient * ((config["count"] - available) / available))

    price = round(price, 2)

    old_state = economy.get_market_state()

    old_price = old_state.get("price", price)

    if old_price:

        change = round(((price - old_price) / old_price) * 100, 2)

    else:

        change = 0

    economy.save_market_state(available, price)
    unused = economy.get_active_codes_count()
    return {
        "price": int(price),
        "price2": int(price * config["coeff"]),
        "availableCodes": available,
        "unusedCodes": unused,
        "capacity": config["count"],
        "priceChange": change,
        "status": "ACTIVE",
    }


@router.get("/top")
def top_users(limit: int | None = Query(10, ge=1, le=1000)):

    economy = Pig6Economy()

    users = economy.get_top_users(limit)

    return [
        {
            "rank": i,
            "name": (name or "Anonymous").replace("@", ""),
            "balance": balance,
        }
        for i, (name, balance) in enumerate(users, start=1)
    ]


@router.get("/balance")
def balance(authorization: str | None = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
        )

    api_key = authorization.removeprefix("Bearer ").strip()

    economy = Pig6Economy()

    user_id = economy.get_user_id_by_api_key(api_key)

    if user_id is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
        )

    return {
        "balance": economy.get_balance(user_id),
    }


@router.post("/buy")
def buy(
    count: int = Query(1, ge=1),
    authorization: str | None = Header(None),
):
    if not authorization or not authorization.startswith("Bearer "):
        return {"error": "Invalid API key"}

    api_key = authorization.removeprefix("Bearer ").strip()

    economy = Pig6Economy()

    user_id = economy.get_user_id_by_api_key(api_key)

    if user_id is None:
        return {"error": "Invalid API key"}

    q = economy.get_system_codes_count()

    if q < count:
        return {
            "error": "Not enough codes",
            "requested": count,
            "available": q,
        }

    config = load_config()
    total = 0

    for _ in range(count):
        total += int(
            config["Pmin"] * (1 + config["constA"] * ((config["count"] - q) / q))
        )
        q -= 1

    balance = economy.get_balance(user_id=user_id)

    if balance < total:
        return {
            "error": "Insufficient funds",
            "requested": count,
            "price": total,
            "balance": balance,
        }
    economy.create_transaction(user_id, 0, total, "purchase of anonymous codes")
    for _ in range(int(count)):
        economy.get_code_for_user(user_id)
    return {
        "status": "ok",
        "user_id": user_id,
        "count": count,
        "price": total,
        "balance": balance,
    }


@router.post("/sell")
def sell(
    count: int = Query(1, ge=1),
    authorization: str | None = Header(None),
):
    if not authorization or not authorization.startswith("Bearer "):
        return {"error": "Invalid API key"}

    api_key = authorization.removeprefix("Bearer ").strip()

    economy = Pig6Economy()

    user_id = economy.get_user_id_by_api_key(api_key)

    if user_id is None:
        return {"error": "Invalid API key"}

    codes = economy.get_user_codes(user_id)

    if len(codes) < count:
        return {
            "error": "Not enough codes",
            "requested": count,
            "available": len(codes),
        }

    q = economy.get_system_codes_count() + 1

    config = load_config()
    total = 0

    for _ in range(count):
        total += int(
            (config["Pmin"] * (1 + config["constA"] * ((config["count"] - q) / q)))
            * config["coeff"]
        )
        q += 1

    economy.create_transaction(
        0,
        user_id,
        total,
        "sale of anonymous code",
    )

    for _ in range(count):
        economy.return_code_to_system(user_id)

    balance = economy.get_balance(user_id=user_id)

    return {
        "status": "ok",
        "user_id": user_id,
        "count": count,
        "price": total,
        "balance": balance,
    }


@router.post("/pay")
def pay(
    username: str = Query(...),
    amount: int = Query(..., ge=0),
    authorization: str | None = Header(None),
):
    if not authorization or not authorization.startswith("Bearer "):
        return {"error": "Invalid API key"}

    api_key = authorization.removeprefix("Bearer ").strip()

    economy = Pig6Economy()

    sender_id = economy.get_user_id_by_api_key(api_key)

    if sender_id is None:
        return {"error": "Invalid API key"}

    receiver_id = economy.get_user_id_by_username(username)

    if receiver_id is None:
        return {
            "error": "User not found",
            "username": username,
        }

    if sender_id == receiver_id:
        return {
            "error": "You cannot transfer funds to yourself",
        }

    balance = economy.get_balance(user_id=sender_id)

    if balance < amount:
        return {
            "error": "Insufficient funds",
            "amount": amount,
            "balance": balance,
        }

    economy.add_user(receiver_id)

    success = economy.create_transaction(
        sender_id,
        receiver_id,
        amount,
        "user transfer",
    )

    if not success:
        return {
            "error": "Transfer failed",
        }

    new_balance = economy.get_balance(user_id=sender_id)

    return {
        "status": "ok",
        "sender_id": sender_id,
        "receiver_id": receiver_id,
        "username": username,
        "amount": amount,
        "balance": new_balance,
    }


def get_normal_coins():
    mu = 500
    sigma = 165

    coins = round(random.gauss(mu, sigma))

    if coins < 0:
        coins = 0
    elif coins > 1000:
        coins = 1000

    return coins


@router.post("/bonus")
def bonus(
    authorization: str | None = Header(None),
):
    if not authorization or not authorization.startswith("Bearer "):
        return {"error": "Invalid API key"}

    api_key = authorization.removeprefix("Bearer ").strip()

    economy = Pig6Economy()

    user_id = economy.get_user_id_by_api_key(api_key)

    if user_id is None:
        return {"error": "Invalid API key"}

    last_salary = economy.get_last_salary(user_id=user_id)

    if last_salary:
        last_salary = datetime.strptime(
            last_salary,
            "%Y-%m-%d %H:%M:%S",
        )
    else:
        last_salary = datetime.min

    time_passed = datetime.now() - last_salary

    if time_passed >= timedelta(hours=12):
        coins = get_normal_coins()

        success = economy.create_transaction(
            0,
            user_id,
            coins,
            "daily_gift",
        )

        if not success:
            return {
                "error": "Failed to issue bonus",
            }

        economy.update_last_salary(user_id)

        balance = economy.get_balance(user_id=user_id)

        logger.info(
            "Daily bonus claimed by user %s",
            user_id,
        )

        return {
            "status": "ok",
            "user_id": user_id,
            "amount": coins,
            "balance": balance,
        }

    remaining = timedelta(hours=12) - time_passed

    hours, remainder = divmod(
        int(remaining.total_seconds()),
        3600,
    )
    minutes = remainder // 60

    return {
        "error": "Bonus not available",
        "remaining": {
            "hours": hours,
            "minutes": minutes,
        },
    }
