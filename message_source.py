import time


class MessageSourceTracker:
    def __init__(self, ttl_seconds=120, max_media_groups=1000, clock=time.monotonic):
        self.ttl_seconds = ttl_seconds
        self.max_media_groups = max_media_groups
        self.clock = clock
        self.authorized_media_groups = {}

    def is_anonymous(self, message):
        self._remove_expired_media_groups()

        if self._has_identifiable_source(message):
            return False

        media_group_key = self._media_group_key(message)
        return media_group_key not in self.authorized_media_groups

    def remember_authorized_media_group(self, message):
        if not self._has_identifiable_source(message):
            return

        media_group_key = self._media_group_key(message)
        if media_group_key is None:
            return

        self._remove_expired_media_groups()
        self.authorized_media_groups[media_group_key] = self.clock()

        while len(self.authorized_media_groups) > self.max_media_groups:
            self.authorized_media_groups.pop(next(iter(self.authorized_media_groups)))

    def _media_group_key(self, message):
        media_group_id = getattr(message, "media_group_id", None)
        if media_group_id is None:
            return None

        return getattr(message, "chat_id", None), media_group_id

    def _has_identifiable_source(self, message):
        if getattr(message, "author_signature", None):
            return True

        return any(
            getattr(message, field, None)
            for field in (
                "forward_origin",
                "forward_from",
                "forward_from_chat",
                "forward_sender_name",
                "forward_date",
            )
        )

    def _remove_expired_media_groups(self):
        expires_before = self.clock() - self.ttl_seconds
        for key, created_at in list(self.authorized_media_groups.items()):
            if created_at <= expires_before:
                del self.authorized_media_groups[key]
