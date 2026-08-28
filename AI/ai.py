import json
import re

import bot.tools as tools
from config.config import *
from AI.jarvis import Jarvis
from bot.settings import *
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters,
)

from bot.censor import *
from bot.protection import *
from economy.p6economy import *

jarvis = Jarvis()

command_detector = Jarvis()


COMMAND_DETECTOR_PROMPT = r"""
Ты — Command Detector для Telegram-бота "P-6 AI".

Твоя задача — НЕ отвечать пользователю и НЕ выполнять команды.

Твоя единственная задача:
определить, содержит ли переданный текст команду управления
Telegram-ботом.

Ты должен вернуть строго JSON.

==================================================
ДОСТУПНЫЕ КОМАНДЫ
==================================================

1. set_base_prompt

Пользователь хочет изменить базовый системный промпт Джарвиса.

Примеры:

"Джарвис установи базовый промпт Ты полезный ассистент"

"установи базовый промпт Отвечай кратко"

"поставь новый базовый промпт Будь умным AI"

Аргумент:
новый текст промпта.

--------------------------------------------------

2. get_base_prompt

Пользователь хочет посмотреть текущий базовый промпт.

Примеры:

"Джарвис покажи базовый промпт"

"какой сейчас базовый промпт"

"покажи системный промпт Джарвиса"

Аргументы отсутствуют.

--------------------------------------------------

3. restart

Пользователь хочет перезапустить Джарвиса.

Примеры:

"Джарвис рестарт"

"Джарвис перезагрузка"

"перезапусти Джарвиса"

"перезагрузи бота"

Аргументы отсутствуют.

--------------------------------------------------

4. enable_logs

Пользователь хочет включить логи.

Примеры:

"Джарвис включи логи"

"включи логирование"

"активируй логи"

Аргументы отсутствуют.

--------------------------------------------------

5. ban_all

Пользователь хочет включить удаление всех сообщений.

Примеры:

"Джарвис банить все"

"удаляй все сообщения"

"включи удаление всех сообщений"

Аргументы отсутствуют.

--------------------------------------------------

6. ban_filtered

Пользователь хочет включить удаление сообщений
по фильтру.

Примеры:

"Джарвис банить по фильтру"

"включи бан по фильтру"

"удаляй сообщения по фильтру"

Аргументы отсутствуют.

--------------------------------------------------

7. ban_off

Пользователь хочет отключить удаление сообщений.

Примеры:

"Джарвис не банить"

"отключи бан"

"не удаляй сообщения"

"отключи удаление сообщений"

Аргументы отсутствуют.

--------------------------------------------------

8. judgment_day

Пользователь хочет переключить режим "Судный день".

Примеры:

"Джарвис судный день"

"включи судный день"

"активируй режим судного дня"

Аргументы отсутствуют.

==================================================
ЧТО НЕ ЯВЛЯЕТСЯ КОМАНДОЙ
==================================================

Обычный разговор — НЕ команда.

Например:

"Привет Джарвис"

→ NO_COMMAND

"Джарвис расскажи анекдот"

→ NO_COMMAND

"Джарвис что такое Python?"

→ NO_COMMAND

"Джарвис помоги написать Telegram бота"

→ NO_COMMAND

"Как дела?"

→ NO_COMMAND

"Расскажи про нейросети"

→ NO_COMMAND

Важно:

Само наличие слова "Джарвис" НЕ означает наличие команды.

Командой считается только действие, которое относится
к управлению самим ботом.

==================================================
ВАЖНЫЕ ПРАВИЛА
==================================================

1. Не выполняй команду.
2. Не отвечай пользователю.
3. Не объясняй свой выбор.
4. Не пиши Markdown.
5. Не пиши никакого текста кроме JSON.
6. Если команда не определена однозначно — используй NO_COMMAND.
7. Не придумывай новые типы команд.
8. Если пользователь просит обычную AI-задачу — NO_COMMAND.
9. Если команда найдена, извлеки аргументы.
10. Для set_base_prompt аргументом является весь новый промпт.

==================================================
ФОРМАТ ОТВЕТА
==================================================

Если команды нет:

{
    "result": "NO_COMMAND",
    "command": null,
    "args": null
}

Если команда есть:

{
    "result": "COMMAND",
    "command": "название_команды",
    "args": "аргументы"
}

==================================================
ПРИМЕРЫ
==================================================

Вход:

Джарвис включи логи

Ответ:

{
    "result": "COMMAND",
    "command": "enable_logs",
    "args": null
}

Вход:

Джарвис расскажи мне про Python

Ответ:

{
    "result": "NO_COMMAND",
    "command": null,
    "args": null
}

Вход:

Джарвис установи базовый промпт
Будь полезным и отвечай кратко

Ответ:

{
    "result": "COMMAND",
    "command": "set_base_prompt",
    "args": "Будь полезным и отвечай кратко"
}

Вход:

Привет Джарвис

Ответ:

{
    "result": "NO_COMMAND",
    "command": null,
    "args": null
}
"""


