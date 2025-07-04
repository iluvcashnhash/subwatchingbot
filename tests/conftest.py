"""Pytest configuration and fixtures for testing SubWatch Bot."""
import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram import Update, Message, Chat, User as TelegramUser
from telegram.ext import CallbackContext

# Disable logging during tests
logging.disable(logging.CRITICAL)

@pytest.fixture
def mock_update():
    """Create a mock Update object."""
    update = AsyncMock(spec=Update)
    update.effective_chat = AsyncMock(spec=Chat, id=12345, type="private")
    update.effective_user = AsyncMock(spec=TelegramUser, id=12345, first_name="Test", is_bot=False)
    update.message = AsyncMock(spec=Message, text="/start", chat=update.effective_chat, from_user=update.effective_user)
    return update

@pytest.fixture
def mock_context():
    """Create a mock Context object."""
    context = MagicMock(spec=CallbackContext)
    context.bot = AsyncMock()
    context.args = []
    context.job_queue = AsyncMock()
    context.user_data = {}
    context.chat_data = {}
    context.bot_data = {}
    return context

@pytest.fixture
def mock_application():
    """Create a mock Application object."""
    app = AsyncMock()
    app.bot = AsyncMock()
    app.job_queue = AsyncMock()
    return app

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

# Mock MongoDB for testing
@pytest.fixture
def mock_mongodb():
    """Create a mock MongoDB client and database."""
    with patch('motor.motor_asyncio.AsyncIOMotorClient') as mock_client:
        mock_db = AsyncMock()
        mock_collection = AsyncMock()
        
        # Setup mock database and collection
        mock_client.return_value = AsyncMock()
        mock_client.return_value.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value = mock_collection
        
        # Add test data helpers
        mock_collection.find = AsyncMock(return_value=AsyncMock())
        mock_collection.find_one = AsyncMock(return_value={})
        mock_collection.insert_one = AsyncMock(return_value=AsyncMock(inserted_id="test_id"))
        mock_collection.update_one = AsyncMock(return_value=AsyncMock())
        mock_collection.delete_one = AsyncMock(return_value=AsyncMock(deleted_count=1))
        
        yield mock_collection
