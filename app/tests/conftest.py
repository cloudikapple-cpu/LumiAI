"""Pytest configuration and fixtures."""

import asyncio
from typing import AsyncIterator

import pytest
import pytest_asyncio


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def mock_session():
    """Mock database session for tests."""
    pass


@pytest_asyncio.fixture
async def mock_redis():
    """Mock Redis client for tests."""
    pass


@pytest.fixture
def mock_user():
    """Mock user data for tests."""
    return {
        "id": 123456,
        "telegram_id": 123456,
        "username": "test_user",
        "first_name": "Test",
        "last_name": "User",
        "mode": "assistant",
    }


@pytest.fixture
def mock_message():
    """Mock message data for tests."""
    return {
        "text": "Hello, how are you?",
        "message_id": 1,
        "chat_id": 123456,
    }