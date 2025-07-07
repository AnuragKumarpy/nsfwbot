import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatMemberStatus

from bot.utils import database as db

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles the /start command.
    Adds the chat to the database and sends a welcome message.
    """
    user = update.effective_user
    chat = update.effective_chat
    # Ensure we have a message to reply to
    message = update.effective_message
    if not user or not chat or not message:
        return

    # Add the chat to our database
    db.add_chat(chat.id, chat.type)

    logger.info(
        f"User {user.username or user.id} started bot in chat {chat.id} ({chat.type})"
    )

    start_message = (
        f"Hello {user.mention_html()}! I am ready to help you.\n\n"
        f"<b>In Groups:</b> I require Admin permissions to delete messages. I will automatically "
        f"remove media that is flagged as NSFW or containing gore.\n"
        f"<b>In Private Chat:</b> You can send me media directly, and I will give you an analysis report."
    )
    await message.reply_html(start_message)


async def handle_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Tracks when the bot is added to or removed from a group.
    Updates the database accordingly.
    """
    if not update.my_chat_member:
        return

    chat = update.my_chat_member.chat
    new_status = update.my_chat_member.new_chat_member.status
    old_status = update.my_chat_member.old_chat_member.status

    logger.info(
        f"Bot status changed in chat {chat.id} ({chat.title}): {old_status} -> {new_status}"
    )

    if new_status in (ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR):
        # Bot was added or promoted
        db.add_chat(chat.id, chat.type)
        # You could add a welcome message to the group here if desired

    elif new_status in (ChatMemberStatus.LEFT, ChatMemberStatus.BANNED):
        # Bot was removed or kicked/banned
        db.set_chat_inactive(chat.id)