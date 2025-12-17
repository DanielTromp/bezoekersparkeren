import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, User, Message, Chat
from telegram.ext import ContextTypes

@pytest.fixture
def mock_update():
    update = MagicMock(spec=Update)
    user = MagicMock(spec=User)
    user.id = 123456789
    user.username = "testuser"
    user.full_name = "Test User"
    
    update.effective_user = user
    update.message = MagicMock(spec=Message)
    update.message.reply_text = AsyncMock()
    update.message.text = "test message"
    
    return update

@pytest.fixture
def mock_context():
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.user_data = {}
    return context

@pytest.mark.asyncio
async def test_authorized_only_middleware(mock_update, mock_context):
    from bezoekersparkeren.bot.middleware import authorized_only
    
    allowed_users = [123456789]
    
    @authorized_only(allowed_users)
    async def handler(update, context):
        return "success"
    
    # Test authorized
    result = await handler(mock_update, mock_context)
    assert result == "success"
    
    # Test unauthorized
    mock_update.effective_user.id = 999999999
    result = await handler(mock_update, mock_context)
    assert result is None
    mock_update.message.reply_text.assert_called_once()
    args, _ = mock_update.message.reply_text.call_args
    assert "niet geautoriseerd" in args[0].lower()

@pytest.mark.asyncio
async def test_auth_filter():
    from bezoekersparkeren.bot.middleware import AuthFilter
    
    filter_obj = AuthFilter([123, 456])
    
    update_auth = MagicMock(spec=Update)
    update_auth.effective_user.id = 123
    assert filter_obj(update_auth) is True
    
    update_unauth = MagicMock(spec=Update)
    update_unauth.effective_user.id = 789
    assert filter_obj(update_unauth) is False

@pytest.mark.asyncio
async def test_bot_initialization():
    from bezoekersparkeren.config import Config, TelegramConfig, Credentials
    from bezoekersparkeren.bot.telegram_bot import ParkeerBot
    
    config = Config(
        credentials=Credentials(email="test", password="test"),
        telegram=TelegramConfig(
            bot_token="test_token",
            allowed_users="123,456"
        )
    )
    
    bot = ParkeerBot(config)
    assert bot.allowed_users == [123, 456]
    assert bot.config.telegram.bot_token == "test_token"
