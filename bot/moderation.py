"""Profile bans and flood limits shared by regular and Shadow publications."""

from collections import deque
from dataclasses import dataclass
import logging
from time import monotonic

from telegram.error import TelegramError

logger = logging.getLogger(__name__)
FLOOD_LIMIT = 10
FLOOD_WINDOW = 5
_recent_messages = deque()


def visible_name(value):
    return "".join(char for char in (value or "") if not 0xE0100 <= ord(char) < 0xE01F0)


def owner_id(entry):
    owner = entry.get("owner")
    value = owner.get("id") if isinstance(owner, dict) else entry.get("id")
    try:
        return str(int(value)) if int(value) > 0 else None
    except (TypeError, ValueError):
        return None


@dataclass
class Profile:
    key: str
    name: str
    owner_id: str | None
    entry: dict


def profile_from_entry(category, entry, key):
    owner = str(key) if category == "signed" else owner_id(entry)
    name = entry.get("name") or entry.get("username") or str(key)
    if category == "shadow":
        name = f"Shadow {key}"
    return Profile(f"{category}:{key}", name, owner, entry)


def find_profile(config, msg):
    """Resolve a stable profile, including replies carrying an old rotating UUID.

    Resolution alone is not authentication. Count floods only after the existing
    signature/certificate checks have accepted the publication.
    """
    signature = getattr(msg, "author_signature", None) or ""
    sender = getattr(msg, "sender_chat", None)
    exact = []
    candidates = []
    for category, key in (("protected", "admins"), ("alpha", "alpha_users")):
        for entry in config.get(key, []):
            profile = profile_from_entry(category, entry, entry.get("channel_id"))
            if sender and str(sender.id) == str(entry.get("channel_id")):
                return profile
            if signature and signature == entry.get("name", "") + entry.get("uuid", ""):
                exact.append(profile)
            if signature and visible_name(signature) == visible_name(entry.get("name")):
                candidates.append(profile)
    if len(exact) == 1:
        return exact[0]
    if len(candidates) == 1:
        return candidates[0]
    if candidates:
        return None
    if signature and visible_name(signature):
        name = visible_name(signature)
        return Profile(f"signature:{name}", name, None, {})
    return None


def current_signature(msg, profile):
    return bool(profile and profile.entry and msg.author_signature == (
        profile.entry.get("name", "") + profile.entry.get("uuid", "")
    ))


def reply_profile(config, msg):
    """Resolve historical replies without requiring the current rotating UUID."""
    from bot.shadow import store
    from bot.protection import signed_user_id

    if msg is None:
        return None
    data = store.read()
    recorded = data["posts"].get(f"{msg.chat_id}:{msg.message_id}")
    if recorded:
        channel = data["channels"].get(str(recorded["channel_id"]))
        if channel:
            return profile_from_entry("shadow", channel, channel["channel_id"])
    profile = find_profile(config, msg)
    if profile and profile.owner_id:
        return profile
    signer = signed_user_id(msg, config)
    if signer:
        return profile_from_entry("signed", config["signed_users"][signer], signer)
    return profile


def user_is_blocked(config, user_id):
    return user_id is not None and str(user_id) in {
        str(value) for value in config.get("blocked_user_ids", [])
    }


def profile_is_blocked(config, profile):
    if profile is None:
        return False
    return (
        user_is_blocked(config, profile.owner_id)
        or profile.entry.get("mute", False)
        or profile.entry.get("EXCOMMUNICADO", False)
        or profile.key in config.get("banned_profiles", [])
        or any(visible_name(value) == visible_name(profile.name)
               for value in config.get("banned_users", []) if visible_name(value))
    )


async def notify_restriction(context, profile, blocked, reason):
    if not profile.owner_id:
        logger.warning("Cannot notify profile %s: owner ID is missing", profile.key)
        return
    status = "🔴 Блокировка установлена" if blocked else "🟢 Блокировка снята"
    text = f"{status}\nПрофиль: {profile.name}\n{reason}"
    if not blocked:
        text += "\nДругие ограничения профиля, если есть, продолжают действовать."
    try:
        await context.bot.send_message(chat_id=int(profile.owner_id), text=text, parse_mode=None)
    except TelegramError:
        logger.warning("Could not notify user %s about profile %s", profile.owner_id, profile.key, exc_info=True)


