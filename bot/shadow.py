"""Telegram handlers for Shadow channels, subscriptions and author lookups."""

import asyncio
import html
import logging
import re
import secrets

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError
from telegram.ext import ApplicationHandlerStop

from bot.settings import MAIN_CHANNEL_ID
from config.security_policy import SECURITY_POLICY_URL, security_policy_fingerprint
from bot.shadow_store import (
    ShadowStore, daily_usage, effective_plan, ensure_subscription, grant_subscription, next_reset,
    now_moscow, parse_datetime, refund_post, reserve_post, reveal_author,
)

logger = logging.getLogger(__name__)
store = ShadowStore()
channel_lock = asyncio.Lock()
QUOTA_BAR_WIDTH = 20
SUBSCRIPTION_TERMS_VERSION = 2
SUBSCRIPTION_TERMS = (
    "<blockquote><b>ВНИМАТЕЛЬНО ПРОЧИТАЙТЕ УСЛОВИЯ ПОДПИСКИ</b>\n"
    "Принимая условия, вы подтверждаете статус администратора и соглашаетесь "
    "с правилами подписки и безопасности канала.</blockquote>\n\n"
    "<b>Лицензионные условия сервиса «Анонимные публикации»</b>\n"
    "Условия предоставления подписки.\n\n"
    "<b>1. Статус пользователя.</b>\n"
    "Принимая настоящие условия и приобретая подписку, пользователь подтверждает, что является администратором канала, "
    "в котором намерен публиковать анонимно, и обладает необходимыми полномочиями. "
    "Подписка сама по себе не предоставляет административных прав.\n\n"
    "<b>2. Предмет предоставления.</b>\n"
    "Пользователю предоставляется ограниченное, личное и непередаваемое право использования программных функций "
    "в пределах выбранного тарифа и срока подписки. Покупка не означает приобретения программного обеспечения "
    "или бессрочного права доступа.\n\n"
    "<b>3. Обязанности пользователя.</b>\n"
    "Пользователь обязуется соблюдать политику безопасности канала, не обходить защиту и лимиты, "
    "не передавать доступ третьим лицам и не злоупотреблять административными полномочиями. "
    "Анонимность не является абсолютной: авторство сохраняется и может раскрываться предусмотренными функциями сервиса.\n\n"
    "<b>4. Меры безопасности.</b>\n"
    "Несмотря на оплату подписки, при нарушении политики безопасности пользователь может быть лишён подписки, "
    "лишён части или всех административных прав, удалён из канала или заблокирован. "
    "Меры могут применяться одновременно и без предварительного предупреждения. "
    "Посты могут быть удалены без уведомления.\n\n"
    "<b>5. Возврат средств.</b>\n"
    "Добровольный возврат средств не предусмотрен ни в денежной, ни в иной форме, в том числе при неиспользовании "
    "подписки, удалении постов, отзыве доступа, снятии административных прав или удалении из канала за нарушение правил. "
    "Это положение не исключает возвратов, обязательных по применимому законодательству.\n\n"
    "<b>6. Ограничение гарантий.</b>\n"
    "Программные функции предоставляются «как есть» и по мере доступности. "
    "Подписка не гарантирует непрерывную работу, сохранность публикаций, членство в канале или сохранение полномочий.\n\n"
    "<b>7. Принятие условий.</b>\n"
    "Нажимая «Подтверждаю и принимаю», пользователь подтверждает свой статус администратора, "
    "ознакомление с настоящими условиями и политикой безопасности и согласие соблюдать их.\n\n"
    f'<a href="{SECURITY_POLICY_URL}">Политика безопасности канала — полный документ</a>'
)
POST_LINK = re.compile(
    r"(?:https?://)?(?:www\.)?t\.me/(?:s/)?(?P<chat>c/\d+|[A-Za-z][A-Za-z0-9_]*)/(?P<message>[1-9]\d*)(?:\?[^\s<>]*)?(?=$|[\s<>])"
)


def new_uuid():
    return "".join(chr(secrets.randbelow(240) + 0xE0100) for _ in range(5))


