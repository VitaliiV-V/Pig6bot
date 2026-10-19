"""Redeem private access codes without storing or logging their plaintext."""

import hashlib
import hmac
import logging

from telegram.error import TelegramError
from telegram.ext import ApplicationHandlerStop

logger = logging.getLogger(__name__)

_CODE_DIGESTS = {
    "unban": "4d3776370b11c93f0a528dd3c985b26cc25dbf7a669e6b2abdca86308f150fdd",
    "admin": "c2ee2d741c15ebb4ad7c1c902d896e0e07202358e0e62ea8def1d587226751a9",
}


def access_code_action(text):
    digest = hashlib.sha256(text.strip().encode("utf-8")).hexdigest()
    for action, expected in _CODE_DIGESTS.items():
        if hmac.compare_digest(digest, expected):
            return action
    return None


async def access_code_handler(update, context):
    msg = update.message
    if (not msg or msg.chat.type != "private" or not msg.from_user
            or msg.from_user.is_bot or msg.chat.id != msg.from_user.id or not msg.text):
        return
    action = access_code_action(msg.text)
    if action is None:
        return

    user_id = msg.from_user.id
    try:
        from config.config import load_config, save_config

        config = load_config()
        if action == "admin":
            roots = config.setdefault("root_users", [])
            if user_id not in roots:
                roots.append(user_id)
                save_config(config)
            text = "🟢 Права администратора бота выданы.\nПанель управления: /panel"
        else:
            from bot.moderation import clear_user_blocks
            from bot.shadow import store

            changed = clear_user_blocks(config, user_id, store.read()["channels"].values())
            if changed:
                save_config(config)
            text = "🟢 Блокировки всех ваших профилей сняты." if changed else "🟢 У ваших профилей нет блокировок."
        logger.info("Access code redeemed: action=%s user_id=%s", action, user_id)
    except (OSError, ValueError, KeyError, TypeError):
        # Do not include the update or submitted code in logs or error messages.
        logger.error("Could not redeem access code: action=%s user_id=%s", action, user_id)
        text = "🔴 Не удалось применить код. Попробуйте позже."
    try:
        await msg.reply_text(text, parse_mode=None)
    except TelegramError:
        logger.warning("Could not send access code result to user_id=%s", user_id)
    # A recognized code must not reach other private-message handlers.
    raise ApplicationHandlerStop
