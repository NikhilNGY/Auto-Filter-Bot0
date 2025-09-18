import pymongo
import logging
from info import DATABASE_URI, DATABASE_NAME

# ------------------------------
# Logger Setup
# ------------------------------
logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

# ------------------------------
# Database Setup
# ------------------------------
client = pymongo.MongoClient(DATABASE_URI)
db = client[DATABASE_NAME]
CONNECTIONS = db['CONNECTION']

# ------------------------------
# Connection Functions
# ------------------------------

async def add_connection(group_id: int, user_id: int) -> bool:
    """Add a connection of a user to a group."""
    try:
        query = CONNECTIONS.find_one({"_id": user_id})
        group_details = {"group_id": group_id}

        if query:
            group_ids = [x["group_id"] for x in query.get("group_details", [])]
            if group_id in group_ids:
                return False  # Already connected

            CONNECTIONS.update_one(
                {"_id": user_id},
                {"$push": {"group_details": group_details}, "$set": {"active_group": group_id}}
            )
            return True
        else:
            data = {
                "_id": user_id,
                "group_details": [group_details],
                "active_group": group_id
            }
            CONNECTIONS.insert_one(data)
            return True
    except Exception as e:
        logger.exception(f"Failed to add connection: {e}", exc_info=True)
        return False


async def active_connection(user_id: int) -> int | None:
    """Return the active group ID for a user in PM."""
    try:
        query = CONNECTIONS.find_one({"_id": user_id}, {"_id": 0, "group_details": 0})
        if query:
            return int(query.get("active_group"))
    except Exception as e:
        logger.exception(f"Failed to get active connection: {e}", exc_info=True)
    return None


async def all_connections(user_id: int) -> list[int] | None:
    """Return a list of all groups connected to the user."""
    try:
        query = CONNECTIONS.find_one({"_id": user_id}, {"_id": 0, "active_group": 0})
        if query:
            return [x["group_id"] for x in query.get("group_details", [])]
    except Exception as e:
        logger.exception(f"Failed to get all connections: {e}", exc_info=True)
    return None


async def if_active(user_id: int, group_id: int) -> bool:
    """Check if a specific group is the user's active group."""
    try:
        query = CONNECTIONS.find_one({"_id": user_id}, {"_id": 0, "group_details": 0})
        return query is not None and query.get("active_group") == group_id
    except Exception as e:
        logger.exception(f"Failed to check active group: {e}", exc_info=True)
        return False


async def make_active(user_id: int, group_id: int) -> bool:
    """Set a specific group as active for the user."""
    try:
        result = CONNECTIONS.update_one({"_id": user_id}, {"$set": {"active_group": group_id}})
        return result.modified_count > 0
    except Exception as e:
        logger.exception(f"Failed to make group active: {e}", exc_info=True)
        return False


async def make_inactive(user_id: int) -> bool:
    """Remove active group for a user."""
    try:
        result = CONNECTIONS.update_one({"_id": user_id}, {"$set": {"active_group": None}})
        return result.modified_count > 0
    except Exception as e:
        logger.exception(f"Failed to make group inactive: {e}", exc_info=True)
        return False


async def delete_connection(user_id: int, group_id: int) -> bool:
    """Delete a specific connection of the user to a group."""
    try:
        result = CONNECTIONS.update_one(
            {"_id": user_id},
            {"$pull": {"group_details": {"group_id": group_id}}}
        )
        if result.modified_count == 0:
            return False

        # Handle active group logic
        query = CONNECTIONS.find_one({"_id": user_id})
        group_details = query.get("group_details", [])

        if group_details:
            if query.get("active_group") == group_id:
                # Set the last group as active
                new_active = group_details[-1]["group_id"]
                CONNECTIONS.update_one({"_id": user_id}, {"$set": {"active_group": new_active}})
        else:
            CONNECTIONS.update_one({"_id": user_id}, {"$set": {"active_group": None}})

        return True
    except Exception as e:
        logger.exception(f"Failed to delete connection: {e}", exc_info=True)
        return False