def is_invisible_title(title):
    return bool(title) and all(0xE0100 <= ord(char) < 0xE01F0 for char in title)


def channel_name(data, previous=None):
    if previous and is_invisible_title(previous["name"]):
        return previous["name"]
    names = {channel["name"] for channel in data["channels"].values()}
    name = new_uuid()
    while name in names:
        name = new_uuid()
    return name


async def migrate_shadow_channels(application):
    """Remove visible titles from previously registered channels on bot startup."""
    async with channel_lock:
        state = store.read()
        for key, channel in state["channels"].items():
            if is_invisible_title(channel["name"]) and is_invisible_title(channel["uuid"]):
                continue
            name, uuid = channel_name(state, channel), new_uuid()
            try:
                await application.bot.set_chat_title(channel["channel_id"], name + uuid)
            except TelegramError:
                logger.exception("Unable to migrate Shadow channel %s", channel["channel_id"])
                with store.transaction() as data:
                    data["channels"][key]["enabled"] = False
                await notify_owner(application, channel["owner"]["id"], "Не удалось обновить название канала. Разрешите боту менять информацию канала и опубликуйте Shadow ещё раз.")
                continue
            with store.transaction() as data:
                data["channels"][key].update(name=name, uuid=uuid)
            channel.update(name=name, uuid=uuid)


def owner_info(user):
    return {"id": user.id, "name": user.full_name, "username": user.username}


def reset_text(now):
    minutes = max(1, int((next_reset(now) - now).total_seconds() + 59) // 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours} ч {minutes} мин (00:00 МСК)"


def quota_lines(data, usage, plan, bars=False):
    lines = []
    limits = data["plans"][plan]
    for label, limit_key, used_key in (
        ("Анонимные посты", "posts_per_day", "posts"),
        ("Просмотры авторства", "views_per_day", "views"),
    ):
        limit = limits[limit_key]
        remaining = max(0, limit - usage[used_key])
        lines.append(f"{label}: {remaining} из {limit} осталось сегодня")
        if bars:
            filled = min(QUOTA_BAR_WIDTH, remaining * QUOTA_BAR_WIDTH // limit) if limit else 0
            lines.append(f"<code>{'▓' * filled}{'░' * (QUOTA_BAR_WIDTH - filled)}</code>")
    return lines


async def track_private_user(update, context):
    msg = update.message
    if not msg or msg.chat.type != "private" or not msg.from_user or msg.from_user.is_bot:
        return
    if str(msg.from_user.id) not in store.read()["subscriptions"]:
        with store.transaction() as data:
            ensure_subscription(data, msg.from_user.id, now_moscow())


def subscription_view(user_id):
    now = now_moscow()
    with store.transaction() as data:
        plan = effective_plan(data, user_id, now)
        usage = daily_usage(data, user_id, now)
        subscription = data["subscriptions"][str(user_id)]
        expires_at = subscription.get("expires_at")
        lines = [
            "<b>Анонимные публикации</b>",
            f"\nТекущая подписка: <b>{html.escape(plan)}</b>",
        ]
        if plan != "Free":
            if plan == "Plus" and expires_at == subscription.get("trial_expires_at") and expires_at:
                lines.append("Plus бесплатно на месяц для новых пользователей.")
            if expires_at:
                expiry = parse_datetime(expires_at).strftime("%d.%m.%Y %H:%M МСК")
                lines.append(f"Действует до: {expiry}")
            else:
                lines.append("Без срока действия.")
        elif expires_at and parse_datetime(expires_at) <= now:
            lines.append("Срок подписки завершён. Сейчас действует Free.")
        else:
            lines.append("Без срока действия.")
        lines.append("")
        lines += quota_lines(data, usage, plan, bars=True)
        lines += [
            f"\nДо обновления лимитов: {reset_text(now)}",
            "\nЧтобы узнать автора, отправьте ссылку на Shadow-пост.",
        ]
    return "\n".join(lines), InlineKeyboardMarkup([
        [InlineKeyboardButton("Изменить подписку", callback_data="sub^change", style="primary")],
    ])


async def sub_handler(update, context):
    msg = update.effective_message
    if not msg or msg.chat.type != "private":
        return
    text, keyboard = subscription_view(msg.from_user.id)
    await msg.reply_text(text, parse_mode="HTML", reply_markup=keyboard)


async def sub_buttons_handler(update, context):
    query = update.callback_query
    if not query or not query.message:
        return
    if query.message.chat.type != "private" or query.message.chat.id != query.from_user.id:
        await query.answer("Откройте /sub в личной переписке с ботом.", show_alert=True)
        return
    action = query.data.split("^")[-1]
    if action not in ("change", "accept", "back"):
        await query.answer("Откройте /sub ещё раз.", show_alert=True)
        return
    await query.answer()
    if action == "change":
        text = SUBSCRIPTION_TERMS
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Подтверждаю и принимаю", callback_data="sub^accept", style="success")],
            [InlineKeyboardButton("Политика безопасности", url=SECURITY_POLICY_URL)],
            [InlineKeyboardButton("К подписке", callback_data="sub^back")],
        ])
    elif action == "accept":
        accepted_at = now_moscow().isoformat()
        policy_fingerprint = security_policy_fingerprint()
        with store.transaction() as data:
            subscription = ensure_subscription(data, query.from_user.id, parse_datetime(accepted_at))
            subscription["terms_accepted_at"] = accepted_at
            subscription["terms_version"] = SUBSCRIPTION_TERMS_VERSION
            subscription["administrator_confirmed_at"] = accepted_at
            subscription["security_policy_url"] = SECURITY_POLICY_URL
            subscription["security_policy_sha256"] = policy_fingerprint
            lines = ["<b>Выберите подписку</b>", "\nЛимиты в день: посты / просмотры авторства.", ""]
            for name, quota in data["plans"].items():
                lines.append(f"<b>{html.escape(name)}</b> · {quota['posts_per_day']} / {quota['views_per_day']}")
        lines += [
            "\nДля покупки нажмите кнопку нужной подписки и отправьте любое сообщение в открывшийся чат. Подписка будет подключена или продлена на месяц.",
            "Ultra подключает администратор.",
        ]
        text = "\n".join(lines)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Plus", url="https://t.me/pig6storeplus?direct", style="primary")],
            [InlineKeyboardButton("Pro x5", url="https://t.me/pig6store_pro_x5?direct", style="primary")],
            [InlineKeyboardButton("Pro x20", url="https://t.me/pig6store_pro_x20?direct", style="primary")],
            [InlineKeyboardButton("К подписке", callback_data="sub^back")],
        ])
    else:
        text, keyboard = subscription_view(query.from_user.id)
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)


