from motor.motor_asyncio import AsyncIOMotorClient
from .config import settings

class Database:
    client: AsyncIOMotorClient = None
    db = None

    @classmethod
    async def connect_db(cls):
        cls.client = AsyncIOMotorClient(settings.MONGODB_URL)
        cls.db = cls.client[settings.DB_NAME]

    @classmethod
    async def close_db(cls):
        if cls.client:
            await cls.client.close()
            cls.client = None
            cls.db = None

    @classmethod
    def get_collection(cls, collection_name: str):
        if not cls.db:
            raise RuntimeError("Database not connected")
        return cls.db[collection_name]

# Initialize database connection
db = Database()
