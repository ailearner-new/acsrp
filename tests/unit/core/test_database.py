"""Tests for database configuration."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.app.core.config import Settings
from backend.app.core.database import DatabaseManager, db_manager


@pytest.mark.unit
def test_database_manager_init():
    """Test DatabaseManager initialization."""
    manager = DatabaseManager()
    assert manager._engine is None
    assert manager._session_factory is None


@pytest.mark.unit
def test_database_manager_engine_property():
    """Test engine property creates engine on first access."""
    with patch('backend.app.core.database.create_async_engine') as mock_create:
        mock_engine = AsyncMock()
        mock_create.return_value = mock_engine

        manager = DatabaseManager()
        engine = manager.engine

        assert engine is mock_engine
        mock_create.assert_called_once()


@pytest.mark.unit
def test_database_manager_session_factory():
    """Test session factory property."""
    with patch('backend.app.core.database.create_async_engine') as mock_create:
        mock_engine = AsyncMock()
        mock_create.return_value = mock_engine

        manager = DatabaseManager()
        factory = manager.session_factory

        assert factory is not None
        # Second call should return cached factory
        factory2 = manager.session_factory
        assert factory is factory2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_database_manager_session_context():
    """Test session context manager."""
    with patch('backend.app.core.database.create_async_engine') as mock_create:
        mock_engine = AsyncMock()
        mock_create.return_value = mock_engine

        mock_session = AsyncMock()
        mock_session_factory = MagicMock(return_value=mock_session)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        manager = DatabaseManager()
        manager._engine = mock_engine
        manager._session_factory = mock_session_factory

        async with manager.session() as session:
            assert session is mock_session

        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_database_manager_session_rollback():
    """Test session rollback on exception."""
    with patch('backend.app.core.database.create_async_engine') as mock_create:
        mock_engine = AsyncMock()
        mock_create.return_value = mock_engine

        mock_session = AsyncMock()
        mock_session_factory = MagicMock(return_value=mock_session)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        manager = DatabaseManager()
        manager._engine = mock_engine
        manager._session_factory = mock_session_factory

        try:
            async with manager.session() as session:
                raise ValueError("Test error")
        except ValueError:
            pass

        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()


@pytest.mark.unit
def test_global_db_manager():
    """Test global db_manager instance."""
    assert db_manager is not None
    assert isinstance(db_manager, DatabaseManager)