async def shop_message_handler(update, context):
    """Run before commands so even a command sent to a store buys a month."""
    msg = update.message
    if not msg or not getattr(msg.chat, "is_direct_messages", False):
        return
    topic = getattr(msg, "direct_messages_topic", None)
    user = getattr(topic, "user", None)
    if not user or not msg.from_user or msg.from_user.id != user.id or user.is_bot:
        return
    chat = await context.bot.get_chat(msg.chat_id)
    parent = getattr(chat, "parent_chat", None)
    if not parent:
        return
    if not parent.username:
        parent = await context.bot.get_chat(parent.id)
    if not parent.username:
        return
    now = now_moscow()
    with store.transaction() as data:
        plan = data["stores"].get(parent.username.lower())
        if plan is None:
            return
        result = grant_subscription(data, user.id, plan, f"{msg.chat_id}:{msg.message_id}", now)
    expiry = parse_datetime(result["expires_at"]).strftime("%d.%m.%Y %H:%M МСК")
    await context.bot.send_message(
        chat_id=msg.chat_id,
        direct_messages_topic_id=topic.topic_id,
        reply_to_message_id=msg.message_id,
        text=f"Подписка {result['plan']} подключена.\nДействует до {expiry}.\n\nВаши лимиты — в /sub у бота.",
    )
    raise ApplicationHandlerStop


