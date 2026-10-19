import ast
import copy
import logging
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import Forbidden
from telegram.ext import ContextTypes

from bot import moderation


def load_functions(path, names, environment):
    source = ast.parse(Path(path).read_text(encoding="utf-8"))
    nodes = [node for node in source.body
             if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names]
    exec(compile(ast.Module(body=nodes, type_ignores=[]), path, "exec"), environment)
    return environment


class ModerationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        moderation._recent_messages.clear()
        self.addCleanup(moderation._recent_messages.clear)
        self.state = {
            "ban_messages": "manual", "mode": "normal", "root_users": [1],
            "admins": [
                {"channel_id": -10, "id": "123", "name": "First", "uuid": chr(0xE0101), "mute": False},
                {"channel_id": -11, "id": 123, "name": "Second", "uuid": chr(0xE0102), "mute": False},
                {"channel_id": -20, "id": "456", "name": "Other", "uuid": "", "mute": False},
            ],
        }
        self.load = Mock(side_effect=lambda: copy.deepcopy(self.state))
        self.save = Mock(side_effect=self.persist)
        self.config_module = SimpleNamespace(load_config=self.load, save_config=self.save)
        patcher = patch.dict("sys.modules", {"config.config": self.config_module})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.bot = SimpleNamespace(send_message=AsyncMock(), delete_message=AsyncMock())
        self.context = SimpleNamespace(bot=self.bot)

    def persist(self, value):
        self.state = copy.deepcopy(value)

    def profile(self, index=0):
        entry = self.state["admins"][index]
        return moderation.profile_from_entry("protected", entry, entry["channel_id"])

    def post(self, message_id=1, index=0, chat_id=-100):
        profile = self.profile(index)
        return SimpleNamespace(chat_id=chat_id, message_id=message_id, sender_chat=None,
                               author_signature=profile.name + profile.entry["uuid"],
                               text="hello", caption=None, poll=None, animation=None)

    async def test_interleaved_authors_and_rotating_profiles_only_ban_spammer(self):
        with patch.object(moderation, "monotonic", return_value=100):
            for number in range(1, 10):
                self.assertFalse(await moderation.check_flood(self.context, self.post(number), self.profile(number % 2)))
                self.assertFalse(await moderation.check_flood(self.context, self.post(100 + number, 2), self.profile(2)))
            self.assertTrue(await moderation.check_flood(self.context, self.post(10, 1), self.profile(1)))
        self.assertEqual(self.state["blocked_user_ids"], ["123"])
        self.assertEqual(self.state["ban_messages"], "manual")
        self.assertEqual(self.state["mode"], "normal")
        deleted = [call.kwargs["message_id"] for call in self.bot.delete_message.await_args_list]
        self.assertEqual(deleted, list(range(1, 11)))
        self.bot.send_message.assert_awaited_once()
        self.assertEqual(self.bot.send_message.call_args.kwargs["chat_id"], 123)
        self.assertIn("Антиспам", self.bot.send_message.call_args.kwargs["text"])

    async def test_window_chat_isolation_and_duplicate_updates(self):
        with patch.object(moderation, "monotonic", return_value=100):
            for number in range(1, 10):
                for chat in (-100, -200):
                    self.assertFalse(await moderation.check_flood(self.context, self.post(number, chat_id=chat), self.profile()))
            self.assertFalse(await moderation.check_flood(self.context, self.post(9), self.profile()))
        with patch.object(moderation, "monotonic", return_value=105):
            self.assertFalse(await moderation.check_flood(self.context, self.post(10), self.profile()))
        self.save.assert_not_called()
        self.bot.delete_message.assert_not_awaited()

    async def test_owner_block_covers_new_profiles_and_unblock_notifies_once(self):
        await moderation.set_user_block(self.context, 123, True)
        await moderation.set_user_block(self.context, "123", True)
        for category, key, entry in (
            ("protected", -99, {"id": 123, "name": "New"}),
            ("alpha", -98, {"id": "123", "name": "Trusted"}),
            ("signed", 123, {"username": "signed"}),
            ("shadow", -97, {"owner": {"id": 123}}),
        ):
            profile = moderation.profile_from_entry(category, entry, key)
            self.assertTrue(await moderation.reject_blocked(self.context, self.post(), self.state, profile))
        self.assertFalse(moderation.profile_is_blocked(self.state, self.profile(2)))
        await moderation.set_user_block(self.context, 123, False)
        await moderation.set_user_block(self.context, 123, False)
        self.assertFalse(moderation.profile_is_blocked(self.state, self.profile()))
        self.assertEqual(self.bot.send_message.await_count, 2)
        self.assertIn("снята", self.bot.send_message.call_args.kwargs["text"])

    async def test_profile_mute_survives_owner_unblock_and_uses_owner_dm(self):
        await moderation.set_profile_block(self.context, self.profile(), True)
        self.assertTrue(self.state["admins"][0]["mute"])
        self.assertFalse(self.state["admins"][1]["mute"])
        await moderation.set_user_block(self.context, 123, True)
        await moderation.set_user_block(self.context, 123, False)
        self.assertTrue(moderation.profile_is_blocked(self.state, self.profile()))
        await moderation.set_profile_block(self.context, self.profile(), False)
        self.assertFalse(self.state["admins"][0]["mute"])
        self.assertTrue(all(call.kwargs["chat_id"] == 123 for call in self.bot.send_message.await_args_list))

    async def test_failed_dm_does_not_interrupt_block_or_cleanup(self):
        self.bot.send_message.side_effect = Forbidden("User blocked the bot")
        with self.assertLogs("bot.moderation", level="WARNING"):
            for number in range(1, 11):
                await moderation.check_flood(self.context, self.post(number), self.profile())
        self.assertEqual(self.state["blocked_user_ids"], ["123"])
        self.assertEqual(self.bot.delete_message.await_count, 10)

    async def test_legacy_profile_without_owner_is_blocked_individually(self):
        del self.state["admins"][0]["id"]
        with self.assertLogs("bot.moderation", level="WARNING"):
            for number in range(1, 11):
                await moderation.check_flood(self.context, self.post(number), self.profile())
        self.assertTrue(self.state["admins"][0]["mute"])
        self.assertNotIn("blocked_user_ids", self.state)
        self.assertFalse(self.state["admins"][1]["mute"])
        self.bot.send_message.assert_not_awaited()

    async def test_old_signatures_and_legacy_bans_can_be_unblocked(self):
        msg = self.post()
        msg.author_signature = "First" + chr(0xE0108)
        profile = moderation.find_profile(self.state, msg)
        self.assertEqual(profile.owner_id, "123")
        self.assertFalse(moderation.current_signature(msg, profile))
        self.state["banned_users"] = [msg.author_signature]
        self.assertTrue(moderation.profile_is_blocked(self.state, profile))
        await moderation.set_profile_block(self.context, profile, False)
        self.assertFalse(moderation.profile_is_blocked(self.state, profile))

    async def test_unverified_media_does_not_count_against_profile_owner(self):
        environment = {"ContextTypes": ContextTypes, "logger": logging.getLogger(__name__),
                       "check_protection": AsyncMock(return_value=(True, True)),
                       "check_flood": AsyncMock(), "reject_blocked": moderation.reject_blocked,
                       "find_profile": moderation.find_profile, "current_signature": moderation.current_signature}
        load_functions("bot/censor.py", {"check_message"}, environment)
        msg = self.post()
        msg.author_signature = "First" + chr(0xE0108)
        await environment["check_message"](self.context, msg, self.state)
        environment["check_flood"].assert_not_awaited()

    async def test_blocked_trusted_profile_cannot_bypass_moderation(self):
        await moderation.set_user_block(self.context, 123, True)
        env = {"Update": Update, "ContextTypes": ContextTypes, "MAIN_CHANNEL_ID": -100,
               "load_config": self.load, "check_shadow_post": AsyncMock(return_value=False),
               "check_owner": AsyncMock(), "check_super_user": AsyncMock(),
               "find_profile": moderation.find_profile, "reject_blocked": moderation.reject_blocked}
        load_functions("bot/channel.py", {"reply_in_channel"}, env)
        update = SimpleNamespace(edited_channel_post=None, channel_post=self.post())
        await env["reply_in_channel"](update, self.context)
        self.bot.delete_message.assert_awaited_once_with(chat_id=-100, message_id=1)
        env["check_owner"].assert_not_awaited()
        env["check_super_user"].assert_not_awaited()

    async def test_verified_certificate_cannot_bypass_owner_block(self):
        self.state["signed_users"] = {"123": {"role": "sudo"}}
        await moderation.set_user_block(self.context, 123, True)
        env = {"Update": Update, "ContextTypes": ContextTypes, "MAIN_CHANNEL_ID": -100,
               "load_config": self.load, "check_shadow_post": AsyncMock(return_value=False),
               "check_owner": AsyncMock(return_value=False), "check_super_user": AsyncMock(return_value=False),
               "find_profile": moderation.find_profile, "reject_blocked": moderation.reject_blocked,
               "profile_from_entry": moderation.profile_from_entry, "current_signature": moderation.current_signature,
               "signed_user_id": Mock(return_value="123"), "check_flood": AsyncMock()}
        load_functions("bot/channel.py", {"reply_in_channel"}, env)
        msg = self.post()
        msg.author_signature = "Unregistered certificate profile"
        await env["reply_in_channel"](SimpleNamespace(edited_channel_post=None, channel_post=msg), self.context)
        self.bot.delete_message.assert_awaited_once_with(chat_id=-100, message_id=1)
        env["check_flood"].assert_not_awaited()

    def panel_environment(self):
        environment = {"Update": Update, "ContextTypes": ContextTypes, "OWNER_ID": 1,
                       "load_config": self.load, "save_config": self.save,
                       "InlineKeyboardButton": InlineKeyboardButton, "InlineKeyboardMarkup": InlineKeyboardMarkup,
                       "audit_logger": Mock(), "logger": Mock(), "tools": SimpleNamespace(),
                       "ROLES": ("root", "sudo", "user"), "CATEGORY_KEY": {"protected": "admins"},
                       "CATEGORY_TITLE": {"protected": "Admins"}, "MAIN_TEXT": "Panel",
                       "main_keyboard": Mock(), "profile_from_entry": moderation.profile_from_entry,
                       "user_is_blocked": moderation.user_is_blocked,
                       "set_user_block": moderation.set_user_block, "set_profile_block": moderation.set_profile_block}
        return load_functions("bot/panel.py", {
            "panel", "check_id", "_who", "_find_in_category", "format_user_info", "user_detail_keyboard",
        }, environment)

    async def test_panel_buttons_block_and_unblock_owner_with_access_check(self):
        env = self.panel_environment()
        keyboard = env["user_detail_keyboard"]("protected", self.state["admins"][0], -10)
        callback = next(button.callback_data for row in keyboard.inline_keyboard for button in row
                        if "blockuser" in button.callback_data)
        query = SimpleNamespace(data=callback, from_user=SimpleNamespace(id=999), message=Mock(),
                                answer=AsyncMock(), edit_message_text=AsyncMock())
        update = SimpleNamespace(callback_query=query)
        await env["panel"](update, self.context)
        self.save.assert_not_called()
        query.from_user.id = 1
        await env["panel"](update, self.context)
        self.assertEqual(self.state["blocked_user_ids"], ["123"])
        keyboard = query.edit_message_text.call_args.kwargs["reply_markup"]
        query.data = next(button.callback_data for row in keyboard.inline_keyboard for button in row
                          if "unblockuser" in button.callback_data)
        await env["panel"](update, self.context)
        self.assertEqual(self.state["blocked_user_ids"], [])
        self.assertEqual(self.bot.send_message.await_count, 2)


if __name__ == "__main__":
    unittest.main()
