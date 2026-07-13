import unittest
from types import SimpleNamespace

from message_source import MessageSourceTracker


class MessageSourceTrackerTests(unittest.TestCase):
    def setUp(self):
        self.now = 100
        self.tracker = MessageSourceTracker(clock=lambda: self.now)

    def message(self, chat_id=1, signature=None, media_group_id=None, **kwargs):
        return SimpleNamespace(
            chat_id=chat_id,
            author_signature=signature,
            media_group_id=media_group_id,
            **kwargs,
        )

    def test_keeps_unsigned_items_from_authorized_media_group(self):
        first_item = self.message(signature="Author", media_group_id="album")
        following_item = self.message(media_group_id="album")

        self.assertFalse(self.tracker.is_anonymous(first_item))
        self.tracker.remember_authorized_media_group(first_item)

        self.assertFalse(self.tracker.is_anonymous(following_item))

    def test_does_not_authorize_anonymous_media_group(self):
        anonymous_item = self.message(media_group_id="album")

        self.tracker.remember_authorized_media_group(anonymous_item)

        self.assertTrue(self.tracker.is_anonymous(anonymous_item))

    def test_keeps_forwarded_message_without_author_signature(self):
        forwarded_message = self.message(forward_origin=object())

        self.assertFalse(self.tracker.is_anonymous(forwarded_message))

    def test_media_group_authorization_is_limited_to_its_chat(self):
        first_item = self.message(chat_id=1, signature="Author", media_group_id="album")
        other_chat_item = self.message(chat_id=2, media_group_id="album")

        self.tracker.remember_authorized_media_group(first_item)

        self.assertTrue(self.tracker.is_anonymous(other_chat_item))

    def test_media_group_authorization_expires(self):
        first_item = self.message(signature="Author", media_group_id="album")
        following_item = self.message(media_group_id="album")
        self.tracker.remember_authorized_media_group(first_item)
        self.now += 121

        self.assertTrue(self.tracker.is_anonymous(following_item))


if __name__ == "__main__":
    unittest.main()