async def register_shadow(context, msg, config):
    if (msg.text or msg.caption or "").strip().casefold() != "shadow":
        return False
    if msg.chat.type != "channel":
        return False
    if any(entry.get("channel_id") == msg.chat_id
           for category in ("admins", "alpha_users") for entry in config.get(category, [])):
        await msg.reply_text("В канале уже действует обычная защита. Отключите её командой unprotect, затем опубликуйте Shadow.")
        return True
    async with channel_lock:
        admins = await context.bot.get_chat_administrators(msg.chat_id)
        humans = [admin for admin in admins if not admin.user.is_bot]
        if len(humans) != 1 or humans[0].status not in ("creator", "owner"):
            await msg.reply_text("Для подключения оставьте в администраторах только владельца канала и бота. Затем опубликуйте Shadow ещё раз.")
            return True
        bot_admin = next((admin for admin in admins if admin.user.id == context.bot.id), None)
        if not bot_admin or not getattr(bot_admin, "can_change_info", False):
            await msg.reply_text("Разрешите боту менять информацию канала. Затем опубликуйте Shadow ещё раз.")
            return True
        state = store.read()
        previous = state["channels"].get(str(msg.chat_id))
        channel = {
            "channel_id": msg.chat_id,
            "owner": owner_info(humans[0].user),
            "name": channel_name(state, previous),
            "uuid": new_uuid(),
            "enabled": True,
        }
        # Persist only after Telegram confirms that the protected title is set.
        try:
            await context.bot.set_chat_title(msg.chat_id, channel["name"] + channel["uuid"])
        except TelegramError:
            logger.exception("Unable to register Shadow channel %s", msg.chat_id)
            await msg.reply_text("Не удалось изменить название канала. Проверьте права бота и опубликуйте Shadow ещё раз.")
            return True
        with store.transaction() as data:
            data["channels"][str(msg.chat_id)] = channel
            ensure_subscription(data, channel["owner"]["id"], now_moscow())
        await msg.reply_text("Анонимные публикации подключены.\n\nПубликуйте в основном канале от имени этого канала. Ваши лимиты — в /sub у бота.")
    return True


async def delete_shadow_post(context, msg):
    await context.bot.delete_message(chat_id=msg.chat_id, message_id=msg.message_id)


async def notify_owner(context, owner_id, text):
    try:
        await context.bot.send_message(chat_id=owner_id, text=text)
    except TelegramError:
        logger.info("Could not notify Shadow owner %s", owner_id)


