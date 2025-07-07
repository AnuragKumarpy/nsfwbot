import logging
import os

from telegram.ext import (
    Application,
    CommandHandler,
    ChatMemberHandler,
    MessageHandler,
    CallbackQueryHandler,
    PicklePersistence,
    filters,
)

import config
from bot.utils import database as db
from bot.utils import ai_models
from bot.handlers import core_handlers, media_handler
from bot.handlers import callback_handlers

# --- Logging Setup ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.DEBUG, # Ensure this is DEBUG
)
# Reduce logging noise from common libraries
logging.getLogger("httpx").setLevel(logging.WARNING)
# --- ADDED: Ensure our own loggers are also at DEBUG level ---
logging.getLogger("bot.utils.ai_models").setLevel(logging.DEBUG)


logger = logging.getLogger(__name__)


def main() -> None:
    """Start the bot."""
    if not config.TELEGRAM_BOT_TOKEN:
        logger.critical("TELEGRAM_BOT_TOKEN not found. Please set it in .env file.")
        return

    os.makedirs(config.DATA_PATH, exist_ok=True)
    os.makedirs(config.LOCAL_MODELS_BASE_DIR, exist_ok=True)
    
    db.init_db()

    logger.info("Loading AI models...")
    ai_models.load_models()
    logger.info("AI models loaded.")

    persistence = PicklePersistence(filepath=config.PERSISTENCE_PATH)
    
    application = (
        Application.builder()
        .token(config.TELEGRAM_BOT_TOKEN)
        .persistence(persistence)
        .build()
    )

    # --- Register Handlers ---
    application.add_handler(CommandHandler("start", core_handlers.start))
    application.add_handler(
        ChatMemberHandler(
            core_handlers.handle_chat_member, ChatMemberHandler.MY_CHAT_MEMBER
        )
    )

    media_filter = (
        filters.PHOTO | filters.Sticker.ALL | filters.VIDEO | filters.ANIMATION
    )
    application.add_handler(
        MessageHandler(
            media_filter & ~filters.COMMAND, media_handler.handle_media
        )
    )
    
    application.add_handler(CallbackQueryHandler(callback_handlers.button_handler))


    # --- Start Bot ---
    logger.info("Starting bot...")
    application.run_polling()


if __name__ == "__main__":
    main()