from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext, Playwright
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

class BrowserManager:
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
    
    def __enter__(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=self.headless,
            args=['--disable-blink-features=AutomationControlled']
        )
        self.context = self.browser.new_context(
            viewport={'width': 1280, 'height': 720},
            device_scale_factor=1.0,
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        self.page = self.context.new_page()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.page:
            self.page.close()
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
    
    _NETWORK_RETRY_ERRORS = (
        "ERR_NETWORK_CHANGED", "ERR_CONNECTION_RESET", "ERR_CONNECTION_REFUSED",
        "ERR_INTERNET_DISCONNECTED", "ERR_NAME_NOT_RESOLVED", "NS_BINDING_ABORTED"
    )

    def navigate(self, url: str, wait_timeout: int = 30000, retries: int = 5):
        for attempt in range(retries):
            try:
                self.page.goto(url, wait_until='networkidle', timeout=wait_timeout)
                time.sleep(2)
                return
            except Exception as e:
                err_str = str(e)
                if attempt < retries - 1 and any(x in err_str for x in self._NETWORK_RETRY_ERRORS):
                    wait = (attempt + 1) * 10
                    logger.warning(f"Navigation failed ({err_str[:80]}...), retry in {wait}s ({attempt + 1}/{retries})")
                    time.sleep(wait)
                else:
                    raise
    
    def wait_for_captcha(self, timeout: int = 30):
        logger.info("Checking for CAPTCHA...")
        try:
            captcha_selectors = [
                'iframe[src*="recaptcha"]',
                'iframe[src*="captcha"]',
                '.g-recaptcha',
                '#captcha',
                '[id*="captcha"]'
            ]
            
            for selector in captcha_selectors:
                element = self.page.query_selector(selector)
                if element:
                    logger.warning(f"CAPTCHA detected with selector: {selector}")
                    logger.warning("Please complete CAPTCHA manually. Waiting 60 seconds...")
                    time.sleep(60)
                    return True
        except Exception as e:
            logger.debug(f"Error checking CAPTCHA: {e}")
        return False
    
    def wait_for_element(self, selector: str, timeout: int = 10000):
        try:
            self.page.wait_for_selector(selector, timeout=timeout)
            return True
        except:
            return False
    
    def wait_for_api_response(self, url_pattern: str, timeout: int = 10000):
        """Wait for a specific API call to complete"""
        try:
            with self.page.expect_response(
                lambda response: url_pattern in response.url,
                timeout=timeout
            ) as response_info:
                response = response_info.value
                logger.info(f"API response received: {response.url} - Status: {response.status}")
                return response
        except Exception as e:
            logger.debug(f"Timeout waiting for API response: {e}")
            return None

