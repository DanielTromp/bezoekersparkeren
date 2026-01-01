from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from telegram import Update, CallbackQuery, Message
from telegram.ext import ContextTypes
from bezoekersparkeren.bot.handlers import button_callback
from bezoekersparkeren.models import ParkingSession
from datetime import datetime, timedelta

@pytest.fixture
def mock_client():
    client = AsyncMock()
    # Mock multiple active sessions for the same plate
    s1 = ParkingSession(id="s1", plate="TEST-PLATE", active=True, start_time=datetime.now())
    s2 = ParkingSession(id="s2", plate="TEST-PLATE", active=True, start_time=datetime.now() + timedelta(days=1))
    client.get_active_sessions.return_value = [s1, s2]
    client.stop_session.return_value = True
    client.register_multiple_days.return_value = [s1]
    return client

@pytest.fixture
def mock_update():
    update = MagicMock(spec=Update)
    query = MagicMock(spec=CallbackQuery)
    query.message = MagicMock(spec=Message)
    query.edit_message_text = AsyncMock()
    query.answer = AsyncMock()
    update.callback_query = query
    update.effective_user = MagicMock()
    update.effective_user.id = 12345
    return update

@pytest.mark.asyncio
async def test_stop_all_sessions(mock_update, mock_client):
    mock_update.callback_query.data = "stop_TEST-PLATE"
    
    with patch('bezoekersparkeren.bot.handlers.get_client', new=AsyncMock(return_value=mock_client)):
        await button_callback(mock_update, MagicMock())
        
        # Verify get_active_sessions was called
        mock_client.get_active_sessions.assert_called_once()
        
        # Verify stop_session was called TWICE
        assert mock_client.stop_session.call_count == 2
        
        # Verify the message confirmed multiple stops
        mock_update.callback_query.edit_message_text.assert_called_with(
            "✅ 2 sessie(s) voor `TEST-PLATE` zijn gestopt!",
            parse_mode="Markdown"
        )

@pytest.mark.asyncio
async def test_register_plate_shows_menu(mock_update, mock_client):
    # Testing that register_PLATE now shows the "Now vs Multi" menu
    mock_update.callback_query.data = "register_TEST-PLATE"
    
    with patch('bezoekersparkeren.bot.handlers.get_client', new=AsyncMock(return_value=mock_client)):
        await button_callback(mock_update, MagicMock())
        
        # Verify it shows the menu
        args, kwargs = mock_update.callback_query.edit_message_text.call_args
        assert "Wat wil je doen?" in args[0]
        assert "Direct starten" in str(kwargs['reply_markup'])
        assert "Meerdaags" in str(kwargs['reply_markup'])

@pytest.mark.asyncio
async def test_register_now_success_message(mock_update, mock_client):
    mock_update.callback_query.data = "register_now_TEST-PLATE"
    
    # Mock session with end time
    session = ParkingSession(
        id="s1", 
        plate="TEST-PLATE", 
        active=True, 
        start_time=datetime.now(),
        end_time=datetime.now().replace(hour=23, minute=59)
    )
    mock_client.register_multiple_days.return_value = [session]
    
    with patch('bezoekersparkeren.bot.handlers.get_client', new=AsyncMock(return_value=mock_client)):
        await button_callback(mock_update, MagicMock())
        
        # Verify success message format
        args, kwargs = mock_update.callback_query.edit_message_text.call_args
        assert "✅ *Kenteken aangemeld!*" in args[0]
        assert "⏰ Gepland tot: 23:59, of meld je eerder af." in args[0]
