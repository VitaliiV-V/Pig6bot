import os
import secrets
import logging
from logging.handlers import RotatingFileHandler
from bot.panel import *
import bot.tools as tools
from bot.settings import *
from config.config import *
from economy.economy import *
from economy.pig6economy import *
from telegram.error import BadRequest, Forbidden
from telegram.ext import ContextTypes
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram import (
    ReplyKeyboardRemove,
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

# ---------------------------------------------------------------------------
# Dedicated audit logger — every admin action goes to its own file,
# separate from the general application log.
# ---------------------------------------------------------------------------
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

audit_logger = logging.getLogger("panel_audit")
audit_logger.setLevel(logging.INFO)
audit_logger.propagate = False  # don't also dump this into the root/app logger

if not audit_logger.handlers:
    _handler = RotatingFileHandler(
        os.path.join(LOG_DIR, "panel_actions.log"),
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    _handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    )
    audit_logger.addHandler(_handler)

# Also keep a normal module logger for unexpected/technical errors.
logger = logging.getLogger(__name__)


def _who(user) -> str:
    """Human-readable actor identity for audit lines."""
    if user is None:
        return "unknown"
    uname = f"@{user.username}" if getattr(user, "username", None) else "no_username"
    return f"id={user.id} ({uname})"


ROLES = ("root", "sudo", "user")
CATEGORIES = ("protected", "alpha", "signed")

CATEGORY_KEY = {
    "protected": "admins",
    "alpha": "alpha_users",
    "signed": "signed_users",
}

CATEGORY_TITLE = {
    "protected": "👤 Admins",
    "alpha": "⭐ Alpha",
    "signed": "✍️ Signed users",
}


async def check_id(user_id, msg, context):
    config = load_config()
    if user_id in config["root_users"] or user_id == OWNER_ID:
        audit_logger.info("ACCESS GRANTED | actor_id=%s", user_id)
        return True

    audit_logger.warning("ACCESS DENIED | actor_id=%s", user_id)
    try:
        await msg.reply_text("🔴 Доступ запрещён.")
    except (BadRequest, Forbidden) as e:
        logger.warning("Failed to send access-denied notice to %s: %s", user_id, e)
    return False


def _get_category_ids(config, category):
    if category == "signed":
        return sorted(config.get("signed_users", {}).keys(), key=str)
    key = CATEGORY_KEY[category]
    return [str(u.get("channel_id")) for u in config.get(key, [])]


def _find_in_category(config, category, user_id):
    user_id = str(user_id)
    if category == "signed":
        return config.get("signed_users", {}).get(user_id)
    key = CATEGORY_KEY[category]
    for u in config.get(key, []):
        if str(u.get("channel_id")) == user_id:
            return u
    return None


def _display_name(category, entry, user_id):
    if category == "signed":
        return entry.get("username") or user_id
    name = entry.get("name") or user_id
    if category == "protected":
        return f"{name}"
    return name


def format_user_info(category, entry, user_id):
    user_id = str(user_id)
    lines = [f"<b>{CATEGORY_TITLE[category]}</b>\n"]

    if entry is None:
        lines.append("Пользователь не найден.")
        return "\n".join(lines)

    if category == "protected":
        lines.append(
            f"Name: {entry.get('name')}\n"
            f"Owner: {entry.get('owner')}\n"
            f"Channel ID: {entry.get('channel_id')}\n"
            f"UUID: {entry.get('uuid')}\n"
            f"Trust: {'yes' if entry.get('trust') else 'no'}\n"
            f"Mute: {'yes' if entry.get('mute') else 'no'}\n"
            f"EXCOMMUNICADO: {'yes' if entry.get('EXCOMMUNICADO') else 'no'}\n"
        )

    elif category == "alpha":
        lines.append(
            f"Name: {entry.get('name')}\n"
            f"Owner: {entry.get('owner')}\n"
            f"Channel ID: {entry.get('channel_id')}\n"
            f"UUID: {entry.get('uuid')}\n"
        )

    elif category == "signed":
        shadow = entry.get("shadow", [])
        shadow_txt = ", ".join(shadow) if shadow else "—"
        channels = entry.get("channels", [])
        channels_txt = ", ".join(channels) if channels else "—"
        lines.append(
            f"Username: {entry.get('username')}\n"
            f"Роль: {entry.get('role')}\n"
            f"Каналы: {channels_txt}\n"
            f"Shadow: {shadow_txt}\n"
        )

    return "\n".join(lines)


def main_keyboard():
    config = load_config()
    text1 = (
        "🟠 Активировать защиту"
        if config["ban_messages"] == "off"
        else "🟢 Деактивировать защиту"
    )
    action1 = "blockall" if config["ban_messages"] == "off" else "disable"
    text2 = (
        "🔴 Деактивировать протокол «Judgment Day»"
        if config["mode"] != "normal"
        else "🟢 Активировать протокол «Judgment Day»"
    )
    action2 = "jday"

    rows = [
        [InlineKeyboardButton(f"{text1}", callback_data=f"panel^{action1}")],
        [InlineKeyboardButton(f"{text2}", callback_data=f"panel^{action2}")],
        [
            InlineKeyboardButton(
                CATEGORY_TITLE["protected"], callback_data="panel^cat^protected"
            )
        ],
        [
            InlineKeyboardButton(
                CATEGORY_TITLE["alpha"], callback_data="panel^cat^alpha"
            )
        ],
        [
            InlineKeyboardButton(
                CATEGORY_TITLE["signed"], callback_data="panel^cat^signed"
            )
        ],
    ]
    return InlineKeyboardMarkup(rows)


def keyboard():
    return main_keyboard()


def category_list_keyboard(config, category):
    entries = []

    for uid in _get_category_ids(config, category):
        entry = _find_in_category(config, category, uid)
        display_name = _display_name(category, entry, uid)
        entries.append((display_name, uid))

    entries.sort(key=lambda item: item[0].casefold())

    rows = [
        [
            InlineKeyboardButton(
                display_name,
                callback_data=f"panel^user^{category}^{uid}",
            )
        ]
        for display_name, uid in entries
    ]

    rows.append([InlineKeyboardButton("⚙️ Главное меню", callback_data="panel^back")])

    return InlineKeyboardMarkup(rows)


def user_detail_keyboard(category, entry, user_id):
    user_id = str(user_id)
    rows = []

    if category == "protected" and entry is not None:
        if entry.get("protected"):
            trust_txt = (
                "🟢 Отозвать доверие" if entry.get("trust") else "🔴 Сделать доверенным"
            )
        mute_txt = "🟠 Unmute" if entry.get("mute") else "🟢 Mute"
        exc_txt = (
            "🔴 Снять EXCOMMUNICADO"
            if entry.get("EXCOMMUNICADO")
            else "🟢 EXCOMMUNICADO"
        )
        rows.append(
            [InlineKeyboardButton(mute_txt, callback_data=f"panel^mute^{user_id}")]
        )
        rows.append(
            [InlineKeyboardButton(exc_txt, callback_data=f"panel^exc^{user_id}")]
        )
        if entry.get("protected"):
            rows.append(
                [
                    InlineKeyboardButton(
                        trust_txt, callback_data=f"panel^trust^{user_id}"
                    )
                ]
            )

    elif category == "alpha" and entry is not None:
        # alpha_users — только просмотр, изменяемых настроек no
        pass

    elif category == "signed" and entry is not None:
        current_role = entry.get("role")
        role_row = []
        for role in ROLES:
            label = f"🟢 {role}" if role == current_role else role
            role_row.append(
                InlineKeyboardButton(
                    label, callback_data=f"panel^role^{user_id}^{role}"
                )
            )
        rows.append(role_row)

        channels = entry.get("channels", [])
        shadow = set(entry.get("shadow", []))
        for idx, ch in enumerate(channels):
            shadow_label = "☀️ Убрать shadow" if ch in shadow else "🌒 В shadow"
            rows.append(
                [
                    InlineKeyboardButton(
                        f"{ch} ❌", callback_data=f"panel^revoke^{user_id}^{idx}"
                    ),
                    InlineKeyboardButton(
                        shadow_label, callback_data=f"panel^shadow^{user_id}^{idx}"
                    ),
                ]
            )

    rows.append(
        [InlineKeyboardButton("⬅️ К списку", callback_data=f"panel^cat^{category}")]
    )
    rows.append([InlineKeyboardButton("⚙️ Главное меню", callback_data="panel^back")])
    return InlineKeyboardMarkup(rows)


MAIN_TEXT = (
    "<b>Добро пожаловать в панель управления Свинья-6.</b>\n\n"
    "Центр управления системой защиты Свинья-6. Здесь доступны настройки, мониторинг"
    ", управление сервисами, сертификатами и внутренней инфраструктурой."
)


def category_text(category):
    return f"<b>{CATEGORY_TITLE[category]}</b>\n\nВыберите пользователя."


PROCESSING_TEXT = "Обработка..."


async def panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    actor = _who(query.from_user)

    if not await check_id(query.from_user.id, query.message, context):
        await query.answer()
        return

    parts = query.data.split("^")
    # parts[0] == "panel"
    action = parts[1] if len(parts) > 1 else None
    config = load_config()

    audit_logger.info("PANEL CALLBACK | actor=%s | raw=%s", actor, query.data)

    text = MAIN_TEXT
    reply_markup = main_keyboard()

    try:
        if action in ("disable", "blockall", "jday"):
            handler = {
                "disable": tools.disable,
                "blockall": tools.blockall,
                "jday": tools.jday,
            }[action]
            audit_logger.info("PROTECTION ACTION | actor=%s | action=%s", actor, action)
            await handler(context, None)
            config = load_config()
            reply_markup = main_keyboard()
            await query.edit_message_text(
                text=PROCESSING_TEXT, parse_mode="HTML", reply_markup=reply_markup
            )
            audit_logger.info(
                "PROTECTION ACTION DONE | actor=%s | action=%s | new_ban_messages=%s | new_mode=%s",
                actor,
                action,
                config.get("ban_messages"),
                config.get("mode"),
            )

        elif action == "back":
            audit_logger.info("NAVIGATE | actor=%s | to=main_menu", actor)

        elif action == "cat":
            category = parts[2]
            text = category_text(category)
            reply_markup = category_list_keyboard(config, category)
            audit_logger.info("OPEN CATEGORY | actor=%s | category=%s", actor, category)

        elif action == "user":
            category, user_id = parts[2], parts[3]
            entry = _find_in_category(config, category, user_id)
            text = format_user_info(category, entry, user_id)
            reply_markup = user_detail_keyboard(category, entry, user_id)
            audit_logger.info(
                "OPEN USER | actor=%s | category=%s | target=%s | found=%s",
                actor,
                category,
                user_id,
                entry is not None,
            )

        elif action == "trust":
            user_id = parts[2]
            entry = _find_in_category(config, "protected", user_id)
            if entry:
                old = entry.get("trust", False)
                entry["trust"] = not old
                save_config(config)
                config = load_config()
                entry = _find_in_category(config, "protected", user_id)
                audit_logger.info(
                    "TRUST TOGGLED | actor=%s | target=%s | old=%s | new=%s",
                    actor,
                    user_id,
                    old,
                    entry.get("trust") if entry else None,
                )
            else:
                audit_logger.warning(
                    "TRUST TOGGLE FAILED (not found) | actor=%s | target=%s",
                    actor,
                    user_id,
                )
            text = format_user_info("protected", entry, user_id)
            reply_markup = user_detail_keyboard("protected", entry, user_id)

        elif action == "mute":
            user_id = parts[2]
            entry = _find_in_category(config, "protected", user_id)
            if entry:
                old = entry.get("mute", False)
                entry["mute"] = not old
                save_config(config)
                config = load_config()
                entry = _find_in_category(config, "protected", user_id)
                audit_logger.info(
                    "MUTE TOGGLED | actor=%s | target=%s | old=%s | new=%s",
                    actor,
                    user_id,
                    old,
                    entry.get("mute") if entry else None,
                )
            else:
                audit_logger.warning(
                    "MUTE TOGGLE FAILED (not found) | actor=%s | target=%s",
                    actor,
                    user_id,
                )
            text = format_user_info("protected", entry, user_id)
            reply_markup = user_detail_keyboard("protected", entry, user_id)

        elif action == "exc":
            await query.edit_message_text(text=PROCESSING_TEXT, parse_mode="HTML")
            user_id = parts[2]
            entry = _find_in_category(config, "protected", user_id)
            if entry:
                old = entry.get("EXCOMMUNICADO", False)
                entry["EXCOMMUNICADO"] = not old
                save_config(config)
                config = load_config()
                entry = _find_in_category(config, "protected", user_id)
                audit_logger.info(
                    "EXCOMMUNICADO TOGGLED | actor=%s | target=%s | old=%s | new=%s",
                    actor,
                    user_id,
                    old,
                    entry.get("EXCOMMUNICADO") if entry else None,
                )
            else:
                audit_logger.warning(
                    "EXCOMMUNICADO TOGGLE FAILED (not found) | actor=%s | target=%s",
                    actor,
                    user_id,
                )

            if entry.get("EXCOMMUNICADO") == True:
                name = entry["name"] + entry["uuid"]
                audit_logger.info(
                    "EXCOMMUNICADO PROTOCOL TRIGGERED | actor=%s | target=%s (%s)",
                    actor,
                    user_id,
                    name,
                )
                await tools.EXCOMMUNICADO(context=context, msg=None, targetname=name)
                text = format_user_info("protected", entry, user_id)
                reply_markup = user_detail_keyboard("protected", entry, user_id)

                await query.answer()

                await query.edit_message_text(
                    text=text,
                    parse_mode="HTML",
                    reply_markup=reply_markup,
                )
                return
            else:
                try:
                    if entry["protected"]:
                        await context.bot.send_message(
                            chat_id=entry["channel_id"],
                            text="⚪ Статус «EXCOMMUNICADO» снят.\nДоступ восстановлен.",
                        )
                except (BadRequest, Forbidden) as e:
                    if entry["protected"]:
                        logger.warning(
                            "Failed to notify channel %s about EXCOMMUNICADO lift: %s",
                            entry.get("channel_id"),
                            e,
                        )
                audit_logger.info(
                    "EXCOMMUNICADO LIFTED | actor=%s | target=%s", actor, user_id
                )
            text = format_user_info("protected", entry, user_id)
            reply_markup = user_detail_keyboard("protected", entry, user_id)

        elif action == "role":
            user_id, role = parts[2], parts[3]
            entry = _find_in_category(config, "signed", user_id)
            if entry and role in ROLES:
                old = entry.get("role")
                entry["role"] = role
                save_config(config)
                config = load_config()
                entry = _find_in_category(config, "signed", user_id)
                audit_logger.info(
                    "ROLE CHANGED | actor=%s | target=%s | old=%s | new=%s",
                    actor,
                    user_id,
                    old,
                    role,
                )
            else:
                audit_logger.warning(
                    "ROLE CHANGE FAILED (not found or invalid role) | actor=%s | target=%s | role=%s",
                    actor,
                    user_id,
                    role,
                )
            text = format_user_info("signed", entry, user_id)
            reply_markup = user_detail_keyboard("signed", entry, user_id)

        elif action == "revoke":
            user_id, idx = parts[2], int(parts[3])
            entry = _find_in_category(config, "signed", user_id)
            if entry:
                channels = entry.get("channels", [])
                if 0 <= idx < len(channels):
                    removed = channels.pop(idx)
                    entry["channels"] = channels
                    shadow = entry.get("shadow", [])
                    if removed in shadow:
                        shadow.remove(removed)
                        entry["shadow"] = shadow
                    save_config(config)
                    config = load_config()
                    entry = _find_in_category(config, "signed", user_id)
                    audit_logger.info(
                        "CHANNEL REVOKED | actor=%s | target=%s | channel=%s",
                        actor,
                        user_id,
                        removed,
                    )
                else:
                    audit_logger.warning(
                        "CHANNEL REVOKE FAILED (bad index) | actor=%s | target=%s | idx=%s",
                        actor,
                        user_id,
                        idx,
                    )
            else:
                audit_logger.warning(
                    "CHANNEL REVOKE FAILED (user not found) | actor=%s | target=%s",
                    actor,
                    user_id,
                )
            text = format_user_info("signed", entry, user_id)
            reply_markup = user_detail_keyboard("signed", entry, user_id)

        elif action == "shadow":
            user_id, idx = parts[2], int(parts[3])
            entry = _find_in_category(config, "signed", user_id)
            if entry:
                channels = entry.get("channels", [])
                if 0 <= idx < len(channels):
                    ch = channels[idx]
                    shadow = set(entry.get("shadow", []))
                    was_shadow = ch in shadow
                    if was_shadow:
                        shadow.discard(ch)
                    else:
                        shadow.add(ch)
                    entry["shadow"] = sorted(shadow)
                    save_config(config)
                    config = load_config()
                    entry = _find_in_category(config, "signed", user_id)
                    audit_logger.info(
                        "SHADOW TOGGLED | actor=%s | target=%s | channel=%s | old=%s | new=%s",
                        actor,
                        user_id,
                        ch,
                        was_shadow,
                        not was_shadow,
                    )
                else:
                    audit_logger.warning(
                        "SHADOW TOGGLE FAILED (bad index) | actor=%s | target=%s | idx=%s",
                        actor,
                        user_id,
                        idx,
                    )
            else:
                audit_logger.warning(
                    "SHADOW TOGGLE FAILED (user not found) | actor=%s | target=%s",
                    actor,
                    user_id,
                )
            text = format_user_info("signed", entry, user_id)
            reply_markup = user_detail_keyboard("signed", entry, user_id)

        else:
            audit_logger.warning(
                "UNKNOWN PANEL ACTION | actor=%s | raw=%s", actor, query.data
            )

    except Exception:
        logger.exception(
            "panel() failed while handling action=%s data=%s", action, query.data
        )
        audit_logger.error(
            "PANEL ACTION ERROR | actor=%s | action=%s | raw=%s",
            actor,
            action,
            query.data,
        )
        raise

    await query.answer()

    await query.edit_message_text(
        text=text,
        parse_mode="HTML",
        reply_markup=reply_markup,
    )


async def panel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    actor = _who(msg.from_user)

    if not await check_id(msg.from_user.id, msg, context):
        return

    audit_logger.info("PANEL OPENED | actor=%s", actor)

    await msg.reply_text(
        text=MAIN_TEXT,
        parse_mode="HTML",
        reply_markup=main_keyboard(),
    )
