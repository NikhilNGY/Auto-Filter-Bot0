import pymongo
from info import DATABASE_URI, DATABASE_NAME
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

myclient = pymongo.MongoClient(DATABASE_URI)
mydb = myclient[DATABASE_NAME]
mycol = mydb['CONNECTION']


# ------------------------------
# Add connection for user to a group
# ------------------------------
async def add_connection(group_id, user_id):
    query = mycol.find_one({"_id": user_id})
    group_details = {"group_id": group_id}

    if query:
        group_ids = [x["group_id"] for x in query.get("group_details", [])]
        if group_id in group_ids:
            return False
        try:
            mycol.update_one(
                {"_id": user_id},
                {"$push": {"group_details": group_details}, "$set": {"active_group": group_id}}
            )
            return True
        except Exception:
            logger.exception('Error adding connection', exc_info=True)
            return False
    else:
        data = {"_id": user_id, "group_details": [group_details], "active_group": group_id}
        try:
            mycol.insert_one(data)
            return True
        except Exception:
            logger.exception('Error inserting connection', exc_info=True)
            return False


# ------------------------------
# Get active group for user
# ------------------------------
async def active_connection(user_id):
    query = mycol.find_one({"_id": user_id}, {"active_group": 1})
    if query and query.get("active_group"):
        return int(query["active_group"])
    return None


# ------------------------------
# List all connections for a user
# ------------------------------
async def all_connections(user_id):
    query = mycol.find_one({"_id": user_id}, {"group_details": 1})
    if query and "group_details" in query:
        return [x["group_id"] for x in query["group_details"]]
    return []


# ------------------------------
# Check if a group is active for a user
# ------------------------------
async def if_active(user_id, group_id):
    query = mycol.find_one({"_id": user_id}, {"active_group": 1})
    return query and query.get("active_group") == group_id


# ------------------------------
# Make a group active
# ------------------------------
async def make_active(user_id, group_id):
    result = mycol.update_one({"_id": user_id}, {"$set": {"active_group": group_id}})
    return result.modified_count > 0


# ------------------------------
# Make all groups inactive
# ------------------------------
async def make_inactive(user_id):
    result = mycol.update_one({"_id": user_id}, {"$set": {"active_group": None}})
    return result.modified_count > 0


# ------------------------------
# Delete a user's connection to a group
# ------------------------------
async def delete_connection(user_id, group_id):
    try:
        result = mycol.update_one({"_id": user_id}, {"$pull": {"group_details": {"group_id": group_id}}})
        if result.modified_count == 0:
            return False

        query = mycol.find_one({"_id": user_id})
        if query and query.get("group_details"):
            if query.get("active_group") == group_id:
                last_group_id = query["group_details"][-1]["group_id"]
                mycol.update_one({"_id": user_id}, {"$set": {"active_group": last_group_id}})
        else:
            mycol.update_one({"_id": user_id}, {"$set": {"active_group": None}})
        return True
    except Exception as e:
        logger.exception(f"Error deleting connection: {e}", exc_info=True)
        return False