try:
    tools.setbaseprompt(COMMAND_DETECTOR_PROMPT)
except Exception as e:
    print(f"[COMMAND DETECTOR] Не удалось установить prompt: {e}")


app = ApplicationBuilder().token(AI_TOKEN).build()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    await update.message.reply_text("Привет! Я P-6 AI!")


async def check_id(user_id: int) -> bool:
    config = load_config()

    if user_id in config.get("root_users", []):
        return True

    if user_id == OWNER_ID:
        return True

    return False


async def detect_command(text: str) -> dict:
    """
    Отправляет сообщение отдельной нейронке
    и получает информацию о команде.
    """

    prompt = f"""
Определи, содержит ли следующий Telegram-текст
команду управления ботом.

Верни только JSON согласно твоей системной инструкции.

ТЕКСТ:

{text}
"""

    try:
        result = command_detector.query(prompt)

    except Exception as e:
        print(f"[COMMAND DETECTOR ERROR] {e}")

        return {
            "result": "NO_COMMAND",
            "command": None,
            "args": None,
        }

    if not result:
        return {
            "result": "NO_COMMAND",
            "command": None,
            "args": None,
        }

    result = result.strip()

    result = re.sub(r"^```json\s*", "", result, flags=re.IGNORECASE)

    result = re.sub(r"\s*```$", "", result)

    try:
        data = json.loads(result)

    except json.JSONDecodeError:
        print("[COMMAND DETECTOR] Некорректный JSON:")
        print(result)

        return {
            "result": "NO_COMMAND",
            "command": None,
            "args": None,
        }

    if not isinstance(data, dict):
        return {
            "result": "NO_COMMAND",
            "command": None,
            "args": None,
        }

    if data.get("result") != "COMMAND":
        return {
            "result": "NO_COMMAND",
            "command": None,
            "args": None,
        }

    allowed_commands = {
        "set_base_prompt",
        "get_base_prompt",
        "restart",
        "enable_logs",
        "ban_all",
        "ban_filtered",
        "ban_off",
        "judgment_day",
    }

    command = data.get("command")

    if command not in allowed_commands:
        print(f"[COMMAND DETECTOR] Неизвестная команда: {command}")

        return {
            "result": "NO_COMMAND",
            "command": None,
            "args": None,
        }

    return {
        "result": "COMMAND",
        "command": command,
        "args": data.get("args"),
    }


