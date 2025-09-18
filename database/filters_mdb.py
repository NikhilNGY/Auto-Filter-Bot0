import pymongo
from info import DATABASE_URI, DATABASE_NAME
from pyrogram import enums
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

# ----------------- MongoDB Connection -----------------
myclient = pymongo.MongoClient(DATABASE_URI)
mydb = myclient[DATABASE_NAME]


# ----------------- ADD OR UPDATE FILTER -----------------
async def add_filter(grp_id: int, text: str, reply_text: str, btn, file, alert):
    mycol = mydb[str(grp_id)]
    data = {
        'text': str(text),
        'reply': str(reply_text) if reply_text else "",
        'btn': str(btn) if btn else "[]",
        'file': str(file) if file else None,
        'alert': str(alert) if alert else None
    }
    try:
        mycol.update_one({'text': str(text)}, {"$set": data}, upsert=True)
    except Exception:
        logger.exception("Error in add_filter", exc_info=True)


# ----------------- FIND FILTER -----------------
async def find_filter(grp_id: int, name: str):
    mycol = mydb[str(grp_id)]
    try:
        doc = mycol.find_one({'text': name})
        if doc:
            reply_text = doc.get('reply', None)
            btn = doc.get('btn', None)
            fileid = doc.get('file', None)
            alert = doc.get('alert', None)
            return reply_text, btn, alert, fileid
    except Exception:
        logger.exception("Error in find_filter", exc_info=True)
    return None, None, None, None


# ----------------- GET ALL FILTERS -----------------
async def get_filters(grp_id: int):
    mycol = mydb[str(grp_id)]
    texts = []
    try:
        for doc in mycol.find({}, {'text': 1, '_id': 0}):
            texts.append(doc['text'])
    except Exception:
        logger.exception("Error in get_filters", exc_info=True)
    return texts


# ----------------- DELETE FILTER -----------------
async def delete_filter(message, text: str, grp_id: int):
    mycol = mydb[str(grp_id)]
    query = {'text': text}
    count = mycol.count_documents(query)
    if count:
        mycol.delete_one(query)
        await message.reply_text(
            f"'`{text}`' deleted. I won't respond to that filter anymore.",
            quote=True,
            parse_mode=enums.ParseMode.MARKDOWN
        )
    else:
        await message.reply_text("Couldn't find that filter!", quote=True)


# ----------------- DELETE ALL FILTERS -----------------
async def del_all(message, grp_id: int, title: str):
    if str(grp_id) not in mydb.list_collection_names():
        await message.edit_text(f"Nothing to remove in {title}!")
        return
    try:
        mydb[str(grp_id)].drop()
        await message.edit_text(f"All filters from {title} have been removed")
    except Exception:
        await message.edit_text("Couldn't remove all filters from group!")
        logger.exception("Error in del_all", exc_info=True)


# ----------------- COUNT FILTERS -----------------
async def count_filters(grp_id: int):
    mycol = mydb[str(grp_id)]
    try:
        return mycol.count_documents({}) or 0
    except Exception:
        logger.exception("Error in count_filters", exc_info=True)
        return 0


# ----------------- FILTER STATS -----------------
async def filter_stats():
    collections = mydb.list_collection_names()
    if "CONNECTION" in collections:
        collections.remove("CONNECTION")

    total_count = 0
    for col_name in collections:
        try:
            total_count += mydb[col_name].count_documents({})
        except Exception:
            logger.exception(f"Error counting collection {col_name}", exc_info=True)

    return len(collections), total_count
