from typing import Optional

from src.meroshare.browser import BrowserManager
from src.config import Config
import logging
import time

logger = logging.getLogger(__name__)

LOGIN_URL = "https://meroshare.cdsc.com.np/#/login"
LOGIN_FORM_WAIT_TIMEOUT_MS = 15000
CAPTCHA_WAIT_TIMEOUT_SEC = 30
POST_LOGIN_WAIT_SEC = 5


class MeroShareLogin:
    def __init__(self, browser: BrowserManager, config: Config):
        self.browser = browser
        self.config = config
        self.meroshare_config = config.get_meroshare()
        self.last_error: str = ""

    def _select_dp_option(self, dp_field, dp_name: Optional[str]):
        """Select DP option and extract clientId."""
        if not dp_name:
            logger.warning("No dp_name provided for DP selection")
            return None, None

        dp_name_upper = dp_name.upper()
        for option in dp_field.query_selector_all("option"):
            option_text = option.inner_text().strip().upper()
            if dp_name_upper in option_text:
                option_value = option.get_attribute("value")
                logger.info(f"Found DP option: {option_text}, value: {option_value}")

                client_id = (
                    option_value if option_value and option_value.isdigit() else None
                )

                logger.info(f"Extracted client_id: {client_id} (from value)")

                try:
                    dp_field.select_option(value=option_value, force=True)
                    time.sleep(1)
                    return option_value, client_id
                except Exception as e:
                    logger.error(f"Error selecting DP option: {e}")
                    return None, None

        logger.warning(f"Could not find DP option matching: {dp_name}")
        return None, None

    def _setup_ajax_interceptors(self, client_id: str) -> None:
        """Set up AJAX interceptors to inject clientId into network requests."""
        page = self.browser.page
        if not page:
            return
        page.evaluate(
            f"""
            (function() {{
                var cid = {client_id};
                var isLoginReq = function(url, method) {{
                    return method === 'POST' && (url.includes('/login') || url.includes('/auth') || url.includes('meroshare'));
                }};
                var injectClientId = function(body) {{
                    try {{
                        var data = typeof body === 'string' ? JSON.parse(body) : body;
                        data.clientId = cid;
                        return JSON.stringify(data);
                    }} catch(e) {{ return body; }}
                }};
                var origFetch = window.fetch;
                window.fetch = function(url, opts) {{
                    if (isLoginReq(url, (opts || {{}}).method)) {{
                        if (opts && opts.body) opts.body = injectClientId(opts.body);
                    }}
                    return origFetch.apply(this, arguments);
                }};
                var origOpen = XMLHttpRequest.prototype.open;
                var origSend = XMLHttpRequest.prototype.send;
                XMLHttpRequest.prototype.open = function(method, url) {{
                    this._method = method;
                    this._url = url;
                    return origOpen.apply(this, arguments);
                }};
                XMLHttpRequest.prototype.send = function(data) {{
                    if (isLoginReq(this._url, this._method) && data) {{
                        data = injectClientId(data);
                    }}
                    return origSend.apply(this, [data]);
                }};
            }})();
        """
        )

    def login(self) -> bool:
        """Perform login to MeroShare. Returns True on success, sets self.last_error on failure."""
        try:
            logger.info("Navigating to MeroShare login page...")
            self.browser.navigate(LOGIN_URL)
            time.sleep(2)
            page = self.browser.page
            if not page:
                self.last_error = "No browser page"
                return False
            if not self.browser.wait_for_element('input[type="password"]', timeout=LOGIN_FORM_WAIT_TIMEOUT_MS):
                self.last_error = "Login form did not load in time"
                return False

            if self.browser.wait_for_captcha():
                self.last_error = "CAPTCHA detected"
                return False

            username = self.meroshare_config.get("username")
            password = self.meroshare_config.get("password")
            dp_name = self.meroshare_config.get("dp_name")

            if not all([username, password, dp_name]):
                self.last_error = "Missing credentials in config"
                return False

            logger.info("Filling login credentials...")

            username_field = page.query_selector(
                'input[name*="username" i]'
            )
            password_field = page.query_selector('input[type="password"]')
            dp_field = page.query_selector("select")

            if not all([username_field, password_field, dp_field]):
                self.last_error = "Login form fields not found"
                return False

            username_field.fill("")
            time.sleep(0.3)
            username_field.fill(username)
            password_field.fill("")
            time.sleep(0.3)
            password_field.fill(password)
            time.sleep(0.5)

            _, extracted_client_id = self._select_dp_option(dp_field, dp_name)

            if not extracted_client_id:
                self.last_error = "Could not select DP option"
                return False

            client_id = str(extracted_client_id)

            if not client_id or client_id == "0":
                self.last_error = "Invalid clientId"
                return False

            logger.info(f"Using extracted client_id: {client_id}")

            self._setup_ajax_interceptors(client_id)

            time.sleep(1)

            login_button = page.query_selector(
                'button[type="submit"], button:has-text("Login"), button:has-text("LOGIN")'
            )
            if not login_button:
                self.last_error = "Login button not found"
                return False

            logger.info("Clicking login button...")
            login_button.click()
            time.sleep(POST_LOGIN_WAIT_SEC)

            current_url = page.url.lower()
            page_text = page.inner_text("body").lower()

            if any(
                err in page_text
                for err in [
                    "incorrect",
                    "invalid",
                    "wrong",
                    "error",
                    "failed",
                    "unauthorized",
                ]
            ):
                error_elem = page.query_selector(
                    '.error, .alert-danger, [class*="error"]'
                )
                if error_elem:
                    self.last_error = error_elem.inner_text()[:150].strip()
                    logger.error(f"Login failed: {self.last_error}")
                else:
                    self.last_error = "Login failed (error on page)"
                return False

            if "login" not in current_url or any(
                ind in current_url or ind in page_text
                for ind in ["dashboard", "home", "portfolio", "asba"]
            ):
                logger.info("Login successful!")
                return True

            self.last_error = "Login status unclear (still on login page?)"
            return False

        except Exception as e:
            self.last_error = str(e)[:150]
            logger.error("Login error: %s", e, exc_info=True)
            return False
