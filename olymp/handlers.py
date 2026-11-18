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


async def olymp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    parts = query.data.split("^")
    action = parts[1] if len(parts) > 1 else None
    config = load_config()
    if action == "all":
        await olymp_handler_all(update, context)
    elif action == "my":
        await olymp_handler_my(update, context)
    elif action == "settings":
        await olymp_handler_settings(update, context)
    elif action == "main":
        await olymp_handler_main(update, context)


async def olymp_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📅  Все олимпиады", callback_data="olymp^all")],
            [InlineKeyboardButton("⭐  Мои олимпиады", callback_data="olymp^my")],
            [InlineKeyboardButton("⚙️  Настройки", callback_data="olymp^settings")],
        ]
    )

    await msg.reply_text(
        text="""Свинья-6 — Ваш олимпиадный календарь
        
Все важные даты олимпиад по информатике — в одном месте.
    
Выбирайте олимпиады, которые хочешь отслеживать, а Свинья-6 напомнит Вам о регистрации и предстоящих этапах заранее.
        """,
        parse_mode="HTML",
        reply_markup=keyboard,
    )


async def olymp_handler_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📅  Все олимпиады", callback_data="olymp^all")],
            [InlineKeyboardButton("⭐  Мои олимпиады", callback_data="olymp^my")],
            [InlineKeyboardButton("⚙️  Настройки", callback_data="olymp^settings")],
        ]
    )

    await query.edit_message_text(
        text="""Свинья-6 — Ваш олимпиадный календарь
        
Все важные даты олимпиад по информатике — в одном месте.
    
Выбирайте олимпиады, которые хочешь отслеживать, а Свинья-6 напомнит Вам о регистрации и предстоящих этапах заранее.
        """,
        parse_mode="HTML",
        reply_markup=keyboard,
    )


async def olymp_handler_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    buttons = []
    with open("olymps.json", "r", encoding="utf-8") as f:
        olymp_data = json.load(f)
    for i in olymp_data["list"]:
        buttons.append(
            [
                InlineKeyboardButton(
                    f"{i['name']}",
                    callback_data=f"olymp^{i['id']}",
                )
            ]
        )
    buttons.append([InlineKeyboardButton("⬅️  Назад", callback_data="olymp^main")])
    keyboard = InlineKeyboardMarkup(buttons)

    await query.edit_message_text(
        text="""Все олимпиады:
        """,
        parse_mode="HTML",
        reply_markup=keyboard,
    )


async def olymp_handler_my(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    buttons = []
    with open("olymps.json", "r", encoding="utf-8") as f:
        olymp_data = json.load(f)
    for i in olymp_data["list"]:
        buttons.append(
            [
                InlineKeyboardButton(
                    f"{i['name']}",
                    callback_data=f"olymp^{i['id']}",
                )
            ]
        )
    buttons.append([InlineKeyboardButton("⬅️  Назад", callback_data="olymp^main")])
    keyboard = InlineKeyboardMarkup(buttons)

    await query.edit_message_text(
        text="""Ваши олимпиады:
        """,
        parse_mode="HTML",
        reply_markup=keyboard,
    )


async def olymp_handler_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pass
