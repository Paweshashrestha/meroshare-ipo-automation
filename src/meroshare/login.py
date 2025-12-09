from src.meroshare.browser import BrowserManager
from src.config import Config
import logging
import time


logger = logging.getLogger(__name__)


class MeroShareLogin:
    def __init__(self, browser: BrowserManager, config: Config):
        self.browser = browser
        self.config = config
        self.meroshare_config = config.get_meroshare()

    def _select_dp_option(self, dp_field, dp_name: str):
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

    def _setup_ajax_interceptors(self, client_id: str):
        """Set up AJAX interceptors to inject clientId into network requests."""
        self.browser.page.evaluate(
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
        """Perform login to MeroShare."""
        try:
            logger.info("Navigating to MeroShare login page...")
            self.browser.navigate("https://meroshare.cdsc.com.np/#/login")
            time.sleep(2)

            if self.browser.wait_for_captcha():
                logger.warning("CAPTCHA detected. Please complete manually.")
                return False

            username = self.meroshare_config.get("username")
            password = self.meroshare_config.get("password")
            dp_name = self.meroshare_config.get("dp_name")

            if not all([username, password, dp_name]):
                logger.error("Missing required credentials in config")
                return False

            logger.info("Filling login credentials...")

            username_field = self.browser.page.query_selector(
                'input[name*="username" i]'
            )
            password_field = self.browser.page.query_selector('input[type="password"]')
            dp_field = self.browser.page.query_selector("select")

            if not all([username_field, password_field, dp_field]):
                logger.error("Required form fields not found")
                return False

            username_field.fill(username)
            password_field.fill(password)
            time.sleep(0.5)

            _, extracted_client_id = self._select_dp_option(dp_field, dp_name)

            if not extracted_client_id:
                logger.error("Could not extract client_id from DP option")
                return False

            client_id = str(extracted_client_id)

            if not client_id or client_id == "0":
                logger.error(f"clientId is invalid: {client_id}")
                return False

            logger.info(f"Using extracted client_id: {client_id}")

            self._setup_ajax_interceptors(client_id)

            time.sleep(1)

            login_button = self.browser.page.query_selector(
                'button[type="submit"], button:has-text("Login"), button:has-text("LOGIN")'
            )
            if not login_button:
                logger.error("Login button not found")
                return False

            logger.info("Clicking login button...")
            login_button.click()
            time.sleep(5)

            current_url = self.browser.page.url.lower()
            page_text = self.browser.page.inner_text("body").lower()

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
                error_elem = self.browser.page.query_selector(
                    '.error, .alert-danger, [class*="error"]'
                )
                if error_elem:
                    logger.error(f"Login failed: {error_elem.inner_text()[:100]}")
                return False

            if "login" not in current_url or any(
                ind in current_url or ind in page_text
                for ind in ["dashboard", "home", "portfolio", "asba"]
            ):
                logger.info("Login successful!")
                return True

            logger.warning("Login status unclear")
            return False

        except Exception as e:
            logger.error(f"Login error: {e}", exc_info=True)
            return False