async def check_shadow_post(context, msg, config, edited=False):
    """Return True whenever the post belongs to Shadow, including rejected forgeries."""
    async with channel_lock:
        data = store.read()
        sender = msg.sender_chat
        signature = msg.author_signature or ""
        if not signature and sender and sender.id != MAIN_CHANNEL_ID:
            signature = sender.title or ""
        channel = data["channels"].get(str(sender.id)) if sender else None
        if channel is None:
            channel = next((entry for entry in data["channels"].values()
                            if entry["name"] and signature.startswith(entry["name"])), None)
        key = f"{msg.chat_id}:{msg.message_id}"
        recorded = data["posts"].get(key)
        if channel is None and recorded:
            channel = data["channels"].get(str(recorded["channel_id"]))
        if channel is None:
            if signature.startswith("Shadow ") or (len(signature) == 10 and is_invisible_title(signature)):
                await delete_shadow_post(context, msg)
                return True
            return False
        if sender and sender.id not in (MAIN_CHANNEL_ID, channel["channel_id"]):
            await delete_shadow_post(context, msg)
            return True
        valid = channel["enabled"] and signature == channel["name"] + channel["uuid"]
        # Edits and later album items legitimately retain the original signature.
        album = next((post for post in data["posts"].values()
                      if msg.media_group_id and post.get("media_group_id") == msg.media_group_id
                      and post["chat_id"] == msg.chat_id and post["channel_id"] == channel["channel_id"]
                      and post["signature"] == signature), None)
        if recorded:
            valid = channel["enabled"] and (valid or recorded["signature"] == signature)
        if album:
            valid = channel["enabled"]
        if not valid or (edited and not recorded):
            await delete_shadow_post(context, msg)
            return True
        owner_id = channel["owner"]["id"]
        if config.get("mode", "normal") != "normal" or config.get("ban_messages") == "all":
            await delete_shadow_post(context, msg)
            return True
        # Shadow remains subject to manual content filtering and banned GIFs.
        from bot.censor import check
        if (config.get("ban_messages") == "manual" and check(msg.text or msg.caption or "")) or (
            msg.animation and msg.animation.file_id in config.get("bad_gifs", [])
        ):
            await delete_shadow_post(context, msg)
            return True
        if recorded:
            return True
        now = now_moscow()
        name = channel_name(data, channel)
        uuid = new_uuid()
        with store.transaction() as data:
            # Re-read subscription settings immediately before spending a quota.
            result = reserve_post(data, channel, msg.chat_id, msg.message_id, now, msg.media_group_id)
            if result == "accepted" and album:
                data["posts"][key]["signature"] = signature
            elif result == "accepted":
                # Commit the next nonce first: a crash or timeout must never
                # leave the previous signature reusable after publication.
                data["channels"][str(channel["channel_id"])]["name"] = name
                data["channels"][str(channel["channel_id"])]["uuid"] = uuid
        if result == "limit":
            await delete_shadow_post(context, msg)
            await notify_owner(context, owner_id, f"Публикации на сегодня закончились.\nЛимит обновится через {reset_text(now)}.\n\nИзменить подписку можно в /sub.")
            return True
        if result == "existing" or album:
            return True
        try:
            await context.bot.set_chat_title(channel["channel_id"], name + uuid)
        except TelegramError:
            logger.exception("Unable to rotate Shadow channel %s", channel["channel_id"])
            with store.transaction() as data:
                refund_post(data, key, now)
                data["channels"][str(channel["channel_id"])]["enabled"] = False
            await delete_shadow_post(context, msg)
            await notify_owner(context, owner_id, "Защита канала приостановлена.\nНе удалось обновить его название.\n\nПроверьте права бота и опубликуйте Shadow ещё раз. Пост удалён, лимит не потрачен.")
            return True
    return True


async def author_handler(update, context):
    msg = update.message
    if not msg or msg.chat.type != "private":
        return
    text = msg.text or ""
    match = POST_LINK.search(text)
    if not match:
        if "t.me/" in text:
            await msg.reply_text("Нужна ссылка на отдельный пост.\nНапример: https://t.me/channel/123 или https://t.me/c/1234567890/123.")
        return
    chat_ref = match["chat"]
    if chat_ref.startswith("c/"):
        chat_id = int("-100" + chat_ref[2:])
    else:
        try:
            chat = await context.bot.get_chat("@" + chat_ref)
            chat_id = chat.id
        except TelegramError:
            await msg.reply_text("Не удалось найти канал по ссылке.")
            return
    if chat_id != MAIN_CHANNEL_ID:
        await msg.reply_text("Узнать автора можно только у Shadow-поста из основного канала.")
        return
    key = f"{chat_id}:{int(match['message'])}"
    now = now_moscow()
    with store.transaction() as data:
        result, owner = reveal_author(data, msg.from_user.id, key, now)
    if result == "unknown":
        await msg.reply_text("Автор этого поста неизвестен.\nИнформация сохраняется для новых анонимных публикаций.")
    elif result == "limit":
        await msg.reply_text(f"Нет доступных просмотров авторства.\nЛимит обновится через {reset_text(now)}.\n\nВыбрать другой план можно в /sub.")
    else:
        name = html.escape(owner["name"])
        username = f" (@{html.escape(owner['username'])})" if owner.get("username") else ""
        try:
            await msg.reply_text(
                f"Автор: <a href=\"tg://user?id={owner['id']}\">{name}</a>{username}",
                parse_mode="HTML",
            )
        except TelegramError:
            # A failed disclosure must not consume the daily view or become free later.
            if result == "revealed":
                with store.transaction() as data:
                    revealed = data["subscriptions"][str(msg.from_user.id)]["revealed_posts"]
                    if key in revealed:
                        revealed.remove(key)
                        usage = daily_usage(data, msg.from_user.id, now)
                        usage["views"] = max(0, usage["views"] - 1)
            raise
