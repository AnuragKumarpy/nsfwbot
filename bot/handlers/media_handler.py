import logging
import os
import tempfile
import uuid
import ffmpeg  # type: ignore

from telegram import Update, File, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ExtBot
from telegram.constants import ChatType, ChatAction, ParseMode
from telegram.error import TelegramError

import config
from bot.utils import database as db
from bot.utils import ai_models

logger = logging.getLogger(__name__)


async def _delete_message_after(context: ContextTypes.DEFAULT_TYPE):
    """Callback job to delete a message."""
    try:
        await context.bot.delete_message(
            chat_id=context.job.chat_id, message_id=context.job.data["message_id"]
        )
        logger.info(f"Auto-deleted warning message in chat {context.job.chat_id}")
    except TelegramError as e:
        logger.warning(
            f"Failed to auto-delete warning message in {context.job.chat_id}: {e}"
        )


async def _extract_frame(video_path: str, image_path: str) -> bool:
    """Extracts a single frame from a video file."""
    try:
        (
            ffmpeg.input(video_path, ss=1)
            .output(image_path, vframes=1)
            .overwrite_output()
            .run(cmd="ffmpeg", capture_stdout=True, capture_stderr=True)
        )
        return os.path.exists(image_path)
    except ffmpeg.Error as e:
        logger.error(f"FFmpeg error: {e.stderr.decode() if e.stderr else str(e)}")
        return False


async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles incoming media (photos, stickers, videos, GIFs)."""
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if not message or not chat or not user:
        return

    is_group = chat.type in (ChatType.GROUP, ChatType.SUPERGROUP)
    file_to_process: File | None = None
    media_type = "media"
    is_video = False
    file_unique_id = ""

    if message.photo:
        photo = message.photo[-1]
        file_to_process = await context.bot.get_file(photo.file_id)
        file_unique_id = photo.file_unique_id
        media_type = "photo"
    elif message.sticker:
        sticker = message.sticker
        file_to_process = await context.bot.get_file(sticker.file_id)
        file_unique_id = sticker.file_unique_id
        media_type = "sticker"
        is_video = sticker.is_video or sticker.is_animated
    elif message.animation:
        animation = message.animation
        file_to_process = await context.bot.get_file(animation.file_id)
        file_unique_id = animation.file_unique_id
        media_type = "GIF"
        is_video = True
    elif message.video:
        video = message.video
        file_to_process = await context.bot.get_file(video.file_id)
        file_unique_id = video.file_unique_id
        media_type = "video"
        is_video = True

    if not file_to_process or not file_unique_id:
        return

    # 1. Check for exceptions
    if is_group and db.check_media_exception(chat.id, file_unique_id):
        logger.info(f"Skipping whitelisted media {file_unique_id} in chat {chat.id}")
        return

    # 2. Download and prepare for analysis
    image_bytes = None
    with tempfile.TemporaryDirectory() as temp_dir:
        download_path = os.path.join(temp_dir, str(uuid.uuid4()))
        await file_to_process.download_to_drive(custom_path=download_path)
        if is_video:
            if chat.type == ChatType.PRIVATE:
                await context.bot.send_chat_action(chat.id, ChatAction.UPLOAD_PHOTO)
            frame_path = os.path.join(temp_dir, f"{uuid.uuid4()}.jpg")
            if await _extract_frame(download_path, frame_path):
                with open(frame_path, "rb") as f:
                    image_bytes = f.read()
        else:
            with open(download_path, "rb") as f:
                image_bytes = f.read()

    # 3. Analyze the image
    if not image_bytes:
        logger.warning(f"Could not extract bytes from {media_type} {file_unique_id}")
        return

    analysis = ai_models.analyze_image(image_bytes)
    if "error" in analysis:
        logger.error(f"Analysis failed for {media_type}: {analysis['error']}")
        return

    is_flagged = analysis.get("is_nsfw", False) or analysis.get("is_gore", False)

    # 4. Take Action
    if is_group and is_flagged:
        reasons = []
        if analysis.get("is_nsfw"):
            reasons.append("NSFW")
        if analysis.get("is_gore"):
            reasons.append("Gore/Violence")
        reasons_str = ", ".join(reasons)

        try:
            await message.delete()
            logger.info(
                f"Deleted flagged {media_type} ({reasons_str}) from {user.id} in chat {chat.id}"
            )

            keyboard = [
                [
                    # We will add a URL to the log entry later
                    # InlineKeyboardButton("View Log", url="https://t.me/your_log_channel"),
                    InlineKeyboardButton(
                        "🧐 Challenge", callback_data=f"challenge_{file_unique_id}"
                    ),
                    InlineKeyboardButton(
                        "✅ Allow Exception",
                        callback_data=f"allow_{chat.id}_{file_unique_id}",
                    ),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            notify_msg = await context.bot.send_message(
                chat_id=chat.id,
                text=f"Message from {user.mention_html()} deleted (Reason: {reasons_str}).",
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML,
            )

            # Schedule the warning message for deletion
            if config.WARNING_MSG_DELETE_SECONDS > 0:
                context.job_queue.run_once(
                    _delete_message_after,
                    config.WARNING_MSG_DELETE_SECONDS,
                    data={"message_id": notify_msg.message_id},
                    chat_id=chat.id,
                    name=f"delete_{chat.id}_{notify_msg.message_id}",
                )

        except Exception as e:
            logger.error(f"Failed during deletion/notification in {chat.id}: {e}")

    elif chat.type == ChatType.PRIVATE:
        nsfw_score = analysis.get("general_nsfw_score", 0.0) * 100
        gore_score = analysis.get("gore_violence_score", 0.0) * 100

        report = (
            "<b>Analysis Report</b>\n"
            f"General NSFW: <code>{nsfw_score:.1f}%</code>\n"
            f"Gore/Violence: <code>{gore_score:.1f}%</code>\n\n"
            f"<b>Status: {'&#9888;&#65039; FLAGGED' if is_flagged else '&#9989; SAFE'}</b>"
        )
        await message.reply_html(report)