async def execute_command(msg, command_data: dict) -> bool:
    """
    Выполняет команду, которую распознала нейронка.

    True  = команда успешно обработана.
    False = ошибка/команда не выполнена.
    """

    command = command_data.get("command")
    args = command_data.get("args")

    user_id = msg.from_user.id

    if not await check_id(user_id):
        await msg.reply_text("🔴 У Вас нет прав на выполнение этой команды.")

        return True

    if command == "set_base_prompt":

        if not args:
            await msg.reply_text("🔴 Не указан новый базовый промпт.")

            return True

        try:
            tools.setbaseprompt(args)

            jarvis.restart()

            await msg.reply_text(
                "✅ Базовый промпт установлен.\n" "🔄 Джарвис перезапущен."
            )

        except Exception as e:
            print(f"[COMMAND] set_base_prompt error: {e}")

            await msg.reply_text("🔴 Ошибка при установке базового промпта.")

        return True

    if command == "get_base_prompt":

        config = load_config()

        base_prompt = config.get("base_prompt", "Базовый промпт не установлен.")

        if len(base_prompt) > 4000:
            base_prompt = base_prompt[:4000] + "\n\n...[обрезано]"

        await msg.reply_text(f"🧠 Текущий базовый промпт:\n\n{base_prompt}")

        return True

    if command == "restart":

        try:
            jarvis.restart()

            await msg.reply_text("🔄 Джарвис перезагружен.")

        except Exception as e:
            print(f"[COMMAND] restart error: {e}")

            await msg.reply_text("🔴 Не удалось перезагрузить Джарвиса.")

        return True

    if command == "enable_logs":

        config = load_config()

        config["logs_mode"] = "on"

        save_config(config)

        await msg.reply_text("📋 Логи включены.")

        return True

    if command == "ban_all":

        config = load_config()

        config["ban_messages"] = "all"

        save_config(config)

        await msg.reply_text("🗑 Все сообщения будут удаляться.")

        return True

    if command == "ban_filtered":

        config = load_config()

        config["ban_messages"] = "manual"

        save_config(config)

        await msg.reply_text("🛡 Сообщения будут удаляться по фильтру.")

        return True

    if command == "ban_off":

        config = load_config()

        config["ban_messages"] = "off"

        save_config(config)

        await msg.reply_text("✅ Удаление сообщений отключено.")

        return True

    if command == "judgment_day":

        config = load_config()

        if config.get("mode") == "normal":

            config["mode"] = "Judgment Day"

            save_config(config)

            await msg.reply_text("☠️ Судный день настал.")

        else:

            config["mode"] = "normal"

            save_config(config)

            await msg.reply_text("🕊 Судный день отменён.")

        return True

    return False


async def query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    if not msg:
        return

    if not msg.text:
        return

    text = msg.text.strip()

    if not text:
        return

    text_lower = text.lower()

    mentioned = "jarvis" in text_lower or "джарвис" in text_lower

    replied_to_bot = False

    if msg.reply_to_message:
        replied_user = msg.reply_to_message.from_user

        if replied_user:
            replied_to_bot = replied_user.id == context.bot.id

    if not mentioned and not replied_to_bot:
        return

    print()
    print("=" * 60)
    print("[COMMAND DETECTOR]")
    print(f"TEXT: {text}")

    command_data = await detect_command(text)

    print(f"RESULT: {command_data}")

    print("=" * 60)

    if command_data["result"] == "COMMAND":

        print(f"[COMMAND FOUND] " f"{command_data['command']}")

        handled = await execute_command(msg, command_data)

        if handled:
            return

    print("[COMMAND DETECTOR] Команды нет.")

    author = msg.from_user.first_name if msg.from_user else "Пользователь"

    ai_prompt = f"""
Ты — P-6 AI, Telegram-ассистент по имени Джарвис.

Пользователь написал тебе сообщение.

Автор: {author}

Сообщение:
{text}

Ответь непосредственно пользователю.

Не классифицируй его сообщение.
Не описывай его намерение.
Не говори "пользователь спрашивает".
Не объясняй, как ты анализировал сообщение.

Если это вопрос — ответь на вопрос.
Если это просьба — выполни её.
Если это обычный разговор — поддержи разговор.
"""

    try:

        ans = jarvis.query(ai_prompt)

    except Exception as e:

        print(f"[JARVIS ERROR] {e}")

        await msg.reply_text("🔴 Произошла ошибка при обращении к AI.")

        return

    if not ans:
        return

    if "rejected" in ans.lower():
        return

    await context.bot.send_message(
        chat_id=msg.chat_id, text=ans, reply_to_message_id=msg.message_id
    )


app.add_handler(CommandHandler("start", start))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, query))

app.run_polling(
    allowed_updates=[
        "message",
        "channel_post",
        "chat_member",
    ]
)
