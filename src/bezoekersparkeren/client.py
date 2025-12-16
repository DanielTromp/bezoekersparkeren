import asyncio
import logging
from typing import List, Optional
from datetime import datetime, timedelta

from playwright.async_api import async_playwright, Page, Browser, Playwright
from bs4 import BeautifulSoup
from .config import Config
from .models import ParkingSession, Balance

logger = logging.getLogger(__name__)

class ParkeerClient:
    def __init__(self, config: Config = None):
        self.config = config or Config.load()
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self._playwright: Optional[Playwright] = None
    
    async def __aenter__(self):
        await self._init_browser()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def _init_browser(self):
        self._playwright = await async_playwright().start()
        self.browser = await self._playwright.chromium.launch(
            headless=self.config.browser.headless,
            slow_mo=self.config.browser.slow_mo,
        )
        self.page = await self.browser.new_page()
        self.page.set_default_timeout(self.config.browser.timeout)
    
    async def login(self) -> bool:
        """Login to bezoek.parkeer.nl"""
        # Go directly to login page
        base_url = f"https://bezoek.parkeer.nl/{self.config.municipality}/login"
        logger.info(f"Navigating to {base_url}")
        
        # Navigate to start page
        await self.page.goto(base_url)

        # Wait for login form
        logger.info("Waiting for login form")
        await self.page.wait_for_selector('input#username')
        
        # Fill credentials
        logger.info("Filling credentials")
        await self.page.fill('input#username', self.config.credentials.email)
        await self.page.fill('input#password', self.config.credentials.password)
        
        # Submit login
        await self.page.click('button#_submit')
        
        # Wait for dashboard/main page
        # Wait for URL to contain 'app' which implies we are inside the application
        try:
            await self.page.wait_for_url('**/app/**', timeout=15000)
        except Exception as e:
            logger.warning(f"Timeout waiting for URL change after login: {e}")
            
            # Check for error messages
            error_element = await self.page.query_selector('div.notification, .alert-danger, .error-message')
            if error_element:
                error_text = await error_element.text_content()
                logger.error(f"Login failed with message: {error_text.strip()}")
                return False

        await self.page.wait_for_load_state('networkidle')
        
        # Verify login success
        # Check for common post-login elements
        if await self.page.query_selector('text="Afmelden"') or \
           await self.page.query_selector('text="Uitloggen"') or \
           await self.page.query_selector('.user-menu') or \
           "app" in self.page.url:
             logger.info("Login successful")
             return True
        
        # Final check for errors if verification failed but no timeout occurred (e.g. immediate reload)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = f"login_failed_{timestamp}.png"
        
        # Try to capture error message
        error_element = await self.page.query_selector('div.notification, .alert-danger, .error-message, .validation-summary-errors, [role="alert"]')
        if error_element:
            error_text = await error_element.text_content()
            logger.error(f"Login failed with message: {error_text.strip()}")
            await self.page.screenshot(path=screenshot_path)
            logger.info(f"Screenshot saved to {screenshot_path}")
            return False
            
        logger.warning(f"Login verification failed. Current URL: {self.page.url}")
        logger.warning("Saving screenshot for debugging...")
        await self.page.screenshot(path=screenshot_path)
        logger.info(f"Screenshot saved to {screenshot_path}")
        
        # Dump page text to help identify the error
        try:
            body_text = await self.page.text_content('body')
            # Log first 500 chars of body text cleaned up
            clean_text = ' '.join(body_text.split())[:500]
            logger.info(f"Page content preview: {clean_text}...")
        except Exception:
            pass
            
        return False
    
    async def register_visitor(self, plate: str, 
                             start_date: str = None, start_time: str = None,
                             end_date: str = None, end_time: str = None,
                             minutes: int = None, hours: int = None) -> ParkingSession:
        """
        Register a visitor's license plate for parking.
        Supports immediate start or planned dates.
        """
        logger.info(f"Registering visitor: {plate}")
        
        try:
            # Navigate directly to the new visitor page to avoid selector issues on dashboard
            target_url = f"https://bezoek.parkeer.nl/{self.config.municipality}/app/park/new"
            logger.info(f"Navigating directly to {target_url}")
            await self.page.goto(target_url)
            await self.page.wait_for_load_state('networkidle')
            
            # Click the "Nieuw kenteken" button to open the form/modal
            # User reported seeing a green button with text "NIEUW KENTEKEN"
            logger.info("Clicking 'NIEUW KENTEKEN' button...")
            try:
                # Try specific class first (from user), then text
                await self.page.click('button.add-license-plate, button:has-text("Nieuw kenteken"), button:has-text("NIEUW KENTEKEN")', timeout=5000)
            except Exception:
                logger.warning("Could not click 'Nieuw Kenteken' button, assuming form might be open...")

            # Enter license plate
            # Wait for input to be visible first
            logger.info("Waiting for license plate input...")
            # User provided HTML shows name="number"
            await self.page.wait_for_selector('input[name="number"]', timeout=10000)
            await self.page.fill('input[name="number"]', plate)
            
            # Wait for vehicle verification
            # User says system checks plate and shows car brand in div.auto-brand
            logger.info("Waiting for vehicle verification...")
            try:
                await self.page.wait_for_selector('.auto-brand', timeout=10000)
                # Wait a bit for text to populate if it's async
                await asyncio.sleep(1) 
                brand_element = await self.page.query_selector('.auto-brand')
                brand_text = await brand_element.text_content()
                brand_text = brand_text.strip()
                logger.info(f"Vehicle identified: {brand_text}")
                
                if "Buitenlands" in brand_text or "onbekend" in brand_text:
                    logger.warning(f"Warning: License plate might be invalid/unknown: {brand_text}")
            except Exception as e:
                logger.warning(f"Could not verify vehicle brand: {e}")
            
            # Save license plate / "KENTEKEN AKKOORD"
            logger.info("Clicking 'KENTEKEN AKKOORD'...")
            await self.page.click('button.license-plate-add', timeout=5000)
            
            # Click "Volgende stap"
            logger.info("Clicking 'Volgende stap'...")
            await self.page.click('button.next-step', timeout=5000)
            
            # Application Logic: Setting Duration/End Time
            # Wait for the duration/confirmation page
            logger.info("Waiting for duration settings...")
            await self.page.wait_for_selector('input#end_time', timeout=10000)
            
            # Set Start Date/Time if provided
            if start_date:
                logger.info(f"Setting start date to {start_date}")
                await self.page.fill('input#start_date', start_date)
                await self.page.evaluate("document.getElementById('start_date').dispatchEvent(new Event('change'))")
            
            if start_time:
                logger.info(f"Setting start time to {start_time}")
                await self.page.fill('input#start_time', start_time)
                await self.page.evaluate("document.getElementById('start_time').dispatchEvent(new Event('change'))")
                
            # Set End Date if provided (default to start_date if not set but valid start_date exist? UI handles this usually)
            if end_date:
                logger.info(f"Setting end date to {end_date}")
                await self.page.fill('input#end_date', end_date)
                await self.page.evaluate("document.getElementById('end_date').dispatchEvent(new Event('change'))")
            
            # Handle End Time / Duration
            final_end_time = end_time
            
            if not final_end_time:
                if minutes:
                    # Calculate based on start time (or now if not provided)
                    # For simplicity, if we don't have python datetime objects passed, we rely on page logic or simple calculation
                    # Ideally main.py passed explicit times.
                    pass
                elif hours:
                    now = datetime.now()
                    if start_time and start_date:
                        # Complex parsing needed if we start from a future date
                        pass 
                    else:
                        dt = now + timedelta(hours=hours)
                        final_end_time = dt.strftime("%H:%M")
            
            if final_end_time:
                logger.info(f"Setting end time to {final_end_time}")
                await self.page.fill('input#end_time', final_end_time)
                await self.page.evaluate("document.getElementById('end_time').dispatchEvent(new Event('change'))")
            
            # Force update by clicking outside (blur inputs) to enable the button
            # User suggested clicking "Parkeerkosten"
            logger.info("Triggering update by clicking 'Parkeerkosten' to blur inputs...")
            try:
                await self.page.click('text="Parkeerkosten"', timeout=2000)
            except Exception:
                # Fallback if text not found, click body or safe area?
                # But user said Parkeerkosten exists.
                logger.warning("Could not click 'Parkeerkosten', attempting generic click on body to blur.")
                await self.page.click('body', Force=True)

            # Wait for price calculation/validation to update UI
            await asyncio.sleep(0.5)

            # Start parking action (Confirm)
            logger.info("Clicking 'Parkeeractie starten' (Confirm)...")
            await self.page.click('button.confirmAction', timeout=5000)
            
            # ... rest of success handling
            await self.page.wait_for_load_state('networkidle')
            
            return ParkingSession(plate=plate, active=True, start_time=datetime.now())
            
        except Exception as e:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = f"register_failed_{timestamp}.png"
            logger.error(f"Registration failed: {e}")
            logger.warning("Saving screenshot for debugging...")
            await self.page.screenshot(path=screenshot_path)
            logger.info(f"Screenshot saved to {screenshot_path}")
            
            # Dump page text
            try:
                body_text = await self.page.text_content('body')
                clean_text = ' '.join(body_text.split())[:1000]
                logger.info(f"Page content preview: {clean_text}...")
            except Exception:
                pass
            raise e

    async def stop_session(self, session: ParkingSession) -> bool:
        """Stop a parking session for a given session object"""
        logger.info(f"Stopping session for {session.plate} (ID: {session.id})")
        
        # Navigate to Active Sessions page if needed
        if not self.page.url or "app" not in self.page.url:
             await self.page.goto(f"https://bezoek.parkeer.nl/{self.config.municipality}/app/park")
             await self.page.wait_for_load_state('networkidle')
        
        # Get all session containers
        elements = await self.page.query_selector_all('.park-item-desktop')
        
        for element in elements:
            # Get HTML of this element AND its sibling if it looks like the start-time row
            # This ensures we match exactly the same way we listed them, covering the sibling structure
            html_data = await element.evaluate("""el => {
                let html = el.outerHTML;
                let sib = el.nextElementSibling;
                if (sib && sib.classList.contains('start-time')) {
                    html += sib.outerHTML;
                }
                return html;
            }""")
            
            # Parse it
            item_soup = BeautifulSoup(html_data, 'html.parser')
            
            # Find the root div in the fragment
            root = item_soup.find('div', class_='park-item-desktop')
            if not root:
                continue
                
            candidate_session = self._parse_single_session_from_soup(root)
            
            if candidate_session:
                 logger.debug(f"Checked candidate session: {candidate_session.id} (Plate: {candidate_session.plate})")
            
            if candidate_session and candidate_session.id == session.id:
                logger.info(f"Found matching session in DOM (ID: {candidate_session.id}), clicking stop...")
                
                # Find stop button within this specific element handle
                btn = await element.query_selector('button.stop-parking-action')
                if btn:
                    await btn.click()
                    
                    # Confirm dialog
                    try: 
                        await self.page.wait_for_selector('button.confirm-stop, button.btn-primary, button:has-text("Stoppen"), button:has-text("Ja")', timeout=2000)
                        await self.page.click('button.confirm-stop, button.btn-primary, button:has-text("Stoppen"), button:has-text("Ja")')
                    except Exception:
                        logger.warning("No confirmation dialog appeared or could not be clicked automatically.")
                    
                    return True
        
        logger.warning(f"Could not find session {session.id} in DOM to stop.")
        return False

    async def get_active_sessions(self) -> List[ParkingSession]:
        """Get list of active parking sessions"""
        logger.info("Fetching active sessions")
        
        # Ensure we are logged in and on a page with session info
        # If we are not on a page that likely has the info, go to the main app page
        if not self.page.url or "app" not in self.page.url:
             await self.page.goto(f"https://bezoek.parkeer.nl/{self.config.municipality}/app/park")
             await self.page.wait_for_load_state('networkidle')

        content = await self.page.content()
        return self._parse_sessions_from_html(content)
        
    def _parse_sessions_from_html(self, html_content: str) -> List[ParkingSession]:
        """Parse parking sessions from HTML content"""
        soup = BeautifulSoup(html_content, 'html.parser')
        sessions = []
        
        # Find the desktop container for parking actions
        container = soup.find(id='parkActions')
        if not container:
            return []
            
        # Iterate over parking items
        items = container.find_all('div', class_='park-item-desktop')
        
        logging.debug(f"Found {len(items)} session items")

        for item in items:
            session = self._parse_single_session_from_soup(item)
            if session:
                sessions.append(session)
                
        return sessions

    def _parse_single_session_from_soup(self, item) -> Optional[ParkingSession]:
        """Helper to parse a single session from a BeautifulSoup tag"""
        try:
            # Extract license plate
            plate_elem = item.find('span', class_='plate')
            if not plate_elem:
                return None
            plate = plate_elem.get_text(strip=True)
            
            # --- Helper for parsing times ---
            def parse_time_element(element):
                """Parses text from a time element into a datetime object"""
                if not element:
                    return None
                    
                # Use get_text() with separator to handle nested spans cleaner
                full_text = element.get_text(" ", strip=True)
                full_str = full_text.lower()
                
                # Remove known labels to clean up string
                for label in ['eindtijd', 'start tijd', 'start actie', 'deze actie start', 'verstreken', 'product']:
                    full_str = full_str.replace(label, "")
                
                # Logic for "morgen", "vandaag", "18 dec."
                now = datetime.now()
                today = now.date()
                target_date = today
                
                # Date parsing
                if "morgen" in full_str:
                    target_date = today + timedelta(days=1)
                    full_str = full_str.replace("morgen", "").strip()
                elif "vandaag" in full_str:
                    target_date = today
                    full_str = full_str.replace("vandaag", "").strip()
                elif any(m in full_str for m in ['jan', 'feb', 'mrt', 'apr', 'mei', 'jun', 'jul', 'aug', 'sep', 'okt', 'nov', 'dec']):
                    months = {
                        'jan': 1, 'feb': 2, 'mrt': 3, 'apr': 4, 'mei': 5, 'jun': 6,
                        'jul': 7, 'aug': 8, 'sep': 9, 'okt': 10, 'nov': 11, 'dec': 12
                    }
                    
                    import re
                    date_match = re.search(r'(\d{1,2})\s+([a-z]{3})', full_str)
                    if date_match:
                        day = int(date_match.group(1))
                        month_str = date_match.group(2)
                        month = months.get(month_str)
                        if month:
                            year = now.year
                            if now.month == 12 and month == 1:
                                year += 1
                            target_date = datetime(year, month, day).date()
                            full_str = full_str.replace(date_match.group(0), "").replace(".", "").strip()

                # Time parsing (HH:MM)
                import re
                time_match = re.search(r'(\d{1,2}:\d{2})', full_str)
                parsed_dt = None
                
                if time_match:
                    time_str = time_match.group(1)
                    h, m = map(int, time_str.split(':'))
                    parsed_dt = datetime.combine(target_date, datetime.min.time().replace(hour=h, minute=m))
                
                return parsed_dt

            # --- Extract Start and End Times ---
            end_time_div = item.find('div', class_='end-time')
            end_time = parse_time_element(end_time_div)
            
            # Start time seems to be in a sibling div in some views
            start_time_div = item.find('div', class_='start-time')
            if not start_time_div:
                 # check sibling
                 start_time_div = item.find_next_sibling('div', class_='start-time')
            
            start_time = parse_time_element(start_time_div)
            
            # Fallback for start_time if not found (required for ID)
            if not start_time:
                start_time = datetime.now() # Should not verify happens if HTML is good

            # --- Generate Unique ID ---
            # Hash of plate + start_time
            import hashlib
            id_base = f"{plate}-{start_time.isoformat()}"
            session_id = hashlib.md5(id_base.encode()).hexdigest()[:8]

            return ParkingSession(
                id=session_id,
                plate=plate,
                active=True,
                start_time=start_time,
                end_time=end_time
            )
            
        except Exception as e:
            logger.error(f"Error parsing session item: {e}")
            return None

    async def get_balance(self) -> Balance:
        """Get current balance"""
        logger.info("Fetching balance")
        
        # Explicitly navigate to the user page where balance is known to be visible
        user_page_url = f"https://bezoek.parkeer.nl/{self.config.municipality}/app/user"
        if self.page.url != user_page_url:
            logger.info(f"Navigating to {user_page_url}")
            await self.page.goto(user_page_url)
            await self.page.wait_for_load_state('networkidle')
        
        try:
            selector = 'input[name="balance"]'
            await self.page.wait_for_selector(selector, timeout=10000)
            value = await self.page.get_attribute(selector, 'value')
            
            if value:
                # Parse "€ 19,10" -> 19.10
                amount_str = value.replace('€', '').replace(',', '.').strip()
                return Balance(amount=float(amount_str))
                
        except Exception as e:
            logger.error(f"Failed to get balance: {e}. Current URL: {self.page.url}")
            
        return Balance(amount=0.0)
    
    async def close(self):
        if self.browser:
            await self.browser.close()
        if self._playwright:
            await self._playwright.stop()
