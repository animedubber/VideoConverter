import logging
import motor.motor_asyncio
from config import MONGO_URI, DATABASE_NAME, USERS_COLLECTION, TASKS_COLLECTION

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        try:
            self.client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
            self.db = self.client[DATABASE_NAME]
            self.users = self.db[USERS_COLLECTION]
            self.tasks = self.db[TASKS_COLLECTION]
            logger.info("MongoDB connection established")
        except Exception as e:
            logger.error(f"MongoDB connection error: {e}")
            raise

    async def get_user_settings(self, user_id: int):
        """Get user settings or create default if not exists"""
        try:
            user = await self.users.find_one({"user_id": user_id})
            if not user:
                default_settings = {
                    "user_id": user_id,
                    "rename_file": False,
                    "upload_mode": "default",
                }
                await self.users.insert_one(default_settings)
                return default_settings
            return user
        except Exception as e:
            logger.error(f"Error getting user settings: {e}")
            # Return default settings in case of error
            return {
                "user_id": user_id,
                "rename_file": False,
                "upload_mode": "default",
            }

    async def update_user_settings(self, user_id: int, field: str, value):
        """Update specific user setting"""
        try:
            await self.users.update_one(
                {"user_id": user_id}, 
                {"$set": {field: value}}
            )
            return True
        except Exception as e:
            logger.error(f"Error updating user settings: {e}")
            return False

    async def create_task(self, user_id: int, task_data: dict):
        """Create a new task for user"""
        try:
            task_data["user_id"] = user_id
            task_data["status"] = "pending"
            result = await self.tasks.insert_one(task_data)
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error creating task: {e}")
            return None

    async def update_task(self, task_id: str, update_data: dict):
        """Update task data"""
        try:
            from bson.objectid import ObjectId
            await self.tasks.update_one(
                {"_id": ObjectId(task_id)}, 
                {"$set": update_data}
            )
            return True
        except Exception as e:
            logger.error(f"Error updating task: {e}")
            return False

    async def get_task(self, task_id: str):
        """Get task by ID"""
        try:
            from bson.objectid import ObjectId
            return await self.tasks.find_one({"_id": ObjectId(task_id)})
        except Exception as e:
            logger.error(f"Error getting task: {e}")
            return None

    async def get_pending_task(self, user_id: int):
        """Get latest pending task for user"""
        try:
            return await self.tasks.find_one(
                {"user_id": user_id, "status": "pending"},
                sort=[("_id", -1)]
            )
        except Exception as e:
            logger.error(f"Error getting pending task: {e}")
            return None
