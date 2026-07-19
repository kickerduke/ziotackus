from telegram import Message
from telegram.ext import filters


class AllowedChatFilter(filters.MessageFilter):
    def __init__(self, allowed_chat_id: int) -> None:
        self.allowed_chat_id = allowed_chat_id
        super().__init__()

    def filter(self, message: Message) -> bool:
        return message.chat_id == self.allowed_chat_id
