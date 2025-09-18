import re
import logging
import asyncio
from pyrogram import Client, filters
from info import DELETE_CHANNELS
from database.ia_filterdb import Media, unpack_new_file_id

logger = logging.getLogger(__name__)

media_filter = filters.document | filters.video | filters.audio


@Client.on_message(filters.chat(DELETE_CHANNELS) & media_filter)
async def deletemultiplemedia(bot, message):
    """Delete multiple files from database & channel, then send silent confirmation (auto-delete in 30s)"""

    # Find media object
    media = None
    for file_type in ("document", "video", "audio"):
        media = getattr(message, file_type, None)
        if media:
            break
    if not media:
        return

    # Extract file_id
    try:
        file_id, file_ref = unpack_new_file_id(media.file_id)
    except Exception as e:
        logger.error(f"Failed to unpack file_id: {e}")
        return

    # Try delete by ID
    result = await Media.collection.delete_one({'_id': file_id})
    deleted_from_db = False

    if result.deleted_count:
        logger.info(f"✅ Deleted from DB by file_id: {media.file_name}")
        deleted_from_db = True
    else:
        # Fallback 1: normalized name
        normalized = re.sub(r"(_|\-|\.|\+)", " ", str(media.file_name))
        result = await Media.collection.delete_many({
            'file_name': normalized,
            'file_size': media.file_size,
            'mime_type': media.mime_type
        })
        if result.deleted_count:
            logger.info(f"✅ Deleted from DB by normalized name: {media.file_name}")
            deleted_from_db = True
        else:
            # Fallback 2: exact name
            result = await Media.collection.delete_many({
                'file_name': media.file_name,
                'file_size': media.file_size,
                'mime_type': media.mime_type
            })
            if result.deleted_count:
                logger.info(f"✅ Deleted from DB by exact name: {media.file_name}")
                deleted_from_db = True

    # Delete message from channel
    try:
        await message.delete()
        logger.info(f"🗑️ Deleted Telegram message: {media.file_name}")
    except Exception as e:
        logger.error(f"❌ Failed to delete message: {e}")

    # Silent confirmation (auto-delete after 30s)
    try:
        text = (
            f"✅ File deleted successfully.\n\n<b>File:</b> <code>{media.file_name}</code>"
            if deleted_from_db
            else f"⚠️ File not found in DB, but message removed.\n\n<b>File:</b> <code>{media.file_name}</code>"
        )
        confirm = await bot.send_message(
            chat_id=message.chat.id,
            text=text,
            disable_notification=True  # 🔇 No ping
        )
        await asyncio.sleep(30)
        await confirm.delete()
    except Exception as e:
        logger.error(f"❌ Failed to send/delete confirmation message: {e}")
