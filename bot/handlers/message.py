import logging
from datetime import datetime, timezone

from telegram import Update
from telegram.ext import ContextTypes

from bot import database, messages, normalizer

logger = logging.getLogger(__name__)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    if msg is None:
        return

    text = msg.text or msg.caption or ""
    if not text:
        return

    url_pairs = normalizer.extract_and_normalize_urls(text)
    if not url_pairs:
        return

    config = context.bot_data["config"]
    chat_id = msg.chat_id
    user = msg.from_user
    if user is None:
        return

    posted_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    for original_url, normalized_url in url_pairs:
        existing = await database.find_existing_link(config.db_path, chat_id, normalized_url)

        if existing is not None:
            shamer = messages.display_name(user.username, user.first_name)
            og_poster = messages.display_name(existing.username, existing.first_name)
            shame_text = messages.pick_shame_message(shamer, og_poster, existing.posted_at)

            await msg.reply_text(shame_text)

            await database.record_duplicate(
                config.db_path,
                original_link_id=existing.id,
                chat_id=chat_id,
                user_id=user.id,
                username=user.username,
                first_name=user.first_name,
                message_id=msg.message_id,
                posted_at=posted_at,
            )
            # Reply only once per message even if multiple duplicates are found
            return
        else:
            await database.record_link(
                config.db_path,
                chat_id=chat_id,
                normalized_url=normalized_url,
                original_url=original_url,
                user_id=user.id,
                username=user.username,
                first_name=user.first_name,
                message_id=msg.message_id,
                posted_at=posted_at,
            )
            logger.debug("Saved new link: %s (user %s)", normalized_url, user.id)
