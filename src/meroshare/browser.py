from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext, Playwright  # type: ignore
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
        try:
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
        except Exception as e:
            logger.error(f"Browser launch failed: {e}")
            self.__exit__(None, None, None)
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.page:
            try:
                self.page.close()
            except Exception as e:
                logger.warning("Error closing page: %s", e)
        if self.context:
            try:
                self.context.close()
            except Exception as e:
                logger.warning("Error closing context: %s", e)
        if self.browser:
            try:
                self.browser.close()
            except Exception as e:
                logger.warning("Error closing browser: %s", e)
        if self.playwright:
            try:
                self.playwright.stop()
            except Exception as e:
                logger.warning("Error stopping playwright: %s", e)
        return False
    
    _NETWORK_RETRY_ERRORS = (
        "ERR_NETWORK_CHANGED", "ERR_CONNECTION_RESET", "ERR_CONNECTION_REFUSED",
        "ERR_INTERNET_DISCONNECTED", "ERR_NAME_NOT_RESOLVED", "NS_BINDING_ABORTED"
    )

    def navigate(self, url: str, wait_timeout: int = 30000, retries: int = 5) -> bool:
        if not self.page:
            logger.warning("navigate called but no page available")
            return False
        for attempt in range(retries):
            try:
                self.page.goto(url, wait_until='networkidle', timeout=wait_timeout)
                time.sleep(2)
                return True
            except Exception as e:
                err_str = str(e)
                if attempt < retries - 1 and any(x in err_str for x in self._NETWORK_RETRY_ERRORS):
                    wait = (attempt + 1) * 10
                    logger.warning(f"Navigation failed ({err_str[:80]}...), retry in {wait}s ({attempt + 1}/{retries})")
                    time.sleep(wait)
                else:
                    raise
        return False

    def wait_for_captcha(self, timeout: int = 30) -> bool:
        if not self.page:
            return False
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
                    wait_sec = min(60, max(10, timeout))
                    logger.warning("Please complete CAPTCHA manually. Waiting %s seconds...", wait_sec)
                    time.sleep(wait_sec)
                    return True
        except Exception as e:
            logger.debug(f"Error checking CAPTCHA: {e}")
        return False
    
    def wait_for_element(self, selector: str, timeout: int = 10000):
        if not self.page:
            return False
        try:
            self.page.wait_for_selector(selector, timeout=timeout)
            return True
        except Exception:
            return False
    
    def wait_for_api_response(self, url_pattern: str, timeout: int = 10000):
        page = self.page
        if not page:
            return None
        try:
            with page.expect_response(
                lambda response: url_pattern in response.url,
                timeout=timeout
            ) as response_info:
                response = response_info.value
                logger.info(f"API response received: {response.url} - Status: {response.status}")
                return response
        except Exception as e:
            logger.debug(f"Timeout waiting for API response: {e}")
            return None

