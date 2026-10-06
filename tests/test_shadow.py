import ast
import copy
import json
import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from bot.shadow_store import (
    DEFAULT_STATE, MOSCOW, ShadowStore, add_month, daily_usage,
    effective_plan, ensure_subscription, grant_subscription, next_reset, refund_post,
    reserve_post, reveal_author,
)

NOW = datetime(2026, 10, 7, 15, tzinfo=MOSCOW)
MAIN = -1001234567890
CHANNEL = -1009876543210
OWNER = {"id": 123, "name": "Иван <Иванов>", "username": "ivan"}
CHANNEL_DATA = {"channel_id": CHANNEL, "owner": OWNER, "name": chr(0xE0101) * 5, "uuid": chr(0xE0100) * 5, "enabled": True}


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.data = copy.deepcopy(DEFAULT_STATE)

    def test_new_user_gets_plus_once_then_free_without_renewing_trial(self):
        subscription = copy.deepcopy(ensure_subscription(self.data, 123, NOW))
        self.assertEqual(subscription["plan"], "Plus")
        self.assertEqual(subscription["expires_at"], add_month(NOW).isoformat())
        self.assertEqual(subscription["trial_started_at"], NOW.isoformat())
        self.assertEqual(subscription["trial_expires_at"], subscription["expires_at"])
        self.assertEqual(effective_plan(self.data, 123, NOW), "Plus")
        self.assertEqual(effective_plan(self.data, 123, add_month(NOW)), "Free")
        self.assertEqual(ensure_subscription(self.data, 123, NOW + timedelta(days=3650)), subscription)
        self.assertEqual(effective_plan(self.data, 123, NOW + timedelta(days=3650)), "Free")
        paid = grant_subscription(self.data, 123, "Pro x5", "store:1", NOW)
        ensure_subscription(self.data, 123, NOW)
        self.assertEqual(self.data["subscriptions"]["123"]["plan"], "Pro x5")
        self.assertEqual(self.data["subscriptions"]["123"]["expires_at"], paid["expires_at"])

    def test_existing_free_paid_and_expired_records_do_not_receive_trial(self):
        for subscription in (
            {"plan": "Free", "expires_at": None},
            {"plan": "Ultra", "expires_at": None},
            {"plan": "Plus", "expires_at": "2026-10-01T00:00:00+03:00"},
        ):
            with self.subTest(subscription=subscription):
                self.data["subscriptions"]["123"] = copy.deepcopy(subscription)
                self.assertEqual(ensure_subscription(self.data, 123, NOW), subscription)
                effective_plan(self.data, 123, NOW)
                self.assertEqual(self.data["subscriptions"]["123"], subscription)

    def test_trial_survives_json_reload_and_respects_calendar_month(self):
        signup = datetime(2026, 1, 31, 15, tzinfo=MOSCOW)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "shadow.json"
            with ShadowStore(path).transaction() as data:
                subscription = copy.deepcopy(ensure_subscription(data, 123, signup))
            self.assertEqual(subscription["expires_at"], "2026-02-28T15:00:00+03:00")
            with ShadowStore(path).transaction() as data:
                self.assertEqual(effective_plan(data, 123, NOW), "Free")
                self.assertEqual(ensure_subscription(data, 123, NOW), subscription)
            self.assertEqual(ShadowStore(path).read()["subscriptions"]["123"], subscription)

    def test_purchase_during_trial_extends_plus_or_switches_immediately(self):
        ensure_subscription(self.data, 123, NOW)
        purchase_time = NOW + timedelta(days=3)
        paid = grant_subscription(self.data, 123, "Plus", "store:1", purchase_time)
        self.assertEqual(paid["expires_at"], add_month(add_month(NOW)).isoformat())
        self.assertEqual(self.data["subscriptions"]["123"]["trial_started_at"], NOW.isoformat())
        switched = grant_subscription(self.data, 123, "Pro x5", "store:2", purchase_time)
        self.assertEqual(switched["expires_at"], add_month(purchase_time).isoformat())

    def test_trial_uses_plus_quota_and_expired_trial_uses_free_quota(self):
        for message_id in range(1, 6):
            self.assertEqual(reserve_post(self.data, CHANNEL_DATA, MAIN, message_id, NOW), "accepted")
        self.assertEqual(reserve_post(self.data, CHANNEL_DATA, MAIN, 6, NOW), "limit")
        expired = add_month(NOW)
        self.assertEqual(reserve_post(self.data, CHANNEL_DATA, MAIN, 7, expired), "accepted")
        self.assertEqual(reserve_post(self.data, CHANNEL_DATA, MAIN, 8, expired), "limit")

    def test_defaults_and_atomic_writes_preserve_manual_edits(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "shadow.json"
            store = ShadowStore(path)
            with store.transaction() as data:
                data["subscriptions"]["123"] = {"plan": "Ultra", "expires_at": "2026-12-01T00:00:00+03:00"}
            self.assertEqual(effective_plan(store.read(), 123, NOW), "Ultra")
            manual = json.loads(path.read_text())
            manual["plans"]["Free"]["posts_per_day"] = 9
            path.write_text(json.dumps(manual))
            self.assertEqual(store.read()["plans"]["Free"]["posts_per_day"], 9)
            path.write_text("broken json")
            with self.assertRaises(json.JSONDecodeError):
                with store.transaction():
                    pass
            self.assertEqual(path.read_text(), "broken json")

    def test_transaction_exception_does_not_save(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ShadowStore(Path(directory) / "state.json")
            with store.transaction():
                pass
            original = store.path.read_text()
            with self.assertRaises(RuntimeError):
                with store.transaction() as data:
                    data["subscriptions"]["123"] = {"plan": "Ultra"}
                    raise RuntimeError("cancel")
            self.assertEqual(store.path.read_text(), original)

    def test_concurrent_json_writers_keep_all_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "shadow.json"
            def increment(_):
                with ShadowStore(path).transaction() as data:
                    data["counter"] = data.get("counter", 0) + 1
            with ThreadPoolExecutor(max_workers=4) as executor:
                list(executor.map(increment, range(20)))
            self.assertEqual(ShadowStore(path).read()["counter"], 20)

    def test_month_end_and_year_end(self):
        self.assertEqual(add_month(datetime(2026, 1, 31, tzinfo=MOSCOW)).date().isoformat(), "2026-02-28")
        self.assertEqual(add_month(datetime(2028, 1, 31, tzinfo=MOSCOW)).date().isoformat(), "2028-02-29")
        self.assertEqual(add_month(datetime(2026, 12, 31, tzinfo=MOSCOW)).date().isoformat(), "2027-01-31")

    def test_renewal_switch_expiry_and_duplicate_receipts(self):
        first = grant_subscription(self.data, 123, "Plus", "store:1", NOW)
        self.assertEqual(grant_subscription(self.data, 123, "Plus", "store:1", NOW), first)
        self.assertEqual(len(self.data["purchases"]), 1)
        second = grant_subscription(self.data, 123, "Plus", "store:2", NOW)
        self.assertTrue(second["expires_at"].startswith("2027-01-07"))
        switched = grant_subscription(self.data, 123, "Pro x5", "store:3", NOW)
        self.assertTrue(switched["expires_at"].startswith("2026-11-07"))
        self.assertEqual(effective_plan(self.data, 123, NOW + timedelta(days=32)), "Free")
        self.assertEqual(effective_plan(self.data, 999, NOW), "Plus")

    def test_all_five_post_limits_and_shared_owner_quota(self):
        for plan, quota in DEFAULT_STATE["plans"].items():
            with self.subTest(plan=plan):
                data = copy.deepcopy(DEFAULT_STATE)
                data["subscriptions"]["123"] = {"plan": plan, "expires_at": None}
                usage = daily_usage(data, 123, NOW)
                usage["posts"] = quota["posts_per_day"] - 1
                self.assertEqual(reserve_post(data, CHANNEL_DATA, MAIN, 1, NOW), "accepted")
                other = {**CHANNEL_DATA, "channel_id": CHANNEL - 1}
                self.assertEqual(reserve_post(data, other, MAIN, 2, NOW), "limit")
                self.assertEqual(reserve_post(data, CHANNEL_DATA, MAIN, 1, NOW), "existing")

    def test_daily_reset_at_moscow_midnight(self):
        before = datetime(2026, 10, 7, 20, 59, 59, tzinfo=timezone.utc)
        after = before + timedelta(seconds=1)
        daily_usage(self.data, 123, before)["posts"] = 1
        self.assertEqual(daily_usage(self.data, 123, after)["posts"], 0)
        self.assertEqual(next_reset(before), after)

    def test_album_counts_once_and_failed_post_refunds(self):
        self.assertEqual(reserve_post(self.data, CHANNEL_DATA, MAIN, 1, NOW, "album"), "accepted")
        self.assertEqual(reserve_post(self.data, CHANNEL_DATA, MAIN, 2, NOW, "album"), "accepted")
        self.assertEqual(daily_usage(self.data, 123, NOW)["posts"], 1)
        refund_post(self.data, f"{MAIN}:2", NOW)
        self.assertEqual(daily_usage(self.data, 123, NOW)["posts"], 1)
        refund_post(self.data, f"{MAIN}:1", NOW)
        self.assertEqual(daily_usage(self.data, 123, NOW)["posts"], 0)

    def test_view_limits_cache_and_plan_switch(self):
        reserve_post(self.data, CHANNEL_DATA, MAIN, 1, NOW)
        key = f"{MAIN}:1"
        self.assertEqual(reveal_author(self.data, 456, key, NOW), ("limit", None))
        grant_subscription(self.data, 456, "Pro x5", "store:1", NOW)
        self.assertEqual(reveal_author(self.data, 456, key, NOW), ("revealed", OWNER))
        self.assertEqual(reveal_author(self.data, 456, key, NOW), ("cached", OWNER))
        grant_subscription(self.data, 456, "Plus", "store:2", NOW)
        self.assertEqual(reveal_author(self.data, 456, key, NOW + timedelta(days=100)), ("cached", OWNER))
        self.assertEqual(reveal_author(self.data, 456, "unknown", NOW), ("unknown", None))

    def test_each_plan_view_limit_and_midnight_reset(self):
        for plan, quota in DEFAULT_STATE["plans"].items():
            with self.subTest(plan=plan):
                data = copy.deepcopy(DEFAULT_STATE)
                data["subscriptions"]["456"] = {"plan": plan, "expires_at": None}
                reserve_post(data, CHANNEL_DATA, MAIN, 1, NOW)
                daily_usage(data, 456, NOW)["views"] = quota["views_per_day"]
                self.assertEqual(reveal_author(data, 456, f"{MAIN}:1", NOW), ("limit", None))
                result, _ = reveal_author(data, 456, f"{MAIN}:1", NOW + timedelta(days=1))
                self.assertEqual(result, "revealed" if quota["views_per_day"] else "limit")


# Only the Telegram-facing tests need third-party dependencies. No real bots,
# config.json or economy DB are imported or modified by this test suite.
with patch.dict(os.environ, {"OWNER_ID": "1", "MAIN_CHANNEL_ID": str(MAIN), "PERSONAL_CHANNEL_ID": "-100777"}):
    with patch("dotenv.load_dotenv"):
        from bot import shadow
from telegram import Bot, Update, User
from telegram.error import Forbidden
from telegram.ext import Application, ApplicationHandlerStop, CommandHandler, MessageHandler, filters


class HandlerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = ShadowStore(Path(self.temp.name) / "shadow.json")
        self.patchers = [
            patch.object(shadow, "store", self.store),
            patch.object(shadow, "now_moscow", return_value=NOW),
            patch.object(shadow, "channel_lock", __import__('asyncio').Lock()),
            patch.dict("sys.modules", {"bot.censor": SimpleNamespace(check=Mock(return_value=False))}),
        ]
        for patcher in self.patchers:
            patcher.start()
            self.addCleanup(patcher.stop)
        self.bot = SimpleNamespace(id=999, get_chat=AsyncMock(), set_chat_title=AsyncMock(),
                                   delete_message=AsyncMock(), send_message=AsyncMock(), get_chat_administrators=AsyncMock())
        self.context = SimpleNamespace(bot=self.bot)
        self.config = {"mode": "normal", "ban_messages": "off"}
        with self.store.transaction() as data:
            data["channels"][str(CHANNEL)] = copy.deepcopy(CHANNEL_DATA)

    def post(self, message_id=1, signature=None, **kwargs):
        return SimpleNamespace(chat_id=MAIN, message_id=message_id, chat=SimpleNamespace(type="channel"),
                               sender_chat=kwargs.pop("sender_chat", SimpleNamespace(id=MAIN)),
                               author_signature=signature if signature is not None else CHANNEL_DATA["name"] + CHANNEL_DATA["uuid"],
                               media_group_id=kwargs.pop("media_group_id", None), text=kwargs.pop("text", "hello"),
                               caption=None, animation=None, **kwargs)

    def private(self, text, user_id=456):
        msg = SimpleNamespace(text=text, from_user=SimpleNamespace(id=user_id, is_bot=False), chat=SimpleNamespace(type="private"), reply_text=AsyncMock())
        return SimpleNamespace(message=msg, effective_message=msg)

    async def test_private_contact_creates_trial_once_without_overwriting_paid(self):
        update = self.private("/start")
        await shadow.track_private_user(update, self.context)
        trial = self.store.read()["subscriptions"]["456"]
        self.assertEqual(trial["plan"], "Plus")
        self.assertEqual(trial["expires_at"], add_month(NOW).isoformat())
        await shadow.track_private_user(update, self.context)
        self.assertEqual(self.store.read()["subscriptions"]["456"], trial)
        with patch.object(shadow, "now_moscow", return_value=NOW + timedelta(days=100)):
            await shadow.track_private_user(update, self.context)
        self.assertEqual(self.store.read()["subscriptions"]["456"], trial)
        with self.store.transaction() as data:
            grant_subscription(data, 456, "Plus", "store:1", NOW)
        paid = self.store.read()["subscriptions"]["456"]
        await shadow.track_private_user(update, self.context)
        self.assertEqual(self.store.read()["subscriptions"]["456"], paid)
        update.message.reply_text.assert_not_awaited()

    async def test_sub_shows_free_plus_month_and_falls_back_after_expiry(self):
        update = self.private("/sub")
        await shadow.sub_handler(update, self.context)
        trial = self.store.read()["subscriptions"]["456"]
        self.assertEqual(trial["plan"], "Plus")
        text = update.message.reply_text.call_args.args[0]
        self.assertIn("Plus бесплатно на месяц", text)
        self.assertIn("07.11.2026", text)
        self.assertIn("5 из 5", text)
        with patch.object(shadow, "now_moscow", return_value=add_month(NOW)):
            await shadow.sub_handler(update, self.context)
        text = update.message.reply_text.call_args.args[0]
        self.assertIn("Сейчас действует Free", text)
        self.assertIn("1 из 1", text)
        self.assertNotIn("Plus бесплатно", text)
        self.assertEqual(self.store.read()["subscriptions"]["456"], trial)

    async def test_post_rotation_replay_edit_and_limit(self):
        with self.store.transaction() as data:
            data["subscriptions"]["123"] = {"plan": "Free", "expires_at": None}
        first = self.post()
        self.assertTrue(await shadow.check_shadow_post(self.context, first, self.config))
        self.bot.set_chat_title.assert_awaited_once()
        self.assertNotEqual(self.store.read()["channels"][str(CHANNEL)]["uuid"], CHANNEL_DATA["uuid"])
        title = self.bot.set_chat_title.call_args.args[1]
        self.assertTrue(title)
        self.assertTrue(all(0xE0100 <= ord(char) < 0xE01F0 for char in title))
        self.assertTrue(await shadow.check_shadow_post(self.context, self.post(2), self.config))
        self.bot.delete_message.assert_awaited_with(chat_id=MAIN, message_id=2)
        await shadow.check_shadow_post(self.context, first, self.config, edited=True)
        self.assertEqual(self.store.read()["usage"]["123"]["posts"], 1)
        current = self.store.read()["channels"][str(CHANNEL)]
        await shadow.check_shadow_post(self.context, self.post(3, current["name"] + current["uuid"]), self.config)
        self.bot.delete_message.assert_awaited_with(chat_id=MAIN, message_id=3)
        self.assertNotIn(f"{MAIN}:3", self.store.read()["posts"])

    async def test_rotation_failure_deletes_refunds_and_pauses(self):
        self.bot.set_chat_title.side_effect = Forbidden("no rights")
        with self.assertLogs(shadow.logger, level="ERROR"):
            await shadow.check_shadow_post(self.context, self.post(), self.config)
        data = self.store.read()
        self.assertEqual(data["usage"]["123"]["posts"], 0)
        self.assertFalse(data["channels"][str(CHANNEL)]["enabled"])
        self.assertEqual(data["posts"], {})
        self.bot.delete_message.assert_awaited_once()

    async def test_album_and_edits_do_not_spend_extra_posts(self):
        await shadow.check_shadow_post(self.context, self.post(1, media_group_id="album"), self.config)
        await shadow.check_shadow_post(self.context, self.post(2, media_group_id="album"), self.config)
        self.assertEqual(len(self.store.read()["posts"]), 2)
        self.assertEqual(self.store.read()["usage"]["123"]["posts"], 1)
        self.bot.set_chat_title.assert_awaited_once()
        self.bot.delete_message.assert_not_awaited()

    async def test_spoofed_sender_unknown_shadow_and_non_shadow(self):
        await shadow.check_shadow_post(self.context, self.post(sender_chat=SimpleNamespace(id=-100555)), self.config)
        self.bot.delete_message.assert_awaited_once()
        await shadow.check_shadow_post(self.context, self.post(2, "Shadow unknown"), self.config)
        await shadow.check_shadow_post(self.context, self.post(4, chr(0xE0102) * 10), self.config)
        self.bot.delete_message.assert_awaited_with(chat_id=MAIN, message_id=4)
        self.assertFalse(await shadow.check_shadow_post(self.context, self.post(3, "ordinary"), self.config))
        self.assertEqual(self.store.read()["posts"], {})

    async def test_lockdown_and_censor_do_not_spend_quota(self):
        await shadow.check_shadow_post(self.context, self.post(), {"mode": "normal", "ban_messages": "all"})
        self.assertEqual(self.store.read()["posts"], {})
        with patch.dict("sys.modules", {"bot.censor": SimpleNamespace(check=Mock(return_value=True))}):
            await shadow.check_shadow_post(self.context, self.post(), {"mode": "normal", "ban_messages": "manual"})
        self.assertEqual(self.store.read()["posts"], {})

    async def test_edited_content_is_still_moderated(self):
        msg = self.post()
        await shadow.check_shadow_post(self.context, msg, self.config)
        with patch.dict("sys.modules", {"bot.censor": SimpleNamespace(check=Mock(return_value=True))}):
            await shadow.check_shadow_post(self.context, msg, {"mode": "normal", "ban_messages": "manual"}, edited=True)
        self.bot.delete_message.assert_awaited_once()

    async def test_registration_uses_owner_and_needs_permissions(self):
        user = SimpleNamespace(id=123, full_name="Иван", username="ivan", is_bot=False)
        owner = SimpleNamespace(user=user, status="creator")
        bot_admin = SimpleNamespace(user=SimpleNamespace(id=999, is_bot=True), can_change_info=True)
        self.bot.get_chat_administrators.return_value = [owner, bot_admin]
        msg = SimpleNamespace(text="Shadow", caption=None, chat_id=CHANNEL, chat=SimpleNamespace(type="channel"), reply_text=AsyncMock())
        self.assertTrue(await shadow.register_shadow(self.context, msg, {}))
        channel = self.store.read()["channels"][str(CHANNEL)]
        self.assertEqual(channel["owner"]["id"], 123)
        self.assertTrue(channel["enabled"])
        title = self.bot.set_chat_title.call_args.args[1]
        self.assertEqual(title, channel["name"] + channel["uuid"])
        self.assertTrue(title)
        self.assertTrue(all(0xE0100 <= ord(char) < 0xE01F0 for char in title))
        trial = self.store.read()["subscriptions"]["123"]
        self.assertEqual(trial["plan"], "Plus")
        self.assertEqual(trial["expires_at"], add_month(NOW).isoformat())
        await shadow.register_shadow(self.context, msg, {})
        self.assertEqual(self.store.read()["subscriptions"]["123"], trial)
        self.assertEqual(self.bot.set_chat_title.await_count, 2)
        self.bot.get_chat_administrators.return_value = [owner, bot_admin, owner]
        await shadow.register_shadow(self.context, msg, {})
        self.assertEqual(self.bot.set_chat_title.await_count, 2)
        self.bot.get_chat_administrators.return_value = [owner, SimpleNamespace(user=bot_admin.user, can_change_info=False)]
        await shadow.register_shadow(self.context, msg, {})
        self.assertEqual(self.bot.set_chat_title.await_count, 2)

    async def test_sub_shows_current_expiry_limits_reset_and_buttons(self):
        with self.store.transaction() as data:
            grant_subscription(data, 456, "Pro x5", "store:1", NOW)
            daily_usage(data, 456, NOW)["posts"] = 2
        update = self.private("/sub")
        await shadow.sub_handler(update, self.context)
        text = update.message.reply_text.call_args.args[0]
        self.assertIn("Pro x5", text)
        self.assertIn("07.11.2026", text)
        self.assertIn("23 из 25", text)
        self.assertIn("<code>" + "▓" * 18 + "░" * 2 + "</code>", text)
        self.assertIn("<code>" + "▓" * 20 + "</code>", text)
        self.assertIn("9 ч 0 мин", text)
        buttons = update.message.reply_text.call_args.kwargs["reply_markup"].inline_keyboard
        self.assertEqual(buttons[0][0].text, "Изменить подписку")
        self.assertEqual(buttons[0][0].callback_data, "sub^change")
        self.assertEqual(buttons[0][0].to_dict()["style"], "primary")
        self.assertTrue(all(button.url is None for row in buttons for button in row))

    def subscription_callback(self, action, user_id=456, chat_id=456, chat_type="private"):
        query = SimpleNamespace(
            data=f"sub^{action}", from_user=SimpleNamespace(id=user_id),
            message=SimpleNamespace(chat=SimpleNamespace(id=chat_id, type=chat_type)),
            answer=AsyncMock(), edit_message_text=AsyncMock(),
        )
        return SimpleNamespace(callback_query=query)

    async def test_subscription_terms_flow_preserves_plan_and_quotas(self):
        with self.store.transaction() as data:
            grant_subscription(data, 456, "Pro x20", "store:1", NOW)
            daily_usage(data, 456, NOW)["posts"] = 18
        before = self.store.read()
        change = self.subscription_callback("change")
        await shadow.sub_buttons_handler(change, self.context)
        text = change.callback_query.edit_message_text.call_args.args[0]
        self.assertIn("Лицензионные условия", text)
        self.assertIn("подтверждает, что является администратором", text)
        self.assertIn("без уведомления", text)
        self.assertIn("лишён подписки", text)
        self.assertIn("административных прав", text)
        self.assertIn("удалён из канала", text)
        self.assertIn("Добровольный возврат средств не предусмотрен", text)
        self.assertIn(shadow.SECURITY_POLICY_URL, text)
        self.assertLess(len(text), 4096)
        buttons = change.callback_query.edit_message_text.call_args.kwargs["reply_markup"].inline_keyboard
        self.assertEqual(buttons[0][0].text, "Подтверждаю и принимаю")
        self.assertEqual(buttons[0][0].to_dict()["style"], "success")
        self.assertNotIn("style", buttons[-1][0].to_dict())
        self.assertEqual({button.url for row in buttons for button in row if button.url}, {shadow.SECURITY_POLICY_URL})
        self.assertEqual(self.store.read(), before)
        accept = self.subscription_callback("accept")
        await shadow.sub_buttons_handler(accept, self.context)
        buttons = accept.callback_query.edit_message_text.call_args.kwargs["reply_markup"].inline_keyboard
        self.assertEqual({button.url for row in buttons for button in row if button.url}, {
            "https://t.me/pig6storeplus?direct", "https://t.me/pig6store_pro_x5?direct", "https://t.me/pig6store_pro_x20?direct"})
        self.assertTrue(all(button.to_dict()["style"] == "primary"
                            for row in buttons for button in row if button.url))
        self.assertNotIn("style", buttons[-1][0].to_dict())
        current = self.store.read()
        self.assertEqual(current["subscriptions"]["456"]["terms_accepted_at"], NOW.isoformat())
        self.assertEqual(current["subscriptions"]["456"]["administrator_confirmed_at"], NOW.isoformat())
        self.assertEqual(current["subscriptions"]["456"]["terms_version"], 2)
        self.assertEqual(current["subscriptions"]["456"]["security_policy_url"], shadow.SECURITY_POLICY_URL)
        self.assertEqual(current["subscriptions"]["456"]["security_policy_sha256"], shadow.security_policy_fingerprint())
        self.assertEqual(current["subscriptions"]["456"]["plan"], "Pro x20")
        self.assertEqual(current["subscriptions"]["456"]["expires_at"], before["subscriptions"]["456"]["expires_at"])
        self.assertEqual(current["usage"], before["usage"])
        back = self.subscription_callback("back")
        await shadow.sub_buttons_handler(back, self.context)
        text = back.callback_query.edit_message_text.call_args.args[0]
        self.assertIn("82 из 100", text)
        self.assertIn("Pro x20", text)
        buttons = back.callback_query.edit_message_text.call_args.kwargs["reply_markup"].inline_keyboard
        self.assertTrue(all(button.url is None for row in buttons for button in row))

    async def test_subscription_callback_is_only_for_its_private_user(self):
        for chat_id, chat_type in ((123, "private"), (-100456, "channel")):
            update = self.subscription_callback("accept", chat_id=chat_id, chat_type=chat_type)
            before = self.store.read()
            await shadow.sub_buttons_handler(update, self.context)
            update.callback_query.edit_message_text.assert_not_awaited()
            self.assertTrue(update.callback_query.answer.call_args.kwargs["show_alert"])
            self.assertEqual(self.store.read(), before)

    async def test_migration_hides_legacy_titles_and_preserves_authorship(self):
        with self.store.transaction() as data:
            channel = data["channels"][str(CHANNEL)]
            channel["name"] = "Shadow abcd"
            reserve_post(data, channel, MAIN, 1, NOW)
            grant_subscription(data, 123, "Plus", "store:1", NOW)
        before = self.store.read()
        await shadow.migrate_shadow_channels(self.context)
        data = self.store.read()
        title = self.bot.set_chat_title.call_args.args[1]
        self.assertTrue(all(0xE0100 <= ord(char) < 0xE01F0 for char in title))
        self.assertEqual(data["posts"], before["posts"])
        self.assertEqual(data["subscriptions"], before["subscriptions"])
        self.assertEqual(title, data["channels"][str(CHANNEL)]["name"] + data["channels"][str(CHANNEL)]["uuid"])
        await shadow.check_shadow_post(self.context, self.post(signature="Shadow abcd" + CHANNEL_DATA["uuid"]), self.config, edited=True)
        self.bot.delete_message.assert_not_awaited()
        await shadow.migrate_shadow_channels(self.context)
        self.bot.set_chat_title.assert_awaited_once()

    async def test_migration_failure_pauses_channel_and_notifies_owner(self):
        with self.store.transaction() as data:
            data["channels"][str(CHANNEL)]["name"] = "Shadow abcd"
        self.bot.set_chat_title.side_effect = Forbidden("no rights")
        with self.assertLogs(shadow.logger, level="ERROR"):
            await shadow.migrate_shadow_channels(self.context)
        self.assertFalse(self.store.read()["channels"][str(CHANNEL)]["enabled"])
        self.assertEqual(self.bot.send_message.call_args.kwargs["chat_id"], OWNER["id"])

    async def test_all_stores_use_real_telegram_direct_message_updates(self):
        for index, (username, plan) in enumerate(DEFAULT_STATE["stores"].items(), start=1):
            with self.subTest(username=username):
                bot = Bot("123456:TEST-TOKEN")
                update = Update.de_json({"update_id": index, "message": {
                    "message_id": index, "date": int(NOW.timestamp()),
                    "chat": {"id": -100666, "type": "supergroup", "is_direct_messages": True, "title": "Store"},
                    "from": {"id": 456, "is_bot": False, "first_name": "Buyer"}, "text": "purchase",
                    "direct_messages_topic": {"topic_id": 77, "user": {"id": 456, "is_bot": False, "first_name": "Buyer"}},
                }}, bot)
                self.bot.get_chat.return_value = SimpleNamespace(parent_chat=SimpleNamespace(username=username))
                with self.assertRaises(ApplicationHandlerStop):
                    await shadow.shop_message_handler(update, self.context)
                self.assertEqual(self.store.read()["subscriptions"]["456"]["plan"], plan)
                self.assertEqual(self.bot.send_message.call_args.kwargs["direct_messages_topic_id"], 77)
                expiry = self.store.read()["subscriptions"]["456"]["expires_at"]
                with self.assertRaises(ApplicationHandlerStop):
                    await shadow.shop_message_handler(update, self.context)
                self.assertEqual(self.store.read()["subscriptions"]["456"]["expires_at"], expiry)

    async def test_admin_reply_does_not_renew_and_unknown_store_is_ignored(self):
        msg = SimpleNamespace(chat=SimpleNamespace(is_direct_messages=True), direct_messages_topic=SimpleNamespace(user=SimpleNamespace(id=456, is_bot=False)),
                              from_user=SimpleNamespace(id=1), chat_id=-100666, message_id=1)
        await shadow.shop_message_handler(SimpleNamespace(message=msg), self.context)
        self.bot.get_chat.assert_not_awaited()
        msg.from_user.id = 456
        self.bot.get_chat.return_value = SimpleNamespace(parent_chat=SimpleNamespace(username="otherstore"))
        await shadow.shop_message_handler(SimpleNamespace(message=msg), self.context)
        self.assertEqual(self.store.read()["subscriptions"], {})

    async def test_author_disclosure_is_owner_only_and_repeat_is_free(self):
        with self.store.transaction() as data:
            reserve_post(data, CHANNEL_DATA, MAIN, 1, NOW)
            grant_subscription(data, 456, "Pro x5", "store:1", NOW)
        update = self.private("https://t.me/c/1234567890/1?single")
        await shadow.author_handler(update, self.context)
        text = update.message.reply_text.call_args.args[0]
        self.assertIn("Иван &lt;Иванов&gt;", text)
        self.assertIn("@ivan", text)
        self.assertTrue(text.startswith("Автор:"))
        self.assertNotIn("Владелец:", text)
        self.assertNotIn("ID:", text)
        self.assertNotIn(f"<code>{OWNER['id']}</code>", text)
        self.assertNotIn("Анонимные посты:", text)
        self.assertNotIn("Просмотры авторства:", text)
        self.assertNotIn(CHANNEL_DATA["name"], text)
        self.assertNotIn(str(CHANNEL), text)
        await shadow.author_handler(update, self.context)
        self.assertEqual(self.store.read()["usage"]["456"]["views"], 1)

    async def test_unknown_foreign_and_invalid_links_do_not_spend_views(self):
        for link in ("https://t.me/c/1234567890/99", "https://t.me/c/777/1", "https://t.me/not_a_post"):
            await shadow.author_handler(self.private(link), self.context)
        self.assertEqual(self.store.read()["usage"], {})
        self.assertEqual(self.store.read()["subscriptions"], {})

    async def test_public_and_preview_links_resolve_main_channel(self):
        with self.store.transaction() as data:
            reserve_post(data, CHANNEL_DATA, MAIN, 1, NOW)
            grant_subscription(data, 456, "Pro x5", "store:1", NOW)
        self.bot.get_chat.return_value = SimpleNamespace(id=MAIN)
        for link in ("https://t.me/main_channel/1", "https://t.me/s/main_channel/1?single"):
            update = self.private(link)
            await shadow.author_handler(update, self.context)
            self.assertIn("Автор:", update.message.reply_text.call_args.args[0])
            self.bot.get_chat.assert_awaited_with("@main_channel")
        self.assertEqual(self.store.read()["usage"]["456"]["views"], 1)

    async def test_failed_disclosure_refunds_view(self):
        with self.store.transaction() as data:
            reserve_post(data, CHANNEL_DATA, MAIN, 1, NOW)
            grant_subscription(data, 456, "Pro x5", "store:1", NOW)
        update = self.private("https://t.me/c/1234567890/1")
        update.message.reply_text.side_effect = Forbidden("blocked")
        with self.assertRaises(Forbidden):
            await shadow.author_handler(update, self.context)
        data = self.store.read()
        self.assertEqual(data["usage"]["456"]["views"], 0)
        self.assertEqual(data["subscriptions"]["456"]["revealed_posts"], [])

    async def test_main_routes_channels_before_commands_and_supports_edits(self):
        # Evaluate only handler registration statements from main.py, avoiding
        # polling, network startup, config writes and SQLite initialization.
        source = ast.parse(Path("main.py").read_text())
        app = Application.builder().token("123456:TEST-TOKEN").build()
        callbacks = {}
        async def stop_channel(update, context):
            callbacks["seen"] = "channel"
            raise ApplicationHandlerStop
        environment = {"app": app, "filters": filters, "MessageHandler": MessageHandler,
                       "CommandHandler": CommandHandler,
                       "CallbackQueryHandler": __import__('telegram.ext', fromlist=['CallbackQueryHandler']).CallbackQueryHandler}
        registrations = [node for node in source.body if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
                         and isinstance(node.value.func, ast.Attribute) and node.value.func.attr == "add_handler"]
        for node in registrations:
            handler_call = node.value.args[0]
            callback = handler_call.args[0] if handler_call.func.id == "CallbackQueryHandler" else handler_call.args[1]
            environment[callback.id] = AsyncMock()
        environment["channel_post_handler"] = stop_channel
        exec(compile(ast.Module(body=registrations, type_ignores=[]), "main.py", "exec"), environment)
        app._initialized = True
        app.bot._bot_user = User(999, "Test", False, username="testbot")
        update = Update.de_json({"update_id": 1, "channel_post": {
            "message_id": 1, "date": int(NOW.timestamp()), "chat": {"id": MAIN, "type": "channel", "title": "Main"},
            "text": "/sub", "entities": [{"type": "bot_command", "offset": 0, "length": 4}],
        }}, app.bot)
        await app.process_update(update)
        self.assertEqual(callbacks["seen"], "channel")
        environment["sub_handler"].assert_not_awaited()
        edit = Update.de_json({"update_id": 2, "edited_channel_post": update.channel_post.to_dict()}, app.bot)
        callbacks.clear()
        await app.process_update(edit)
        self.assertEqual(callbacks["seen"], "channel")
        environment["shop_message_handler"].assert_awaited()


if __name__ == "__main__":
    unittest.main()
