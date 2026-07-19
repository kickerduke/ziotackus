import logging

from telegram import Update
from telegram.ext import ContextTypes

from bot import messages

logger = logging.getLogger(__name__)


async def on_chat_member_updated(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send the welcome message when the bot is added to the allowed chat."""
    result = update.my_chat_member
    if result is None:
        return

    config = context.bot_data["config"]
    if result.chat.id != config.allowed_chat_id:
        return

    new_status = result.new_chat_member.status
    old_status = result.old_chat_member.status

    bot_joined = new_status in ("member", "administrator") and old_status in ("left", "kicked", "restricted")
    if not bot_joined:
        return

    logger.info("Bot added to allowed chat %s, sending welcome message.", result.chat.id)
    await context.bot.send_message(chat_id=result.chat.id, text=messages.WELCOME_MESSAGE, parse_mode="Markdown")
