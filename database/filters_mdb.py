import pymongo
from info import DATABASE_URI, DATABASE_NAME
from pyrogram import enums
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

myclient = pymongo.MongoClient(DATABASE_URI)
mydb = myclient[DATABASE_NAME]


# ------------------------------
# Add / update filter
# ------------------------------
async def add_filter(grp_id, text, reply_text, btn, file, alert):
    mycol = mydb[str(grp_id)]
    data = {
        "text": str(text),
        "reply": str(reply_text),
        "btn": str(btn),
        "file": str(file),
        "alert": str(alert)
    }
    try:
        mycol.update_one({"text": str(text)}, {"$set": data}, upsert=True)
    except Exception:
        logger.exception("Error adding filter", exc_info=True)


# ------------------------------
# Get all filters for a group
# ------------------------------
async def get_filters(group_id):
    mycol = mydb[str(group_id)]
    texts = []
    try:
        for item in mycol.find():
            texts.append(item["text"])
    except Exception:
        pass
    return texts


# ------------------------------
# Delete single filter
# ------------------------------
async def delete_filter(message, text, group_id):
    mycol = mydb[str(group_id)]
    query = {"text": text}
    count = mycol.count_documents(query)
    if count == 1:
        mycol.delete_one(query)
        await message.reply_text(f"`{text}` deleted. I'll not respond to this filter anymore.",
                                 quote=True, parse_mode=enums.ParseMode.MARKDOWN)
    else:
        await message.reply_text("Couldn't find that filter!", quote=True)


# ------------------------------
# Delete all filters
# ------------------------------
async def del_all(message, group_id, title):
    if str(group_id) not in mydb.list_collection_names():
        await message.edit_text(f"Nothing to remove in {title}!")
        return
    mycol = mydb[str(group_id)]
    try:
        mycol.drop()
        await message.edit_text(f"All filters from {title} have been removed!")
    except Exception:
        await message.edit_text("Failed to remove filters from the group!")


# ------------------------------
# Count filters
# ------------------------------
async def count_filters(group_id):
    mycol = mydb[str(group_id)]
    return mycol.count_documents({})


# ------------------------------
# Get filter statistics
# ------------------------------
async def filter_stats():
    collections = mydb.list_collection_names()
    if "CONNECTION" in collections:
        collections.remove("CONNECTION")

    totalcount = 0
    for collection in collections:
        mycol = mydb[collection]
        totalcount += mycol.count_documents({})

    totalcollections = len(collections)
    return totalcollections, totalcount
