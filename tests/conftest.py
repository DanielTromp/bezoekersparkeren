import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_page():
    page = AsyncMock()
    page.goto = AsyncMock()
    page.click = AsyncMock()
    page.fill = AsyncMock()
    page.wait_for_selector = AsyncMock()
    page.wait_for_load_state = AsyncMock()
    page.query_selector = AsyncMock(return_value=True) # Mock successful login check
    return page

@pytest.fixture
def config():
    from bezoekersparkeren.config import Config, Credentials, BrowserConfig
    return Config(
        municipality="almere",
        credentials=Credentials(email="test@test.nl", password="test123"),
        browser=BrowserConfig(headless=True)
    )
