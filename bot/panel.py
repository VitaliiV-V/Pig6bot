import secrets
from bot.panel import *
import bot.tools as tools
from bot.settings import *
from config.config import *
from economy.economy import *
from economy.pig6economy import *
from telegram.ext import ContextTypes
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram import (
    ReplyKeyboardRemove,
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

ROLES = ("root", "sudo", "user")
CATEGORIES = ("protected", "super", "signed")

CATEGORY_KEY = {
    "protected": "protected_users",
    "super": "super_users",
    "signed": "signed_users",
}

CATEGORY_TITLE = {
    "protected": "🛡 Protected users",
    "super": "⭐ Super users",
    "signed": "✍️ Signed users",
}


async def check_id(user_id, msg, context):
    config = load_config()
    if user_id in config["root_users"]:
        return True
    if user_id == OWNER_ID:
        return True
    try:
        await msg.reply_text("🔴 Доступ запрещён.")
    except Exception as e:
        pass
    return False


def _get_category_ids(config, category):
    if category == "signed":
        return sorted(config.get("signed_users", {}).keys(), key=str)
    key = CATEGORY_KEY[category]
    return [str(u.get("id")) for u in config.get(key, [])]


def _find_in_category(config, category, user_id):
    user_id = str(user_id)
    if category == "signed":
        return config.get("signed_users", {}).get(user_id)
    key = CATEGORY_KEY[category]
    for u in config.get(key, []):
        if str(u.get("id")) == user_id:
            return u
    return None


def _display_name(category, entry, user_id):
    if category == "signed":
        return entry.get("username") or user_id
    return entry.get("name") or user_id


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
            f"Mute: {'yes' if entry.get('mute') else 'no'}\n"
            f"EXCOMMUNICADO: {'yes' if entry.get('EXCOMMUNICADO') else 'no'}\n"
        )

    elif category == "super":
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
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(f"{text1}", callback_data=f"panel^{action1}")],
            [InlineKeyboardButton(f"{text2}", callback_data=f"panel^{action2}")],
            [
                InlineKeyboardButton(
                    CATEGORY_TITLE["protected"], callback_data="panel^cat^protected"
                )
            ],
            [
                InlineKeyboardButton(
                    CATEGORY_TITLE["super"], callback_data="panel^cat^super"
                )
            ],
            [
                InlineKeyboardButton(
                    CATEGORY_TITLE["signed"], callback_data="panel^cat^signed"
                )
            ],
        ]
    )


def keyboard():
    return main_keyboard()


def category_list_keyboard(config, category):
    rows = []
    for uid in _get_category_ids(config, category):
        entry = _find_in_category(config, category, uid)
        rows.append(
            [
                InlineKeyboardButton(
                    _display_name(category, entry, uid),
                    callback_data=f"panel^user^{category}^{uid}",
                )
            ]
        )
    rows.append([InlineKeyboardButton("⚙️ Главное меню", callback_data="panel^back")])
    return InlineKeyboardMarkup(rows)


def user_detail_keyboard(category, entry, user_id):
    user_id = str(user_id)
    rows = []

    if category == "protected" and entry is not None:
        mute_txt = "🟢 Unmute" if entry.get("mute") else "🟠 Mute"
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

    elif category == "super" and entry is not None:
        # super_users — только просмотр, изменяемых настроек no
        pass

    elif category == "signed" and entry is not None:
        current_role = entry.get("role")
        role_row = []
        for role in ROLES:
            label = f"✅ {role}" if role == current_role else role
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


