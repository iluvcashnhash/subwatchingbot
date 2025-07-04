"""Tests for database operations in SubWatch Bot."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from motor.motor_asyncio import AsyncIOMotorCollection
from app.db import get_client, get_collection

class TestDatabaseOperations:
    """Test database connection and operations."""
    
    @pytest.mark.asyncio
    async def test_get_client_singleton(self):
        """Test that get_client returns a singleton instance."""
        with patch('motor.motor_asyncio.AsyncIOMotorClient') as mock_client:
            # First call
            client1 = await get_client()
            # Second call should return the same instance
            client2 = await get_client()
            
            assert client1 is client2
            mock_client.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_collection(self, mock_mongodb):
        """Test getting a collection from the database."""
        # Mock the client
        with patch('app.db.get_client', return_value=AsyncMock()):
            # Get a test collection
            collection = await get_collection("test_collection")
            
            # Verify it's a collection
            assert isinstance(collection, AsyncIOMotorCollection)
            
            # Test that getting the same collection returns the same instance
            same_collection = await get_collection("test_collection")
            assert collection is same_collection
            
            # Test getting a different collection
            other_collection = await get_collection("other_collection")
            assert collection is not other_collection
    
    @pytest.mark.asyncio
    async def test_database_operations(self, mock_mongodb):
        """Test basic database operations."""
        # Test insert
        result = await mock_mongodb.insert_one({"test": "data"})
        assert result.inserted_id == "test_id"
        
        # Test find
        cursor = await mock_mongodb.find({"test": "data"})
        assert cursor is not None
        
        # Test update
        update_result = await mock_mongodb.update_one(
            {"test": "data"}, 
            {"$set": {"updated": True}}
        )
        assert update_result is not None
        
        # Test delete
        delete_result = await mock_mongodb.delete_one({"test": "data"})
        assert delete_result.deleted_count == 1
