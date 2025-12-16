import pytest
from unittest.mock import AsyncMock
from bezoekersparkeren.client import ParkeerClient
async def test_get_balance(mock_page, config):
    client = ParkeerClient(config)
    client.page = mock_page
    client.browser = AsyncMock()
    client._playwright = AsyncMock()
    
    # Mock the balance input
    mock_page.get_attribute.return_value = "€ 19,10"
    
    balance = await client.get_balance()
    
    mock_page.wait_for_selector.assert_called_with('input[name="balance"]', timeout=10000)
    assert balance.amount == 19.10
    assert balance.currency == "EUR"

@pytest.mark.asyncio
async def test_login_failure(mock_page, config):
    client = ParkeerClient(config)
    client.page = mock_page
    client.browser = AsyncMock()
    client._playwright = AsyncMock()
    
    # Simulate timeout on URL wait
    mock_page.wait_for_url.side_effect = Exception("Timeout")
    
    # Simulate finding the error element
    mock_error_element = AsyncMock()
    mock_error_element.text_content.return_value = "Gebruikersnaam onbekend"
    mock_page.query_selector.return_value = mock_error_element
    
    success = await client.login()
    
    assert success is False
    mock_page.query_selector.assert_called_with('div.notification, .alert-danger, .error-message')
