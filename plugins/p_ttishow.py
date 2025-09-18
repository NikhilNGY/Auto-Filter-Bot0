from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.errors.exceptions.bad_request_400 import MessageTooLong, PeerIdInvalid
from pyrogram.errors import ChatAdminRequired
from info import *
from database.users_chats_db import db
from database.ia_filterdb import Media, Media2, db as db_stats, db2 as db2_stats
from utils import get_size, temp, get_settings, get_readable_time
from Script import script
from bot import botStartTime
from logging_helper import LOGGER
import asyncio
import psutil
import time


"""----------------------------------------- https://t.me/KR_PICTURE -------------------"""


@Client.on_message(filters.new_chat_members & filters.group)
async def save_group(bot, message):
    r_j_check = [u.id for u in message.new_chat_members]

    # Bot added to a group
    if temp.ME in r_j_check:
        if not await db.get_chat(message.chat.id):
            try:
                total = await bot.get_chat_members_count(message.chat.id)
            except Exception as e:
                LOGGER.warning(f"Cannot fetch member count for {message.chat.id}: {e}")
                total = 0

            mention = message.from_user.mention if message.from_user else "Anonymous"
            await bot.send_message(
                LOG_CHANNEL,
                script.LOG_TEXT_G.format(message.chat.title, message.chat.id, total, mention),
            )
            await db.add_chat(message.chat.id, message.chat.title)

        # If group is banned
        if message.chat.id in temp.BANNED_CHATS:
            buttons = [[InlineKeyboardButton('📌 Contact Support 📌', url=OWNER_LNK)]]
            reply_markup = InlineKeyboardMarkup(buttons)
            k = await message.reply(
                text="<b>This chat is not allowed 🚫\n\nMy admins have restricted me from working here. "
                     "If you think this is a mistake, please contact support.</b>",
                reply_markup=reply_markup,
            )
            try:
                await k.pin()
            except Exception:
                pass
            await bot.leave_chat(message.chat.id)
            return

        # Normal welcome when bot is added
        buttons = [[InlineKeyboardButton("📌 Contact Support 📌", url=OWNER_LNK)]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await message.reply_text(
            text=f"<b>Thank you for adding me in {message.chat.title} ❣️\n\n"
                 "If you have any questions or doubts, contact support.</b>",
            reply_markup=reply_markup,
        )

        try:
            if message.from_user:
                await db.connect_group(message.chat.id, message.from_user)
        except Exception as e:
            LOGGER.error(f"DB error connecting group: {e}")

    # Normal users joining
    else:
        settings = await get_settings(message.chat.id)
        if settings.get("welcome"):
            for u in message.new_chat_members:
                old_welcome = temp.MELCOW.get("welcome")
                if old_welcome:
                    try:
                        await old_welcome.delete()
                    except Exception as e:
                        LOGGER.warning(f"Could not delete old welcome: {e}")

                try:
                    temp.MELCOW["welcome"] = await message.reply_video(
                        video=MELCOW_VID,
                        caption=script.MELCOW_ENG.format(u.mention, message.chat.title),
                        reply_markup=InlineKeyboardMarkup(
                            [[InlineKeyboardButton("📌 Contact Support 📌", url=OWNER_LNK)]]
                        ),
                        parse_mode=enums.ParseMode.HTML,
                    )
                except Exception as e:
                    LOGGER.error(f"Failed to send welcome video: {e}")

        if settings.get("auto_delete") and "welcome" in temp.MELCOW:
            await asyncio.sleep(10800)
            try:
                await temp.MELCOW["welcome"].delete()
                temp.MELCOW.pop("welcome", None)
            except Exception as e:
                LOGGER.warning(f"Auto delete failed: {e}")


@Client.on_message(filters.command("leave") & filters.user(ADMINS))
async def leave_a_chat(bot, message):
    if len(message.command) == 1:
        return await message.reply("Give me a chat id")
    chat = message.command[1]
    try:
        chat = int(chat)
    except Exception:
        pass
    try:
        buttons = [[InlineKeyboardButton("📌 Contact Support 📌", url=OWNER_LNK)]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await bot.send_message(
            chat_id=chat,
            text="<b>Hello friends,\nMy admin asked me to leave this group, so I must go. "
                 "\nIf you want to add me again, please contact support.</b>",
            reply_markup=reply_markup,
        )
        await bot.leave_chat(chat)
        await message.reply(f"Left the chat `{chat}`")
    except Exception as e:
        await message.reply(f"Error - {e}")


@Client.on_message(filters.command("disable") & filters.user(ADMINS))
async def disable_chat(bot, message):
    if len(message.command) == 1:
        return await message.reply("Give me a chat id")

    r = message.text.split(None)
    if len(r) > 2:
        reason = r[2]
        chat = r[1]
    else:
        chat = message.command[1]
        reason = "No reason provided"

    try:
        chat_ = int(chat)
    except Exception:
        return await message.reply("Give me a valid chat ID")

    cha_t = await db.get_chat(chat_)
    if not cha_t:
        return await message.reply("Chat not found in DB")
    if cha_t.get("is_disabled"):
        return await message.reply(
            f"This chat is already disabled:\nReason - <code>{cha_t['reason']}</code>"
        )

    await db.disable_chat(chat_, reason)
    temp.BANNED_CHATS.append(chat_)
    await message.reply("Chat successfully disabled")

    try:
        buttons = [[InlineKeyboardButton("📌 Contact Support 📌", url=OWNER_LNK)]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await bot.send_message(
            chat_id=chat_,
            text=f"<b>Hello friends,\nMy admin asked me to leave this group, so I must go. "
                 f"\nIf you want to add me again, please contact support.</b>\nReason: <code>{reason}</code>",
            reply_markup=reply_markup,
        )
        await bot.leave_chat(chat_)
    except Exception as e:
        await message.reply(f"Error - {e}")


@Client.on_message(filters.command("enable") & filters.user(ADMINS))
async def re_enable_chat(bot, message):
    if len(message.command) == 1:
        return await message.reply("Give me a chat id")
    chat = message.command[1]
    try:
        chat_ = int(chat)
    except Exception:
        return await message.reply("Give me a valid chat ID")

    sts = await db.get_chat(chat_)
    if not sts:
        return await message.reply("Chat not found in DB")
    if not sts.get("is_disabled"):
        return await message.reply("This chat is not disabled.")

    await db.re_enable_chat(chat_)
    if chat_ in temp.BANNED_CHATS:
        temp.BANNED_CHATS.remove(chat_)
    await message.reply("Chat successfully re-enabled")


@Client.on_message(filters.command("stats") & filters.user(ADMINS))
async def get_stats(bot, message):
    try:
        SilentXBotz = await message.reply("Accessing status details...")
        total_users = await db.total_users_count()
        totl_chats = await db.total_chat_count()
        premium = await db.all_premium_users()
        file1 = await Media.count_documents()
        DB_SIZE = 512 * 1024 * 1024

        dbstats = await db_stats.command("dbStats")
        db_size = dbstats["dataSize"]
        free = DB_SIZE - db_size

        uptime = get_readable_time(time.time() - botStartTime)
        ram = psutil.virtual_memory().percent
        cpu = psutil.cpu_percent()

        if not MULTIPLE_DB:
            await SilentXBotz.edit(
                script.STATUS_TXT.format(
                    total_users,
                    totl_chats,
                    premium,
                    file1,
                    get_size(db_size),
                    get_size(free),
                    uptime,
                    ram,
                    cpu,
                )
            )
            return

        file2 = await Media2.count_documents()
        db2stats = await db2_stats.command("dbStats")
        db2_size = db2stats["dataSize"]
        free2 = DB_SIZE - db2_size

        await SilentXBotz.edit(
            script.MULTI_STATUS_TXT.format(
                total_users,
                totl_chats,
                premium,
                file1,
                get_size(db_size),
                get_size(free),
                file2,
                get_size(db2_size),
                get_size(free2),
                uptime,
                ram,
                cpu,
                (int(file1) + int(file2)),
            )
        )
    except Exception as e:
        LOGGER.error(e)


@Client.on_message(filters.command("invite") & filters.user(ADMINS))
async def gen_invite(bot, message):
    if len(message.command) == 1:
        return await message.reply("Give me a chat id")
    chat = message.command[1]
    try:
        chat = int(chat)
    except Exception:
        return await message.reply("Give me a valid chat ID")

    try:
        link = await bot.create_chat_invite_link(chat)
    except ChatAdminRequired:
        return await message.reply("Invite link generation failed: not enough rights")
    except Exception as e:
        return await message.reply(f"Error {e}")

    await message.reply(f"Here is your invite link: {link.invite_link}")


@Client.on_message(filters.command("ban") & filters.user(ADMINS))
async def ban_a_user(bot, message):
    if len(message.command) == 1:
        return await message.reply("Give me a user id / username")

    r = message.text.split(None)
    if len(r) > 2:
        reason = r[2]
        chat = r[1]
    else:
        chat = message.command[1]
        reason = "No reason provided"

    try:
        k = await bot.get_users(chat)
    except PeerIdInvalid:
        return await message.reply("Invalid user: make sure I have met them before.")
    except IndexError:
        return await message.reply("This might be a channel, not a user.")
    except Exception as e:
        return await message.reply(f"Error - {e}")

    jar = await db.get_ban_status(k.id)
    if jar.get("is_banned"):
        return await message.reply(
            f"{k.mention} is already banned\nReason: {jar['ban_reason']}"
        )

    await db.ban_user(k.id, reason)
    temp.BANNED_USERS.append(k.id)
    await message.reply(f"Successfully banned {k.mention}")


@Client.on_message(filters.command("unban") & filters.user(ADMINS))
async def unban_a_user(bot, message):
    if len(message.command) == 1:
        return await message.reply("Give me a user id / username")

    chat = message.command[1]
    try:
        k = await bot.get_users(chat)
    except PeerIdInvalid:
        return await message.reply("Invalid user: make sure I have met them before.")
    except IndexError:
        return await message.reply("This might be a channel, not a user.")
    except Exception as e:
        return await message.reply(f"Error - {e}")

    jar = await db.get_ban_status(k.id)
    if not jar.get("is_banned"):
        return await message.reply(f"{k.mention} is not banned.")

    await db.remove_ban(k.id)
    if k.id in temp.BANNED_USERS:
        temp.BANNED_USERS.remove(k.id)
    await message.reply(f"Successfully unbanned {k.mention}")


@Client.on_message(filters.command("users") & filters.user(ADMINS))
async def list_users(bot, message):
    raju = await message.reply("Getting list of users...")
    users = await db.get_all_users()
    out = "Users saved in DB:\n\n"

    async for user in users:
        out += f"<a href=tg://user?id={user['id']}>{user['name']}</a>"
        if user["ban_status"]["is_banned"]:
            out += " (Banned)"
        out += "\n"

    try:
        await raju.edit_text(out)
    except MessageTooLong:
        with open("users.txt", "w+", encoding="utf-8") as outfile:
            outfile.write(out)
        await message.reply_document("users.txt", caption="List of users")


@Client.on_message(filters.command("chats") & filters.user(ADMINS))
async def list_chats(bot, message):
    raju = await message.reply("Getting list of chats...")
    chats = await db.get_all_chats()
    out = "Chats saved in DB:\n\n"

    async for chat in chats:
        out += f"**Title:** `{chat['title']}`\n**ID:** `{chat['id']}`"
        if chat["chat_status"]["is_disabled"]:
            out += " (Disabled)"
        out += "\n"

    try:
        await raju.edit_text(out)
    except MessageTooLong:
        with open("chats.txt", "w+", encoding="utf-8") as outfile:
            outfile.write(out)
        await message.reply_document("chats.txt", caption="List of chats")