async def panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not await check_id(query.from_user.id, query.message, context):
        await query.answer()
        return

    parts = query.data.split("^")
    # parts[0] == "panel"
    action = parts[1] if len(parts) > 1 else None
    config = load_config()

    text = MAIN_TEXT
    reply_markup = main_keyboard()

    if action == "disable":
        await tools.disable(context, None)
        config = load_config()

        reply_markup = main_keyboard()
        await query.edit_message_text(
            text="Добро пожаловать в панель управления Свинья-6.Центр управления системой защиты Свинья-6. Здесь доступны настройки, мониторинг, управление сервисами, сертификатами и внутренней инфраструктурой.\n\nОбработка...",
            parse_mode="HTML",
            reply_markup=reply_markup,
        )
    elif action == "blockall":
        await tools.blockall(context, None)
        config = load_config()

        reply_markup = main_keyboard()
        await query.edit_message_text(
            text="Добро пожаловать в панель управления Свинья-6.Центр управления системой защиты Свинья-6. Здесь доступны настройки, мониторинг, управление сервисами, сертификатами и внутренней инфраструктурой.\n\nОбработка...",
            parse_mode="HTML",
            reply_markup=reply_markup,
        )
    elif action == "jday":
        await tools.jday(context, None)
        config = load_config()

        reply_markup = main_keyboard()
        await query.edit_message_text(
            text="Добро пожаловать в панель управления Свинья-6.Центр управления системой защиты Свинья-6. Здесь доступны настройки, мониторинг, управление сервисами, сертификатами и внутренней инфраструктурой.\n\nОбработка...",
            parse_mode="HTML",
            reply_markup=reply_markup,
        )
    elif action == "back":
        pass  # остаёмся на главном тексте/клавиатуре

    elif action == "cat":
        category = parts[2]
        text = category_text(category)
        reply_markup = category_list_keyboard(config, category)

    elif action == "user":
        category, user_id = parts[2], parts[3]
        entry = _find_in_category(config, category, user_id)
        text = format_user_info(category, entry, user_id)
        reply_markup = user_detail_keyboard(category, entry, user_id)

    elif action == "mute":
        user_id = parts[2]
        entry = _find_in_category(config, "protected", user_id)
        if entry:
            entry["mute"] = not entry.get("mute", False)
            save_config(config)
            config = load_config()
            entry = _find_in_category(config, "protected", user_id)
        text = format_user_info("protected", entry, user_id)
        reply_markup = user_detail_keyboard("protected", entry, user_id)

    elif action == "exc":
        await query.edit_message_text(
            text="Добро пожаловать в панель управления Свинья-6.Центр управления системой защиты Свинья-6. Здесь доступны настройки, мониторинг, управление сервисами, сертификатами и внутренней инфраструктурой.\n\nОбработка...",
            parse_mode="HTML",
            reply_markup=reply_markup,
        )
        user_id = parts[2]
        entry = _find_in_category(config, "protected", user_id)
        if entry:
            entry["EXCOMMUNICADO"] = not entry.get("EXCOMMUNICADO", False)
            save_config(config)
            config = load_config()
            entry = _find_in_category(config, "protected", user_id)

        if entry.get("EXCOMMUNICADO") == True:
            name = entry["name"] + entry["uuid"]
            await tools.EXCOMMUNICADO(context=context, msg=None, targetname=name)
            return

        text = format_user_info("protected", entry, user_id)
        reply_markup = user_detail_keyboard("protected", entry, user_id)

    elif action == "role":
        user_id, role = parts[2], parts[3]
        entry = _find_in_category(config, "signed", user_id)
        if entry and role in ROLES:
            entry["role"] = role
            save_config(config)
            config = load_config()
            entry = _find_in_category(config, "signed", user_id)
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
                if ch in shadow:
                    shadow.discard(ch)
                else:
                    shadow.add(ch)
                entry["shadow"] = sorted(shadow)
                save_config(config)
                config = load_config()
                entry = _find_in_category(config, "signed", user_id)
        text = format_user_info("signed", entry, user_id)
        reply_markup = user_detail_keyboard("signed", entry, user_id)

    await query.answer()

    await query.edit_message_text(
        text=text,
        parse_mode="HTML",
        reply_markup=reply_markup,
    )


async def showpanel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not await check_id(msg.from_user.id, msg, context):
        return

    await msg.reply_text(
        text=MAIN_TEXT,
        parse_mode="HTML",
        reply_markup=main_keyboard(),
    )