async def set_user_block(context, user_id, blocked, reason="Решение администратора."):
    from config.config import load_config, save_config

    user_id = str(int(user_id))
    if int(user_id) <= 0:
        raise ValueError("A user block requires a positive Telegram user ID")
    config = load_config()
    ids = {str(value) for value in config.get("blocked_user_ids", [])}
    if (user_id in ids) == blocked:
        return False
    if blocked:
        ids.add(user_id)
    else:
        ids.discard(user_id)
    config["blocked_user_ids"] = sorted(ids)
    save_config(config)
    # Do not carry an earlier burst across a manual unblock.
    remaining = [event for event in _recent_messages if event[2] != f"user:{user_id}"]
    _recent_messages.clear()
    _recent_messages.extend(remaining)
    profile = Profile(f"user:{user_id}", "все ваши профили в основном канале", user_id, {})
    await notify_restriction(context, profile, blocked, reason)
    logger.info("User block changed: user=%s blocked=%s reason=%s", user_id, blocked, reason)
    return True


async def set_profile_block(context, profile, blocked, reason=None):
    from config.config import load_config, save_config

    config = load_config()
    category, key = profile.key.split(":", 1)
    entry = next((entry for entry in config.get(
        {"protected": "admins", "alpha": "alpha_users"}.get(category, ""), []
    ) if str(entry.get("channel_id")) == key), None)
    banned = set(config.get("banned_profiles", []))
    legacy = config.get("banned_users", [])
    matches = [value for value in legacy if visible_name(value) == visible_name(profile.name)]
    old = bool((entry and entry.get("mute")) or profile.key in banned or matches)
    if entry is not None:
        entry["mute"] = blocked
    elif blocked:
        banned.add(profile.key)
    if not blocked:
        banned.discard(profile.key)
        config["banned_users"] = [value for value in legacy if value not in matches]
    config["banned_profiles"] = sorted(banned)
    if old == blocked:
        return False
    save_config(config)
    if not blocked:
        identity = f"user:{profile.owner_id}" if profile.owner_id else profile.key
        remaining = [event for event in _recent_messages if event[2] != identity]
        _recent_messages.clear()
        _recent_messages.extend(remaining)
    if reason is None:
        reason = "Публикации профиля заблокированы администратором." if blocked else "Блокировка публикаций профиля снята администратором."
    await notify_restriction(context, profile, blocked, reason)
    return True


async def delete_post(context, chat_id, message_id):
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except TelegramError:
        logger.warning("Could not delete moderated post %s:%s", chat_id, message_id, exc_info=True)


async def reject_blocked(context, msg, config, profile):
    legacy = msg.author_signature and any(
        visible_name(msg.author_signature) == visible_name(value)
        for value in config.get("banned_users", []) if visible_name(value)
    )
    if legacy or profile_is_blocked(config, profile):
        await delete_post(context, msg.chat_id, msg.message_id)
        return True
    return False


async def check_flood(context, msg, profile):
    """Block only the authenticated author; purge only their recent messages."""
    if profile is None:
        return False
    now = monotonic()
    while _recent_messages and now - _recent_messages[0][0] >= FLOOD_WINDOW:
        _recent_messages.popleft()
    identity = f"user:{profile.owner_id}" if profile.owner_id else profile.key
    event = (now, msg.chat_id, identity, msg.message_id)
    if any(previous[1:] == event[1:] for previous in _recent_messages):
        return False
    _recent_messages.append(event)
    burst = [previous for previous in _recent_messages
             if previous[1:3] == (msg.chat_id, identity)]
    if len(burst) < FLOOD_LIMIT:
        return False
    reason = f"Антиспам: {FLOOD_LIMIT} сообщений за {FLOOD_WINDOW} секунд. Блокировка до снятия администратором."
    if profile.owner_id:
        await set_user_block(context, profile.owner_id, True, reason)
    else:
        await set_profile_block(context, profile, True, reason)
    remaining = [previous for previous in _recent_messages if previous[1:3] != (msg.chat_id, identity)]
    _recent_messages.clear()
    _recent_messages.extend(remaining)
    for _, chat_id, _, message_id in burst:
        await delete_post(context, chat_id, message_id)
    return True
