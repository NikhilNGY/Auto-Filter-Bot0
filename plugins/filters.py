import io
import asyncio
from pyrogram import filters, Client, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database.filters_mdb import add_filter, get_filters, delete_filter, count_filters
from database.connections_mdb import active_connection
from utils import get_file_id, parser, split_quotes
from info import ADMINS

# ---------------- ADD FILTER ----------------
@Client.on_message(filters.command(['filter', 'addf']) & filters.incoming)
async def addfilter(client, message):
    user = message.from_user
    if not user:
        return await message.reply(f"You are anonymous. Use /connect {message.chat.id} in PM.")

    userid = user.id
    chat_type = message.chat.type
    args = message.text.html.split(None, 1)

    # Determine group
    if chat_type == enums.ChatType.PRIVATE:
        grpid = await active_connection(str(userid))
        if not grpid:
            return await message.reply_text("I'm not connected to any groups!", quote=True)
        grp_id = grpid
        try:
            chat = await client.get_chat(grpid)
            title = chat.title
        except:
            return await message.reply_text("Make sure I'm present in your group!", quote=True)

    elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        grp_id = message.chat.id
        title = message.chat.title
    else:
        return

    # Check admin
    member = await client.get_chat_member(grp_id, userid)
    if member.status not in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER] and str(userid) not in ADMINS:
        return

    if len(args) < 2:
        return await message.reply_text("Command incomplete :(", quote=True)

    extracted = split_quotes(args[1])
    keyword = extracted[0].lower()

    # Determine reply content
    fileid, reply_text, btn, alert = None, None, None, None

    if message.reply_to_message:
        msg = message.reply_to_message
        if msg.reply_markup:
            btn = msg.reply_markup.inline_keyboard
            fileid_msg = get_file_id(msg)
            fileid = fileid_msg.file_id if fileid_msg else None
            reply_text = msg.caption.html if msg.caption else msg.text.html
        elif msg.media:
            fileid_msg = get_file_id(msg)
            fileid = fileid_msg.file_id if fileid_msg else None
            reply_text, btn, alert = parser(msg.caption.html if msg.caption else "", keyword)
        elif msg.text:
            reply_text, btn, alert = parser(msg.text.html, keyword)
    else:
        if len(extracted) >= 2:
            reply_text, btn, alert = parser(extracted[1], keyword)
        else:
            return await message.reply_text("Add some content to save your filter!", quote=True)

    if not reply_text and (not btn or btn == "[]"):
        return await message.reply_text("You cannot have buttons alone. Provide text too!", quote=True)

    await add_filter(grp_id, keyword, reply_text, btn, fileid, alert)

    await message.reply_text(
        f"Filter for `{keyword}` added in **{title}**",
        quote=True,
        parse_mode=enums.ParseMode.MARKDOWN
    )

# ---------------- VIEW FILTERS ----------------
@Client.on_message(filters.command(['viewfilters', 'filters']) & filters.incoming)
async def viewfilters(client, message):
    user = message.from_user
    if not user:
        return await message.reply(f"You are anonymous. Use /connect {message.chat.id} in PM.")

    userid = user.id
    chat_type = message.chat.type

    if chat_type == enums.ChatType.PRIVATE:
        grpid = await active_connection(str(userid))
        if not grpid:
            return await message.reply_text("I'm not connected to any groups!", quote=True)
        grp_id = grpid
        try:
            chat = await client.get_chat(grpid)
            title = chat.title
        except:
            return await message.reply_text("Make sure I'm present in your group!", quote=True)
    else:
        grp_id = message.chat.id
        title = message.chat.title

    member = await client.get_chat_member(grp_id, userid)
    if member.status not in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER] and str(userid) not in ADMINS:
        return

    filters_list = await get_filters(grp_id)
    total = await count_filters(grp_id)

    if total:
        text = f"Total filters in **{title}**: {total}\n\n"
        for f in filters_list:
            text += f" × `{f}`\n"

        if len(text) > 4096:
            with io.BytesIO(str.encode(text.replace('`',''))) as file:
                file.name = "filters.txt"
                await message.reply_document(document=file, quote=True)
            return
    else:
        text = f"No active filters in **{title}**"

    await message.reply_text(text, quote=True, parse_mode=enums.ParseMode.MARKDOWN)

# ---------------- DELETE FILTER ----------------
@Client.on_message(filters.command('del') & filters.incoming)
async def delfilter(client, message):
    user = message.from_user
    if not user:
        return await message.reply(f"You are anonymous. Use /connect {message.chat.id} in PM.")

    userid = user.id
    chat_type = message.chat.type

    if chat_type == enums.ChatType.PRIVATE:
        grpid = await active_connection(str(userid))
        if not grpid:
            return await message.reply_text("I'm not connected to any groups!", quote=True)
        grp_id = grpid
        try:
            chat = await client.get_chat(grpid)
            title = chat.title
        except:
            return await message.reply_text("Make sure I'm present in your group!", quote=True)
    else:
        grp_id = message.chat.id
        title = message.chat.title

    member = await client.get_chat_member(grp_id, userid)
    if member.status not in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER] and str(userid) not in ADMINS:
        return

    try:
        _, keyword = message.text.split(None, 1)
    except:
        return await message.reply_text(
            "<i>Mention the filtername to delete!</i>\n<code>/del filtername</code>\nUse /viewfilters to see all",
            quote=True
        )

    await delete_filter(message, keyword.lower(), grp_id)

# ---------------- DELETE ALL ----------------
@Client.on_message(filters.command('delall') & filters.incoming)
async def delall(client, message):
    user = message.from_user
    if not user:
        return await message.reply(f"You are anonymous. Use /connect {message.chat.id} in PM.")

    userid = user.id
    chat_type = message.chat.type

    if chat_type == enums.ChatType.PRIVATE:
        grpid = await active_connection(str(userid))
        if not grpid:
            return await message.reply_text("I'm not connected to any groups!", quote=True)
        grp_id = grpid
        try:
            chat = await client.get_chat(grpid)
            title = chat.title
        except:
            return await message.reply_text("Make sure I'm present in your group!", quote=True)
    else:
        grp_id = message.chat.id
        title = message.chat.title

    member = await client.get_chat_member(grp_id, userid)
    if member.status == enums.ChatMemberStatus.OWNER or str(userid) in ADMINS:
        await message.reply_text(
            f"This will delete all filters from '{title}'.\nDo you want to continue?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("YES", callback_data="delallconfirm")],
                [InlineKeyboardButton("CANCEL", callback_data="delallcancel")]
            ]),
            quote=True
              )
