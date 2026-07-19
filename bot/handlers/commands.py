from telegram import Update
from telegram.ext import ContextTypes

from bot import database, messages


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(messages.WELCOME_MESSAGE, parse_mode="Markdown")


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    config = context.bot_data["config"]
    chat_id = update.effective_message.chat_id
    user_stats = await database.get_user_stats(config.db_path, chat_id)

    if not user_stats:
        await update.effective_message.reply_text("Nessun link registrato ancora. Iniziate a postare! 📭")
        return

    lines = ["*Statistiche del gruppo* 📊\n"]
    medals = ["🥇", "🥈", "🥉"]
    for i, stat in enumerate(user_stats):
        prefix = medals[i] if i < 3 else f"{i + 1}."
        name = messages.display_name(stat.username, stat.first_name)
        lines.append(
            f"{prefix} {_escape_md(name)}\n"
            f"   Links: {stat.link_count} | Doppioni: {stat.duplicate_count}"
        )

    await update.effective_message.reply_text("\n".join(lines), parse_mode="Markdown")


async def hall_of_shame(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    config = context.bot_data["config"]
    chat_id = update.effective_message.chat_id
    shamers = await database.get_hall_of_shame(config.db_path, chat_id)

    if not shamers:
        await update.effective_message.reply_text(
            "La Hall of Shame è vuota! Nessun doppione ancora. Bravi, per ora. 😏"
        )
        return

    lines = ["*Hall of Shame* 🏆🤌\n", "Il podio dei copincollatori seriali:\n"]
    medals = ["🥇", "🥈", "🥉"]
    for i, stat in enumerate(shamers):
        prefix = medals[i] if i < 3 else f"{i + 1}."
        name = messages.display_name(stat.username, stat.first_name)
        pct = round(stat.duplicate_count / stat.link_count * 100) if stat.link_count else 0
        dup_word = "doppione" if stat.duplicate_count == 1 else "doppioni"
        lines.append(
            f"{prefix} {_escape_md(name)} — {stat.duplicate_count} {dup_word} "
            f"su {stat.link_count} link ({pct}%)"
        )

    lines.append("\nLa vergogna è servita. 😤")
    await update.effective_message.reply_text("\n".join(lines), parse_mode="Markdown")


def _escape_md(text: str) -> str:
    """Escape special Markdown v1 characters."""
    for ch in ("_", "*", "`", "["):
        text = text.replace(ch, f"\\{ch}")
    return text
