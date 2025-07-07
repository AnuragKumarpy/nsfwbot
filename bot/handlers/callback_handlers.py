import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query
    if not query or not query.data:
        return
    
    await query.answer() # Answer the callback to remove the "loading" state on the user's end.

    action = query.data.split("_")[0]

    if action == "challenge":
        logger.info(f"User {query.from_user.id} 'Challenged' media {query.data}")
        # We will add logic here to direct the user to the bot's PM
        await query.edit_message_text(text=f"{query.message.text}\n\n✅ Challenge noted.")

    elif action == "allow":
        logger.info(f"User {query.from_user.id} clicked 'Allow Exception' for {query.data}")
        # We will add admin checks and database logic here
        await query.edit_message_text(text=f"{query.message.text}\n\n⚠️ Admin action required.")