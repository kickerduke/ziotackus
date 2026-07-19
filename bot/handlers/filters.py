import logging

from telegram import Message
from telegram.ext import filters

logger = logging.getLogger(__name__)


class AllowedChatFilter(filters.MessageFilter):
    def __init__(self, allowed_chat_id: int) -> None:
        self.allowed_chat_id = allowed_chat_id
        super().__init__()

    def filter(self, message: Message) -> bool:
        match = message.chat_id == self.allowed_chat_id
        if not match:
            logger.warning("Rejected message from chat_id=%s (allowed: %s)", message.chat_id, self.allowed_chat_id)
        return match
