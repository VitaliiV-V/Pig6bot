"""JSON state and quota rules for Shadow Protocol (no Telegram side effects)."""

import calendar
import copy
import fcntl
import json
import os
import tempfile
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

MOSCOW = timezone(timedelta(hours=3), "Europe/Moscow")
DEFAULT_STATE = {
    "plans": {
        "Free": {"posts_per_day": 1, "views_per_day": 0},
        "Plus": {"posts_per_day": 5, "views_per_day": 0},
        "Pro x5": {"posts_per_day": 25, "views_per_day": 1},
        "Pro x20": {"posts_per_day": 100, "views_per_day": 5},
        "Ultra": {"posts_per_day": 1000, "views_per_day": 100},
    },
    "stores": {
        "pig6storeplus": "Plus",
        "pig6store_pro_x5": "Pro x5",
        "pig6store_pro_x20": "Pro x20",
    },
    "subscriptions": {},
    "usage": {},
    "channels": {},
    "posts": {},
    "purchases": {},
}


def now_moscow():
    return datetime.now(MOSCOW)


def parse_datetime(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return result.replace(tzinfo=MOSCOW) if result.tzinfo is None else result.astimezone(MOSCOW)


def next_reset(now):
    return (now.astimezone(MOSCOW) + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )


def add_month(now):
    year, month = (now.year + 1, 1) if now.month == 12 else (now.year, now.month + 1)
    return now.replace(year=year, month=month, day=min(now.day, calendar.monthrange(year, month)[1]))


class ShadowStore:
    def __init__(self, path="shadow.json"):
        self.path = Path(path)

    def _read(self):
        if self.path.exists():
            with self.path.open(encoding="utf-8") as handle:
                data = json.load(handle)
        else:
            data = {}
        for key, value in DEFAULT_STATE.items():
            data.setdefault(key, copy.deepcopy(value))
        for plan, limits in DEFAULT_STATE["plans"].items():
            current = data["plans"].setdefault(plan, copy.deepcopy(limits))
            for key, limit in limits.items():
                current.setdefault(key, limit)
                if type(current[key]) is not int or current[key] < 0:
                    raise ValueError(f"Invalid Shadow quota: {plan}.{key}")
        return data

    @contextmanager
    def transaction(self):
        """Serialize writers and atomically replace JSON; never overwrite malformed data."""
        with Path(str(self.path) + ".lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            data = self._read()
            yield data
            fd, filename = tempfile.mkstemp(prefix=self.path.name + ".", dir=self.path.parent)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(data, handle, ensure_ascii=False, indent=4)
                    handle.write("\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(filename, self.path)
            finally:
                if os.path.exists(filename):
                    os.unlink(filename)

    def read(self):
        # Atomic replacement means readers see either complete version.
        return self._read()


def ensure_subscription(data, user_id, now=None):
    """Give new accounts one free month of Plus; preserve existing records."""
    key = str(user_id)
    if key not in data["subscriptions"]:
        now = now if now is not None else now_moscow()
        expires_at = add_month(now).isoformat()
        data["subscriptions"][key] = {
            "plan": "Plus",
            "expires_at": expires_at,
            "trial_started_at": now.isoformat(),
            "trial_expires_at": expires_at,
        }
    return data["subscriptions"][key]


def effective_plan(data, user_id, now):
    subscription = ensure_subscription(data, user_id, now)
    plan = subscription.get("plan", "Free")
    if plan not in data["plans"]:
        return "Free"
    expiry = subscription.get("expires_at")
    if expiry is not None and parse_datetime(expiry) <= now:
        return "Free"
    return plan


def daily_usage(data, user_id, now):
    key = str(user_id)
    date = now.astimezone(MOSCOW).date().isoformat()
    usage = data["usage"].get(key)
    if usage is None or usage.get("date") != date:
        usage = {"date": date, "posts": 0, "views": 0}
        data["usage"][key] = usage
    return usage


def grant_subscription(data, user_id, plan, receipt, now):
    """One incoming store message = one month. Redelivered updates are idempotent."""
    if receipt in data["purchases"]:
        return data["purchases"][receipt]
    if plan == "Free" or plan not in data["plans"]:
        raise ValueError("Invalid store subscription")
    previous = ensure_subscription(data, user_id, now)
    base = now
    if effective_plan(data, user_id, now) == plan and previous.get("expires_at"):
        base = max(now, parse_datetime(previous["expires_at"]))
    subscription = {**previous, "plan": plan, "expires_at": add_month(base).isoformat()}
    data["subscriptions"][str(user_id)] = subscription
    result = {"user_id": user_id, "plan": plan, "expires_at": subscription["expires_at"], "created_at": now.isoformat()}
    data["purchases"][receipt] = result
    return result


def reserve_post(data, channel, chat_id, message_id, now, media_group_id=None):
    key = f"{chat_id}:{message_id}"
    if key in data["posts"]:
        return "existing"
    usage = daily_usage(data, channel["owner"]["id"], now)
    plan = effective_plan(data, channel["owner"]["id"], now)
    # An album is one publication, including all of its message IDs.
    album = next((post for post in data["posts"].values()
                  if media_group_id and post.get("media_group_id") == media_group_id
                  and post["chat_id"] == chat_id and post["channel_id"] == channel["channel_id"]), None)
    if album is None and usage["posts"] >= data["plans"][plan]["posts_per_day"]:
        return "limit"
    if album is None:
        usage["posts"] += 1
    data["posts"][key] = {
        "chat_id": chat_id,
        "message_id": message_id,
        "channel_id": channel["channel_id"],
        "owner": copy.deepcopy(channel["owner"]),
        "created_at": now.isoformat(),
        "media_group_id": media_group_id,
        "signature": channel["name"] + channel["uuid"],
        "charged": album is None,
    }
    return "accepted"


def refund_post(data, key, now):
    post = data["posts"].pop(key, None)
    if post and post["charged"]:
        usage = daily_usage(data, post["owner"]["id"], now)
        if usage["date"] == parse_datetime(post["created_at"]).date().isoformat():
            usage["posts"] = max(0, usage["posts"] - 1)


def reveal_author(data, user_id, key, now):
    post = data["posts"].get(key)
    if post is None:
        return "unknown", None
    usage = daily_usage(data, user_id, now)
    # Keep already disclosed authors available across daily resets and plan expiry.
    subscription = ensure_subscription(data, user_id, now)
    revealed = subscription.setdefault("revealed_posts", [])
    if key in revealed:
        return "cached", post["owner"]
    plan = effective_plan(data, user_id, now)
    if usage["views"] >= data["plans"][plan]["views_per_day"]:
        return "limit", None
    usage["views"] += 1
    revealed.append(key)
    return "revealed", post["owner"]
