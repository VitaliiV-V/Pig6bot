import ast
import copy
import hashlib
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

from telegram import Update, User
from telegram.error import Forbidden
from telegram.ext import (
    Application, ApplicationHandlerStop, CallbackQueryHandler, CommandHandler,
    MessageHandler, filters,
)

from bot import access, moderation


class AccessCodeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.state = {
            "root_users": [1], "blocked_user_ids": [123, "456"],
            "ban_messages": "all", "mode": "normal",
            "admins": [
                {"channel_id": -10, "id": "123", "name": "First", "mute": True, "EXCOMMUNICADO": True},
                {"channel_id": -11, "id": 123, "name": "Second", "mute": True},
                {"channel_id": -20, "id": 456, "name": "Other", "mute": True, "EXCOMMUNICADO": True},
            ],
            "alpha_users": [{"channel_id": -12, "id": 123, "name": "Alpha", "mute": True}],
            "signed_users": {"123": {"username": "signer", "channels": ["Signed channel"]}},
            "banned_profiles": ["protected:-10", "alpha:-12", "signed:123", "shadow:-13", "signature:First", "shadow:-23"],
            "banned_users": ["First" + chr(0xE0101), "Signed channel", "123", "Other"],
        }
        self.load = Mock(side_effect=lambda: copy.deepcopy(self.state))
        self.save = Mock(side_effect=self.persist)
        self.shadow_state = {"channels": {
            "-13": {"channel_id": -13, "owner": {"id": 123}, "enabled": False},
            "-23": {"channel_id": -23, "owner": {"id": 456}, "enabled": True},
        }}
        self.store = Mock(read=Mock(return_value=copy.deepcopy(self.shadow_state)))
        patcher = patch.dict("sys.modules", {
            "config.config": SimpleNamespace(load_config=self.load, save_config=self.save),
            "bot.shadow": SimpleNamespace(store=self.store),
        })
        patcher.start()
        self.addCleanup(patcher.stop)
        self.codes = {"admin": "a" * 64, "unban": "b" * 64}
        patcher = patch.object(access, "_CODE_DIGESTS", {
            action: hashlib.sha256(code.encode()).hexdigest() for action, code in self.codes.items()
        })
        patcher.start()
        self.addCleanup(patcher.stop)
        moderation._recent_messages.clear()
        self.addCleanup(moderation._recent_messages.clear)
        self.context = SimpleNamespace(bot=SimpleNamespace(send_message=AsyncMock()))

    def persist(self, config):
        self.state = copy.deepcopy(config)

    def update(self, text, user_id=123, chat_type="private", chat_id=None):
        msg = SimpleNamespace(text=text, from_user=SimpleNamespace(id=user_id, is_bot=False),
                              chat=SimpleNamespace(type=chat_type, id=user_id if chat_id is None else chat_id),
                              reply_text=AsyncMock())
        return SimpleNamespace(message=msg)

    async def redeem(self, update):
        with self.assertRaises(ApplicationHandlerStop):
            await access.access_code_handler(update, self.context)

    def test_only_bare_codes_match_with_optional_surrounding_whitespace(self):
        for action, code in self.codes.items():
            self.assertEqual(access.access_code_action(code), action)
            self.assertEqual(access.access_code_action(f"  {code}\n"), action)
            for text in (action, f"{action}: {code}", f"{action} {code}", code.upper(), code + "0"):
                self.assertIsNone(access.access_code_action(text))

    async def test_admin_code_persists_root_access_without_duplicates(self):
        update = self.update(self.codes["admin"])
        await self.redeem(update)
        await self.redeem(update)
        self.assertEqual(self.state["root_users"], [1, 123])
        self.assertEqual(self.state["blocked_user_ids"], [123, "456"])
        self.save.assert_called_once()
        self.assertIn("/panel", update.message.reply_text.call_args.args[0])

    async def test_unban_clears_all_own_profiles_preserving_every_other_owner(self):
        moderation._recent_messages.extend([(1, -100, "user:123", 1), (1, -100, "user:456", 2)])
        other = copy.deepcopy(self.state["admins"][2])
        update = self.update(self.codes["unban"])
        await self.redeem(update)
        self.assertEqual(self.state["blocked_user_ids"], ["456"])
        self.assertEqual(self.state["banned_profiles"], ["shadow:-23"])
        self.assertEqual(self.state["banned_users"], ["Other"])
        for entry in self.state["admins"][:2] + self.state["alpha_users"]:
            self.assertFalse(entry.get("mute"))
            self.assertFalse(entry.get("EXCOMMUNICADO"))
        self.assertEqual(self.state["admins"][2], other)
        self.assertEqual(self.state["root_users"], [1])
        self.assertEqual(self.state["ban_messages"], "all")
        self.assertEqual(self.store.read.return_value, self.shadow_state)
        self.assertEqual(list(moderation._recent_messages), [(1, -100, "user:456", 2)])
        self.assertIn("сняты", update.message.reply_text.call_args.args[0])
        await self.redeem(update)
        self.save.assert_called_once()
        self.assertIn("нет блокировок", update.message.reply_text.call_args.args[0])

    async def test_legacy_shared_name_bans_still_block_other_owner(self):
        self.state["admins"][2]["name"] = "First"
        await self.redeem(self.update(self.codes["unban"]))
        self.assertNotIn("signature:First", self.state["banned_profiles"])
        self.assertIn("protected:-20", self.state["banned_profiles"])
        self.assertFalse(moderation.profile_is_blocked(
            self.state, moderation.profile_from_entry("protected", self.state["admins"][0], -10)))

    async def test_codes_cannot_be_redeemed_from_group_channel_or_another_user_chat(self):
        for update in (self.update(self.codes["admin"], chat_type="group", chat_id=-10),
                       self.update(self.codes["unban"], chat_type="channel", chat_id=-11),
                       self.update(self.codes["admin"], chat_id=456)):
            await access.access_code_handler(update, self.context)
            update.message.reply_text.assert_not_awaited()
        bot_update = self.update(self.codes["admin"])
        bot_update.message.from_user.is_bot = True
        await access.access_code_handler(bot_update, self.context)
        await access.access_code_handler(SimpleNamespace(message=None), self.context)
        self.load.assert_not_called()
        self.save.assert_not_called()

    async def test_ordinary_messages_and_action_names_continue_without_side_effects(self):
        for text in ("hello", "admin", "unban", None, f"admin: {self.codes['admin']}"):
            update = self.update(text)
            await access.access_code_handler(update, self.context)
            update.message.reply_text.assert_not_awaited()
        self.load.assert_not_called()

    async def test_save_failure_does_not_report_success_or_log_code(self):
        self.save.side_effect = OSError("disk full")
        update = self.update(self.codes["admin"])
        with self.assertLogs("bot.access", level="ERROR") as logs:
            await self.redeem(update)
        self.assertNotIn(self.codes["admin"], " ".join(logs.output))
        self.assertEqual(self.state["root_users"], [1])
        self.assertIn("Не удалось", update.message.reply_text.call_args.args[0])

    async def test_failed_reply_preserves_applied_access_and_stops_dispatch(self):
        update = self.update(self.codes["admin"])
        update.message.reply_text.side_effect = Forbidden("Blocked")
        with self.assertLogs("bot.access", level="WARNING"):
            await self.redeem(update)
        self.assertIn(123, self.state["root_users"])

    async def test_main_dispatch_consumes_code_and_preserves_ordinary_private_messages(self):
        source = ast.parse(Path("main.py").read_text(encoding="utf-8"))
        registrations = [node for node in source.body if isinstance(node, ast.Expr)
                         and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Attribute)
                         and node.value.func.attr == "add_handler"]
        app = Application.builder().token("123456:TEST-TOKEN").build()
        env = {"app": app, "filters": filters, "MessageHandler": MessageHandler,
               "CommandHandler": CommandHandler, "CallbackQueryHandler": CallbackQueryHandler}
        for node in registrations:
            handler = node.value.args[0]
            callback = handler.args[0] if handler.func.id == "CallbackQueryHandler" else handler.args[1]
            env[callback.id] = AsyncMock()
        env["access_code_handler"] = access.access_code_handler
        exec(compile(ast.Module(body=registrations, type_ignores=[]), "main.py", "exec"), env)
        app._initialized = True
        app.bot._bot_user = User(999, "Test", True, username="testbot")
        def telegram_update(text):
            return Update.de_json({"update_id": 1, "message": {
                "message_id": 1, "date": 1, "chat": {"id": 123, "type": "private"},
                "from": {"id": 123, "first_name": "User", "is_bot": False}, "text": text,
            }}, app.bot)
        with patch.object(type(app.bot), "send_message", new_callable=AsyncMock):
            await app.process_update(telegram_update(self.codes["admin"]))
        self.assertIn(123, self.state["root_users"])
        env["author_handler"].assert_not_awaited()
        env["track_private_user"].assert_not_awaited()
        await app.process_update(telegram_update("ordinary message"))
        env["author_handler"].assert_awaited_once()
        env["track_private_user"].assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
