from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from telegram import Update, CallbackQuery, Message
from telegram.ext import ContextTypes
import bezoekersparkeren.bot.handlers as handlers
from bezoekersparkeren.bot.handlers import button_callback, quick_stop
from bezoekersparkeren.models import ParkingSession

@pytest.fixture
def mock_client():
    client = AsyncMock()
    # Mock active sessions
    session = ParkingSession(
        id="12345",
        plate="TEST-PLATE",
        active=True
    )
    client.get_active_sessions.return_value = [session]
    client.stop_session.return_value = True
    return client

@pytest.fixture
def mock_update_callback():
    update = MagicMock(spec=Update)
    query = MagicMock(spec=CallbackQuery)
    query.data = "stop_TEST-PLATE"
    query.message = MagicMock(spec=Message)
    query.edit_message_text = AsyncMock()
    query.answer = AsyncMock()
    update.callback_query = query
    return update

@pytest.fixture
def mock_update_command():
    update = MagicMock(spec=Update)
    update.message = MagicMock(spec=Message)
    update.message.reply_text = AsyncMock()
    return update

@pytest.fixture
def mock_context():
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = ["TEST-PLATE"]
    return context

@pytest.mark.asyncio
async def test_button_callback_stop(mock_update_callback, mock_context, mock_client):
    # Patch get_client to return our mock
    with patch('bezoekersparkeren.bot.handlers.get_client', new=AsyncMock(return_value=mock_client)):
        await button_callback(mock_update_callback, mock_context)
        
        # Verify get_active_sessions was called
        mock_client.get_active_sessions.assert_called_once()
        
        # Verify stop_session was called WITH A SESSION OBJECT, not a string
        mock_client.stop_session.assert_called_once()
        args, _ = mock_client.stop_session.call_args
        assert isinstance(args[0], ParkingSession)
        assert args[0].plate == "TEST-PLATE"

@pytest.mark.asyncio
async def test_quick_stop(mock_update_command, mock_context, mock_client):
    # Patch get_client
    with patch('bezoekersparkeren.bot.handlers.get_client', new=AsyncMock(return_value=mock_client)):
        await quick_stop(mock_update_command, mock_context)
        
        # Verify get_active_sessions was called
        mock_client.get_active_sessions.assert_called_once()
        
        # Verify stop_session was called WITH A SESSION OBJECT
        mock_client.stop_session.assert_called_once()
        args, _ = mock_client.stop_session.call_args
        assert isinstance(args[0], ParkingSession)
        assert args[0].plate == "TEST-PLATE"
