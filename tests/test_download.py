import ast
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, MessageEntity, Update
from telegram.ext import ContextTypes


class DownloadTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Import only these handlers: the full module initializes unrelated services.
        source = ast.parse(Path("bot/handlers.py").read_text())
        handlers = [node for node in source.body if isinstance(node, ast.AsyncFunctionDef)
                    and node.name in ("download_handler", "buttons_handler", "check_id")]
        self.environment = {
            "Update": Update, "ContextTypes": ContextTypes, "os": os, "json": json,
            "secrets": SimpleNamespace(token_hex=lambda size: "test-request"),
            "InlineKeyboardButton": InlineKeyboardButton, "InlineKeyboardMarkup": InlineKeyboardMarkup,
            "MessageEntity": MessageEntity, "OWNER_ID": 1, "OWNER_USERNAME": "@owner",
            "load_config": Mock(return_value={"root_users": [100]}),
        }
        exec(compile(ast.Module(body=handlers, type_ignores=[]), "bot/handlers.py", "exec"), self.environment)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.addCleanup(os.chdir, os.getcwd())
        os.chdir(self.temp.name)
        Path("tmp").mkdir()
        self.allowed = Path("tmp/allowed_messages.json")
        self.allowed.write_text(json.dumps({"messages": []}))
        self.bot = SimpleNamespace(**{name: AsyncMock() for name in (
            "send_message", "send_animation", "send_photo", "send_video", "send_sticker",
            "send_video_note", "send_voice",
        )})
        self.context = SimpleNamespace(bot=self.bot)

    def command(self, user_id=200, text="Текст 🙂\n<b>Без HTML-разметки</b>", entities=(), **media):
        original = SimpleNamespace(message_id=42, text=text, entities=entities,
                                   animation=None, photo=[], video=None, sticker=None,
                                   video_note=None, voice=None)
        for name, value in media.items():
            setattr(original, name, value)
        msg = SimpleNamespace(chat_id=-777, from_user=SimpleNamespace(id=user_id, username="reader"),
                              reply_to_message=original, reply_text=AsyncMock())
        return SimpleNamespace(message=msg)

    async def test_allowed_text_is_sent_as_text_with_original_formatting(self):
        self.allowed.write_text(json.dumps({"messages": ["-77742"]}))
        entities = (MessageEntity("bold", 0, 5),)
        update = self.command(entities=entities)
        await self.environment["download_handler"](update, self.context)
        self.bot.send_message.assert_awaited_once_with(
            chat_id=200, text=update.message.reply_to_message.text,
            entities=list(entities), parse_mode=None,
        )
        self.bot.send_sticker.assert_not_awaited()
        self.bot.send_photo.assert_not_awaited()
        update.message.reply_text.assert_awaited_once_with("🟢 Текст отправлен Вам в личные сообщения.")
        self.assertEqual(list(Path("tmp").glob(".download_*.json")), [])

    async def test_owner_and_root_receive_text_without_approval(self):
        for user_id in (1, 100):
            with self.subTest(user_id=user_id):
                self.bot.send_message.reset_mock()
                update = self.command(user_id=user_id)
                await self.environment["download_handler"](update, self.context)
                self.assertEqual(self.bot.send_message.call_args.kwargs["chat_id"], user_id)
        self.assertEqual(list(Path("tmp").glob(".download_*.json")), [])

    async def test_text_request_requires_approval_and_survives_json_roundtrip(self):
        entities = (MessageEntity("text_link", 0, 5, url="https://example.com"),)
        update = self.command(entities=entities)
        await self.environment["download_handler"](update, self.context)
        self.bot.send_message.assert_not_awaited()
        request_path = Path("tmp/.download_test-request.json")
        request = json.loads(request_path.read_text())
        self.assertEqual(request["text"], update.message.reply_to_message.text)
        self.assertEqual(request["entities"], [entity.to_dict() for entity in entities])
        keyboard = update.message.reply_text.call_args.kwargs["reply_markup"]
        query = SimpleNamespace(data=keyboard.inline_keyboard[0][0].callback_data,
                                from_user=SimpleNamespace(id=100),
                                edit_message_text=AsyncMock(), answer=AsyncMock())
        await self.environment["buttons_handler"](SimpleNamespace(callback_query=query), self.context)
        self.bot.send_message.assert_awaited_once_with(
            chat_id=200, text=request["text"], entities=list(entities), parse_mode=None,
        )
        query.edit_message_text.assert_awaited_once_with("🟢 Текст отправлен Вам в личные сообщения.")
        self.assertIn(request["id"], json.loads(self.allowed.read_text())["messages"])

    async def test_non_admin_cannot_approve_text_request(self):
        await self.environment["download_handler"](self.command(), self.context)
        before = self.allowed.read_text()
        query = SimpleNamespace(data="approve^tmp/.download_test-request.json",
                                from_user=SimpleNamespace(id=200),
                                reply_text=AsyncMock(), answer=AsyncMock(), edit_message_text=AsyncMock())
        await self.environment["buttons_handler"](SimpleNamespace(callback_query=query), self.context)
        self.bot.send_message.assert_not_awaited()
        query.edit_message_text.assert_not_awaited()
        self.assertEqual(self.allowed.read_text(), before)

    async def test_existing_media_downloads_still_send_the_original_file(self):
        file = SimpleNamespace(file_id="original-file")
        for attribute, value, method, argument in (
            ("animation", file, "send_animation", "animation"),
            ("photo", [file], "send_photo", "photo"),
            ("video", file, "send_video", "video"),
            ("sticker", file, "send_sticker", "sticker"),
            ("video_note", file, "send_video_note", "video_note"),
            ("voice", file, "send_voice", "voice"),
        ):
            with self.subTest(media=attribute):
                update = self.command(user_id=100, text=None, **{attribute: value})
                await self.environment["download_handler"](update, self.context)
                kwargs = getattr(self.bot, method).call_args.kwargs
                self.assertEqual(kwargs["chat_id"], 100)
                self.assertEqual(kwargs[argument], file.file_id)
        self.bot.send_message.assert_not_awaited()

    async def test_missing_reply_or_unsupported_message_explains_usage(self):
        for original in (None, self.command(text=None).message.reply_to_message):
            with self.subTest(original=original):
                update = self.command()
                update.message.reply_to_message = original
                await self.environment["download_handler"](update, self.context)
                update.message.reply_text.assert_awaited_once()
        self.bot.send_message.assert_not_awaited()
        self.assertEqual(list(Path("tmp").glob(".download_*.json")), [])


if __name__ == "__main__":
    unittest.main()
