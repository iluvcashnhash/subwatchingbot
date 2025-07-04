from __future__ import annotations

import asyncio
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure

from .config import settings

class _MongoDBManager:
    _instance: Optional[_MongoDBManager] = None
    _lock = asyncio.Lock()
    _client: Optional[AsyncIOMotorClient] = None
    _db: Optional[AsyncIOMotorDatabase] = None
    _is_connected: bool = False
    _connection_string: str
    _db_name: str

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(_MongoDBManager, cls).__new__(cls)
            cls._connection_string = settings.MONGODB_URI
            cls._db_name = settings.DB_NAME
        return cls._instance

    async def _ensure_connected(self) -> None:
        """Ensure the database connection is established."""
        if not self._is_connected or not self._client or not self._db:
            async with self._lock:
                if not self._is_connected or not self._client or not self._db:
                    try:
                        self._client = AsyncIOMotorClient(
                            self._connection_string,
                            serverSelectionTimeoutMS=5000  # 5 second timeout
                        )
                        # Test the connection
                        await self._client.server_info()
                        self._db = self._client[self._db_name]
                        self._is_connected = True
                    except ConnectionFailure as e:
                        self._is_connected = False
                        raise ConnectionError(f"Failed to connect to MongoDB: {e}") from e

    async def get_client(self) -> AsyncIOMotorClient:
        """Get the MongoDB client instance.
        
        Returns:
            AsyncIOMotorClient: The MongoDB client instance.
            
        Raises:
            ConnectionError: If connection to MongoDB fails.
        """
        await self._ensure_connected()
        if not self._client:
            raise RuntimeError("MongoDB client not initialized")
        return self._client

    async def get_collection(self, name: str):
        """Get a collection from the database.
        
        Args:
            name: The name of the collection to retrieve.
            
        Returns:
            The requested collection.
            
        Raises:
            RuntimeError: If the database is not connected.
            ConnectionError: If connection to MongoDB fails.
        """
        await self._ensure_connected()
        if not self._db:
            raise RuntimeError("Database not connected")
        return self._db[name]

    async def close(self) -> None:
        """Close the MongoDB connection."""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
            self._is_connected = False

# Global instance
_db_manager = _MongoDBManager()

async def get_client() -> AsyncIOMotorClient:
    """Get the MongoDB client instance.
    
    Returns:
        AsyncIOMotorClient: The MongoDB client instance.
    """
    return await _db_manager.get_client()

async def get_collection(name: str):
    """Get a collection from the database.
    
    Args:
        name: The name of the collection to retrieve.
        
    Returns:
        The requested collection.
    """
    return await _db_manager.get_collection(name)

# For backward compatibility
class Database:
    """Legacy database interface for backward compatibility."""
    
    @classmethod
    async def connect_db(cls):
        """Initialize the database connection."""
        await _db_manager._ensure_connected()
    
    @classmethod
    async def close_db(cls):
        """Close the database connection."""
        await _db_manager.close()
    
    @classmethod
    async def get_collection(cls, collection_name: str):
        """Get a collection by name."""
        return await get_collection(collection_name)

# Initialize database connection
db = Database()
