import pytest
from bezoekersparkeren.client import ParkeerClient
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_register_visitor(mock_page, config):
    client = ParkeerClient(config)
    client.page = mock_page
    
    # Mock browser init since we are injecting page directly
    client.browser = AsyncMock()
    client._playwright = AsyncMock()

    await client.register_visitor("AB-123-CD")
    
    # Updated expectations based on new implementation
    mock_page.goto.assert_called()
    mock_page.click.assert_any_call('button.license-plate-add', timeout=5000)
    mock_page.click.assert_any_call('button.next-step', timeout=5000)
    mock_page.click.assert_any_call('button.confirmAction', timeout=5000)
    mock_page.fill.assert_any_call('input[name="number"]', "AB-123-CD")

@pytest.mark.asyncio
async def test_login(mock_page, config):
    client = ParkeerClient(config)
    client.page = mock_page
    
    # Mock browser init
    client.browser = AsyncMock()
    client._playwright = AsyncMock()
    
    mock_page.query_selector.side_effect = ["Afmelden"]
    success = await client.login()
    
    assert success is True
    mock_page.goto.assert_called_with(f"https://bezoek.parkeer.nl/{config.municipality}/login")
    mock_page.fill.assert_any_call('input#username', config.credentials.email)
