import logging

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ChatMemberHandler, filters

from bot import database
from bot.config import Config
from bot.handlers import commands, member, message
from bot.handlers.filters import AllowedChatFilter


async def build_and_run() -> None:
    config = Config.from_env()

    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        level=getattr(logging, config.log_level, logging.INFO),
    )
    logger = logging.getLogger(__name__)
    logger.info("Starting ziotackus bot (allowed chat: %s)", config.allowed_chat_id)

    await database.init_db(config.db_path)

    app = ApplicationBuilder().token(config.bot_token).build()
    app.bot_data["config"] = config

    chat_filter = AllowedChatFilter(config.allowed_chat_id)

    app.add_handler(CommandHandler("start", commands.start, filters=chat_filter))
    app.add_handler(CommandHandler("stats", commands.stats, filters=chat_filter))
    app.add_handler(CommandHandler("hall_of_shame", commands.hall_of_shame, filters=chat_filter))
    app.add_handler(
        MessageHandler(
            (filters.TEXT | filters.CAPTION) & chat_filter & ~filters.COMMAND,
            message.handle_message,
        )
    )
    app.add_handler(ChatMemberHandler(member.on_chat_member_updated, ChatMemberHandler.MY_CHAT_MEMBER))

    await app.run_polling(allowed_updates=Update.ALL_TYPES)
